"""
ClauseGuard — AI-Powered Document Clause Risk Analyzer
Flask application entry point.
"""

import os
import uuid
import datetime
import html
from flask import Flask, request, jsonify, render_template, session, abort, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from config import Config
import db

# Input length limits (prevent payload flooding / DoS)
MAX_PROMPT_LEN    = 2000   # user_prompt field
MAX_QUESTION_LEN  = 2000   # chat question
MAX_CLAUSE_LEN    = 50000  # clause_text for explain
MAX_LOGIN_ATTEMPTS = 5     # lockout after N failures
LOCKOUT_SECONDS   = 900    # 15 minutes


# ── Secure Credentials (set via environment variables) ─────────────
# Default credentials only for local dev. ALWAYS override via env vars in production.
APP_USERNAME = os.environ.get('APP_USERNAME', 'admin')
APP_PASSWORD_HASH = generate_password_hash(
    os.environ.get('APP_PASSWORD', 'clauseguard2024')
)


def login_required(f):
    """Decorator that redirects unauthenticated users to login page."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required.'}), 401
            return render_template('login.html', mode='login')
        return f(*args, **kwargs)
    return decorated


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY
    Config.init_app(app)
    
    # Initialize multi-user database
    db.init_db()

    # ── CORS configuration (supports all onrender.com subdomains & localhost) ──
    CORS(app, resources={r'/api/*': {'origins': [
        r'https://.*\.onrender\.com',
        r'http://localhost:\d+',
        r'http://127\.0\.0\.1:\d+',
    ]}}, supports_credentials=True)

    # ── Background Pre-warming of ML / NLP engines ─────────────────
    import threading
    def _prewarm_engines():
        try:
            get_parser()
            get_extractor()
            get_analyzer()
        except Exception:
            pass
    threading.Thread(target=_prewarm_engines, daemon=True).start()

    # ── Rate Limiting ──────────────────────────────────────────────
    limiter = None
    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=['200 per day', '60 per minute'],
            storage_uri='memory://',
        )
    except ImportError:
        limiter = None

    # ── Security Headers on every response ────────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    # ── Lazy-loaded engine singletons ───────────────────────────────
    _engine_cache = {}
    
    # ── Temporary In-Memory Document Store for Q&A ──────────────────
    TEMP_DOCS = {}
    
    # ── Analysis History Store ──────────────────────────────────────
    ANALYSIS_HISTORY = []

    def get_parser():
        if 'parser' not in _engine_cache:
            from engine.document_parser import DocumentParser
            _engine_cache['parser'] = DocumentParser()
        return _engine_cache['parser']

    def get_extractor():
        if 'extractor' not in _engine_cache:
            from engine.clause_extractor import ClauseExtractor
            _engine_cache['extractor'] = ClauseExtractor()
        return _engine_cache['extractor']

    def get_analyzer():
        if 'analyzer' not in _engine_cache:
            from engine.risk_analyzer import RiskAnalyzer
            _engine_cache['analyzer'] = RiskAnalyzer()
        return _engine_cache['analyzer']

    def get_explainer():
        if 'explainer' not in _engine_cache:
            from engine.llm_explainer import LLMExplainer
            api_key = session.get('gemini_api_key') or os.environ.get('GEMINI_API_KEY')
            _engine_cache['explainer'] = LLMExplainer(api_key=api_key)
        return _engine_cache['explainer']

    def get_playbook_analyzer():
        if 'playbook_analyzer' not in _engine_cache:
            from engine.playbook_analyzer import PlaybookAnalyzer
            api_key = session.get('gemini_api_key') or os.environ.get('GEMINI_API_KEY')
            playbook_path = os.path.join(Config.BASE_DIR, 'playbook.json')
            _engine_cache['playbook_analyzer'] = PlaybookAnalyzer(playbook_path=playbook_path, api_key=api_key)
        return _engine_cache['playbook_analyzer']

    def get_obligation_extractor():
        if 'obligation_extractor' not in _engine_cache:
            from engine.obligation_extractor import ObligationExtractor
            api_key = session.get('gemini_api_key') or os.environ.get('GEMINI_API_KEY')
            _engine_cache['obligation_extractor'] = ObligationExtractor(api_key=api_key)
        return _engine_cache['obligation_extractor']

    def allowed_file(filename: str) -> bool:
        """Check if the uploaded file has an allowed extension."""
        return (
            '.' in filename
            and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS
        )

    # ── Routes ──────────────────────────────────────────────────────

    @app.route('/')
    def index():
        """Serve the main single-page application."""
        if not session.get('user_id') and not session.get('user'):
            return render_template('login.html', mode='login')
        return render_template('index.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Multi-user login route — validates against SQLite database."""
        import time
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            if not username or not password:
                return render_template('login.html', mode='login', error='Please provide both username/email and password.')

            # ── Brute-force protection ──
            now = time.time()
            fail_key  = f'login_fails_{username}'
            lock_key  = f'login_lock_{username}'
            locked_until = session.get(lock_key, 0)

            if now < locked_until:
                remaining = int(locked_until - now)
                return render_template('login.html', mode='login',
                    error=f'Too many failed attempts. Try again in {remaining} seconds.')

            user = db.get_user_by_login(username)

            if user and check_password_hash(user['password_hash'], password):
                # Success — set session
                session.pop(fail_key, None)
                session.pop(lock_key, None)
                session['user']    = user['username']
                session['user_id'] = user['id']
                session['email']   = user['email']
                session.permanent  = True
                app.permanent_session_lifetime = datetime.timedelta(hours=8)
                return render_template('index.html')
            else:
                # Track failures
                fails = session.get(fail_key, 0) + 1
                session[fail_key] = fails
                if fails >= MAX_LOGIN_ATTEMPTS:
                    session[lock_key] = now + LOCKOUT_SECONDS
                    session[fail_key] = 0
                    return render_template('login.html', mode='login',
                        error=f'Account locked for 15 minutes after {MAX_LOGIN_ATTEMPTS} failed attempts.')
                remaining_tries = MAX_LOGIN_ATTEMPTS - fails
                return render_template('login.html', mode='login',
                    error=f'Invalid credentials. {remaining_tries} attempt(s) remaining.')
        return render_template('login.html', mode='login')

    @app.route('/register', methods=['POST'])
    def register():
        """User registration route — creates new user in SQLite database."""
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not username or not email or not password:
            return render_template('login.html', mode='register', error='All fields are required.')

        if len(password) < 6:
            return render_template('login.html', mode='register', error='Password must be at least 6 characters long.')

        # Hash password securely
        password_hash = generate_password_hash(password)
        success, res = db.create_user(username, email, password_hash)

        if success:
            # Auto-log in user on successful registration
            session['user']    = res['username']
            session['user_id'] = res['id']
            session['email']   = res['email']
            session.permanent  = True
            app.permanent_session_lifetime = datetime.timedelta(hours=8)
            return render_template('index.html')
        else:
            return render_template('login.html', mode='register', error=res)

    @app.route('/logout')
    def logout():
        """Log out the user and clear the session."""
        session.clear()
        return render_template('login.html', mode='login')

    @app.route('/api/upload', methods=['POST'])
    @login_required
    def upload_document():
        # ── Per-route rate limit: max 10 uploads per minute per IP ──
        if limiter:
            from flask_limiter.errors import RateLimitExceeded
            try:
                limiter.check()  # already applied by default
            except Exception:
                pass
        # Hard enforce: use a per-session counter stored in session
        import time
        now = time.time()
        window_key = 'upload_window'
        count_key = 'upload_count'
        window_start = session.get(window_key, 0)
        upload_count = session.get(count_key, 0)

        # Reset counter if more than 60 seconds have passed
        if now - window_start > 60:
            session[window_key] = now
            session[count_key] = 1
        else:
            upload_count += 1
            session[count_key] = upload_count
            if upload_count > 10:
                return jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded: max 10 uploads per minute. Please wait before uploading again.'
                }), 429
        """
        Upload and analyze one or more documents.
        Accepts multipart/form-data with one or more 'document' file fields.
        Returns per-document analysis results in a 'documents' array.
        """
        if 'document' not in request.files:
            return jsonify({'success': False, 'error': 'No document uploaded.'}), 400

        files = request.files.getlist('document')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'error': 'No file selected.'}), 400

        user_prompt = request.form.get('user_prompt', '')[:MAX_PROMPT_LEN]  # cap length

        extractor         = get_extractor()
        analyzer          = get_analyzer()
        playbook_analyzer = get_playbook_analyzer()
        obligation_extractor = get_obligation_extractor()
        parser            = get_parser()

        all_results = []

        for file in files:
            if file.filename == '':
                continue

            if not allowed_file(file.filename):
                return jsonify({'success': False, 'error': f'Unsupported file type: {file.filename}'}), 400

            filename  = secure_filename(file.filename)
            file_path = os.path.join(Config.UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{filename}")
            unique_name = f"{uuid.uuid4().hex}_{filename}"

            try:
                file.save(file_path)

                # Step 1: Parse
                doc_data = parser.parse(file_path)
                if not doc_data['text'].strip():
                    all_results.append({'success': False, 'filename': filename, 'error': 'Could not extract text. File may be empty or image-based.'})
                    continue

                text = doc_data['text']

                # Step 2: Extract clauses
                clauses = extractor.extract(text)
                if not clauses:
                    all_results.append({'success': False, 'filename': filename, 'error': 'No analyzable clauses found.'})
                    continue

                # Step 3: Analyze risk
                analyzed_clauses = []
                summary = {'high_risk': 0, 'medium_risk': 0, 'low_risk': 0}
                for clause in clauses:
                    risk_result  = analyzer.analyze(clause['text'])
                    clause_result = {
                        'id':               clause['id'],
                        'text':             clause['text'],
                        'section_header':   clause.get('section_header', ''),
                        'entities':         clause.get('entities', []),
                        'sentence_count':   clause.get('sentence_count', 1),
                        'risk_level':       risk_result['risk_level'],
                        'risk_score':       risk_result['risk_score'],
                        'risk_categories':  risk_result['risk_categories'],
                        'keywords':         risk_result['keywords'],
                    }
                    analyzed_clauses.append(clause_result)
                    level_key = f"{risk_result['risk_level']}_risk"
                    summary[level_key] = summary.get(level_key, 0) + 1

                high_count = summary['high_risk']
                med_count  = summary['medium_risk']

                # Step 4: Summary text
                risk_explanations = {
                    'Indemnification':      'means you must pay for the other party\'s legal costs and damages',
                    'Unlimited Liability':  'means you could owe unlimited money if something goes wrong',
                    'Auto Renewal':         'means the contract automatically continues and you might forget to cancel it',
                    'Non-Compete':          'means you can\'t work in a similar business even after the contract ends',
                    'IP Assignment':        'means your creative work or ideas become their property',
                    'Unilateral Termination':'means only they can end the contract, leaving you at risk',
                    'Rights Waiver':        'means you give up important legal protections',
                    'Penalty Clauses':      'means you\'ll face large fines for minor violations',
                    'Perpetual Terms':      'means certain obligations last forever after the contract ends',
                    'Data Rights':          'means they control your personal or business data indefinitely',
                }
                if high_count > 0:
                    high_cats = list(set([c['risk_categories'][0] for c in analyzed_clauses if c['risk_level'] == 'high' and c['risk_categories']]))
                    cat_detail = ""
                    cat_explanations = [f"<strong>{cat}</strong> — {risk_explanations[cat]}" for cat in high_cats[:3] if cat in risk_explanations]
                    if cat_explanations:
                        cat_detail = "<br><strong>Found in your document:</strong><ul style='margin:8px 0;padding-left:20px;'>" + "".join(f"<li style='margin:4px 0;'>{e}</li>" for e in cat_explanations) + "</ul>"
                    doc_summary_text = (
                        f"<span style='color:#d84c42;font-weight:600;'>ATTENTION: {high_count} High-Risk Clause(s) Found</span><br><br>"
                        f"This document contains <strong>serious issues</strong> that could harm you financially or legally.{cat_detail}<br>"
                        f"<strong>Action Required:</strong> Do NOT sign until you review and negotiate these clauses. Legal consultation is advised."
                    )
                    if med_count > 0:
                        doc_summary_text += f"<br><br>Additionally, there are <strong>{med_count} medium-risk clause(s)</strong> that need attention."
                elif med_count > 0:
                    doc_summary_text = (
                        f"This document is mostly standard, but we found <strong>{med_count} medium-risk clause(s)</strong>. "
                        "Review these sections to ensure you are comfortable with the obligations before signing."
                    )
                else:
                    doc_summary_text = (
                        f"All {len(analyzed_clauses)} clauses analyzed. No high or medium risk patterns detected. "
                        "The language appears standard and balanced. A final read-through is always recommended before signing."
                    )

                # Step 5: Playbook
                playbook_violations = playbook_analyzer.analyze_document(analyzed_clauses, user_prompt=user_prompt)
                for clause in analyzed_clauses:
                    c_id_str = str(clause['id'])
                    clause['playbook_violations'] = playbook_violations.get(c_id_str, playbook_violations.get(clause['id'], []))

                # Step 6: Obligations
                obligations = obligation_extractor.extract(text, user_prompt=user_prompt)

                # Save for Q&A
                TEMP_DOCS[unique_name] = text

                timestamp_str = datetime.datetime.utcnow().isoformat() + 'Z'
                doc_info_data = {'extension': doc_data.get('extension',''), 'word_count': doc_data['word_count'], 'char_count': doc_data['char_count']}
                full_res_data = {
                    'filename': filename,
                    'doc_id': unique_name,
                    'document_info': doc_info_data,
                    'total_clauses': len(analyzed_clauses),
                    'summary': summary,
                    'document_summary_text': doc_summary_text,
                    'clauses': analyzed_clauses,
                    'obligations': obligations,
                    'user_prompt': user_prompt,
                }

                # Save history into SQLite database for current user (safely handled)
                try:
                    user_id = session.get('user_id')
                    if not user_id and session.get('user'):
                        u = db.get_user_by_login(session.get('user'))
                        if u:
                            user_id = u['id']
                            session['user_id'] = user_id
                    if user_id:
                        db.add_history_entry(user_id, unique_name, filename, timestamp_str, len(analyzed_clauses), summary, doc_info_data, full_res_data)
                except Exception as hist_err:
                    print(f"[Warning] Failed to save history entry: {hist_err}")

                all_results.append({
                    'success':               True,
                    'filename':              filename,
                    'doc_id':               unique_name,
                    'document_info':         doc_info_data,
                    'total_clauses':         len(analyzed_clauses),
                    'summary':               summary,
                    'document_summary_text': doc_summary_text,
                    'clauses':               analyzed_clauses,
                    'obligations':           obligations,
                    'user_prompt':           user_prompt,
                })

            except Exception as e:
                all_results.append({'success': False, 'filename': filename, 'error': f'Analysis failed: {str(e)}'})
            finally:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass

        successful = [r for r in all_results if r.get('success')]
        failed     = [r for r in all_results if not r.get('success')]

        if not successful:
            errors = '; '.join(f"{r['filename']}: {r['error']}" for r in failed)
            return jsonify({'success': False, 'error': errors}), 400

        # Single doc: return legacy flat format for UI compatibility
        if len(successful) == 1 and len(files) == 1:
            return jsonify(successful[0]), 200

        # Multi-doc: return array under 'documents'
        return jsonify({
            'success':   True,
            'multi':     True,
            'documents': successful,
            'failed':    failed,
        }), 200


    @app.route('/api/history', methods=['GET', 'DELETE'])
    @login_required
    def manage_history():
        """Get or clear analysis history for current user."""
        user_id = session.get('user_id', 0)
        if request.method == 'DELETE':
            db.clear_user_history(user_id)
            TEMP_DOCS.clear()
            return jsonify({'success': True})
        
        history = db.get_user_history(user_id)
        return jsonify({'success': True, 'history': history})

    @app.route('/api/history/<item_id>', methods=['DELETE'])
    @login_required
    def delete_history_item(item_id):
        """Delete a single history entry for current user."""
        user_id = session.get('user_id', 0)
        db.delete_user_history_item(user_id, item_id)
        TEMP_DOCS.pop(item_id, None)
        return jsonify({'success': True})

    @app.route('/api/explain', methods=['POST'])
    @login_required
    def explain_clause():
        """
        Get a plain-English LLM explanation of a clause.
        Accepts JSON with clause_text, risk_level, risk_categories.
        """
        data = request.get_json()
        if not data or 'clause_text' not in data:
            return jsonify({'success': False, 'error': 'No clause text provided.'}), 400

        clause_text = data['clause_text'][:MAX_CLAUSE_LEN]  # cap to prevent DoS
        risk_level = data.get('risk_level', 'medium')
        risk_categories = data.get('risk_categories', [])

        try:
            explainer = get_explainer()

            # Update API key from session if changed
            current_key = session.get('gemini_api_key')
            if current_key and current_key != explainer.api_key:
                explainer.configure(current_key)

            result = explainer.explain(clause_text, risk_level, risk_categories)
            result['success'] = True
            return jsonify(result)

        except Exception as e:
            is_dev = os.environ.get('FLASK_ENV', 'production') == 'development'
            return jsonify({
                'success': False,
                'error': str(e) if is_dev else 'Explanation service temporarily unavailable.',
            }), 500

    @app.route('/api/chat', methods=['POST'])
    @login_required
    def chat_document():
        """
        Q&A Chat feature to ask questions about the uploaded document.
        Accepts JSON with doc_id, question.
        """
        data = request.get_json()
        if not data or 'question' not in data or 'doc_id' not in data:
            return jsonify({'success': False, 'error': 'Missing doc_id or question.'}), 400

        doc_id = data['doc_id']
        question = data['question'][:MAX_QUESTION_LEN]  # cap to prevent DoS
        user_prompt = data.get('user_prompt', '')[:MAX_PROMPT_LEN]

        if doc_id not in TEMP_DOCS:
            return jsonify({'success': False, 'error': 'Document session expired. Please re-upload the document.'}), 404

        try:
            explainer = get_explainer()

            # Update API key from session if changed
            current_key = session.get('gemini_api_key')
            if current_key and current_key != explainer.api_key:
                explainer.configure(current_key)
                
            document_text = TEMP_DOCS[doc_id]
            
            if user_prompt:
                question = f"{question}\n\nAdditional user instructions:\n{user_prompt}"
                
            answer = explainer.answer_question(document_text, question)
            
            return jsonify({'success': True, 'answer': answer})

        except Exception as e:
            is_dev = os.environ.get('FLASK_ENV', 'production') == 'development'
            return jsonify({
                'success': False,
                'error': str(e) if is_dev else 'Chat service temporarily unavailable.',
            }), 500

    @app.route('/api/settings', methods=['POST'])
    @login_required
    def save_settings():
        """Save user settings (API key) to the session."""
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No settings provided.'}), 400

        api_key = data.get('api_key', '').strip()

        if api_key:
            session['gemini_api_key'] = api_key

            # Re-initialize the explainer with the new key
            if 'explainer' in _engine_cache:
                _engine_cache['explainer'].configure(api_key)
            else:
                from engine.llm_explainer import LLMExplainer
                _engine_cache['explainer'] = LLMExplainer(api_key=api_key)

            if 'playbook_analyzer' in _engine_cache:
                _engine_cache['playbook_analyzer'].configure(api_key)
                
            if 'obligation_extractor' in _engine_cache:
                _engine_cache['obligation_extractor'].configure(api_key)

            return jsonify({
                'success': True,
                'message': 'API key saved successfully.',
                'llm_available': True,
            })
        else:
            session.pop('gemini_api_key', None)
            if 'explainer' in _engine_cache:
                _engine_cache['explainer'] = None
                del _engine_cache['explainer']
            if 'playbook_analyzer' in _engine_cache:
                _engine_cache['playbook_analyzer'] = None
                del _engine_cache['playbook_analyzer']
            if 'obligation_extractor' in _engine_cache:
                _engine_cache['obligation_extractor'] = None
                del _engine_cache['obligation_extractor']

            return jsonify({
                'success': True,
                'message': 'API key removed.',
                'llm_available': False,
            })

    @app.route('/api/playbook', methods=['GET'])
    @login_required
    def get_playbook():
        import json
        playbook_path = os.path.join(Config.BASE_DIR, 'playbook.json')
        try:
            with open(playbook_path, 'r') as f:
                return jsonify({'success': True, 'playbook': json.load(f).get('playbook', {})})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'app': 'ClauseGuard',
            'version': '2.0.0',
            'llm_available': bool(session.get('gemini_api_key')),
        })

    @app.route('/api/report', methods=['POST'])
    @login_required
    def generate_report():
        """
        Generate a downloadable HTML report from analysis results.
        Accepts JSON with the full analysis result object.
        Returns an HTML report as a file download.
        """
        from flask import make_response
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided.'}), 400

        if 'analysis_data' in data:
            data = data['analysis_data']

        filename = data.get('filename', 'contract.pdf')
        total_clauses = data.get('total_clauses', 0)
        summary = data.get('summary', {})
        clauses = data.get('clauses', [])
        obligations = data.get('obligations', [])
        doc_summary_text = data.get('document_summary_text', '')
        user_prompt = data.get('user_prompt', '')
        generated_at = datetime.datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')

        high = summary.get('high_risk', 0)
        med = summary.get('medium_risk', 0)
        low = summary.get('low_risk', 0)

        risk_color = '#c0392b' if high > 0 else ('#e67e22' if med > 0 else '#27ae60')
        risk_label = 'HIGH RISK' if high > 0 else ('MEDIUM RISK' if med > 0 else 'LOW RISK')

        clauses_html = ''
        for c in clauses:
            level = c.get('risk_level', 'low')
            score = c.get('risk_score', 0)
            text = html.escape(str(c.get('text', '')))
            section = html.escape(str(c.get('section_header') or f"Clause {c.get('id', 0) + 1}"))
            cats = html.escape(', '.join(c.get('risk_categories', [])) or 'General')
            lcolor = {'high': '#c0392b', 'medium': '#e67e22', 'low': '#27ae60'}.get(level, '#888')
            lbg = {'high': '#fdf0ef', 'medium': '#fef5e4', 'low': '#eafaf1'}.get(level, '#f5f5f5')

            violations_html = ''
            for v in c.get('playbook_violations', []):
                violations_html += f"""
                <div style="margin-top:10px;padding:10px;background:#fff5f5;border-left:3px solid #c0392b;border-radius:4px;font-size:12px;">
                    <strong style="color:#c0392b;">&#9888; Playbook: {html.escape(str(v.get('rule_id','')))} &ndash; {html.escape(str(v.get('category','')))}</strong><br>
                    <span style="color:#555;">{html.escape(str(v.get('explanation','')))}</span><br>
                    <em style="color:#777;">Suggested: {html.escape(str(v.get('alternative_text','')))}</em>
                </div>"""

            clauses_html += f"""
            <div style="background:{lbg};border:1px solid #e0e0e0;border-left:4px solid {lcolor};border-radius:8px;padding:18px;margin-bottom:16px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                    <span style="background:{lcolor};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">{level} risk</span>
                    <span style="font-size:13px;color:#666;font-weight:500;">{section}</span>
                    <span style="margin-left:auto;font-size:12px;color:#888;font-weight:600;">{score}/100</span>
                </div>
                <p style="font-size:13px;color:#333;line-height:1.7;margin-bottom:8px;">{text}</p>
                <p style="font-size:11px;color:#888;margin:0;">Categories: {cats}</p>
                {violations_html}
            </div>"""

        obligations_html = ''
        if obligations:
            items = ''.join([f"""
            <tr>
                <td style="padding:10px 12px;font-size:13px;font-weight:600;color:#333;">{o.get('title','')}</td>
                <td style="padding:10px 12px;font-size:13px;color:#555;">{o.get('description','')}</td>
                <td style="padding:10px 12px;font-size:13px;color:#1a73e8;font-weight:500;">{o.get('timeline','')}</td>
                <td style="padding:10px 12px;font-size:13px;color:#666;">{o.get('responsible_party','')}</td>
            </tr>""" for o in obligations])
            obligations_html = f"""
            <h2 style="font-size:18px;font-weight:700;margin:32px 0 16px;color:#111;border-bottom:2px solid #e0e0e0;padding-bottom:8px;">📅 Actionable Obligations</h2>
            <table style="width:100%;border-collapse:collapse;background:#fff;border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;">
                <thead><tr style="background:#f8f9fa;">
                    <th style="padding:10px 12px;font-size:12px;color:#666;text-align:left;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Task</th>
                    <th style="padding:10px 12px;font-size:12px;color:#666;text-align:left;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Description</th>
                    <th style="padding:10px 12px;font-size:12px;color:#666;text-align:left;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Timeline</th>
                    <th style="padding:10px 12px;font-size:12px;color:#666;text-align:left;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Responsible</th>
                </tr></thead>
                <tbody>{items}</tbody>
            </table>"""

        prompt_html = f'<p style="font-size:13px;color:#555;background:#f0f4ff;padding:12px;border-radius:6px;margin-top:8px;"><strong>User Instructions:</strong> {user_prompt}</p>' if user_prompt else ''

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ClauseGuard Report — {filename}</title>
<style>
  body {{ font-family: 'Georgia', serif; background: #f5f5f5; margin: 0; padding: 40px; color: #111; }}
  .report {{ max-width: 860px; margin: 0 auto; background: #fff; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.1); overflow: hidden; }}
  .header {{ background: linear-gradient(135deg, #0f0f0f 0%, #1a1a2e 100%); color: #fff; padding: 40px 48px; }}
  .header h1 {{ font-size: 28px; font-weight: 700; margin: 0 0 6px; letter-spacing: -0.5px; }}
  .header p {{ font-size: 14px; opacity: 0.7; margin: 0; }}
  .badge {{ display:inline-block;padding:6px 16px;border-radius:4px;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-top:16px; }}
  .body {{ padding: 40px 48px; }}
  .stats {{ display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:32px; }}
  .stat {{ background:#f8f9fa;border:1px solid #e0e0e0;border-radius:8px;padding:16px;text-align:center; }}
  .stat-num {{ font-size:28px;font-weight:700;margin-bottom:4px; }}
  .stat-label {{ font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.5px;font-weight:600; }}
  .summary-box {{ background:#f8f9fa;border:1px solid #e0e0e0;border-left:4px solid #1a73e8;border-radius:8px;padding:20px;margin-bottom:32px;font-size:14px;line-height:1.7; }}
  @media print {{ body {{ padding: 0; background: #fff; }} .report {{ box-shadow: none; border-radius: 0; }} }}
</style>
</head>
<body>
<div class="report">
  <div class="header">
    <div style="font-size:12px;opacity:0.5;text-transform:uppercase;letter-spacing:2px;margin-bottom:12px;">ClauseGuard AI Analysis Report</div>
    <h1>📄 {filename}</h1>
    <p>Generated {generated_at}</p>
    <span class="badge" style="background:{risk_color};color:#fff;">{risk_label}</span>
  </div>
  <div class="body">
    {prompt_html}
    <div class="stats">
      <div class="stat"><div class="stat-num" style="color:#111;">{total_clauses}</div><div class="stat-label">Total Clauses</div></div>
      <div class="stat"><div class="stat-num" style="color:#c0392b;">{high}</div><div class="stat-label">High Risk</div></div>
      <div class="stat"><div class="stat-num" style="color:#e67e22;">{med}</div><div class="stat-label">Medium Risk</div></div>
      <div class="stat"><div class="stat-num" style="color:#27ae60;">{low}</div><div class="stat-label">Low Risk</div></div>
    </div>
    <h2 style="font-size:18px;font-weight:700;margin:0 0 12px;color:#111;border-bottom:2px solid #e0e0e0;padding-bottom:8px;">📋 Risk Summary</h2>
    <div class="summary-box">{doc_summary_text}</div>
    {obligations_html}
    <h2 style="font-size:18px;font-weight:700;margin:32px 0 16px;color:#111;border-bottom:2px solid #e0e0e0;padding-bottom:8px;">🔍 Clause Analysis ({total_clauses} clauses)</h2>
    {clauses_html}
    <div style="margin-top:48px;padding-top:24px;border-top:1px solid #e0e0e0;font-size:12px;color:#aaa;text-align:center;">
      Generated by ClauseGuard AI · {generated_at} · For informational purposes only. Not legal advice.
    </div>
  </div>
</div>
</body>
</html>"""

        response = make_response(html)
        safe_name = filename.replace(' ', '_').replace('/', '_')
        response.headers['Content-Disposition'] = f'attachment; filename="ClauseGuard_Report_{safe_name}.html"'
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response

    return app


# ── Application Entry Point ────────────────────────────────────────

if __name__ == '__main__':
    app = create_app()
    is_dev = os.environ.get('FLASK_ENV', 'production') == 'development'
    print("\n" + "=" * 60)
    print("   ClauseGuard -- AI-Powered Clause Risk Analyzer")
    print("=" * 60)
    print("   Server running at: http://localhost:5000")
    print("   Press Ctrl+C to stop")
    print("=" * 60 + "\n")
    app.run(debug=is_dev, host='0.0.0.0', port=5000)
