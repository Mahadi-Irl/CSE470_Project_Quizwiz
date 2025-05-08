from datetime import datetime
from app import db

class Bookmark(db.Model):
    __tablename__ = 'bookmarks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    quiz = db.relationship('Quiz', backref=db.backref('bookmarks', lazy='dynamic'))

    def __repr__(self):
        return f'<Bookmark {self.id}: Quiz {self.quiz_id} by User {self.user_id}>'

    @classmethod
    def toggle_bookmark(cls, user, quiz):
        """Toggle bookmark status for a quiz."""
        bookmark = cls.query.filter_by(user_id=user.id, quiz_id=quiz.id).first()
        if bookmark:
            db.session.delete(bookmark)
            db.session.commit()
            return False  # Bookmark removed
        else:
            bookmark = cls(user_id=user.id, quiz_id=quiz.id)
            db.session.add(bookmark)
            db.session.commit()
            return True  # Bookmark added 