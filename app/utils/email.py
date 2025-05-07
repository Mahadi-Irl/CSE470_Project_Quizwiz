from flask import current_app, render_template
from flask_mail import Message
from app import mail
from threading import Thread

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject, sender, recipients, text_body, html_body):
    if not current_app.config.get('MAIL_SERVER'):
        print(f"Email not sent (email not configured): {subject}")
        return
        
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email,
           args=(current_app._get_current_object(), msg)).start()

def send_password_reset_email(user):
    if not current_app.config.get('MAIL_SERVER'):
        print(f"Password reset email not sent for user: {user.email}")
        return
        
    token = user.get_reset_password_token()
    send_email('[Quizwizz] Reset Your Password',
               sender=current_app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template('email/reset_password.txt',
                                       user=user, token=token),
               html_body=render_template('email/reset_password.html',
                                       user=user, token=token))

def send_quiz_result_email(user, quiz, score, max_score, attempt):
    if not current_app.config.get('MAIL_SERVER'):
        print(f"Quiz result email not sent for user: {user.email}")
        return
        
    send_email('[Quizwizz] Quiz Results',
               sender=current_app.config['MAIL_USERNAME'],
               recipients=[user.email],
               text_body=render_template('email/quiz_result.txt',
                                       user=user, quiz=quiz,
                                       score=score, max_score=max_score,
                                       attempt=attempt),
               html_body=render_template('email/quiz_result.html',
                                       user=user, quiz=quiz,
                                       score=score, max_score=max_score,
                                       attempt=attempt))

def send_quiz_invitation_email(user, quiz, password=None):
    if not current_app.config.get('MAIL_SERVER'):
        print(f"Quiz invitation email not sent for user: {user.email}")
        return
        
    send_email('[Quizwizz] Quiz Invitation',
               sender=current_app.config['MAIL_USERNAME'],
               recipients=[user.email],
               text_body=render_template('email/quiz_invitation.txt',
                                       user=user, quiz=quiz, password=password),
               html_body=render_template('email/quiz_invitation.html',
                                       user=user, quiz=quiz, password=password))

def send_quiz_grades_email(user, quiz, attempt):
    """Send an email notification when quiz grades are released."""
    subject = f'Grades Released: {quiz.title}'
    template = 'email/quiz_grades.html'
    
    # Calculate percentage score
    percentage = (attempt.score / attempt.max_score) * 100
    
    # Determine grade category
    if percentage >= 70:
        grade_category = 'success'
    elif percentage >= 40:
        grade_category = 'warning'
    else:
        grade_category = 'danger'
    
    send_email(
        subject=subject,
        recipients=[user.email],
        template=template,
        user=user,
        quiz=quiz,
        attempt=attempt,
        percentage=percentage,
        grade_category=grade_category
    ) 