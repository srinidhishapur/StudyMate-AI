"""live_check.py - Diagnose exactly what's wrong with the running app."""
import os, sys, traceback
from dotenv import load_dotenv
load_dotenv(override=True)

print("=== ENVIRONMENT ===")
print(f"SECRET_KEY set    : {bool(os.environ.get('SECRET_KEY'))}")
print(f"DATABASE_URL      : {os.environ.get('DATABASE_URL','NOT SET')[:60]}")
print(f"FLASK_ENV         : {os.environ.get('FLASK_ENV','NOT SET')}")
print(f"WATSONX_API_KEY   : {'SET' if os.environ.get('WATSONX_API_KEY','').strip() and os.environ.get('WATSONX_API_KEY') != 'your-ibm-cloud-api-key' else 'NOT SET'}")
print(f"WATSONX_PROJECT_ID: {'SET' if os.environ.get('WATSONX_PROJECT_ID','').strip() and os.environ.get('WATSONX_PROJECT_ID') != 'your-watsonx-project-id' else 'NOT SET'}")

print("\n=== APP IMPORT ===")
try:
    from app import create_app, db
    print("  app imported OK")
except Exception as e:
    print(f"  IMPORT FAILED: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n=== APP CREATE ===")
try:
    app = create_app()
    print(f"  App created OK")
    print(f"  Blueprints: {list(app.blueprints.keys())}")
    print(f"  DEBUG: {app.config['DEBUG']}")
    print(f"  DB URL: {str(app.config['SQLALCHEMY_DATABASE_URI'])[:60]}")
except Exception as e:
    print(f"  CREATE FAILED: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n=== DATABASE ===")
try:
    with app.app_context():
        from sqlalchemy import text, inspect as sa_inspect
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("  DB connection OK")
        tables = sa_inspect(db.engine).get_table_names()
        print(f"  Tables: {tables}")
        if 'users' not in tables:
            print("  WARNING: 'users' table missing - run: python init_db.py")
except Exception as e:
    print(f"  DB ERROR: {e}")
    traceback.print_exc()

print("\n=== LIVE REQUEST TEST ===")
try:
    with app.app_context():
        with app.test_client() as c:
            # Landing page
            r = c.get('/')
            print(f"  GET /           -> {r.status_code}")

            r = c.get('/auth/register')
            print(f"  GET /auth/register -> {r.status_code}")
            if r.status_code != 200:
                print(f"    BODY: {r.data[:300].decode(errors='replace')}")

            r = c.get('/auth/login')
            print(f"  GET /auth/login -> {r.status_code}")

            # Try accessing dashboard without login
            r = c.get('/dashboard', follow_redirects=False)
            print(f"  GET /dashboard (no login) -> {r.status_code} (should be 302)")
except Exception as e:
    print(f"  REQUEST ERROR: {e}")
    traceback.print_exc()

print("\n=== TEMPLATES ===")
import os
template_dir = os.path.join('app', 'templates')
required = [
    'base.html',
    'auth/register.html', 'auth/login.html',
    'main/index.html', 'main/dashboard.html',
    'main/documents.html', 'main/study_plans.html',
    'main/progress.html', 'main/profile.html',
    'ai/document_detail.html', 'ai/summary.html',
    'ai/quiz.html', 'ai/quiz_results.html',
    'ai/flashcards.html', 'ai/chat.html',
    'ai/study_plan_detail.html',
]
for t in required:
    path = os.path.join(template_dir, t)
    exists = os.path.exists(path)
    print(f"  {'OK' if exists else 'MISSING'} {t}")

print("\n=== STATIC FILES ===")
for f in ['app/static/css/style.css', 'app/static/js/main.js']:
    size = os.path.getsize(f) if os.path.exists(f) else 0
    print(f"  {'OK' if size > 100 else 'MISSING/EMPTY'} {f}  ({size} bytes)")

print("\n=== DONE ===")
print("If all above says OK, run: python run.py")
print("Then open http://localhost:5000 in your browser")
