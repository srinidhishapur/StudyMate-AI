"""
app/ai/routes.py

All AI-powered feature routes:
  POST /ai/summarize/<doc_id>       – generate / view summary
  GET  /ai/summary/<doc_id>         – view existing summary
  POST /ai/generate-quiz/<doc_id>   – generate quiz questions
  GET  /ai/quiz/<doc_id>            – take the quiz
  POST /ai/quiz/<doc_id>/submit     – submit quiz answers
  POST /ai/generate-flashcards/<doc_id> – generate flashcards
  GET  /ai/flashcards/<doc_id>      – review flashcards
  GET  /ai/chat/<doc_id>            – RAG chat page
  POST /ai/chat/<doc_id>/message    – send a chat message (AJAX)
  POST /ai/study-plan/<plan_id>/generate – generate AI study plan
"""
import json
import os
from datetime import datetime

from flask import (render_template, redirect, url_for, flash,
                   request, jsonify, current_app)
from flask_login import login_required, current_user

from app.ai import ai
from app import db
from app.models import (Document, Flashcard, QuizQuestion, QuizAttempt,
                         LearningProgress, StudyPlan, ChatHistory)
from app.utils.file_processor import extract_text_from_file, chunk_text
from app.services import watsonx_service as wx


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_doc_or_404(doc_id: int) -> Document:
    return Document.query.filter_by(
        id=doc_id, user_id=current_user.id
    ).first_or_404()


def _read_document_text(doc: Document) -> str:
    """Return cached extracted text, or extract & cache now."""
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, str(doc.user_id), doc.filename)

    if not os.path.exists(file_path):
        return ''

    text, pages, words = extract_text_from_file(file_path, doc.file_type)

    # Cache metadata back onto the document
    if pages and not doc.page_count:
        doc.page_count = pages
    if words and not doc.word_count:
        doc.word_count = words
        db.session.commit()

    return text


