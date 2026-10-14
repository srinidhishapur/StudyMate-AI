"""
comprehensive_test.py - Full end-to-end test suite for StudyMate AI
Run: python comprehensive_test.py
"""
import os, re, io, sys, tempfile
from dotenv import load_dotenv
load_dotenv(override=True)

from app import create_app, db
app = create_app()
results = []

def check(name, ok, detail=''):
    tag = '[PASS]' if ok else '[FAIL]'
    results.append((tag, name, detail))
    line = f'  {tag} {name}'
    if detail:
        line += f'  ({detail})'
    print(line)

def extract_csrf(html):
    m = re.search(r'id="csrf_token"[^>]*value="([^"]+)"', html)
    if m: return m.group(1)
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return m.group(1) if m else ''

def extract_all_csrf(html):
    return re.findall(r'name="csrf_token"\s+value="([^"]+)"', html)

TEST_EMAIL = 'testrunner99@studymate.com'
TEST_PW    = 'RunnerP@ss123'
TEST_USER  = 'testrunner99'

with app.app_context():

    # ── CLEAN UP from any previous test run ──────────────────────
    from app.models import User, Document, StudyPlan, LearningProgress
    old = User.query.filter_by(email=TEST_EMAIL).first()
    if old:
        db.session.delete(old)
        db.session.commit()

    # ── DATABASE TABLES ──────────────────────────────────────────
    print('\n=== DATABASE TABLES ===')
    from sqlalchemy import inspect as sa_inspect
    tables = sa_inspect(db.engine).get_table_names()
    for t in ['users','documents','study_plans','flashcards',
              'quiz_questions','quiz_attempts','learning_progress','chat_history']:
        check(f'Table exists: {t}', t in tables)

    # ── ROUTES ───────────────────────────────────────────────────
    print('\n=== ROUTES ===')
    route_strs = [str(r) for r in app.url_map.iter_rules()]
    for expected in [
        '/auth/register', '/auth/login', '/auth/logout',
        '/dashboard', '/documents', '/documents/upload',
        '/study-plans', '/study-plans/create',
        '/progress', '/profile',
        '/ai/document/<int:doc_id>', '/ai/summarize/<int:doc_id>',
        '/ai/quiz/<int:doc_id>',    '/ai/flashcards/<int:doc_id>',
        '/ai/chat/<int:doc_id>',    '/ai/chat/<int:doc_id>/message',
        '/ai/study-plan/<int:plan_id>/generate',
    ]:
        check(f'Route: {expected}', expected in route_strs)

    # ── ALL AUTH + FEATURE TESTS IN ONE CLIENT ───────────────────
    with app.test_client() as c:

        # -- REGISTER ------------------------------------------------
        print('\n=== REGISTER ===')
        r = c.get('/auth/register')
        tok = extract_csrf(r.data.decode())
        check('GET /register returns 200', r.status_code == 200)
        check('CSRF token on register page', bool(tok))

        r2 = c.post('/auth/register', data={
            'csrf_token': tok, 'full_name': 'Test Runner',
            'username': TEST_USER, 'email': TEST_EMAIL,
            'password': TEST_PW, 'confirm_password': TEST_PW,
        }, follow_redirects=False)
        check('Valid register -> 302 to login', r2.status_code == 302 and 'login' in r2.headers.get('Location',''))

        u = User.query.filter_by(email=TEST_EMAIL).first()
        check('User saved in DB', u is not None, str(u))
        check('Password hashed', u is not None and u.password_hash != TEST_PW)
        check('Registration activity logged',
              u is not None and LearningProgress.query.filter_by(user_id=u.id).count() > 0)

        # Duplicate email should fail
        tok_dup = extract_csrf(c.get('/auth/register').data.decode())
        r3 = c.post('/auth/register', data={
            'csrf_token': tok_dup, 'full_name': 'Dup', 'username': 'dup99x',
            'email': TEST_EMAIL, 'password': TEST_PW, 'confirm_password': TEST_PW,
        }, follow_redirects=False)
        check('Duplicate email blocked', r3.status_code == 200)

        # Short password
        tok_sh = extract_csrf(c.get('/auth/register').data.decode())
        r4 = c.post('/auth/register', data={
            'csrf_token': tok_sh, 'full_name': 'Short', 'username': 'shortx99',
            'email': 'short@x.com', 'password': 'abc', 'confirm_password': 'abc',
        }, follow_redirects=False)
        body_sh = r4.data.decode()
        check('Short password blocked', r4.status_code == 200)
        check('Short password error shown', 'at least 8' in body_sh or 'text-danger' in body_sh)

        # -- LOGIN ---------------------------------------------------
        print('\n=== LOGIN ===')
        r5 = c.get('/auth/login')
        tok_l = extract_csrf(r5.data.decode())
        check('GET /login returns 200', r5.status_code == 200)

        # Wrong password
        r6 = c.post('/auth/login', data={
            'csrf_token': tok_l, 'email': TEST_EMAIL, 'password': 'wrongpass99',
        }, follow_redirects=False)
        check('Wrong password blocked', r6.status_code == 200)

        # Correct login
        tok_l2 = extract_csrf(c.get('/auth/login').data.decode())
        r7 = c.post('/auth/login', data={
            'csrf_token': tok_l2, 'email': TEST_EMAIL, 'password': TEST_PW,
        }, follow_redirects=False)
        check('Correct login -> 302 to dashboard',
              r7.status_code == 302 and 'dashboard' in r7.headers.get('Location',''))

        # -- AUTHENTICATED PAGES -------------------------------------
        print('\n=== AUTHENTICATED PAGES ===')
        u = User.query.filter_by(email=TEST_EMAIL).first()
        for url, label in [
            ('/dashboard',   'Dashboard'),
            ('/documents',   'Documents'),
            ('/study-plans', 'Study Plans'),
            ('/progress',    'Progress'),
            ('/profile',     'Profile'),
        ]:
            r = c.get(url)
            check(f'{label} -> 200', r.status_code == 200)

        rd = c.get('/dashboard')
        check('Dashboard has content', b'dashboard' in rd.data.lower() or b'Document' in rd.data)

        # -- DOCUMENT UPLOAD -----------------------------------------
        print('\n=== DOCUMENT UPLOAD ===')
        rdocs = c.get('/documents')
        toks_up = extract_all_csrf(rdocs.data.decode())
        tok_up = toks_up[0] if toks_up else extract_csrf(rdocs.data.decode())
        check('CSRF on /documents page', bool(tok_up))

        txt = (b'Chapter 1: Python Basics\n\nPython is a high-level interpreted language.\n'
               b'\nChapter 2: Data Types\n\nint, str, list, dict are common types.\n'
               b'\nChapter 3: Functions\n\nDefined with the def keyword.\n')
        rup = c.post('/documents/upload', data={
            'csrf_token': tok_up, 'title': 'Python Study Guide',
            'subject': 'Computer Science',
            'file': (io.BytesIO(txt), 'python_guide.txt'),
        }, content_type='multipart/form-data', follow_redirects=False)
        check('Upload -> 302', rup.status_code == 302,
              f'got {rup.status_code}' + (': ' + rup.data[:100].decode() if rup.status_code != 302 else ''))

        doc = Document.query.filter_by(user_id=u.id, title='Python Study Guide').first() if u else None
        check('Document in DB', doc is not None, str(doc))
        if doc:
            fpath = os.path.join('uploads', str(u.id), doc.filename)
            check('File on disk', os.path.exists(fpath), fpath)

        # Invalid file type
        rdocs2 = c.get('/documents')
        toks2 = extract_all_csrf(rdocs2.data.decode())
        tok2 = toks2[0] if toks2 else ''
        rbad = c.post('/documents/upload', data={
            'csrf_token': tok2, 'title': 'Bad File',
            'file': (io.BytesIO(b'exe content'), 'malware.exe'),
        }, content_type='multipart/form-data', follow_redirects=False)
        check('Invalid .exe blocked', rbad.status_code == 302)
        bad = Document.query.filter_by(user_id=u.id if u else 0, title='Bad File').first()
        check('.exe not in DB', bad is None)

        # -- AI PAGES ------------------------------------------------
        print('\n=== AI PAGES ===')
        if doc:
            rai = c.get(f'/ai/document/{doc.id}')
            check('AI document detail -> 200', rai.status_code == 200)
            check('AI feature cards in page', b'ai-feature-card' in rai.data)
            check('Summarize button present', b'Summarize' in rai.data or b'Generate' in rai.data)
            check('Quiz button present', b'Quiz' in rai.data)
            check('Flashcard button present', b'Flashcard' in rai.data)
            check('Chat button present', b'Chat' in rai.data)

            rch = c.get(f'/ai/chat/{doc.id}')
            check('Chat page -> 200', rch.status_code == 200)
            check('Chat input present', b'chatInput' in rch.data)
            check('Send button present', b'sendBtn' in rch.data)

            rsm = c.get(f'/ai/summary/{doc.id}')
            check('Summary view -> 200', rsm.status_code == 200)
        else:
            check('AI pages (skipped - no doc)', False, 'upload failed')

        # -- STUDY PLANS ---------------------------------------------
        print('\n=== STUDY PLANS ===')
        rsp = c.get('/study-plans')
        toks_sp = extract_all_csrf(rsp.data.decode())
        tok_sp = toks_sp[0] if toks_sp else ''
        check('CSRF on /study-plans', bool(tok_sp))

        rcsp = c.post('/study-plans/create', data={
            'csrf_token': tok_sp, 'title': 'Python Exam Prep',
            'subject': 'CS', 'goal': 'Ace the finals',
            'duration_days': '30', 'difficulty': 'medium',
        }, follow_redirects=False)
        check('Study plan create -> 302', rcsp.status_code == 302, f'got {rcsp.status_code}')

        plan = StudyPlan.query.filter_by(user_id=u.id if u else 0, title='Python Exam Prep').first()
        check('Study plan in DB', plan is not None)
        if plan:
            rspd = c.get(f'/ai/study-plan/{plan.id}')
            check('AI study plan detail -> 200', rspd.status_code == 200)

        # -- PROFILE UPDATE ------------------------------------------
        print('\n=== PROFILE UPDATE ===')
        rprof = c.get('/profile')
        toks_pr = extract_all_csrf(rprof.data.decode())
        tok_pr = toks_pr[0] if toks_pr else ''
        rupr = c.post('/profile', data={
            'csrf_token': tok_pr, 'full_name': 'Srinidhi S',
        }, follow_redirects=False)
        check('Profile update -> 302', rupr.status_code == 302)
        db.session.expire_all()
        u2 = User.query.filter_by(email=TEST_EMAIL).first()
        check('Full name updated in DB', u2 is not None and u2.full_name == 'Srinidhi S',
              f'got: {u2.full_name if u2 else None}')

        # -- LOGOUT --------------------------------------------------
        print('\n=== LOGOUT ===')
        rlo = c.get('/auth/logout', follow_redirects=False)
        check('Logout -> 302 to login', rlo.status_code == 302 and 'login' in rlo.headers.get('Location',''))
        rprot = c.get('/dashboard', follow_redirects=False)
        check('Dashboard blocked after logout', rprot.status_code == 302)

    # ── TEXT EXTRACTION ──────────────────────────────────────────
    print('\n=== TEXT EXTRACTION ===')
    from app.utils.file_processor import extract_text_from_file, chunk_text
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write('Intro\n\nPython basics.\n\nVariables store data.\n\nFunctions use def.\n')
        tmpf = f.name
    text, pages, words = extract_text_from_file(tmpf, 'txt')
    os.unlink(tmpf)
    check('TXT extraction works', len(text) > 0, f'{words} words')
    check('Word count > 0', words > 0)
    chunks = chunk_text(text, chunk_size=60, overlap=10)
    check('Chunking works', len(chunks) >= 1, f'{len(chunks)} chunks')

    # ── WATSONX SERVICE ──────────────────────────────────────────
    print('\n=== WATSONX SERVICE ===')
    from app.services.watsonx_service import is_configured
    configured = is_configured()
    check('is_configured() callable without error', True, f'configured={configured}')
    if not configured:
        print('     NOTE: Add WATSONX_API_KEY + WATSONX_PROJECT_ID to .env for full AI features.')

    # ── CLEANUP ──────────────────────────────────────────────────
    print('\n=== CLEANUP ===')
    final_u = User.query.filter_by(email=TEST_EMAIL).first()
    if final_u:
        db.session.delete(final_u)
        db.session.commit()
        check('Test data removed from DB', True)
    else:
        check('Test data removed from DB', True, 'already gone')

    # ── RESULTS ──────────────────────────────────────────────────
    print('\n' + '='*55)
    passed = sum(1 for s,_,_ in results if s == '[PASS]')
    failed = sum(1 for s,_,_ in results if s == '[FAIL]')
    print(f'  RESULTS: {passed} passed / {failed} failed / {len(results)} total')
    if failed:
        print('\n  FAILED:')
        for s, n, d in results:
            if s == '[FAIL]':
                print(f'    - {n}' + (f' ({d})' if d else ''))
    else:
        print('  ALL CHECKS PASSED - StudyMate AI is fully functional!')
    print('='*55)
    sys.exit(0 if failed == 0 else 1)
