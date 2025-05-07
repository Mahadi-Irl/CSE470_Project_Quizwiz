from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.quiz import Quiz, QuizAttempt
from app.models.user import User
from app import db

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

@teacher_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_teacher:
        flash('Access denied. Teachers only.', 'danger')
        return redirect(url_for('main.index'))
    
    # Get all quizzes created by the teacher
    quizzes = Quiz.query.filter_by(author_id=current_user.id).all()
    
    # Calculate statistics for each quiz
    quiz_stats = []
    for quiz in quizzes:
        attempts = QuizAttempt.query.filter_by(quiz_id=quiz.id).all()
        total_attempts = len(attempts)
        if total_attempts > 0:
            scores = [attempt.score for attempt in attempts]
            avg_score = sum(scores) / total_attempts
            max_score = sum(question.points for question in quiz.questions)
            highest_score = max(scores)
            lowest_score = min(scores)
            avg_percentage = (avg_score / max_score) * 100
        else:
            avg_score = 0
            max_score = sum(question.points for question in quiz.questions)
            highest_score = 0
            lowest_score = 0
            avg_percentage = 0
        
        quiz_stats.append({
            'quiz': quiz,
            'total_attempts': total_attempts,
            'avg_score': avg_score,
            'max_score': max_score,
            'highest_score': highest_score,
            'lowest_score': lowest_score,
            'avg_percentage': avg_percentage
        })
    
    return render_template('teacher/dashboard.html', 
                         quizzes=quizzes,
                         quiz_stats=quiz_stats)

@teacher_bp.route('/quiz/<int:quiz_id>/results')
@login_required
def quiz_results(quiz_id):
    if not current_user.is_teacher:
        flash('Access denied. Teachers only.', 'danger')
        return redirect(url_for('main.index'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.author_id != current_user.id:
        flash('Access denied. You can only view results for your own quizzes.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    attempts = quiz.attempts.all()
    total_attempts = len(attempts)
    
    # Calculate statistics
    if total_attempts > 0:
        scores = [attempt.score for attempt in attempts if attempt.score is not None]
        avg_score = sum(scores) / len(scores) if scores else 0
        highest_score = max(scores) if scores else 0
        lowest_score = min(scores) if scores else 0
    else:
        avg_score = highest_score = lowest_score = 0
    
    # Calculate question-wise statistics
    question_stats = []
    for question in quiz.questions:
        correct_answers = sum(1 for attempt in attempts 
                            for answer in attempt.answers 
                            if answer.question_id == question.id and answer.is_correct)
        success_rate = (correct_answers / total_attempts * 100) if total_attempts > 0 else 0
        
        question_stats.append({
            'question': question,
            'correct_answers': correct_answers,
            'success_rate': round(success_rate, 2)
        })
    
    return render_template('teacher/quiz_results.html',
                         quiz=quiz,
                         attempts=attempts,
                         total_attempts=total_attempts,
                         avg_score=round(avg_score, 2),
                         highest_score=round(highest_score, 2),
                         lowest_score=round(lowest_score, 2),
                         question_stats=question_stats) 