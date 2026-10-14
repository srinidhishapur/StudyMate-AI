from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import config
import os

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()
csrf = CSRFProtect()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    cfg_obj = config.get(config_name, config['default'])
    app.config.from_object(cfg_obj)
    # Re-read DATABASE_URL at call time so .env changes after import are respected
    app.config['SQLALCHEMY_DATABASE_URI'] = cfg_obj.get_db_url()

    # Ensure upload folder exists
    upload_folder = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Register blueprints
    from app.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from app.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from app.ai import ai as ai_blueprint
    app.register_blueprint(ai_blueprint, url_prefix='/ai')

    # Context processors
    from datetime import datetime

    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    # Custom Jinja2 filters
    import re as _re

    @app.template_filter('markdown_to_html')
    def markdown_to_html_filter(text):
        """Convert basic markdown to HTML (headers, bold, bullets)."""
        if not text:
            return ''
        import html as _html
        text = _html.escape(text)
        # Headers
        text = _re.sub(r'^### (.+)$', r'<h5 class="fw-semibold mt-3 mb-1">\1</h5>', text, flags=_re.MULTILINE)
        text = _re.sub(r'^## (.+)$', r'<h4 class="fw-bold mt-4 mb-2 text-primary">\1</h4>', text, flags=_re.MULTILINE)
        text = _re.sub(r'^# (.+)$', r'<h3 class="fw-bold mt-4 mb-2">\1</h3>', text, flags=_re.MULTILINE)
        # Bold
        text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Bullet lists
        text = _re.sub(r'^- (.+)$', r'<li>\1</li>', text, flags=_re.MULTILINE)
        text = _re.sub(r'(<li>.*?</li>(\n|$))+', lambda m: '<ul class="mb-2">' + m.group(0) + '</ul>', text, flags=_re.DOTALL)
        # Paragraphs (blank-line separated)
        paras = _re.split(r'\n{2,}', text)
        result = []
        for p in paras:
            p = p.strip()
            if p and not p.startswith('<h') and not p.startswith('<ul'):
                p = f'<p class="mb-2">{p}</p>'
            result.append(p)
        return '\n'.join(result)

    @app.template_filter('format_number')
    def format_number_filter(n):
        return f'{n:,}' if n else ''

    return app
