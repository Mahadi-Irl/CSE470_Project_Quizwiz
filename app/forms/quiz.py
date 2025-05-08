from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, BooleanField, SubmitField, SelectField, FieldList, FormField, DateTimeField
from wtforms.validators import DataRequired, Length, Optional, NumberRange
from datetime import datetime

# List of predefined categories
QUIZ_CATEGORIES = [
    ('mathematics', 'Mathematics'),
    ('science', 'Science'),
    ('history', 'History'),
    ('geography', 'Geography'),
    ('literature', 'Literature'),
    ('computer_science', 'Computer Science'),
    ('languages', 'Languages'),
    ('arts', 'Arts'),
    ('music', 'Music'),
    ('sports', 'Sports'),
    ('general_knowledge', 'General Knowledge'),
    ('business', 'Business'),
    ('technology', 'Technology'),
    ('health', 'Health'),
    ('social_studies', 'Social Studies')
]

class QuestionOptionForm(FlaskForm):
    id = IntegerField('ID', validators=[Optional()])
    text = TextAreaField('Option Text', validators=[DataRequired()])
    is_correct = BooleanField('Is Correct')
    order = IntegerField('Order', validators=[Optional()])

class QuestionForm(FlaskForm):
    id = IntegerField('ID', validators=[Optional()])
    text = TextAreaField('Question Text', validators=[DataRequired()])
    question_type = SelectField('Question Type', choices=[('mcq', 'Multiple Choice'), ('descriptive', 'Descriptive')])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=1)], default=1)
    order = IntegerField('Order', validators=[Optional()])
    options = FieldList(FormField(QuestionOptionForm), min_entries=1)

    def validate(self):
        if not super().validate():
            return False
        
        if self.question_type.data == 'mcq':
            # For MCQ, require at least 2 options
            if len(self.options.data) < 2:
                self.options.errors.append('Multiple choice questions require at least 2 options.')
                return False
            # Check if exactly one option is marked as correct
            correct_options = sum(1 for option in self.options.data if option.get('is_correct'))
            if correct_options != 1:
                self.options.errors.append('Multiple choice questions must have exactly one correct answer.')
                return False
        else:  # Descriptive question
            # For descriptive, require exactly one option as the correct answer
            if len(self.options.data) != 1:
                self.options.errors.append('Descriptive questions require exactly one correct answer.')
                return False
            if not self.options.data[0].get('text'):
                self.options.errors.append('Please provide the correct answer for the descriptive question.')
                return False
        
        return True

class QuizForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    category = SelectField('Category', choices=QUIZ_CATEGORIES, validators=[DataRequired()])
    is_public = BooleanField('Public Quiz', default=True)
    password = StringField('Password (if private)', validators=[Optional()])
    time_limit = IntegerField('Time Limit (minutes)', validators=[Optional(), NumberRange(min=1)])
    max_attempts = IntegerField('Maximum Attempts', validators=[Optional(), NumberRange(min=1)], default=1)
    start_time = DateTimeField('Start Time', format='%Y-%m-%d %H:%M', validators=[Optional()], default=datetime.utcnow)
    end_time = DateTimeField('End Time', format='%Y-%m-%d %H:%M', validators=[Optional()])
    questions = FieldList(FormField(QuestionForm), min_entries=1)
    submit = SubmitField('Create Quiz')

class QuizSearchForm(FlaskForm):
    search = StringField('Search Quizzes', validators=[Optional()])
    category = SelectField('Category', choices=QUIZ_CATEGORIES, validators=[Optional()])
    submit = SubmitField('Search')

class QuizPasswordForm(FlaskForm):
    password = StringField('Quiz Password', validators=[DataRequired()])
    submit = SubmitField('Access Quiz')

class AnswerForm(FlaskForm):
    selected_option = SelectField('Select Answer', coerce=int, validators=[Optional()])
    text_answer = TextAreaField('Your Answer', validators=[Optional()])
    submit = SubmitField('Submit Answer')

class FeedbackForm(FlaskForm):
    feedback = TextAreaField('Feedback', validators=[DataRequired()])
    submit = SubmitField('Submit Feedback') 