from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.main import main
from app.models import Document, StudyPlan, QuizAttempt, LearningProgress, Flashcard
from app import db
from datetime import datetime, timedelta
import os
import uuid


@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('main/index.html', title='StudyMate AI – Smart Study Generator')


@main.route('/dashboard')
@login_required
def dashboard():
    # Gather stats for dashboard cards
    doc_count = current_user.get_document_count()
    plan_count = current_user.get_study_plan_count()
    quiz_count = current_user.get_quiz_count()

    # Recent documents (last 5)
    recent_docs = Document.query.filter_by(user_id=current_user.id)\
        .order_by(Document.uploaded_at.desc()).limit(5).all()

    # Active study plans
    active_plans = StudyPlan.query.filter_by(
        user_id=current_user.id, status='active'
    ).order_by(StudyPlan.created_at.desc()).limit(3).all()

    # Recent quiz attempts (last 5)
    recent_quizzes = QuizAttempt.query.filter_by(user_id=current_user.id)\
        .order_by(QuizAttempt.attempted_at.desc()).limit(5).all()

    # Average quiz score
    all_quizzes = QuizAttempt.query.filter_by(user_id=current_user.id).all()
    avg_score = 0.0
    if all_quizzes:
        avg_score = sum(q.percentage for q in all_quizzes) / len(all_quizzes)

    # Recent activity (last 10)
    recent_activity = LearningProgress.query.filter_by(user_id=current_user.id)\
        .order_by(LearningProgress.recorded_at.desc()).limit(10).all()

    # Weekly activity data for chart (last 7 days)
    weekly_data = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        count = LearningProgress.query.filter(
            LearningProgress.user_id == current_user.id,
            LearningProgress.recorded_at >= day_start,
            LearningProgress.recorded_at <= day_end
        ).count()
        weekly_data.append({'day': day.strftime('%a'), 'count': count})

    return render_template('main/dashboard.html',
                           title='Dashboard',
                           doc_count=doc_count,
                           plan_count=plan_count,
                           quiz_count=quiz_count,
                           recent_docs=recent_docs,
                           active_plans=active_plans,
                           recent_quizzes=recent_quizzes,
                           avg_score=avg_score,
                           recent_activity=recent_activity,
                           weekly_data=weekly_data)


@main.route('/documents')
@login_required
def documents():
    page = request.args.get('page', 1, type=int)
    per_page = 9
    docs = Document.query.filter_by(user_id=current_user.id)\
        .order_by(Document.uploaded_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    return render_template('main/documents.html', title='My Documents', docs=docs)


@main.route('/study-plans')
@login_required
def study_plans():
    plans = StudyPlan.query.filter_by(user_id=current_user.id)\
        .order_by(StudyPlan.created_at.desc()).all()
    return render_template('main/study_plans.html', title='Study Plans', plans=plans)


@main.route('/progress')
@login_required
def progress():
    all_quizzes = QuizAttempt.query.filter_by(user_id=current_user.id)\
        .order_by(QuizAttempt.attempted_at.desc()).all()

    # 30-day activity
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    monthly_activity = LearningProgress.query.filter(
        LearningProgress.user_id == current_user.id,
        LearningProgress.recorded_at >= thirty_days_ago
    ).order_by(LearningProgress.recorded_at.desc()).all()

    total_docs = current_user.get_document_count()
    total_quizzes = current_user.get_quiz_count()
    avg_score = 0.0
    if all_quizzes:
        avg_score = sum(q.percentage for q in all_quizzes) / len(all_quizzes)

    return render_template('main/progress.html',
                           title='Learning Progress',
                           all_quizzes=all_quizzes,
                           monthly_activity=monthly_activity,
                           total_docs=total_docs,
                           total_quizzes=total_quizzes,
                           avg_score=avg_score)


@main.route('/documents/upload', methods=['POST'])
@login_required
def upload_document():
    title = request.form.get('title', '').strip()
    subject = request.form.get('subject', '').strip()
    description = request.form.get('description', '').strip()
    file = request.files.get('file')

    if not title:
        flash('Document title is required.', 'danger')
        return redirect(url_for('main.documents'))

    if not file or file.filename == '':
        flash('Please select a file to upload.', 'danger')
        return redirect(url_for('main.documents'))

    # Validate extension
    allowed = current_app.config['ALLOWED_EXTENSIONS']
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed:
        flash('Only PDF and TXT files are allowed.', 'danger')
        return redirect(url_for('main.documents'))

    # Secure filename with UUID
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    upload_folder = current_app.config['UPLOAD_FOLDER']
    user_folder = os.path.join(upload_folder, str(current_user.id))
    os.makedirs(user_folder, exist_ok=True)
    file_path = os.path.join(user_folder, unique_name)
    file.save(file_path)
    file_size = os.path.getsize(file_path)

    doc = Document(
        user_id=current_user.id,
        title=title,
        filename=unique_name,
        original_filename=file.filename,
        file_type=ext,
        file_size=file_size,
        subject=subject or None,
        description=description or None,
        status='uploaded'
    )
    db.session.add(doc)
    db.session.flush()  # get doc.id

    progress = LearningProgress(
        user_id=current_user.id,
        activity_type='document_upload',
        activity_detail=f'Uploaded: {title}'
    )
    db.session.add(progress)
    db.session.commit()

    flash(f'"{title}" uploaded successfully!', 'success')
    return redirect(url_for('main.documents'))


@main.route('/study-plans/create', methods=['POST'])
@login_required
def create_study_plan():
    title = request.form.get('title', '').strip()
    subject = request.form.get('subject', '').strip()
    goal = request.form.get('goal', '').strip()
    duration_days = request.form.get('duration_days', 30, type=int)
    difficulty = request.form.get('difficulty', 'medium')

    if not title:
        flash('Plan title is required.', 'danger')
        return redirect(url_for('main.study_plans'))

    plan = StudyPlan(
        user_id=current_user.id,
        title=title,
        subject=subject or None,
        goal=goal or None,
        duration_days=max(1, min(365, duration_days)),
        difficulty=difficulty if difficulty in ('easy', 'medium', 'hard') else 'medium'
    )
    db.session.add(plan)

    progress = LearningProgress(
        user_id=current_user.id,
        activity_type='study_plan_created',
        activity_detail=f'Created plan: {title}'
    )
    db.session.add(progress)
    db.session.commit()

    flash(f'Study plan "{title}" created!', 'success')
    return redirect(url_for('main.study_plans'))


@main.route('/study-plans/<int:plan_id>/delete', methods=['POST'])
@login_required
def delete_study_plan(plan_id):
    plan = StudyPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
    db.session.delete(plan)
    db.session.commit()
    flash('Study plan deleted.', 'info')
    return redirect(url_for('main.study_plans'))


@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        if full_name and len(full_name) >= 2:
            current_user.full_name = full_name
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        else:
            flash('Full name must be at least 2 characters.', 'danger')
        return redirect(url_for('main.profile'))

    return render_template('main/profile.html', title='My Profile')
