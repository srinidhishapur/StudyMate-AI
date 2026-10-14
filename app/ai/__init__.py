from flask import Blueprint

ai = Blueprint('ai', __name__)

from app.ai import routes  # noqa: F401, E402
