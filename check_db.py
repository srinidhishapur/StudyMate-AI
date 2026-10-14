"""
check_db.py  --  Safe database connection diagnostic for StudyMate AI.
Does NOT print your password or modify any data.

Run:  python check_db.py
"""
import os, sys, re
from dotenv import load_dotenv

# ── Step 1: Load .env ────────────────────────────────────────────
# find_dotenv() searches upward from cwd, handles edge cases
from dotenv import find_dotenv
dotenv_path = find_dotenv(usecwd=True)
loaded = load_dotenv(dotenv_path, override=True)

print("=" * 58)
print("  StudyMate AI  --  Database Connection Diagnostic")
print("=" * 58)

print(f"\n[1] .env file")
print(f"    Path   : {dotenv_path if dotenv_path else 'NOT FOUND'}")
print(f"    Loaded : {loaded}")
if not dotenv_path:
    print("    FIX    : Create a .env file in the project root.")
    print("             Copy .env.example and fill in your password.")

# ── Step 2: Read DATABASE_URL and mask the password ──────────────
raw_url = os.environ.get('DATABASE_URL', '')
print(f"\n[2] DATABASE_URL from environment")
if not raw_url:
    print("    Status : NOT SET")
    print("    FIX    : Add DATABASE_URL=postgresql+psycopg2://postgres:YOURPW@localhost:5432/studymate_db")
    print("             to your .env file.")
else:
    # Mask password safely
    masked = re.sub(r'(:)([^:@/]+)(@)', r'\1****\3', raw_url)
    print(f"    Value  : {masked}")

# ── Step 3: Check what config.py resolves to ────────────────────
print(f"\n[3] Config class resolution")
try:
    from config import Config, _fix_db_url
    resolved = Config.SQLALCHEMY_DATABASE_URI
    masked_resolved = re.sub(r'(:)([^:@/]+)(@)', r'\1****\3', resolved)
    print(f"    SQLALCHEMY_DATABASE_URI : {masked_resolved}")

    # Compare with env var
    env_fixed = _fix_db_url(raw_url) if raw_url else ''
    if env_fixed and resolved != env_fixed:
        print(f"    WARNING: Config value differs from DATABASE_URL env var!")
        print(f"    Config  : {masked_resolved}")
        print(f"    Env var : {re.sub(r'(:)([^:@/]+)(@)', r':****@', env_fixed)}")
        print(f"    CAUSE   : Config class was evaluated BEFORE .env was loaded.")
        print(f"    FIX     : Ensure load_dotenv() runs before 'from config import ...'")
    else:
        print(f"    Match   : Config matches DATABASE_URL env var  [OK]")
except Exception as e:
    print(f"    ERROR reading config: {e}")

# ── Step 4: Parse the URL components ────────────────────────────
print(f"\n[4] URL components (password hidden)")
try:
    from urllib.parse import urlparse
    url_to_parse = resolved if 'resolved' in dir() else raw_url
    # urlparse needs // after scheme
    parsed = urlparse(url_to_parse)
    print(f"    Scheme   : {parsed.scheme}")
    print(f"    Host     : {parsed.hostname}")
    print(f"    Port     : {parsed.port or 5432}")
    print(f"    Database : {parsed.path.lstrip('/')}")
    print(f"    Username : {parsed.username}")
    print(f"    Password : {'SET (hidden)' if parsed.password else 'NOT SET  <-- this causes auth failure'}")
    if not parsed.password:
        print(f"    FIX      : Check your .env for DATABASE_URL -- password field is empty.")
except Exception as e:
    print(f"    Parse error: {e}")

# ── Step 5: Attempt TCP connection (no auth) ─────────────────────
print(f"\n[5] TCP reachability (port check only, no credentials)")
import socket
host = parsed.hostname if 'parsed' in dir() else 'localhost'
port = parsed.port if 'parsed' in dir() and parsed.port else 5432
try:
    with socket.create_connection((host, port), timeout=3):
        print(f"    {host}:{port}  REACHABLE  [OK]")
