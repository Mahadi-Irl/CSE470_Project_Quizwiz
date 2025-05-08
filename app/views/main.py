from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from app import db
from app.models.user import User
from app.models.quiz import Quiz, QuizAttempt
from app.models.bookmark import Bookmark
from app.forms.auth import UpdateProfileForm

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/index')
def index():
    if current_user.is_authenticated:
        if current_user.is_teacher:
            return redirect(url_for('main.teacher_home'))
        else:
            return redirect(url_for('main.student_home'))
    return render_template('main/index.html', title='Welcome to Quizwizz')

@main_bp.route('/profile/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    if current_user.is_teacher:
        quizzes = Quiz.query.filter_by(author_id=user.id).order_by(Quiz.created_at.desc()).all()
    else:
        quizzes = Quiz.query.filter_by(is_public=True).order_by(Quiz.created_at.desc()).all()
    return render_template('main/profile.html', user=user, quizzes=quizzes)

@main_bp.route('/profile/<username>/edit', methods=['GET', 'POST'])
@login_required
def edit_profile(username):
    if username != current_user.username:
        flash('You can only edit your own profile.', 'danger')
        return redirect(url_for('main.profile', username=username))
    
    form = UpdateProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.bio = form.bio.data
        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('main.profile', username=current_user.username))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.bio.data = current_user.bio
    return render_template('main/edit_profile.html', title='Edit Profile', form=form)

@main_bp.route('/history')
@login_required
def history():
    """View quiz history."""
    if current_user.is_teacher:
        # Get all quizzes created by the teacher
        quizzes = Quiz.query.filter_by(author_id=current_user.id)
        category = request.args.get('category')
        if category:
            quizzes = quizzes.filter_by(category=category)
        quizzes = quizzes.order_by(Quiz.created_at.desc()).all()
        
        # Get unique categories for the filter dropdown
        categories = db.session.query(Quiz.category).distinct().all()
        categories = [cat[0] for cat in categories if cat[0]]  # Extract unique categories
        
        return render_template('main/teacher_dashboard.html', 
                             quizzes=quizzes,
                             categories=categories,
                             selected_category=category)
    else:
        # Get all attempts by the student
        attempts = QuizAttempt.query.filter_by(student_id=current_user.id)\
            .order_by(QuizAttempt.started_at.desc()).all()
        return render_template('student/history.html', attempts=attempts)

@main_bp.route('/student')
@login_required
def student_home():
    """Student dashboard showing performance indicators."""
    if not current_user.is_authenticated or current_user.is_teacher:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))
    
    # Get student's quiz attempts
    attempts = QuizAttempt.query.filter_by(student_id=current_user.id).all()
    
    # Calculate performance metrics
    total_quizzes = len(attempts)
    completed_quizzes = len([a for a in attempts if a.completed_at is not None])
    
    # Calculate average score as a percentage
    completed_attempts = [a for a in attempts if a.completed_at is not None and a.quiz.grades_released and a.score is not None]
    if completed_attempts:
        total_score = sum(a.score for a in completed_attempts)
        total_max_score = sum(a.max_score for a in completed_attempts)
        average_score = (total_score / total_max_score) * 100 if total_max_score > 0 else 0
    else:
        average_score = 0
    
    # Get recent attempts
    recent_attempts = QuizAttempt.query\
        .filter_by(student_id=current_user.id)\
        .order_by(QuizAttempt.completed_at.desc())\
        .limit(5)\
        .all()
    
    # Get available quizzes (public quizzes not attempted yet)
    attempted_quiz_ids = [a.quiz_id for a in attempts]
    available_quizzes = Quiz.query\
        .filter(Quiz.is_public == True)\
        .filter(~Quiz.id.in_(attempted_quiz_ids))\
        .order_by(Quiz.created_at.desc())\
        .limit(5)\
        .all()
    
    # Calculate performance by category
    category_performance = {}
    for attempt in completed_attempts:
        category = attempt.quiz.category
        if category not in category_performance:
            category_performance[category] = {
                'attempts': 0,
                'total_score': 0,
                'avg_score': 0
            }
        
        category_performance[category]['attempts'] += 1
        category_performance[category]['total_score'] += attempt.percentage_score
    
    # Calculate average scores for each category
    for category in category_performance:
        stats = category_performance[category]
        stats['avg_score'] = stats['total_score'] / stats['attempts']
    
    return render_template('main/student_home.html',
                         total_quizzes=total_quizzes,
                         completed_quizzes=completed_quizzes,
                         average_score=average_score,
                         recent_attempts=recent_attempts,
                         available_quizzes=available_quizzes,
                         category_performance=category_performance)

