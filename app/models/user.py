from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login
from app.models.feedback import QuizFeedback

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='student')
    is_teacher = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile_picture = db.Column(db.String(200), default='default.jpg')
    bio = db.Column(db.Text)
    
    # Relationships
    quizzes = db.relationship('Quiz', back_populates='author', lazy='dynamic')
    quiz_attempts = db.relationship('QuizAttempt', back_populates='student', lazy='dynamic', overlaps="attempts,user")
    shared_quizzes = db.relationship('Quiz', secondary='shared_quizzes', back_populates='shared_with_users', lazy='dynamic', overlaps="shared_quizzes_list,shared_with_users")
    feedback = db.relationship(QuizFeedback, backref='student', lazy='dynamic')
    bookmarks = db.relationship('Bookmark', backref='user', lazy='dynamic')
    bookmarked_quizzes = db.relationship('Quiz', 
                                       secondary='user_bookmarks',
                                       backref=db.backref('bookmarked_by', lazy='dynamic'),
                                       lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

    def get_reset_password_token(self):
        # Implementation for password reset token
        pass
    
    @staticmethod
    def verify_reset_password_token(token):
        # Implementation for verifying reset token
        pass

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

# Association table for shared quizzes
shared_quizzes = db.Table('shared_quizzes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('quiz_id', db.Integer, db.ForeignKey('quizzes.id'), primary_key=True),
    db.Column('shared_at', db.DateTime, default=datetime.utcnow)
) 