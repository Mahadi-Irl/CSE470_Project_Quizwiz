from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.quiz import Quiz, QuizAttempt
from app.models.user import User
from app import db

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_teacher:
        flash('Access denied. Students only.', 'danger')
        return redirect(url_for('main.index'))
    
    # Get in-progress attempts
    in_progress = QuizAttempt.query.filter_by(
        student_id=current_user.id
    ).filter(QuizAttempt.completed_at.is_(None)).order_by(QuizAttempt.started_at.desc()).all()
    
    # Get completed attempts
    completed = QuizAttempt.query.filter_by(
        student_id=current_user.id
    ).filter(QuizAttempt.completed_at.isnot(None)).order_by(QuizAttempt.started_at.desc()).all()
    
    # Get quizzes shared with the student
    shared_quizzes = Quiz.query.filter(
        Quiz.is_public == True,
        Quiz.shared_with_users.contains(current_user)
    ).all()
    
    return render_template('student/dashboard.html',
                         in_progress=in_progress,
                         completed=completed,
                         shared_quizzes=shared_quizzes)

@student_bp.route('/quiz/<int:quiz_id>/feedback', methods=['GET', 'POST'])
@login_required
def submit_feedback(quiz_id):
    if current_user.is_teacher:
        flash('Access denied. Students only.', 'danger')
        return redirect(url_for('main.index'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Check if student has completed the quiz
    attempt = QuizAttempt.query.filter_by(
        quiz_id=quiz_id,
        student_id=current_user.id,
        completed=True
    ).first()
    
    if not attempt:
        flash('You must complete the quiz before providing feedback.', 'warning')
        return redirect(url_for('student.dashboard'))
    
    # Check if feedback has already been submitted
    if quiz.feedback.filter_by(student_id=current_user.id).first():
        flash('You have already submitted feedback for this quiz.', 'info')
        return redirect(url_for('quiz.view', quiz_id=quiz_id))
    
    if request.method == 'POST':
        feedback_text = request.form.get('feedback')
        if feedback_text:
            from app.models.feedback import QuizFeedback
            feedback = QuizFeedback(
                quiz_id=quiz_id,
                student_id=current_user.id,
                feedback=feedback_text
            )
            db.session.add(feedback)
            db.session.commit()
            flash('Thank you for your feedback!', 'success')
            return redirect(url_for('quiz.view', quiz_id=quiz_id))
        else:
            flash('Please provide feedback.', 'warning')
    
    return render_template('quiz/feedback.html', quiz=quiz) 