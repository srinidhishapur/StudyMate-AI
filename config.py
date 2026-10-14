import os
from dotenv import load_dotenv

# Always load .env from project root (works even when gitignored)
load_dotenv(override=True)


def _fix_db_url(url: str) -> str:
    """Ensure psycopg2 driver prefix is present for SQLAlchemy 2.x."""
    if url and url.startswith('postgresql://') and 'psycopg2' not in url:
        return url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'studymate-fallback-secret-key-2024'

    @staticmethod
    def get_db_url() -> str:
        """Read DATABASE_URL fresh from environment each time create_app() is called."""
        return _fix_db_url(
            os.environ.get('DATABASE_URL') or
            'postgresql+psycopg2://postgres:postgres@localhost:5432/studymate_db'
        )

    SQLALCHEMY_DATABASE_URI = _fix_db_url(
        os.environ.get('DATABASE_URL') or
        'postgresql+psycopg2://postgres:postgres@localhost:5432/studymate_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'txt'}
    WTF_CSRF_ENABLED = True

    # IBM watsonx AI
    WATSONX_API_KEY    = os.environ.get('WATSONX_API_KEY', '')
    WATSONX_PROJECT_ID = os.environ.get('WATSONX_PROJECT_ID', '')
    WATSONX_URL        = os.environ.get('WATSONX_URL', 'https://us-south.ml.cloud.ibm.com')
    WATSONX_MODEL_ID   = os.environ.get('WATSONX_MODEL_ID', 'ibm/granite-13b-instruct-v2')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    WTF_CSRF_SSL_STRICT = False


config = {
    'development':  DevelopmentConfig,
    'production':   ProductionConfig,
    'default':      DevelopmentConfig,
}
