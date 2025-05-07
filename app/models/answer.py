from app import db

class Answer(db.Model):
    __tablename__ = 'answers'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('quiz_attempts.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey('question_options.id'))
    text_answer = db.Column(db.Text)
    score = db.Column(db.Float)  # For descriptive questions scored by teacher

    # Relationships
    question = db.relationship('Question', backref=db.backref('answers', lazy='dynamic'))
    selected_option = db.relationship('QuestionOption', backref=db.backref('answers', lazy='dynamic'))

    def __repr__(self):
        return f'<Answer {self.id}: Question {self.question_id} in Attempt {self.attempt_id}>' 