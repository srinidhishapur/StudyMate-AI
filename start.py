"""
start.py - Simple startup script for StudyMate AI
Run: python start.py
"""
import os
import sys

# Load .env first
from dotenv import load_dotenv
load_dotenv(override=True)

# Verify environment
db_url = os.environ.get('DATABASE_URL', '')
secret = os.environ.get('SECRET_KEY', '')
if not db_url:
    print("ERROR: DATABASE_URL not set. Create a .env file first.")
    print("  Run: python setup_env.py")
    sys.exit(1)
if not secret:
    print("ERROR: SECRET_KEY not set. Create a .env file first.")
    sys.exit(1)

# Import and run
from app import create_app, db

app = create_app()

with app.app_context():
    # Auto-create tables if they don't exist yet
    db.create_all()

print("")
print("=" * 50)
print("  StudyMate AI - Smart Study Generator")
print("=" * 50)
print(f"  URL    -> http://localhost:5000")
print(f"  Debug  -> {app.config['DEBUG']}")
wx = bool(os.environ.get('WATSONX_API_KEY','').strip()
          and os.environ.get('WATSONX_API_KEY') != 'your-ibm-cloud-api-key')
print(f"  AI     -> {'ENABLED' if wx else 'Add WATSONX keys to .env to enable'}")
print("=" * 50)
print("  Press CTRL+C to stop the server")
print("")

# Use werkzeug directly to avoid reloader issues on Windows
from werkzeug.serving import run_simple
run_simple('0.0.0.0', 5000, app, use_reloader=False, use_debugger=True)