def _check_watsonx() -> bool:
    """Flash an error and return False if watsonx is not configured."""
    if not wx.is_configured():
        flash(
            'IBM watsonx AI is not configured. '
            'Please add WATSONX_API_KEY and WATSONX_PROJECT_ID to your .env file.',
            'warning'
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Summarization
# ---------------------------------------------------------------------------

@ai.route('/summarize/<int:doc_id>', methods=['POST'])
@login_required
def summarize(doc_id):
    doc = _get_doc_or_404(doc_id)

    if not _check_watsonx():
        return redirect(url_for('main.documents'))

    text = _read_document_text(doc)
    if not text:
        flash('Could not extract text from the document.', 'danger')
        return redirect(url_for('main.documents'))

    try:
        doc.status = 'processing'
        db.session.commit()

        summary = wx.generate_summary(text, title=doc.title)
        doc.summary = summary
        doc.status = 'ready'
        doc.processed_at = datetime.utcnow()
        db.session.commit()

        LearningProgress(
            user_id=current_user.id,
            activity_type='summary_generated',
            activity_detail=f'Summary for: {doc.title}'
        ).save_to_db()

        flash('AI summary generated successfully!', 'success')
    except Exception as e:
        doc.status = 'error'
        db.session.commit()
        flash(f'AI Error: {str(e)}', 'danger')

    return redirect(url_for('ai.view_summary', doc_id=doc_id))


@ai.route('/summary/<int:doc_id>')
@login_required
def view_summary(doc_id):
    doc = _get_doc_or_404(doc_id)
    return render_template('ai/summary.html', doc=doc, title=f'Summary – {doc.title}')


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------

@ai.route('/generate-quiz/<int:doc_id>', methods=['POST'])
@login_required
def generate_quiz(doc_id):
    doc = _get_doc_or_404(doc_id)

    if not _check_watsonx():
        return redirect(url_for('main.documents'))

    # Delete old questions for this doc
    QuizQuestion.query.filter_by(document_id=doc_id).delete()
    db.session.commit()

    text = _read_document_text(doc)
    if not text:
        flash('Could not extract text from the document.', 'danger')
        return redirect(url_for('main.documents'))

    num_q = int(request.form.get('num_questions', 5))
    num_q = max(3, min(10, num_q))

    try:
        questions = wx.generate_quiz(text, num_questions=num_q, title=doc.title)
        if not questions:
            flash('AI could not generate quiz questions. Please try again.', 'warning')
            return redirect(url_for('ai.view_document', doc_id=doc_id))

        for q in questions:
            qq = QuizQuestion(
                document_id=doc_id,
                question=q.get('question', ''),
                option_a=q.get('option_a', ''),
                option_b=q.get('option_b', ''),
                option_c=q.get('option_c', ''),
                option_d=q.get('option_d', ''),
                correct_answer=q.get('correct_answer', 'A').upper(),
                explanation=q.get('explanation', ''),
                topic=q.get('topic', '')
            )
            db.session.add(qq)
        db.session.commit()

        flash(f'{len(questions)} quiz questions generated!', 'success')
    except Exception as e:
        flash(f'AI Error: {str(e)}', 'danger')
        return redirect(url_for('ai.view_document', doc_id=doc_id))

    return redirect(url_for('ai.take_quiz', doc_id=doc_id))


@ai.route('/quiz/<int:doc_id>')
@login_required
def take_quiz(doc_id):
    doc = _get_doc_or_404(doc_id)
    questions = QuizQuestion.query.filter_by(document_id=doc_id).all()
    if not questions:
        flash('No quiz questions yet. Generate a quiz first.', 'info')
        return redirect(url_for('ai.view_document', doc_id=doc_id))
    return render_template('ai/quiz.html', doc=doc, questions=questions,
                           title=f'Quiz – {doc.title}')


@ai.route('/quiz/<int:doc_id>/submit', methods=['POST'])
@login_required
def submit_quiz(doc_id):
    doc = _get_doc_or_404(doc_id)
    questions = QuizQuestion.query.filter_by(document_id=doc_id).all()

    score = 0
    results = []
    for q in questions:
        user_answer = request.form.get(f'q_{q.id}', '').upper()
        correct = (user_answer == q.correct_answer)
        if correct:
            score += 1
        results.append({
            'question': q.question,
            'user_answer': user_answer,
            'correct_answer': q.correct_answer,
            'correct': correct,
            'explanation': q.explanation,
            'option_a': q.option_a,
            'option_b': q.option_b,
            'option_c': q.option_c,
            'option_d': q.option_d,
        })

    total = len(questions)
    percentage = (score / total * 100) if total > 0 else 0

    attempt = QuizAttempt(
        user_id=current_user.id,
        document_id=doc_id,
        score=score,
        total_questions=total,
        percentage=round(percentage, 1)
    )
    db.session.add(attempt)

    LearningProgress(
        user_id=current_user.id,
        activity_type='quiz_completed',
        activity_detail=f'Quiz on "{doc.title}": {score}/{total} ({percentage:.0f}%)',
        score=percentage
    ).save_to_db()

    flash(f'Quiz submitted! You scored {score}/{total} ({percentage:.0f}%)', 'success')
    return render_template('ai/quiz_results.html', doc=doc, results=results,
                           score=score, total=total, percentage=percentage,
                           title='Quiz Results')


# ---------------------------------------------------------------------------
# Flashcards
# ---------------------------------------------------------------------------

@ai.route('/generate-flashcards/<int:doc_id>', methods=['POST'])
@login_required
def generate_flashcards(doc_id):
    doc = _get_doc_or_404(doc_id)

    if not _check_watsonx():
        return redirect(url_for('main.documents'))

    Flashcard.query.filter_by(document_id=doc_id).delete()
    db.session.commit()

    text = _read_document_text(doc)
    if not text:
        flash('Could not extract text from the document.', 'danger')
        return redirect(url_for('main.documents'))

    num_cards = int(request.form.get('num_cards', 8))
    num_cards = max(4, min(15, num_cards))

    try:
        cards = wx.generate_flashcards(text, num_cards=num_cards, title=doc.title)
        if not cards:
            flash('AI could not generate flashcards. Please try again.', 'warning')
            return redirect(url_for('ai.view_document', doc_id=doc_id))

        for card in cards:
            fc = Flashcard(
                document_id=doc_id,
                front=card.get('front', ''),
                back=card.get('back', ''),
                difficulty=card.get('difficulty', 'medium')
            )
            db.session.add(fc)
        db.session.commit()

        LearningProgress(
            user_id=current_user.id,
            activity_type='flashcards_created',
            activity_detail=f'{len(cards)} flashcards for: {doc.title}'
        ).save_to_db()

        flash(f'{len(cards)} flashcards created!', 'success')
    except Exception as e:
        flash(f'AI Error: {str(e)}', 'danger')
        return redirect(url_for('ai.view_document', doc_id=doc_id))

    return redirect(url_for('ai.review_flashcards', doc_id=doc_id))


@ai.route('/flashcards/<int:doc_id>')
@login_required
def review_flashcards(doc_id):
    doc = _get_doc_or_404(doc_id)
    cards = Flashcard.query.filter_by(document_id=doc_id).all()
    if not cards:
        flash('No flashcards yet. Generate flashcards first.', 'info')
        return redirect(url_for('ai.view_document', doc_id=doc_id))
    return render_template('ai/flashcards.html', doc=doc, cards=cards,
                           title=f'Flashcards – {doc.title}')


@ai.route('/flashcards/<int:doc_id>/mark-reviewed', methods=['POST'])
@login_required
def mark_flashcard_reviewed(doc_id):
    card_id = request.form.get('card_id', type=int)
    card = Flashcard.query.filter_by(id=card_id, document_id=doc_id).first()
    if card:
        card.times_reviewed += 1
        card.last_reviewed = datetime.utcnow()
        db.session.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# RAG Chat
# ---------------------------------------------------------------------------

@ai.route('/chat/<int:doc_id>')
@login_required
def chat(doc_id):
    doc = _get_doc_or_404(doc_id)
    history = ChatHistory.query.filter_by(
        user_id=current_user.id, document_id=doc_id
    ).order_by(ChatHistory.created_at.asc()).all()
    return render_template('ai/chat.html', doc=doc, history=history,
                           title=f'Chat – {doc.title}',
                           watsonx_ready=wx.is_configured())


@ai.route('/chat/<int:doc_id>/message', methods=['POST'])
@login_required
def chat_message(doc_id):
    doc = _get_doc_or_404(doc_id)

    if not wx.is_configured():
        return jsonify({'error': 'IBM watsonx AI is not configured.'}), 503

    data = request.get_json(silent=True) or {}
    question = (data.get('message') or '').strip()
    if not question:
        return jsonify({'error': 'Empty message.'}), 400

    # Save user message
    user_msg = ChatHistory(
        user_id=current_user.id,
        document_id=doc_id,
        role='user',
        content=question
    )
    db.session.add(user_msg)
    db.session.commit()

    # Build context chunks from document
    text = _read_document_text(doc)
    chunks = chunk_text(text, chunk_size=1200, overlap=150)

    # Simple keyword relevance — pick chunks containing question keywords
    q_words = set(question.lower().split())
    scored = []
    for chunk in chunks:
        cl = chunk.lower()
        score = sum(1 for w in q_words if w in cl)
        scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    context_chunks = [c for _, c in scored[:4]] or chunks[:4]

    # Load recent chat history
    history_rows = ChatHistory.query.filter_by(
        user_id=current_user.id, document_id=doc_id
    ).order_by(ChatHistory.created_at.asc()).all()
    history = [{'role': h.role, 'content': h.content} for h in history_rows[-8:]]

    try:
        answer = wx.chat_with_document(question, context_chunks, history)
    except Exception as e:
        answer = f'Sorry, I encountered an error: {str(e)}'

    # Save assistant message
    ai_msg = ChatHistory(
        user_id=current_user.id,
        document_id=doc_id,
        role='assistant',
        content=answer
    )
    db.session.add(ai_msg)

    LearningProgress(
        user_id=current_user.id,
        activity_type='rag_chat',
        activity_detail=f'Chat with: {doc.title}'
    ).save_to_db()

    return jsonify({'answer': answer})


@ai.route('/chat/<int:doc_id>/clear', methods=['POST'])
@login_required
def clear_chat(doc_id):
    _get_doc_or_404(doc_id)
    ChatHistory.query.filter_by(
        user_id=current_user.id, document_id=doc_id
    ).delete()
    db.session.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Document detail page (hub for all AI actions on one doc)
# ---------------------------------------------------------------------------

@ai.route('/document/<int:doc_id>')
@login_required
def view_document(doc_id):
    doc = _get_doc_or_404(doc_id)
    questions = QuizQuestion.query.filter_by(document_id=doc_id).all()
    cards = Flashcard.query.filter_by(document_id=doc_id).all()
    return render_template('ai/document_detail.html',
                           doc=doc,
                           questions=questions,
                           cards=cards,
                           watsonx_ready=wx.is_configured(),
                           title=doc.title)


# ---------------------------------------------------------------------------
# AI Study Plan Generation
# ---------------------------------------------------------------------------

@ai.route('/study-plan/<int:plan_id>/generate', methods=['POST'])
@login_required
def generate_study_plan(plan_id):
    plan = StudyPlan.query.filter_by(
        id=plan_id, user_id=current_user.id
    ).first_or_404()

    if not _check_watsonx():
        return redirect(url_for('main.study_plans'))

    try:
        content = wx.generate_study_plan(
            title=plan.title,
            subject=plan.subject or '',
            goal=plan.goal or '',
            duration_days=plan.duration_days,
            difficulty=plan.difficulty
        )
        plan.plan_content = content
        db.session.commit()

        LearningProgress(
            user_id=current_user.id,
            activity_type='study_plan_generated',
            activity_detail=f'AI plan for: {plan.title}'
        ).save_to_db()

        flash('AI study plan generated!', 'success')
    except Exception as e:
        flash(f'AI Error: {str(e)}', 'danger')

    return redirect(url_for('ai.view_study_plan', plan_id=plan_id))


@ai.route('/study-plan/<int:plan_id>')
@login_required
def view_study_plan(plan_id):
    plan = StudyPlan.query.filter_by(
        id=plan_id, user_id=current_user.id
    ).first_or_404()
    return render_template('ai/study_plan_detail.html', plan=plan,
                           watsonx_ready=wx.is_configured(),
                           title=plan.title)