@main_bp.route('/student/history')
@login_required
def student_history():
    """View student's quiz attempt history."""
    if not current_user.is_authenticated or current_user.is_teacher:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))
    
    # Get the category filter from query parameters
    category = request.args.get('category')
    
    # Base query for attempts
    attempts_query = QuizAttempt.query.filter_by(student_id=current_user.id)
    
    # Apply category filter if specified
    if category:
        attempts_query = attempts_query.join(Quiz).filter(Quiz.category == category)
    
    # Get all attempts ordered by start date
    attempts = attempts_query.order_by(QuizAttempt.started_at.desc()).all()
    
    # Get unique categories for the filter dropdown
    categories = db.session.query(Quiz.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]  # Extract unique categories
    
    return render_template('student/history.html', 
                         attempts=attempts,
                         categories=categories,
                         selected_category=category)

@main_bp.route('/student/bookmarks')
@login_required
def student_bookmarks():
    """View student's bookmarked quizzes."""
    if not current_user.is_authenticated or current_user.is_teacher:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))
    
    # Get bookmarked quizzes
    bookmarked_quizzes = current_user.bookmarked_quizzes
    
    # Get attempts for each quiz
    quiz_data = []
    for quiz in bookmarked_quizzes:
        attempt = QuizAttempt.query.filter_by(
            quiz_id=quiz.id,
            student_id=current_user.id
        ).order_by(QuizAttempt.started_at.desc()).first()
        quiz_data.append((quiz, attempt))
    
    return render_template('student/bookmarks.html', quiz_data=quiz_data)

@main_bp.route('/teacher')
@login_required
def teacher_home():
    """Teacher dashboard showing performance indicators."""
    if not current_user.is_authenticated or not current_user.is_teacher:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))
    
    # Get all quizzes created by the teacher
    quizzes = Quiz.query.filter_by(author_id=current_user.id).all()
    
    # Calculate statistics for each quiz
    quiz_stats = []
    for quiz in quizzes:
        attempts = QuizAttempt.query.filter_by(quiz_id=quiz.id).all()
        total_attempts = len(attempts)
        if total_attempts > 0:
            scores = [attempt.score for attempt in attempts if attempt.score is not None]
            if scores:  # Only calculate if we have valid scores
                avg_score = sum(scores) / len(scores)
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
    
    # Get recent attempts across all quizzes
    recent_attempts = QuizAttempt.query\
        .join(Quiz)\
        .filter(Quiz.author_id == current_user.id)\
        .order_by(QuizAttempt.completed_at.desc())\
        .limit(5)\
        .all()
    
    # Get popular quizzes (most attempts) with their average scores
    popular_quizzes = []
    for quiz in sorted(quizzes, key=lambda x: len(x.attempts), reverse=True)[:5]:
        attempts = QuizAttempt.query.filter_by(quiz_id=quiz.id).all()
        if attempts:
            scores = [a.score for a in attempts if a.score is not None]
            if scores:
                max_score = sum(q.points for q in quiz.questions)
                avg_score = (sum(scores) / len(scores) / max_score) * 100 if max_score > 0 else 0
            else:
                avg_score = 0
        else:
            avg_score = 0
        popular_quizzes.append({
            'quiz': quiz,
            'avg_score': avg_score
        })
    
    from datetime import datetime
    return render_template('main/teacher_home.html', 
                         quizzes=quizzes,
                         quiz_stats=quiz_stats,
                         recent_attempts=recent_attempts,
                         popular_quizzes=popular_quizzes,
                         now=datetime.utcnow())

# Remove or comment out the old dashboard route since we're replacing it
# @main_bp.route('/dashboard')
# @login_required
# def dashboard():
#     if current_user.is_teacher:
#         return redirect(url_for('teacher.dashboard'))
#     else:
#         return redirect(url_for('student.dashboard')) 