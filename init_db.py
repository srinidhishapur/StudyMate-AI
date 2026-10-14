"""
init_db.py — Creates all database tables for StudyMate AI.
Run once after setting up your PostgreSQL database.

Usage:
    python init_db.py
"""
from dotenv import load_dotenv
load_dotenv(override=True)

from app import create_app, db
from app.models import (User, Document, StudyPlan, Flashcard,
                         QuizQuestion, QuizAttempt, LearningProgress, ChatHistory)


def init_db():
    app = create_app()
    with app.app_context():
        print("Creating all database tables...")
        db.create_all()
        print("Tables created successfully.")
        print("\nTables in database:")
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        for table in inspector.get_table_names():
            print(f"  - {table}")
        print("\nDatabase initialized! You can now run: python run.py")


if __name__ == '__main__':
    init_db()
