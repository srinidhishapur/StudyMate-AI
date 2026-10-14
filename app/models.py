from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(128), nullable=True)
    avatar_url = db.Column(db.String(256), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    documents = db.relationship('Document', backref='owner', lazy='dynamic',
                                cascade='all, delete-orphan')
    study_plans = db.relationship('StudyPlan', backref='owner', lazy='dynamic',
                                  cascade='all, delete-orphan')
    quiz_attempts = db.relationship('QuizAttempt', backref='student', lazy='dynamic',
                                    cascade='all, delete-orphan')
    progress_records = db.relationship('LearningProgress', backref='student', lazy='dynamic',
                                       cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

    def get_document_count(self):
        return self.documents.count()

    def get_study_plan_count(self):
        return self.study_plans.count()

    def get_quiz_count(self):
        return self.quiz_attempts.count()


class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(256), nullable=False)
    filename = db.Column(db.String(256), nullable=False)
    original_filename = db.Column(db.String(256), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)  # 'pdf' or 'txt'
    file_size = db.Column(db.Integer, nullable=True)  # bytes
    subject = db.Column(db.String(128), nullable=True)
    description = db.Column(db.Text, nullable=True)
    page_count = db.Column(db.Integer, nullable=True)
    word_count = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='uploaded')  # uploaded, processing, ready, error
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)

    # AI-generated content
    summary = db.Column(db.Text, nullable=True)
    key_topics = db.Column(db.Text, nullable=True)  # JSON string

    # Relationships
    flashcards = db.relationship('Flashcard', backref='document', lazy='dynamic',
                                 cascade='all, delete-orphan')
    quiz_questions = db.relationship('QuizQuestion', backref='document', lazy='dynamic',
                                     cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Document {self.title}>'

    def get_size_display(self):
        if self.file_size:
            if self.file_size < 1024:
                return f'{self.file_size} B'
            elif self.file_size < 1024 * 1024:
                return f'{self.file_size // 1024} KB'
            else:
                return f'{self.file_size // (1024 * 1024):.1f} MB'
        return 'Unknown'


class StudyPlan(db.Model):
    __tablename__ = 'study_plans'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(256), nullable=False)
    subject = db.Column(db.String(128), nullable=True)
    goal = db.Column(db.Text, nullable=True)
    duration_days = db.Column(db.Integer, default=30)
    difficulty = db.Column(db.String(20), default='medium')  # easy, medium, hard
    status = db.Column(db.String(20), default='active')  # active, completed, paused
    progress_percent = db.Column(db.Integer, default=0)
    plan_content = db.Column(db.Text, nullable=True)  # JSON string with daily tasks
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    target_date = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<StudyPlan {self.title}>'


class Flashcard(db.Model):
    __tablename__ = 'flashcards'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    front = db.Column(db.Text, nullable=False)
    back = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), default='medium')
    times_reviewed = db.Column(db.Integer, default=0)
    last_reviewed = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Flashcard {self.id}>'


class QuizQuestion(db.Model):
    __tablename__ = 'quiz_questions'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.Text, nullable=False)
    option_b = db.Column(db.Text, nullable=False)
    option_c = db.Column(db.Text, nullable=False)
    option_d = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', 'D'
    explanation = db.Column(db.Text, nullable=True)
    topic = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<QuizQuestion {self.id}>'


class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)
    score = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    percentage = db.Column(db.Float, default=0.0)
    time_taken_seconds = db.Column(db.Integer, nullable=True)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<QuizAttempt {self.id} score={self.score}/{self.total_questions}>'


class LearningProgress(db.Model):
    __tablename__ = 'learning_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)
    # e.g. 'document_upload', 'quiz_completed', 'flashcard_review', 'summary_generated'
    activity_detail = db.Column(db.Text, nullable=True)
    score = db.Column(db.Float, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<LearningProgress {self.activity_type} at {self.recorded_at}>'

    def save_to_db(self):
        from app import db
        db.session.add(self)
        db.session.commit()


class ChatHistory(db.Model):
    __tablename__ = 'chat_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ChatHistory {self.role} at {self.created_at}>'