except Exception as e:
    print(f"    {host}:{port}  NOT REACHABLE  -- PostgreSQL may not be running")
    print(f"    Error: {e}")

# ── Step 6: Attempt real DB connection ───────────────────────────
print(f"\n[6] Database authentication test")
try:
    import psycopg2
    from urllib.parse import urlparse, unquote
    p = urlparse(url_to_parse if 'url_to_parse' in dir() else raw_url)
    conn = psycopg2.connect(
        host=p.hostname,
        port=p.port or 5432,
        dbname=p.path.lstrip('/'),
        user=p.username,
        password=unquote(p.password or ''),
        connect_timeout=5
    )
    cur = conn.cursor()
    cur.execute("SELECT current_database(), current_user, version()")
    db_name, db_user, pg_ver = cur.fetchone()
    conn.close()
    print(f"    Connection  : SUCCESS  [OK]")
    print(f"    Database    : {db_name}")
    print(f"    User        : {db_user}")
    print(f"    PG Version  : {pg_ver[:40]}")
except psycopg2.OperationalError as e:
    err = str(e).strip()
    print(f"    Connection  : FAILED")
    # Mask any password that might appear in the error
    err_masked = re.sub(r'password\s*=\s*\S+', 'password=****', err, flags=re.IGNORECASE)
    print(f"    Error       : {err_masked}")
    print()
    if 'password authentication failed' in err:
        print("    DIAGNOSIS  : PostgreSQL rejected the password.")
        print("    CAUSE 1    : The password in DATABASE_URL does not match")
        print("                 the postgres user password in PostgreSQL.")
        print("    CAUSE 2    : The .env file has a typo or trailing space.")
        print("    CAUSE 3    : The .env file was not saved before running.")
        print()
        print("    HOW TO FIX :")
        print("      Open your .env file and verify the DATABASE_URL line.")
        print("      The password between : and @ must exactly match what")
        print("      you use to log in to pgAdmin.")
        print("      Example: DATABASE_URL=postgresql+psycopg2://postgres:MyPw123@localhost:5432/studymate_db")
    elif 'database' in err and 'does not exist' in err:
        print("    DIAGNOSIS  : Database 'studymate_db' does not exist.")
        print("    FIX        : In pgAdmin, right-click Databases -> Create -> Database")
        print("                 Name it: studymate_db")
        print("                 Then run: python init_db.py")
    elif 'could not connect' in err or 'Connection refused' in err:
        print("    DIAGNOSIS  : PostgreSQL server is not running or wrong port.")
        print("    FIX        : Start PostgreSQL service.")
        print("                 In Windows: search 'Services' -> postgresql -> Start")
except Exception as e:
    print(f"    Unexpected error: {e}")

# ── Step 7: Flask app config check ───────────────────────────────
print(f"\n[7] Flask app config")
try:
    from app import create_app, db as flask_db
    app = create_app()
    flask_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    masked_flask = re.sub(r'(:)([^:@/]+)(@)', r'\1****\3', flask_uri)
    print(f"    Flask DB URI : {masked_flask}")
    with app.app_context():
        from sqlalchemy import text
        with flask_db.engine.connect() as conn:
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
        print(f"    SQLAlchemy   : Connected to '{db_name}'  [OK]")
        from sqlalchemy import inspect as sa_inspect
        tables = sa_inspect(flask_db.engine).get_table_names()
        print(f"    Tables found : {len(tables)}  ({', '.join(tables[:4])}{'...' if len(tables) > 4 else ''})")
except Exception as e:
    err_str = re.sub(r'password\s*=\s*\S+', 'password=****', str(e), flags=re.IGNORECASE)
    print(f"    Flask app error: {err_str}")

print()
print("=" * 58)
print("  Run this script any time to verify your DB connection.")
print("  To start the app: python start.py")
print("=" * 58)
