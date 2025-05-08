from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, Response
from flask_login import current_user, login_required
from app import db
from app.models.quiz import Quiz, QuizAttempt, Question, QuestionOption, Answer, QuizFeedback
from app.models.user import User
from app.forms.quiz import QuizForm, QuizSearchForm, QuizPasswordForm, AnswerForm, FeedbackForm
from app.utils.email import send_quiz_result_email, send_quiz_invitation_email, send_quiz_grades_email
from datetime import datetime
from urllib.parse import urlparse
from io import StringIO
import csv

quiz_bp = Blueprint('quiz', __name__, url_prefix='/quiz')

@quiz_bp.route('/quiz/create', methods=['GET', 'POST'])
@login_required
def create_quiz():
    if not current_user.is_teacher:
        flash('Only teachers can create quizzes.', 'danger')
        return redirect(url_for('main.index'))
    
    form = QuizForm()
    # Initialize start_time to current time if not set
    if not form.start_time.data:
        form.start_time.data = datetime.utcnow()
    
    if form.validate_on_submit():
        try:
            quiz = Quiz(
                title=form.title.data,
                description=form.description.data,
                category=form.category.data,
                is_public=form.is_public.data,
                password=form.password.data if not form.is_public.data else None,
                time_limit=form.time_limit.data,
                max_attempts=form.max_attempts.data,
                start_time=form.start_time.data or datetime.utcnow(),
                end_time=form.end_time.data,
                author_id=current_user.id,
                grades_released=False  # Initialize as not released
            )
            db.session.add(quiz)
            
            for q_index, q_form in enumerate(form.questions):
                question = Question(
                    text=q_form.text.data,
                    question_type=q_form.question_type.data,
                    points=q_form.points.data,
                    order=q_index + 1,  # Use form index as order
                    quiz=quiz
                )
                db.session.add(question)
                
                for o_index, o_form in enumerate(q_form.options):
                    option = QuestionOption(
                        text=o_form.text.data,
                        is_correct=o_form.is_correct.data,
                        order=o_index + 1,  # Use form index as order
                        question=question
                    )
                    db.session.add(option)
            
            db.session.commit()
            flash('Quiz created successfully!', 'success')
            return redirect(url_for('quiz.view_quiz', quiz_id=quiz.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating quiz: {str(e)}', 'danger')
            return render_template('quiz/create.html', title='Create Quiz', form=form)
    
    return render_template('quiz/create.html', title='Create Quiz', form=form)

@quiz_bp.route('/quiz/<int:quiz_id>')
@login_required
def view_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if not quiz.is_public and quiz.author_id != current_user.id:
        if not quiz.password:
            flash('This quiz is private.', 'danger')
            return redirect(url_for('main.index'))
        if quiz not in current_user.shared_quizzes:
            return redirect(url_for('quiz.enter_password', quiz_id=quiz_id))
    
    # Calculate statistics
    attempts = quiz.attempts  # This is already a list
    total_attempts = len(attempts)  # Use len() instead of count()
    if total_attempts > 0:
        scores = [attempt.score for attempt in attempts if attempt.score is not None]
        avg_score = sum(scores) / len(scores) if scores else 0
        max_score = sum(question.points for question in quiz.questions)
        highest_score = max(scores) if scores else 0
        lowest_score = min(scores) if scores else 0
    else:
        avg_score = 0
        max_score = sum(question.points for question in quiz.questions)
        highest_score = 0
        lowest_score = 0
    
    # Get student attempts if user is a student
    student_attempts = None
    if not current_user.is_teacher:
        student_attempts = QuizAttempt.query.filter_by(
            quiz_id=quiz_id,
            student_id=current_user.id
        ).order_by(QuizAttempt.started_at.desc()).all()
    
    # Get feedback if user is the quiz author
    feedback = None
    if current_user.id == quiz.author_id:
        feedback = quiz.feedback.all()
    
    # Calculate total questions
    total_questions = len(quiz.questions)
    
    return render_template('quiz/view.html', 
                         quiz=quiz,
                         attempts=student_attempts,
                         total_attempts=total_attempts,
                         total_questions=total_questions,  # Pass total_questions to template
                         avg_score=avg_score,
                         max_score=max_score,
                         highest_score=highest_score,
                         lowest_score=lowest_score,
                         feedback=feedback)

@quiz_bp.route('/quiz/<int:quiz_id>/password', methods=['GET', 'POST'])
@login_required
def enter_password(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.is_public or quiz.author_id == current_user.id:
        return redirect(url_for('quiz.view_quiz', quiz_id=quiz_id))
    
    form = QuizPasswordForm()
    if form.validate_on_submit():
        if form.password.data == quiz.password:
            # Share quiz with user
            if quiz not in current_user.shared_quizzes:
                current_user.shared_quizzes.append(quiz)
                db.session.commit()
                flash('Quiz accessed successfully!', 'success')
            else:
                flash('You already have access to this quiz.', 'info')
            return redirect(url_for('quiz.take_quiz', quiz_id=quiz_id))
        flash('Invalid password.', 'danger')
    
    return render_template('quiz/password.html', form=form)

@quiz_bp.route('/quiz/<int:quiz_id>/take', methods=['GET', 'POST'])
@login_required
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Check if user can take the quiz
    if not quiz.is_public and quiz.author_id != current_user.id:
        if not quiz.password:
            flash('This quiz is private.', 'danger')
            return redirect(url_for('main.index'))
        if quiz not in current_user.shared_quizzes:
            return redirect(url_for('quiz.enter_password', quiz_id=quiz_id))
    
    # Check if grades have been released and user is a student
    if quiz.grades_released and not current_user.is_teacher:
        flash('This quiz is over. Grades have been released.', 'info')
        return redirect(url_for('main.index'))
    
    # Check time restrictions
    now = datetime.utcnow()
    if quiz.start_time and now < quiz.start_time:
        flash('This quiz is not available yet.', 'info')
        return redirect(url_for('main.index'))
    if quiz.end_time and now > quiz.end_time:
        flash('This quiz is no longer available.', 'info')
        return redirect(url_for('main.index'))
    
    # Check attempt limits
    attempts = QuizAttempt.query.filter_by(quiz_id=quiz_id, student_id=current_user.id).all()
    completed_attempts = [attempt for attempt in attempts if attempt.completed_at]
    if len(completed_attempts) >= quiz.max_attempts:
        flash('You have reached the maximum number of attempts for this quiz.', 'info')
        return redirect(url_for('main.index'))
    
    # Check for incomplete attempt
    incomplete_attempt = next((attempt for attempt in attempts if not attempt.completed_at), None)
    if incomplete_attempt:
        attempt = incomplete_attempt
    else:
        # Start new attempt
        attempt = QuizAttempt(quiz_id=quiz_id, student_id=current_user.id)
        db.session.add(attempt)
        db.session.commit()
    
    if request.method == 'POST':
        # Process answers
        for question in quiz.questions:
            if question.question_type == 'mcq':
                option_id = request.form.get(f'question_{question.id}')
                option = QuestionOption.query.get(option_id)
                answer = Answer(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    selected_option_id=option_id,
                    is_correct=option.is_correct if option else False,
                    points_earned=question.points if option and option.is_correct else 0
                )
            else:  # Descriptive question
                text_answer = request.form.get(f'question_{question.id}')
                # Get the correct answer from the question's options (first option is the correct answer)
                correct_option = QuestionOption.query.filter_by(question_id=question.id).order_by(QuestionOption.order).first()
                correct_answer = correct_option.text if correct_option else ""
                
                # Remove whitespace and convert to lowercase for comparison
                student_answer = ''.join(text_answer.split()).lower() if text_answer else ""
                correct_answer = ''.join(correct_answer.split()).lower() if correct_answer else ""
                
                is_correct = student_answer == correct_answer
                answer = Answer(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    text_answer=text_answer,
                    is_correct=is_correct,
                    points_earned=question.points if is_correct else 0
                )
            db.session.add(answer)
        
        attempt.completed_at = datetime.utcnow()
        attempt.score = sum(a.points_earned for a in attempt.answers if a.points_earned)
        attempt.max_score = sum(q.points for q in quiz.questions)
        db.session.commit()
        
        # Send email with results
        send_quiz_result_email(current_user, quiz, attempt.score, attempt.max_score, attempt)
        
        flash('Quiz submitted successfully! You will be able to view your results once the teacher releases the grades.', 'success')
        return redirect(url_for('main.index'))
    
    return render_template('quiz/take.html', quiz=quiz)

@quiz_bp.route('/quiz/results/<int:attempt_id>')
@login_required
def view_results(attempt_id):
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    if attempt.student_id != current_user.id and attempt.quiz.author_id != current_user.id:
        flash('You do not have permission to view these results.', 'danger')
        return redirect(url_for('main.index'))
    
    # Check if grades have been released for this quiz
    if not attempt.quiz.grades_released and attempt.student_id == current_user.id:
        flash('Grades for this quiz have not been released yet.', 'warning')
        return redirect(url_for('main.index'))
    
    return render_template('quiz/detailed_results.html', 
                         attempt=attempt,
                         quiz=attempt.quiz)

@quiz_bp.route('/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.author_id != current_user.id:
        flash('You can only edit your own quizzes.', 'danger')
        return redirect(url_for('main.index'))
    
    form = QuizForm(obj=quiz)
    if form.validate_on_submit():
        quiz.title = form.title.data
        quiz.description = form.description.data
        quiz.category = form.category.data
        quiz.is_public = form.is_public.data
        quiz.password = form.password.data if not form.is_public.data else None
        quiz.time_limit = form.time_limit.data
        quiz.max_attempts = form.max_attempts.data
        quiz.start_time = form.start_time.data
        quiz.end_time = form.end_time.data
        
        # Get all existing question IDs from the form
        form_question_ids = set()
        for q_index, q_form in enumerate(form.questions):
            question_id = request.form.get(f'questions-{q_index}-id')
            if question_id and question_id.strip():
                form_question_ids.add(int(question_id))
        
        # Delete questions that are not in the form
        for question in quiz.questions:
            if question.id not in form_question_ids:
                # Delete associated options first
                QuestionOption.query.filter_by(question_id=question.id).delete()
                # Then delete the question
                db.session.delete(question)
        
        # Update or create questions and options
        for q_index, q_form in enumerate(form.questions):
            question_id = request.form.get(f'questions-{q_index}-id')
            
            if question_id and question_id.strip():
                # Update existing question
                question = Question.query.get(int(question_id))
                if question and question.quiz_id == quiz.id:
                    question.text = q_form.text.data
                    question.question_type = q_form.question_type.data
                    question.points = q_form.points.data
                    question.order = q_index + 1
            else:
                # Create new question
                question = Question(
                    text=q_form.text.data,
                    question_type=q_form.question_type.data,
                    points=q_form.points.data,
                    order=q_index + 1,
                    quiz=quiz
                )
                db.session.add(question)
            
            # Get all existing option IDs for this question from the form
            form_option_ids = set()
            for o_index, o_form in enumerate(q_form.options):
                option_id = request.form.get(f'questions-{q_index}-options-{o_index}-id')
                if option_id and option_id.strip():
                    form_option_ids.add(int(option_id))
            
            # Delete options that are not in the form
            for option in question.options:
                if option.id not in form_option_ids:
                    db.session.delete(option)
            
            # Update or create options
            for o_index, o_form in enumerate(q_form.options):
                option_id = request.form.get(f'questions-{q_index}-options-{o_index}-id')
                
                if option_id and option_id.strip():
                    # Update existing option
                    option = QuestionOption.query.get(int(option_id))
                    if option and option.question_id == question.id:
                        option.text = o_form.text.data
                        option.is_correct = o_form.is_correct.data
                        option.order = o_index + 1
                else:
                    # Create new option
                    option = QuestionOption(
                        text=o_form.text.data,
                        is_correct=o_form.is_correct.data,
                        order=o_index + 1,
                        question=question
                    )
                    db.session.add(option)
        
        db.session.commit()
        flash('Quiz updated successfully!', 'success')
        return redirect(url_for('quiz.view_quiz', quiz_id=quiz.id))
    
    return render_template('quiz/edit.html', title='Edit Quiz', form=form, quiz=quiz)

@quiz_bp.route('/quiz/<int:quiz_id>/delete', methods=['POST'])
@login_required
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.author_id != current_user.id:
        flash('You can only delete your own quizzes.', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        # First, remove all shared quiz associations
        quiz.shared_with = []
        db.session.commit()
        
        # Delete all related quiz attempts
        QuizAttempt.query.filter_by(quiz_id=quiz_id).delete()
        
        # Delete all related answers
        Answer.query.filter(Answer.attempt_id.in_(
            db.session.query(QuizAttempt.id).filter_by(quiz_id=quiz_id)
        )).delete(synchronize_session=False)
        
        # Delete all related questions and options
        for question in quiz.questions:
            QuestionOption.query.filter_by(question_id=question.id).delete()
        Question.query.filter_by(quiz_id=quiz_id).delete()
        
        # Delete all related feedback
        QuizFeedback.query.filter_by(quiz_id=quiz_id).delete()
        
        # Finally delete the quiz
        db.session.delete(quiz)
        db.session.commit()
        flash('Quiz deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting quiz: {str(e)}', 'danger')
    
    if current_user.is_teacher:
        return redirect(url_for('main.history'))
    else:
        return redirect(url_for('student.dashboard'))

@quiz_bp.route('/quiz/search', methods=['GET', 'POST'])
@login_required
def search_quizzes():
    form = QuizSearchForm()
    if form.validate_on_submit():
        query = Quiz.query.filter_by(is_public=True)
        if form.search.data:
            query = query.filter(Quiz.title.ilike(f'%{form.search.data}%'))
        if form.category.data:
            query = query.filter_by(category=form.category.data)
        quizzes = query.order_by(Quiz.created_at.desc()).all()
    else:
        quizzes = Quiz.query.filter_by(is_public=True).order_by(Quiz.created_at.desc()).all()
    
    return render_template('quiz/search.html', title='Search Quizzes', form=form, quizzes=quizzes)

@quiz_bp.route('/quiz/<int:quiz_id>/bookmark', methods=['POST'])
@login_required
def toggle_bookmark(quiz_id):
    """Toggle bookmark status for a quiz."""
    if current_user.is_teacher:
        return jsonify({'error': 'Access denied'}), 403
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if quiz in current_user.bookmarked_quizzes:
        current_user.bookmarked_quizzes.remove(quiz)
        status = 'removed'
    else:
        current_user.bookmarked_quizzes.append(quiz)
        status = 'added'
    
    db.session.commit()
    return jsonify({'status': status})

@quiz_bp.route('/quiz/enter-link', methods=['POST'])
@login_required
def enter_quiz_link():
    if current_user.is_teacher:
        flash('Teachers cannot take quizzes.', 'warning')
        return redirect(url_for('main.index'))
    
    quiz_link = request.form.get('quiz_link')
    if not quiz_link:
        flash('Please enter a quiz link.', 'warning')
        return redirect(url_for('main.index'))
    
    try:
        # Parse the URL to get the quiz_id
        parsed_url = urlparse(quiz_link)
        quiz_id = int(parsed_url.path.split('/')[-1])
        
        quiz = Quiz.query.get_or_404(quiz_id)
        
        # Check if the quiz is private and user is not the author
        if not quiz.is_public and quiz.author_id != current_user.id:
            if not quiz.password:
                flash('This quiz is private.', 'danger')
                return redirect(url_for('main.index'))
            if quiz not in current_user.shared_quizzes:
                return redirect(url_for('quiz.enter_password', quiz_id=quiz_id))
        
        # If we get here, either the quiz is public or the user has access
        if quiz not in current_user.shared_quizzes:
            current_user.shared_quizzes.append(quiz)
            db.session.commit()
            flash('Quiz has been added to your dashboard!', 'success')
        else:
            flash('You already have access to this quiz.', 'info')
        
        return redirect(url_for('quiz.take_quiz', quiz_id=quiz_id))
    except (ValueError, IndexError):
        flash('Invalid quiz link.', 'danger')
        return redirect(url_for('main.index'))

@quiz_bp.route('/quiz/<int:quiz_id>/shared', methods=['GET'])
@login_required
def take_shared_quiz(quiz_id):
    if current_user.is_teacher:
        flash('Teachers cannot take quizzes.', 'warning')
        return redirect(url_for('main.index'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Check if the quiz is private and user is not the author
    if not quiz.is_public and quiz.author_id != current_user.id:
        if not quiz.password:
            flash('This quiz is private.', 'danger')
            return redirect(url_for('main.index'))
        if quiz not in current_user.shared_quizzes:
            return redirect(url_for('quiz.enter_password', quiz_id=quiz_id))
    
    # If we get here, either the quiz is public or the user has access
    if quiz not in current_user.shared_quizzes:
        current_user.shared_quizzes.append(quiz)
        db.session.commit()
        flash('Quiz has been added to your dashboard!', 'success')
    
    return redirect(url_for('quiz.take_quiz', quiz_id=quiz_id))

@quiz_bp.route('/quiz/<int:quiz_id>/results')
@login_required
def quiz_results(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.author_id != current_user.id and not current_user.is_teacher:
        flash('You do not have permission to view these results.', 'danger')
        return redirect(url_for('main.index'))
    
    # Get all attempts for this quiz
    attempts = QuizAttempt.query.filter_by(quiz_id=quiz_id).all()
    
    # Calculate statistics
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
    
    # Calculate question-wise statistics
    question_stats = []
    for question in quiz.questions:
        correct_answers = 0
        total_answers = 0
        
        for attempt in attempts:
            if attempt.completed_at:  # Only count completed attempts
                answer = Answer.query.filter_by(
                    attempt_id=attempt.id,
                    question_id=question.id
                ).first()
                
                if answer:
                    total_answers += 1
                    if answer.is_correct:
                        correct_answers += 1
        
        success_rate = (correct_answers / total_answers * 100) if total_answers > 0 else 0
        
        question_stats.append({
            'question': question,
            'correct_count': correct_answers,
            'total_attempts': total_answers,
            'success_rate': round(success_rate, 2)
        })
    
    # Get all feedback for this quiz
    feedback = QuizFeedback.query.filter_by(quiz_id=quiz_id).all()
    
    return render_template('quiz/results.html', 
                         quiz=quiz, 
                         attempts=attempts,
                         avg_score=avg_score,
                         max_score=max_score,
                         avg_percentage=avg_percentage,
                         highest_score=highest_score,
                         lowest_score=lowest_score,
                         total_attempts=total_attempts,
                         question_stats=question_stats,
                         feedback=feedback)

@quiz_bp.route('/quiz/<int:quiz_id>/release-grades', methods=['POST'])
@login_required
def release_grades(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.author_id != current_user.id:
        flash('You can only release grades for your own quizzes.', 'danger')
        return redirect(url_for('main.index'))
    
    quiz.grades_released = True
    db.session.commit()
    flash('Grades have been released to students.', 'success')
    return redirect(url_for('quiz.quiz_results', quiz_id=quiz_id))

@quiz_bp.route('/quiz/<int:quiz_id>/export')
@login_required
def export_results(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.author_id != current_user.id and not current_user.is_teacher:
        flash('You do not have permission to export these results.', 'danger')
        return redirect(url_for('main.index'))
    
    attempts = QuizAttempt.query.filter_by(quiz_id=quiz_id).all()
    
    # Create CSV data
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Student', 'Score', 'Max Score', 'Percentage', 'Attempt Date', 'Time Taken'])
    
    # Write data
    for attempt in attempts:
        student = User.query.get(attempt.student_id)
        time_taken = (attempt.completed_at - attempt.started_at).total_seconds() / 60 if attempt.completed_at else 0
        writer.writerow([
            student.username,
            attempt.score,
            attempt.max_score,
            f"{(attempt.score / attempt.max_score * 100):.2f}%" if attempt.max_score > 0 else "0%",
            attempt.completed_at.strftime('%Y-%m-%d %H:%M:%S') if attempt.completed_at else 'Not completed',
            f"{time_taken:.2f} minutes"
        ])
    
    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=quiz_{quiz_id}_results.csv'
        }
    )

@quiz_bp.route('/quiz/<int:quiz_id>/feedback', methods=['GET', 'POST'])
@login_required
def submit_feedback(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if current_user.is_teacher:
        flash('Teachers cannot submit feedback.', 'warning')
        return redirect(url_for('main.index'))
    
    # Get the latest attempt for this quiz by the current user
    attempt = QuizAttempt.query.filter_by(
        quiz_id=quiz_id,
        student_id=current_user.id
    ).order_by(QuizAttempt.started_at.desc()).first()
    
    if not attempt:
        flash('You must attempt the quiz before submitting feedback.', 'warning')
        return redirect(url_for('quiz.view_quiz', quiz_id=quiz_id))
    
    form = FeedbackForm()
    if form.validate_on_submit():
        feedback = QuizFeedback(
            quiz_id=quiz_id,
            student_id=current_user.id,
            feedback=form.feedback.data
        )
        db.session.add(feedback)
        db.session.commit()
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('quiz.view_results', attempt_id=attempt.id))
    
    return render_template('quiz/feedback.html', form=form, quiz=quiz)

@quiz_bp.route('/student/history')
@login_required
def student_history():
    if current_user.is_teacher:
        flash('This page is for students only.', 'warning')
        return redirect(url_for('main.index'))
    
    attempts = QuizAttempt.query.filter_by(student_id=current_user.id).order_by(QuizAttempt.started_at.desc()).all()
    return render_template('quiz/history.html', attempts=attempts)

@quiz_bp.route('/student/bookmarks')
@login_required
def student_bookmarks():
    if current_user.is_teacher:
        flash('This page is for students only.', 'warning')
        return redirect(url_for('main.index'))
    
    bookmarked_quizzes = current_user.bookmarked_quizzes.all()
    return render_template('student/bookmarks.html', bookmarked_quizzes=bookmarked_quizzes)

@quiz_bp.route('/student/performance')
@login_required
def student_performance():
    if current_user.is_teacher:
        flash('This page is for students only.', 'warning')
        return redirect(url_for('main.index'))
    
    # Get all completed attempts by the student
    attempts = QuizAttempt.query.filter_by(
        student_id=current_user.id,
        completed_at=not None
    ).order_by(QuizAttempt.completed_at.desc()).all()
    
    # Group attempts by quiz
    quiz_performance = {}
    for attempt in attempts:
        if attempt.quiz_id not in quiz_performance:
            quiz_performance[attempt.quiz_id] = {
                'quiz': attempt.quiz,
                'attempts': [],
                'highest_score': 0,
                'lowest_score': float('inf'),
                'avg_score': 0
            }
        
        quiz_performance[attempt.quiz_id]['attempts'].append(attempt)
        
        # Update statistics
        scores = [a.score for a in quiz_performance[attempt.quiz_id]['attempts']]
        quiz_performance[attempt.quiz_id]['highest_score'] = max(scores)
        quiz_performance[attempt.quiz_id]['lowest_score'] = min(scores)
        quiz_performance[attempt.quiz_id]['avg_score'] = sum(scores) / len(scores)
    
    return render_template('quiz/performance.html', quiz_performance=quiz_performance)

@quiz_bp.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.is_teacher:
        flash('This page is for students only.', 'warning')
        return redirect(url_for('main.index'))
    
    # Get all attempts by the student
    all_attempts = QuizAttempt.query.filter_by(student_id=current_user.id).all()
    
    # Separate attempts into in-progress and completed
    in_progress_quizzes = [attempt for attempt in all_attempts if not attempt.completed_at]
    completed_quizzes = [attempt for attempt in all_attempts if attempt.completed_at]
    
    # Get all quizzes the student has access to
    accessible_quizzes = Quiz.query.filter(
        (Quiz.is_public == True) |  # Public quizzes
        (Quiz.id.in_([q.id for q in current_user.shared_quizzes]))  # Shared quizzes
    ).all()
    
    # Filter out quizzes that the student has already attempted
    attempted_quiz_ids = {attempt.quiz_id for attempt in all_attempts}
    available_quizzes = [
        quiz for quiz in accessible_quizzes 
        if quiz.id not in attempted_quiz_ids and 
        (not quiz.start_time or quiz.start_time <= datetime.utcnow()) and
        (not quiz.end_time or quiz.end_time >= datetime.utcnow())
    ]
    
    # For completed quizzes, ensure we have the latest attempt for each quiz
    latest_attempts = {}
    for attempt in completed_quizzes:
        if attempt.quiz_id not in latest_attempts or attempt.completed_at > latest_attempts[attempt.quiz_id].completed_at:
            latest_attempts[attempt.quiz_id] = attempt
    
    # Convert attempts to quiz objects with their latest attempt
    completed_quizzes = []
    for attempt in latest_attempts.values():
        quiz = attempt.quiz
        quiz.attempts = [attempt]  # Add the latest attempt to the quiz object
        completed_quizzes.append(quiz)
    
    # Sort completed quizzes by completion date
    completed_quizzes.sort(key=lambda q: q.attempts[0].completed_at, reverse=True)
    
    return render_template('student/dashboard.html',
                         in_progress_quizzes=in_progress_quizzes,
                         completed_quizzes=completed_quizzes,
                         available_quizzes=available_quizzes,
                         now=datetime.utcnow())

@quiz_bp.route('/history')
@login_required
def quiz_history():
    """View quiz attempt history."""
    if not current_user.is_student():
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))
    
    # Get all attempts by the student, ordered by most recent first
    attempts = QuizAttempt.query.filter_by(student_id=current_user.id)\
        .order_by(QuizAttempt.started_at.desc()).all()
    
    return render_template('student/history.html', attempts=attempts)

@quiz_bp.route('/quiz/attempt/<int:attempt_id>/export')
@login_required
def export_attempt_results(attempt_id):
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    if attempt.student_id != current_user.id and attempt.quiz.author_id != current_user.id:
        flash('You do not have permission to export these results.', 'danger')
        return redirect(url_for('main.index'))
    
    # Create CSV data
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Quiz Title', 'Student', 'Score', 'Max Score', 'Percentage', 'Completion Date', 'Time Taken'])
    
    # Write attempt data
    student = User.query.get(attempt.student_id)
    time_taken = (attempt.completed_at - attempt.started_at).total_seconds() / 60 if attempt.completed_at else 0
    writer.writerow([
        attempt.quiz.title,
        student.username,
        attempt.score,
        attempt.max_score,
        f"{(attempt.score / attempt.max_score * 100):.2f}%" if attempt.max_score > 0 else "0%",
        attempt.completed_at.strftime('%Y-%m-%d %H:%M:%S') if attempt.completed_at else 'Not completed',
        f"{time_taken:.2f} minutes"
    ])
    
    # Add a blank line
    writer.writerow([])
    
    # Write question-wise breakdown
    writer.writerow(['Question', 'Type', 'Your Answer', 'Correct Answer', 'Points Earned', 'Max Points', 'Result'])
    
    for answer in attempt.answers:
        if answer.question.question_type == 'mcq':
            student_answer = answer.selected_option.text if answer.selected_option else "No answer"
            correct_answer = next((opt.text for opt in answer.question.options if opt.is_correct), "No correct answer")
        else:  # descriptive
            student_answer = answer.text_answer or "No answer"
            correct_answer = answer.question.options[0].text if answer.question.options else "No correct answer"
        
        writer.writerow([
            answer.question.text,
            answer.question.question_type.upper(),
            student_answer,
            correct_answer,
            answer.points_earned,
            answer.question.points,
            "Correct" if answer.is_correct else "Incorrect"
        ])
    
    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=quiz_attempt_{attempt_id}_results.csv'
        }
    ) 