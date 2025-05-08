from datetime import datetime
from app import db
from app.models.feedback import QuizFeedback

# Association table for user bookmarks
user_bookmarks = db.Table('user_bookmarks',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('quiz_id', db.Integer, db.ForeignKey('quizzes.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=True)
    password = db.Column(db.String(128))
    time_limit = db.Column(db.Integer)  # in minutes
    max_attempts = db.Column(db.Integer, default=1)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    category = db.Column(db.String(50))
    grades_released = db.Column(db.Boolean, default=False)
    
    # Relationships
    author = db.relationship('User', back_populates='quizzes')
    questions = db.relationship('Question', back_populates='quiz', cascade='all, delete-orphan')
    attempts = db.relationship('QuizAttempt', back_populates='quiz', cascade='all, delete-orphan')
    shared_with_users = db.relationship('User', secondary='shared_quizzes', back_populates='shared_quizzes', lazy='dynamic', overlaps="shared_quizzes_list,shared_with")
    feedback = db.relationship(QuizFeedback, backref='quiz', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Quiz {self.title}>'

class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default='mcq')  # mcq or descriptive
    points = db.Column(db.Integer, default=1)
    order = db.Column(db.Integer)
    
    # Relationships
    quiz = db.relationship('Quiz', back_populates='questions')
    options = db.relationship('QuestionOption', back_populates='question', lazy='dynamic', cascade='all, delete-orphan')
    answers = db.relationship('Answer', back_populates='question', lazy='dynamic')

    def __repr__(self):
        return f'<Question {self.id}>'

class QuestionOption(db.Model):
    __tablename__ = 'question_options'
    
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer)
    
    # Relationships
    question = db.relationship('Question', back_populates='options')

    def __repr__(self):
        return f'<QuestionOption {self.id}>'

class Answer(db.Model):
    __tablename__ = 'answers'
    
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('quiz_attempts.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey('question_options.id'))
    text_answer = db.Column(db.Text)  # For descriptive questions
    is_correct = db.Column(db.Boolean)
    points_earned = db.Column(db.Float)
    feedback = db.Column(db.Text)  # Teacher's feedback for descriptive answers
    
    # Relationships
    attempt = db.relationship('QuizAttempt', back_populates='answers')
    question = db.relationship('Question', back_populates='answers')
    selected_option = db.relationship('QuestionOption')

    def __repr__(self):
        return f'<Answer {self.id}>'

class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    completed = db.Column(db.Boolean, default=False)
    score = db.Column(db.Float)
    max_score = db.Column(db.Float)
    
    # Relationships
    quiz = db.relationship('Quiz', back_populates='attempts')
    student = db.relationship('User', back_populates='quiz_attempts', overlaps="attempts,user")
    answers = db.relationship('Answer', back_populates='attempt', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<QuizAttempt {self.id}>'
    
    @property
    def percentage_score(self):
        if self.max_score and self.max_score > 0:
            return (self.score / self.max_score) * 100
        return 0 