"""
StudyMate AI – Smart Study Generator Agent
Entry point for the Flask application.

Run:  python run.py
"""
import os
from dotenv import load_dotenv

# Load .env BEFORE importing app so all config picks it up
load_dotenv(override=True)

from app import create_app, db
from app.models import (User, Document, StudyPlan, Flashcard, QuizQuestion,
                        QuizAttempt, LearningProgress, ChatHistory)

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Document=Document, StudyPlan=StudyPlan,
                Flashcard=Flashcard, QuizQuestion=QuizQuestion,
                QuizAttempt=QuizAttempt, LearningProgress=LearningProgress,
                ChatHistory=ChatHistory)


if __name__ == '__main__':
    db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    wx_key = bool(os.environ.get('WATSONX_API_KEY', '').strip())
    wx_pid = bool(os.environ.get('WATSONX_PROJECT_ID', '').strip())

    print('\n' + '='*55)
    print('  StudyMate AI  --  Smart Study Generator Agent')
    print('='*55)
    print(f'  DB     : {db_url[:55]}')
    print(f'  watsonx: {"CONFIGURED" if (wx_key and wx_pid) else "NOT configured (AI features disabled)"}')
    print(f'  Debug  : {app.config.get("DEBUG")}')
    print('  URL    : http://localhost:5000')
    print('='*55 + '\n')

    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=True)
