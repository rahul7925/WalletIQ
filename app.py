"""
WalletIQ v2.0 — Production-Grade Multi-User Personal Finance App
================================================================
- MySQL via PyMySQL + SQLAlchemy connection pooling
- Per-user data isolation (ALL queries filtered by user_id)
- Session security: HTTPOnly cookies, SameSite, secure tokens
- Rate limiting on auth routes
- DB error rollback on every write
- Concurrent-safe AI chat sessions (per-user keyed)
- Schema managed via Flask-Migrate / Alembic
"""

import os, io, logging
from urllib.parse import quote_plus


from datetime import datetime, date
from functools import wraps
from collections import defaultdict
import time
import pytz, pickle

from flask import (Flask, render_template, request, redirect,
                   jsonify, send_file, abort)
from dotenv import load_dotenv
load_dotenv()

from flask_login import (LoginManager, UserMixin, login_user,
                         logout_user, login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


# ── Create Directories ──────────────────────────────────────────────────────────
for d in ['uploads', 'instance/reports', 'instance/temp', 'logs']:
    os.makedirs(d, exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
from logging.handlers import RotatingFileHandler
log = logging.getLogger('walletiq')
log.setLevel(logging.INFO)

# Console stream logger fallback
if not log.handlers:
    # console logger
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    log.addHandler(console_handler)

    # rotating file logger
    try:
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10*1024*1024, backupCount=5)
        file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        log.addHandler(file_handler)
    except Exception:
        pass


# ── App Setup ──────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder='templates', static_folder='templates/static')

# ── Security Config ────────────────────────────────────────────────────────────
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32).hex())
app.config['SESSION_COOKIE_HTTPONLY']  = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE']   = False   # set True in production with HTTPS
app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 7  # 7 days

# ── Database Config — MySQL ───────────────────────────────────────────────────
# Uses PyMySQL via SQLAlchemy. Reads connection settings from .env.
# Required env vars: MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

# Diagnostic env dump toggle (set WALLETIQ_DB_DIAGNOSTIC=1)
_WALLETIQ_DB_DIAGNOSTIC = os.environ.get('WALLETIQ_DB_DIAGNOSTIC', '0') == '1'



MYSQL_HOST = os.environ.get('MYSQL_HOST')
MYSQL_PORT = os.environ.get('MYSQL_PORT')
MYSQL_USER = os.environ.get('MYSQL_USER')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE')

missing = [k for k, v in {
    'MYSQL_HOST': MYSQL_HOST,
    'MYSQL_PORT': MYSQL_PORT,
    'MYSQL_USER': MYSQL_USER,
    'MYSQL_PASSWORD': MYSQL_PASSWORD,
    'MYSQL_DATABASE': MYSQL_DATABASE,
}.items() if not v]

if missing:
    raise RuntimeError(f"Missing required MySQL env vars: {', '.join(missing)}")

user_enc = quote_plus(MYSQL_USER or '')
pwd_enc  = quote_plus(MYSQL_PASSWORD or '')

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{user_enc}:{pwd_enc}"
    f"@{MYSQL_HOST}:{int(MYSQL_PORT)}/{MYSQL_DATABASE}"
    f"?charset=utf8mb4"
)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# MySQL engine options
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}


db = SQLAlchemy(app)
migrate = Migrate(app, db)

if _WALLETIQ_DB_DIAGNOSTIC:
    with app.app_context():
        print('WALLETIQ_DIAG db.engine.url=', str(db.engine.url))
        try:
            from sqlalchemy import inspect, text
            insp = inspect(db.engine)
            print('WALLETIQ_DIAG tables=', sorted(insp.get_table_names()))
            with db.engine.connect() as conn:
                print('WALLETIQ_DIAG ping=', conn.execute(text('SELECT 1')).scalar())
        except Exception as exc:
            print('WALLETIQ_DIAG connectivity_error=', exc)


# ── Login Manager ──────────────────────────────────────────────────────────────
login_manager = LoginManager()

login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = None  # suppress default flash


# ── ML Model (optional) ────────────────────────────────────────────────────────
_ml_pipeline = None
def get_ml():
    global _ml_pipeline
    if _ml_pipeline is None:
        try:
            with open('pipeline.pkl', 'rb') as f:
                _ml_pipeline = pickle.load(f)
            log.info("ML pipeline loaded")
        except FileNotFoundError:
            log.info("ML pipeline not found — run train_model.py or use keyword fallback")
        except Exception as exc:
            log.warning(f"ML pipeline load failed: {exc}")
    return _ml_pipeline

# ── Constants ──────────────────────────────────────────────────────────────────
IST = pytz.timezone('Asia/Kolkata')

CATEGORY_KEYWORDS = {
    'Food':          ['pizza','burger','kfc','swiggy','zomato','restaurant','cafe',
                      'coffee','lunch','dinner','breakfast','biryani','dosa','idli',
                      'chai','tea','grocery','milk','vegetables','dominos','subway','eat','meal'],
    'Travel':        ['uber','ola','bus','train','flight','metro','auto','petrol',
                      'diesel','toll','rapido','indigo','irctc','cab','taxi','parking','fuel'],
    'Entertainment': ['netflix','amazon prime','hotstar','spotify','movie','cinema',
                      'concert','game','pvr','inox','youtube','bookmyshow','event'],
    'Bills':         ['electricity','water','internet','airtel','jio','bsnl','rent',
                      'insurance','gas','mobile','dth','maintenance','subscription'],
    'Shopping':      ['amazon','flipkart','myntra','shoes','shirt','jeans','dress',
                      'meesho','nykaa','ajio','decathlon','jewellery','electronics'],
    'Health':        ['medicine','doctor','hospital','pharmacy','gym','yoga','medical',
                      'clinic','dentist','apollo','vitamins','prescription','blood test'],
    'Education':     ['books','udemy','coaching','school','college','tuition',
                      'stationery','coursera','byjus','unacademy','exam fee'],
    'Savings':       ['mutual fund','sip','ppf','nps','fixed deposit','gold',
                      'zerodha','groww','stocks','investment','recurring deposit'],
    'EMI':           ['emi','loan','credit card bill','home loan','car loan','personal loan'],
}

CATEGORY_ICONS = {
    'Food':'🍽️','Travel':'🚗','Entertainment':'🎬','Bills':'💡',
    'Shopping':'🛍️','Health':'🏥','Education':'📚','Savings':'💰',
    'EMI':'💳','General':'📦'
}

CATEGORY_COLORS = {
    'Food':'#ffb300','Travel':'#00e5ff','Entertainment':'#f72585',
    'Bills':'#7c5cfc','Shopping':'#00d68f','Health':'#ff6464',
    'Education':'#64a0ff','Savings':'#00d68f','EMI':'#ff9f40','General':'#6b7a99'
}

TAMIL = {
    'good_morning':'காலை வணக்கம்','good_afternoon':'மதிய வணக்கம்','good_evening':'மாலை வணக்கம்',
}

# ── Simple in-process rate limiter (auth routes) ───────────────────────────────
_rate_store = defaultdict(list)  # ip -> [timestamps]

def rate_limit(max_calls=10, window=60, template='login.html'):
    """Allow max_calls per window seconds per IP."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip  = request.remote_addr or 'unknown'
            now = time.time()
            calls = [t for t in _rate_store[ip] if now - t < window]
            if len(calls) >= max_calls:
                log.warning(f"Rate limit hit: {ip}")
                return render_template(
                    template,
                    error='Too many attempts. Please wait a minute.'
                ), 429
            calls.append(now)
            _rate_store[ip] = calls
            return f(*args, **kwargs)
        return wrapped
    return decorator

# ── Helpers ────────────────────────────────────────────────────────────────────
def ist_now():
    return datetime.now(IST)

def is_strong_password(p):
    if len(p) < 6:
        return False, "Password must be at least 6 characters long."
    if not any(c.isupper() for c in p):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in p):
        return False, "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in p):
        return False, "Password must contain at least one digit."
    if not any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?`~" for c in p):
        return False, "Password must contain at least one special character."
    return True, ""


def predict_category(title: str) -> str:
    pipe = get_ml()
    if pipe:
        try:
            return pipe.predict([title])[0]
        except Exception:
            pass
    tl = title.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(k in tl for k in kws):
            return cat
    return 'General'

def safe_commit():
    """Commit with rollback on error."""
    try:
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        log.error(f"DB commit error: {e}")
        return False

def owned_or_404(model, record_id):
    """Fetch a record that must belong to current_user — abort 404 otherwise.
    Prevents one user accessing another user's data via URL manipulation."""
    record = model.query.filter_by(id=record_id, user_id=current_user.id).first()
    if not record:
        abort(404)
    return record

# ── Database Models ────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id             = db.Column(db.Integer, primary_key=True)
    username       = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email          = db.Column(db.String(200), unique=True, nullable=True)
    password       = db.Column(db.String(200), nullable=False)
    full_name      = db.Column(db.String(200), default='')
    language       = db.Column(db.String(10), default='en')
    monthly_budget = db.Column(db.Float, default=0.0)
    monthly_income = db.Column(db.Float, default=50000.0)
    created_at     = db.Column(db.DateTime, default=ist_now)
    last_seen      = db.Column(db.DateTime, default=ist_now)
    recovery_pin   = db.Column(db.String(200), nullable=True)


    # Relationships with cascade delete — when user is deleted, all their data goes too
    expenses    = db.relationship('Expense',    backref='user', lazy='dynamic',
                                   cascade='all, delete-orphan', passive_deletes=True)
    budgets     = db.relationship('Budget',     backref='user', lazy='dynamic',
                                   cascade='all, delete-orphan', passive_deletes=True)
    investments = db.relationship('Investment', backref='user', lazy='dynamic',
                                   cascade='all, delete-orphan', passive_deletes=True)
    bills       = db.relationship('Bill',       backref='user', lazy='dynamic',
                                   cascade='all, delete-orphan', passive_deletes=True)
    financial_healths = db.relationship('FinancialHealth', backref='user', lazy='dynamic',
                                         cascade='all, delete-orphan', passive_deletes=True)
    prediction_histories = db.relationship('PredictionHistory', backref='user', lazy='dynamic',
                                            cascade='all, delete-orphan', passive_deletes=True)
    loan_predictions = db.relationship('LoanPredictionHistory', backref='user', lazy='dynamic',
                                       cascade='all, delete-orphan', passive_deletes=True)
    notifications = db.relationship('Notification', backref='user', lazy='dynamic',
                                    cascade='all, delete-orphan', passive_deletes=True)
    payments = db.relationship('PaymentHistory', backref='user', lazy='dynamic',
                               cascade='all, delete-orphan', passive_deletes=True)
    reports = db.relationship('ReportHistory', backref='user', lazy='dynamic',
                              cascade='all, delete-orphan', passive_deletes=True)
    goals = db.relationship('Goal', backref='user', lazy='dynamic',
                            cascade='all, delete-orphan', passive_deletes=True)
    insights = db.relationship('InsightHistory', backref='user', lazy='dynamic',
                               cascade='all, delete-orphan', passive_deletes=True)
    recommendations = db.relationship('RecommendationHistory', backref='user', lazy='dynamic',
                                      cascade='all, delete-orphan', passive_deletes=True)

    def touch(self):
        self.last_seen = ist_now()

    def __repr__(self):
        return f'<User {self.username}>'


class Expense(db.Model):
    __tablename__ = 'expense'
    __table_args__ = (
        db.Index('idx_expense_user_date', 'user_id', 'created_at'),  # fast per-user queries
    )
    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(200), nullable=False)
    amount       = db.Column(db.Float, nullable=False)
    category     = db.Column(db.String(100), default='General')
    note         = db.Column(db.String(500), default='')
    payment_mode = db.Column(db.String(50), default='UPI')
    created_at   = db.Column(db.DateTime, default=ist_now)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)


class Budget(db.Model):
    __tablename__ = 'budget'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'category', 'month', 'year', name='uq_budget_user_cat_month'),
    )
    id       = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    amount   = db.Column(db.Float, nullable=False)
    month    = db.Column(db.Integer, nullable=False)
    year     = db.Column(db.Integer, nullable=False)
    user_id  = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)


class Investment(db.Model):
    __tablename__ = 'investment'
    __table_args__ = (
        db.Index('idx_investment_user', 'user_id'),
    )
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(200), nullable=False)
    type          = db.Column(db.String(100), nullable=False)
    invested      = db.Column(db.Float, nullable=False)
    current_value = db.Column(db.Float, nullable=False)
    start_date    = db.Column(db.Date, nullable=True)
    maturity_date = db.Column(db.Date, nullable=True)
    note          = db.Column(db.String(500), default='')
    created_at    = db.Column(db.DateTime, default=ist_now)
    user_id       = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)


class Bill(db.Model):
    __tablename__ = 'bill'
    __table_args__ = (
        db.Index('idx_bill_user', 'user_id'),
    )
    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(200), nullable=False)
    amount         = db.Column(db.Float, nullable=False)
    due_day        = db.Column(db.Integer, nullable=False)  # backward compatibility: day of the month
    category       = db.Column(db.String(100), default='Bills')
    is_recurring   = db.Column(db.Boolean, default=True)
    is_paid        = db.Column(db.Boolean, default=False)
    paid_date      = db.Column(db.Date, nullable=True)
    note           = db.Column(db.String(500), default='')
    created_at     = db.Column(db.DateTime, default=ist_now)
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    
    # New columns for Financial Command Center
    priority       = db.Column(db.String(50), default='Medium') # Critical, High, Medium, Low
    auto_pay       = db.Column(db.Boolean, default=False)
    payment_method = db.Column(db.String(100), default='UPI')
    due_date       = db.Column(db.Date, nullable=True)  # Specific date if one-time
    frequency      = db.Column(db.String(100), default='Monthly') # Daily, Weekly, Monthly, Quarterly, Yearly, One-Time


class Notification(db.Model):
    __tablename__ = 'notification'
    __table_args__ = (
        db.Index('idx_notification_user', 'user_id'),
    )
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    bill_id      = db.Column(db.Integer, db.ForeignKey('bill.id', ondelete='SET NULL'), nullable=True)
    title        = db.Column(db.String(250), nullable=False)
    message      = db.Column(db.Text, nullable=False)
    category     = db.Column(db.String(100), nullable=False) # 'Bill', 'Budget', 'Balance', 'Savings', 'Spike'
    priority     = db.Column(db.String(50), default='Medium') # 'Critical', 'High', 'Medium', 'Low'
    is_read      = db.Column(db.Boolean, default=False)
    is_archived  = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=ist_now)


class PaymentHistory(db.Model):
    __tablename__ = 'payment_history'
    __table_args__ = (
        db.Index('idx_payment_history_user', 'user_id'),
    )
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    bill_id      = db.Column(db.Integer, db.ForeignKey('bill.id', ondelete='CASCADE'), nullable=False)
    name         = db.Column(db.String(200), nullable=False)
    amount       = db.Column(db.Float, nullable=False)
    paid_date    = db.Column(db.Date, nullable=False)
    payment_mode = db.Column(db.String(100), default='UPI')
    created_at   = db.Column(db.DateTime, default=ist_now)


class FinancialHealth(db.Model):
    __tablename__ = 'financial_health'
    __table_args__ = (
        db.Index('idx_financial_health_user', 'user_id'),
    )
    id                   = db.Column(db.Integer, primary_key=True)
    user_id              = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    score                = db.Column(db.Integer, nullable=False)
    savings_rate         = db.Column(db.Float, nullable=False)
    investment_ratio     = db.Column(db.Float, nullable=False)
    expense_ratio        = db.Column(db.Float, nullable=False)
    budget_score         = db.Column(db.Float, nullable=False)
    emergency_fund_score = db.Column(db.Float, nullable=False)
    created_at           = db.Column(db.DateTime, default=ist_now)


class PredictionHistory(db.Model):
    __tablename__ = 'prediction_history'
    __table_args__ = (
        db.Index('idx_prediction_history_user', 'user_id'),
    )
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    prediction  = db.Column(db.Text, nullable=False)  # JSON representation of the prediction
    period      = db.Column(db.Integer, nullable=False)  # period in months (e.g. 12 or 60)
    created_at  = db.Column(db.DateTime, default=ist_now)


class LoanPredictionHistory(db.Model):
    __tablename__ = 'loan_prediction_history'
    __table_args__ = (
        db.Index('idx_loan_prediction_history_user', 'user_id'),
    )
    id                   = db.Column(db.Integer, primary_key=True)
    user_id              = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    requested_amount     = db.Column(db.Float, nullable=False)
    tenure_months        = db.Column(db.Integer, nullable=False)
    approval_probability = db.Column(db.Float, nullable=False)
    eligible_amount      = db.Column(db.Float, nullable=False)
    estimated_emi        = db.Column(db.Float, nullable=False)
    risk_level           = db.Column(db.String(50), nullable=False)
    is_eligible          = db.Column(db.Boolean, nullable=False)
    created_at           = db.Column(db.DateTime, default=ist_now)


class ReportHistory(db.Model):
    __tablename__ = 'report_history'
    __table_args__ = (
        db.Index('idx_report_history_user', 'user_id'),
    )
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    report_name     = db.Column(db.String(250), nullable=False, default='Financial Report')  # Human-readable name
    report_type     = db.Column(db.String(100), nullable=False)   # Monthly, Yearly, Budget, Investment, Loan, Health
    file_name       = db.Column(db.String(250), nullable=False)
    file_path       = db.Column(db.String(500), nullable=True)    # Absolute path on disk
    file_size       = db.Column(db.Integer, default=0)            # File size in bytes
    version         = db.Column(db.Integer, default=1)            # Version counter for regenerated reports
    is_favorite     = db.Column(db.Boolean, default=False)
    share_key       = db.Column(db.String(100), nullable=True, unique=True)  # Secure public share token
    generated_date  = db.Column(db.DateTime, default=ist_now)
    last_downloaded = db.Column(db.DateTime, nullable=True)
    download_count  = db.Column(db.Integer, default=0)
    created_at      = db.Column(db.DateTime, default=ist_now)


# ── AI Goal Planner & Spending Insights Models ───────────────────────────────────

class Goal(db.Model):
    __tablename__ = 'goals'
    __table_args__ = (
        db.Index('idx_goal_user', 'user_id'),
    )
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    name         = db.Column(db.String(250), nullable=False)
    category     = db.Column(db.String(100), nullable=False)  # Emergency Fund, Laptop, Vehicle, Travel, Education, Wedding, House, Investment, Retirement, Custom Goal
    target_amount = db.Column(db.Float, nullable=False)
    current_savings = db.Column(db.Float, default=0.0)
    deadline     = db.Column(db.Date, nullable=False)
    monthly_contribution = db.Column(db.Float, default=0.0)
    priority     = db.Column(db.String(50), default='Medium')  # High, Medium, Low
    status       = db.Column(db.String(50), default='Active')  # Active, Completed, Paused
    notes        = db.Column(db.Text, nullable=True)
    created_at   = db.Column(db.DateTime, default=ist_now)

    history = db.relationship('GoalHistory', backref='goal', lazy='dynamic', cascade='all, delete-orphan')
    progress = db.relationship('GoalProgress', backref='goal', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('GoalNotifications', backref='goal', lazy='dynamic', cascade='all, delete-orphan')


class GoalHistory(db.Model):
    __tablename__ = 'goal_history'
    id           = db.Column(db.Integer, primary_key=True)
    goal_id      = db.Column(db.Integer, db.ForeignKey('goals.id', ondelete='CASCADE'), nullable=False)
    amount       = db.Column(db.Float, nullable=False)
    created_at   = db.Column(db.DateTime, default=ist_now)


class GoalProgress(db.Model):
    __tablename__ = 'goal_progress'
    id           = db.Column(db.Integer, primary_key=True)
    goal_id      = db.Column(db.Integer, db.ForeignKey('goals.id', ondelete='CASCADE'), nullable=False)
    monthly_target = db.Column(db.Float, nullable=False)
    weekly_target  = db.Column(db.Float, nullable=False)
    daily_target   = db.Column(db.Float, nullable=False)
    est_completion_date = db.Column(db.Date, nullable=True)
    success_probability = db.Column(db.Float, default=50.0)  # Percentage (0-100)
    created_at   = db.Column(db.DateTime, default=ist_now)


class GoalNotifications(db.Model):
    __tablename__ = 'goal_notifications'
    id           = db.Column(db.Integer, primary_key=True)
    goal_id      = db.Column(db.Integer, db.ForeignKey('goals.id', ondelete='CASCADE'), nullable=False)
    type         = db.Column(db.String(100), nullable=False)  # Target Missed, Milestone Reached, Adjustment Recommended
    message      = db.Column(db.Text, nullable=False)
    is_read      = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=ist_now)


class InsightHistory(db.Model):
    __tablename__ = 'insight_history'
    __table_args__ = (
        db.Index('idx_insight_user', 'user_id'),
    )
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    type         = db.Column(db.String(50), nullable=False)  # Daily, Weekly, Monthly, Yearly
    content      = db.Column(db.Text, nullable=False)        # JSON representation or text
    created_at   = db.Column(db.DateTime, default=ist_now)


class RecommendationHistory(db.Model):
    __tablename__ = 'recommendation_history'
    __table_args__ = (
        db.Index('idx_reco_user', 'user_id'),
    )
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    category     = db.Column(db.String(100), nullable=True)   # Budget adjustment, Cost-cutting, Saving
    message      = db.Column(db.Text, nullable=False)
    potential_savings = db.Column(db.Float, default=0.0)
    is_applied   = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=ist_now)


class GoalRecommendations(db.Model):
    __tablename__ = 'goal_recommendations'
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    goal_id      = db.Column(db.Integer, db.ForeignKey('goals.id', ondelete='CASCADE'), nullable=False)
    action       = db.Column(db.String(250), nullable=False)
    impact_amount = db.Column(db.Float, default=0.0)
    created_at   = db.Column(db.DateTime, default=ist_now)



@login_manager.user_loader
def load_user(user_id):
    """Called on every request — must be fast. Uses primary key lookup."""
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(User, uid)


@app.context_processor
def inject_nav_stats():
    """Lightweight overdue-bill count for sidebar badge on all pages."""
    if current_user.is_authenticated:
        now = ist_now()
        overdue = (Bill.query
                   .filter_by(user_id=current_user.id, is_paid=False)
                   .filter(Bill.due_day < now.day)
                   .count())
        return {'stats': {'overdue_bills': overdue}}
    return {}


# ── Before-request: update last_seen ──────────────────────────────────────────
@app.before_request
def update_last_seen():
    if current_user.is_authenticated:
        # Only update once per 60s to avoid hammering DB
        last = current_user.last_seen
        now = ist_now()
        if last:
            # last_seen might be naive/aware depending on DB driver; normalize safely
            if getattr(last, "tzinfo", None) is None:
                last_dt = last.replace(tzinfo=IST)
            else:
                last_dt = last
            if (now - last_dt).total_seconds() > 60:
                current_user.touch()
                safe_commit()


# ── Per-user stats (all queries scoped to user_id) ────────────────────────────
def get_user_stats(user_id: int) -> dict:
    now = ist_now()

    # All expenses for user — use .filter() not .all() to keep as query
    expenses = Expense.query.filter_by(user_id=user_id).all()

    this_month = [e for e in expenses
                  if e.created_at.month == now.month
                  and e.created_at.year  == now.year]

    total       = sum(e.amount for e in expenses)
    month_total = sum(e.amount for e in this_month)
    avg         = total / len(expenses) if expenses else 0

    cat_totals = {}
    for e in expenses:
        cat_totals[e.category] = cat_totals.get(e.category, 0) + e.amount

    monthly = {}
    for e in sorted(expenses, key=lambda x: x.created_at):
        key = e.created_at.strftime('%b %Y')
        monthly[key] = monthly.get(key, 0) + e.amount
    # Keep last 6 months
    monthly_keys = list(monthly.keys())[-6:]
    monthly_vals = [monthly[k] for k in monthly_keys]

    # Budget data — scoped to this user + this month
    budgets = Budget.query.filter_by(
        user_id=user_id, month=now.month, year=now.year
    ).all()

    budget_data = {}
    for b in budgets:
        spent = sum(e.amount for e in this_month if e.category == b.category)
        pct   = min(int((spent / b.amount) * 100), 100) if b.amount > 0 else 0
        budget_data[b.category] = {
            'budget': b.amount, 'spent': round(spent, 2),
            'remaining': round(max(b.amount - spent, 0), 2),
            'pct': pct, 'over': spent > b.amount
        }

    # Investments — scoped
    investments   = Investment.query.filter_by(user_id=user_id).all()
    total_invested = sum(i.invested      for i in investments)
    total_current  = sum(i.current_value for i in investments)
    inv_gain       = total_current - total_invested

    # Bills — scoped
    bills      = Bill.query.filter_by(user_id=user_id).all()
    overdue    = [b for b in bills if not b.is_paid and b.due_day < now.day]
    due_soon   = [b for b in bills if not b.is_paid
                  and now.day <= b.due_day <= now.day + 5]

    return {
        'total':          round(total, 2),
        'month_total':    round(month_total, 2),
        'avg':            round(avg, 2),
        'count':          len(expenses),
        'month_count':    len(this_month),
        'cat_totals':     cat_totals,
        'monthly_keys':   monthly_keys,
        'monthly_vals':   monthly_vals,
        'budget_data':    budget_data,
        'total_invested': round(total_invested, 2),
        'total_current':  round(total_current, 2),
        'inv_gain':       round(inv_gain, 2),
        'overdue_bills':  len(overdue),
        'due_soon_bills': len(due_soon),
        'top_category':   max(cat_totals, key=cat_totals.get) if cat_totals else '—',
    }


from services.financial_health import compute_financial_health
from services.savings_prediction import compute_savings_prediction


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════

# ── Dashboard ──────────────────────────────────────────────────────────────────
@app.route('/')
@login_required
def home():
    stats    = get_user_stats(current_user.id)
    expenses = (Expense.query
                .filter_by(user_id=current_user.id)
                .order_by(Expense.created_at.desc())
                .limit(25).all())
    now  = ist_now()
    hour = now.hour
    if   5  <= hour < 12: greeting = 'காலை வணக்கம்' if current_user.language == 'ta' else 'Good Morning'
    elif 12 <= hour < 17: greeting = 'மதிய வணக்கம்' if current_user.language == 'ta' else 'Good Afternoon'
    else:                  greeting = 'மாலை வணக்கம்' if current_user.language == 'ta' else 'Good Evening'

    # Module 1: Health Score
    health_info = compute_financial_health(current_user.id)
    health_score = health_info.get('score', 0)
    health_status = health_info.get('status', '—')

    # Module 2: Savings Projections
    last_pred = PredictionHistory.query.filter_by(user_id=current_user.id).order_by(PredictionHistory.created_at.desc()).first()
    if last_pred:
        try:
            import json
            pred_data = json.loads(last_pred.prediction)
            savings_1y = pred_data['moderate']['savings_1y']
        except Exception:
            savings_1y = 0.0
    else:
        pred_data = compute_savings_prediction(current_user.id)
        savings_1y = pred_data.get('moderate', {}).get('savings_1y', 0.0)

    # Module 3: Loan Eligibility
    last_loan = LoanPredictionHistory.query.filter_by(user_id=current_user.id).order_by(LoanPredictionHistory.created_at.desc()).first()

    # Notifications count
    from services.notification_service import get_user_notifications
    notifications = get_user_notifications(current_user.id)

    return render_template('index.html',
        stats=stats, expenses=expenses, greeting=greeting,
        category_icons=CATEGORY_ICONS, category_colors=CATEGORY_COLORS,
        now=now, lang=current_user.language,
        health_score=health_score, health_status=health_status,
        savings_1y=savings_1y, last_loan=last_loan,
        notifications=notifications
    )

# ── Add Expense ────────────────────────────────────────────────────────────────
@app.route('/add', methods=['POST'])
@login_required
def add_expense():
    title        = request.form.get('title', '').strip()
    amount_raw   = request.form.get('amount', '0').strip()
    note         = request.form.get('note', '').strip()
    payment_mode = request.form.get('payment_mode', 'UPI')
    category     = request.form.get('category', '').strip()

    if not title:
        return redirect('/')
    try:
        amount_f = float(amount_raw)
        if amount_f <= 0:
            return redirect('/')
    except ValueError:
        return redirect('/')

    if not category:
        category = predict_category(title)

    expense = Expense(
        title=title, amount=round(amount_f, 2),
        category=category, note=note,
        payment_mode=payment_mode,
        user_id=current_user.id          # ← always scoped to THIS user
    )
    db.session.add(expense)
    if not safe_commit():
        log.error(f"Failed to add expense for user {current_user.id}")
    return redirect('/')

# ── Delete Expense ─────────────────────────────────────────────────────────────
@app.route('/delete/<int:eid>', methods=['POST'])
@login_required
def delete_expense(eid):
    e = owned_or_404(Expense, eid)    # ← 404 if not this user's record
    db.session.delete(e)
    safe_commit()
    return redirect('/')

# ── Budget ─────────────────────────────────────────────────────────────────────
@app.route('/budget')
@login_required
def budget():
    now     = ist_now()
    budgets = Budget.query.filter_by(
        user_id=current_user.id, month=now.month, year=now.year
    ).all()

    this_month_expenses = (Expense.query
        .filter_by(user_id=current_user.id)
        .filter(
            db.extract('month', Expense.created_at) == now.month,
            db.extract('year',  Expense.created_at) == now.year
        ).all())

    budget_data = []
    for b in budgets:
        spent = sum(e.amount for e in this_month_expenses if e.category == b.category)
        pct   = min(int((spent / b.amount) * 100), 100) if b.amount > 0 else 0
        budget_data.append({
            'id': b.id, 'category': b.category,
            'budget': b.amount, 'spent': round(spent, 2),
            'remaining': round(max(b.amount - spent, 0), 2),
            'pct': pct, 'over': spent > b.amount,
            'icon':  CATEGORY_ICONS.get(b.category, '📦'),
            'color': CATEGORY_COLORS.get(b.category, '#6b7a99'),
        })

    return render_template('budget.html',
        budget_data=budget_data,
        total_budget=round(sum(b.amount for b in budgets), 2),
        total_spent=round(sum(b['spent'] for b in budget_data), 2),
        categories=list(CATEGORY_ICONS.keys()),
        category_icons=CATEGORY_ICONS,
        now=now, lang=current_user.language,
    )

@app.route('/budget/add', methods=['POST'])
@login_required
def add_budget():
    now      = ist_now()
    category = request.form.get('category', '').strip()
    try:
        amount_f = float(request.form.get('amount', 0))
        if amount_f <= 0:
            return redirect('/budget')
    except ValueError:
        return redirect('/budget')

    # Upsert — update if exists for this user+category+month, insert otherwise
    existing = Budget.query.filter_by(
        user_id=current_user.id,
        category=category,
        month=now.month,
        year=now.year
    ).first()

    if existing:
        existing.amount = amount_f
    else:
        db.session.add(Budget(
            category=category, amount=amount_f,
            month=now.month, year=now.year,
            user_id=current_user.id
        ))
    safe_commit()
    return redirect('/budget')

@app.route('/budget/delete/<int:bid>', methods=['POST'])
@login_required
def delete_budget(bid):
    b = owned_or_404(Budget, bid)
    db.session.delete(b)
    safe_commit()
    return redirect('/budget')

# ── Investments ────────────────────────────────────────────────────────────────
@app.route('/investments')
@login_required
def investments():
    invs = (Investment.query
            .filter_by(user_id=current_user.id)
            .order_by(Investment.created_at.desc()).all())

    total_invested = sum(i.invested      for i in invs)
    total_current  = sum(i.current_value for i in invs)
    gain           = total_current - total_invested
    gain_pct       = (gain / total_invested * 100) if total_invested > 0 else 0

    by_type = {}
    for i in invs:
        by_type[i.type] = by_type.get(i.type, 0) + i.current_value

    return render_template('investments.html',
        investments=invs,
        total_invested=round(total_invested, 2),
        total_current=round(total_current, 2),
        gain=round(gain, 2),
        gain_pct=round(gain_pct, 2),
        by_type=by_type,
        lang=current_user.language,
    )

@app.route('/investments/add', methods=['POST'])
@login_required
def add_investment():
    try:
        name     = request.form.get('name', '').strip()
        inv_type = request.form.get('type', 'SIP')
        invested = float(request.form.get('invested', 0))
        current  = float(request.form.get('current_value', 0))
        note     = request.form.get('note', '').strip()
        start_s  = request.form.get('start_date', '')
        mat_s    = request.form.get('maturity_date', '')

        if not name or invested <= 0:
            return redirect('/investments')

        start_d = datetime.strptime(start_s, '%Y-%m-%d').date() if start_s else None
        mat_d   = datetime.strptime(mat_s,   '%Y-%m-%d').date() if mat_s   else None

        db.session.add(Investment(
            name=name, type=inv_type,
            invested=round(invested, 2),
            current_value=round(current, 2),
            start_date=start_d, maturity_date=mat_d,
            note=note, user_id=current_user.id
        ))
        safe_commit()
    except Exception as e:
        log.error(f"add_investment error user={current_user.id}: {e}")
    return redirect('/investments')

@app.route('/investments/delete/<int:iid>', methods=['POST'])
@login_required
def delete_investment(iid):
    i = owned_or_404(Investment, iid)
    db.session.delete(i)
    safe_commit()
    return redirect('/investments')

@app.route('/investments/update/<int:iid>', methods=['POST'])
@login_required
def update_investment(iid):
    inv = owned_or_404(Investment, iid)
    try:
        new_val = float(request.form.get('current_value', inv.current_value))
        inv.current_value = round(new_val, 2)
        safe_commit()
    except ValueError:
        pass
    return redirect('/investments')

# ── Bills ──────────────────────────────────────────────────────────────────────
@app.route('/bills')
@login_required
def bills():
    now   = ist_now()
    bills = (Bill.query
             .filter_by(user_id=current_user.id)
             .order_by(Bill.due_day).all())

    bill_data = []
    for b in bills:
        days_left = b.due_day - now.day
        if b.is_paid:              status = 'paid'
        elif days_left < 0:        status = 'overdue'
        elif days_left <= 3:       status = 'due_soon'
        else:                      status = 'upcoming'
        bill_data.append({
            'id': b.id, 'name': b.name, 'amount': b.amount,
            'due_day': b.due_day, 'category': b.category,
            'is_paid': b.is_paid, 'note': b.note,
            'status': status, 'days_left': days_left,
            'icon': CATEGORY_ICONS.get(b.category, '📦'),
        })

    return render_template('bills.html',
        bill_data=bill_data,
        total_monthly=round(sum(b.amount for b in bills if b.is_recurring), 2),
        total_paid=round(sum(b['amount'] for b in bill_data if b['is_paid']), 2),
        total_pending=round(sum(b['amount'] for b in bill_data if not b['is_paid']), 2),
        categories=list(CATEGORY_ICONS.keys()),
        now=now, lang=current_user.language,
    )

@app.route('/bills/add', methods=['POST'])
@login_required
def add_bill():
    try:
        name    = request.form.get('name', '').strip()
        amount  = float(request.form.get('amount', 0))
        due_day = int(request.form.get('due_day', 1))
        if not name or amount <= 0 or not (1 <= due_day <= 31):
            return redirect('/bills')
        db.session.add(Bill(
            name=name, amount=round(amount, 2), due_day=due_day,
            category=request.form.get('category', 'Bills'),
            note=request.form.get('note', '').strip(),
            is_recurring=request.form.get('is_recurring') == 'on',
            user_id=current_user.id
        ))
        safe_commit()
    except Exception as e:
        log.error(f"add_bill error user={current_user.id}: {e}")
    return redirect('/bills')

@app.route('/bills/pay/<int:bid>', methods=['POST'])
@login_required
def pay_bill(bid):
    b = owned_or_404(Bill, bid)
    b.is_paid   = True
    b.paid_date = ist_now().date()
    # Auto-create expense entry
    db.session.add(Expense(
        title=f"Bill: {b.name}", amount=b.amount,
        category=b.category, note='Auto-paid from Bills',
        payment_mode='NetBanking',
        user_id=current_user.id
    ))
    safe_commit()
    return redirect('/bills')

@app.route('/bills/delete/<int:bid>', methods=['POST'])
@login_required
def delete_bill(bid):
    b = owned_or_404(Bill, bid)
    db.session.delete(b)
    safe_commit()
    return redirect('/bills')

# ── AI Advisor ─────────────────────────────────────────────────────────────────
@app.route('/advisor')
@login_required
def advisor():
    from chatbot import build_financial_context
    from services.financial_health import compute_financial_health
    stats = compute_financial_health(current_user.id)
    return render_template('advisor.html',
                           lang=current_user.language,
                           user_name=current_user.full_name or current_user.username,
                           stats=stats)


@app.route('/chat', methods=['POST'])
@login_required
def chat():
    from chatbot import ask_ai
    msg  = request.form.get('message', '').strip()
    lang = current_user.language
    if not msg:
        return jsonify({'reply': 'Please ask a question.', 'ok': False})
    # BUG FIX: include lang in session_id to properly isolate EN/TA sessions
    session_id = f"user_{current_user.id}_{lang}"
    try:
        # Pass user_id so chatbot can inject live financial context
        reply = ask_ai(msg, lang=lang, session_id=session_id, user_id=current_user.id)
        return jsonify({'reply': reply, 'ok': True})
    except Exception as e:
        log.error(f"Chat error user={current_user.id}: {e}")
        return jsonify({'reply': '⚠️ AI temporarily unavailable. Please try again in a moment.', 'ok': False})


@app.route('/api/chat/clear', methods=['POST'])
@login_required
def api_chat_clear():
    """Wipes the server-side Gemini session so 'Clear Chat' also resets AI memory."""
    from chatbot import clear_session
    lang = current_user.language
    session_id = f"user_{current_user.id}_{lang}"
    clear_session(session_id, lang)
    return jsonify({'ok': True, 'message': 'Chat memory cleared successfully'})


@app.route('/api/chat/context')
@login_required
def api_chat_context():
    """Returns user's live financial snapshot for the advisor page dynamic suggestions."""
    from chatbot import build_financial_context
    from services.financial_health import compute_financial_health
    stats = compute_financial_health(current_user.id)
    return jsonify({
        'ok': True,
        'income': current_user.monthly_income or 0,
        'health_score': stats.get('score', 0),
        'health_status': stats.get('status', 'N/A'),
        'savings_rate': stats.get('savings_rate', 0),
        'expense_ratio': stats.get('expense_ratio', 0),
        'months_covered': stats.get('months_covered', 0),
        'debt_ratio': stats.get('debt_ratio', 0),
        'user_name': current_user.full_name or current_user.username,
    })


# ── AI Goal Planner & Spending Insights Endpoints ───────────────────────────────

@app.route('/goals')
@login_required
def goals_dashboard():
    from app import Goal
    active_goals = Goal.query.filter_by(user_id=current_user.id).all()
    return render_template('goals.html', goals=active_goals, lang=current_user.language)


@app.route('/api/goals', methods=['GET', 'POST'])
@login_required
def api_goals():
    from app import Goal
    from services.goal_service import create_user_goal
    if request.method == 'POST':
        data = request.json or {}
        name = data.get('name')
        category = data.get('category')
        target_amount = float(data.get('target_amount', 0))
        current_savings = float(data.get('current_savings', 0))
        deadline = data.get('deadline')
        priority = data.get('priority', 'Medium')
        notes = data.get('notes')
        
        if not name or not category or target_amount <= 0 or not deadline:
            return jsonify({'ok': False, 'message': 'Missing required goal parameters'}), 400
            
        goal = create_user_goal(
            user_id=current_user.id,
            name=name,
            category=category,
            target_amount=target_amount,
            current_savings=current_savings,
            deadline_str=deadline,
            priority=priority,
            notes=notes
        )
        return jsonify({'ok': True, 'message': 'Goal created successfully', 'goal_id': goal.id})

    # GET request
    user_goals = Goal.query.filter_by(user_id=current_user.id).all()
    goals_list = []
    for g in user_goals:
        prog = g.progress.first()
        goals_list.append({
            'id': g.id,
            'name': g.name,
            'category': g.category,
            'target_amount': g.target_amount,
            'current_savings': g.current_savings,
            'deadline': g.deadline.isoformat(),
            'monthly_contribution': g.monthly_contribution,
            'priority': g.priority,
            'status': g.status,
            'progress_pct': round((g.current_savings / g.target_amount * 100.0) if g.target_amount > 0 else 0.0, 1),
            'success_probability': prog.success_probability if prog else 50.0,
            'est_completion_date': prog.est_completion_date.isoformat() if (prog and prog.est_completion_date) else g.deadline.isoformat()
        })
    return jsonify({'ok': True, 'goals': goals_list})


@app.route('/api/goals/<int:gid>', methods=['PUT', 'DELETE'])
@login_required
def api_goal_detail(gid):
    from app import Goal
    from services.goal_service import update_user_goal_savings, recalculate_goal_targets
    goal = Goal.query.filter_by(id=gid, user_id=current_user.id).first()
    if not goal:
        return jsonify({'ok': False, 'message': 'Goal not found'}), 404

    if request.method == 'DELETE':
        db.session.delete(goal)
        db.session.commit()
        return jsonify({'ok': True, 'message': 'Goal deleted successfully'})

    # PUT request
    data = request.json or {}
    if 'current_savings' in data:
        new_savings = float(data['current_savings'])
        update_user_goal_savings(gid, current_user.id, new_savings)
    
    if 'target_amount' in data:
        goal.target_amount = float(data['target_amount'])
    if 'deadline' in data:
        goal.deadline = datetime.strptime(data['deadline'], "%Y-%m-%d").date()
    if 'notes' in data:
        goal.notes = data['notes']
        
    db.session.commit()
    recalculate_goal_targets(gid)
    return jsonify({'ok': True, 'message': 'Goal updated successfully'})


@app.route('/api/goal-progress')
@login_required
def api_goal_progress():
    from app import Goal
    active_goals = Goal.query.filter_by(user_id=current_user.id).all()
    res = []
    for g in active_goals:
        prog = g.progress.first()
        res.append({
            'goal_name': g.name,
            'monthly_target': prog.monthly_target if prog else g.monthly_contribution,
            'weekly_target': prog.weekly_target if prog else 0,
            'daily_target': prog.daily_target if prog else 0,
            'success_probability': prog.success_probability if prog else 50.0,
            'est_completion_date': prog.est_completion_date.isoformat() if (prog and prog.est_completion_date) else g.deadline.isoformat()
        })
    return jsonify({'ok': True, 'progress': res})


@app.route('/api/goal-recommendations')
@login_required
def api_goal_recos():
    from app import Goal
    from services.goal_ai_service import generate_goal_ai_recommendations
    active_goals = Goal.query.filter_by(user_id=current_user.id).all()
    res = {}
    for g in active_goals:
        recos = generate_goal_ai_recommendations(current_user.id, g.id)
        res[g.name] = recos
    return jsonify({'ok': True, 'goal_recommendations': res})


@app.route('/insights')
@login_required
def insights_dashboard():
    from services.insight_service import generate_spending_insights_data
    insights = generate_spending_insights_data(current_user.id)
    return render_template('insights.html', insights=insights, lang=current_user.language)


@app.route('/api/spending-insights')
@login_required
def api_spending_insights():
    from services.insight_service import generate_spending_insights_data
    data = generate_spending_insights_data(current_user.id)
    return jsonify({'ok': True, 'insights': data})


@app.route('/api/monthly-analysis')
@login_required
def api_monthly_analysis():
    from services.insight_service import generate_spending_insights_data
    data = generate_spending_insights_data(current_user.id)
    return jsonify({'ok': True, 'monthly_analysis': data})


@app.route('/api/recommendations')
@login_required
def api_general_recos():
    from services.recommendation_service import generate_user_recommendations
    recos = generate_user_recommendations(current_user.id)
    return jsonify({'ok': True, 'recommendations': recos})


# ── Settings ───────────────────────────────────────────────────────────────────
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    error = None
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'profile':
            email = request.form.get('email', '').strip() or None
            if email and email != current_user.email:
                existing_email = User.query.filter(User.email == email).first()
                if existing_email:
                    error = 'Email is already registered by another account.'
            if not error:
                current_user.full_name     = request.form.get('full_name', '').strip()[:200]
                current_user.email         = email
                current_user.language      = request.form.get('language', current_user.language)
                try:
                    current_user.monthly_budget = float(request.form.get('monthly_budget', 0) or 0)
                except ValueError:
                    pass
                try:
                    current_user.monthly_income = float(request.form.get('monthly_income', 0) or 50000.0)
                except ValueError:
                    pass
                if not safe_commit():
                    error = 'Failed to save. Please try again.'

        elif action == 'password':
            old_pwd = request.form.get('old_password', '')
            new_pwd = request.form.get('new_password', '')
            is_ok, err_msg = is_strong_password(new_pwd)
            if not is_ok:
                error = err_msg
            elif not check_password_hash(current_user.password, old_pwd):
                error = 'Current password is incorrect.'
            else:
                current_user.password = generate_password_hash(new_pwd, method='pbkdf2:sha256', salt_length=16)
                safe_commit()

        if not error:
            return redirect('/settings')

    return render_template('settings.html',
        lang=current_user.language, error=error)


# ── Export ─────────────────────────────────────────────────────────────────────
@app.route('/export/csv')
@login_required
def export_csv():
    expenses = (Expense.query
                .filter_by(user_id=current_user.id)
                .order_by(Expense.created_at.desc()).all())

    lines = ['ID,Title,Amount,Category,Payment Mode,Note,Date']
    for e in expenses:
        note_safe  = e.note.replace('"', "'")
        title_safe = e.title.replace('"', "'")
        lines.append(
            f'{e.id},"{title_safe}",{e.amount},{e.category},'
            f'{e.payment_mode},"{note_safe}",'
            f'{e.created_at.strftime("%Y-%m-%d %H:%M")}'
        )

    output = '\n'.join(lines)
    return send_file(
        io.BytesIO(output.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'walletiq_{current_user.username}_{date.today()}.csv'
    )

# ── API ────────────────────────────────────────────────────────────────────────
@app.route('/api/stats')
@login_required
def api_stats():
    return jsonify(get_user_stats(current_user.id))


# ── Financial Health Routes ───────────────────────────────────────────────────
@app.route('/financial-health')
@login_required
def financial_health():
    from chatbot import generate_health_suggestions
    stats = compute_financial_health(current_user.id)
    lang = current_user.language
    
    recommendations = generate_health_suggestions(stats, lang=lang)
    
    # Store daily calculation in DB history
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    
    existing = (FinancialHealth.query
                .filter_by(user_id=current_user.id)
                .filter(FinancialHealth.created_at >= today_start,
                        FinancialHealth.created_at <= today_end)
                .first())
                
    if existing:
        existing.score = stats['score']
        existing.savings_rate = stats['savings_rate']
        existing.investment_ratio = stats['investment_ratio']
        existing.expense_ratio = stats['expense_ratio']
        existing.budget_score = stats['budget_score']
        existing.emergency_fund_score = stats['emergency_fund_score']
    else:
        db.session.add(FinancialHealth(
            user_id=current_user.id,
            score=stats['score'],
            savings_rate=stats['savings_rate'],
            investment_ratio=stats['investment_ratio'],
            expense_ratio=stats['expense_ratio'],
            budget_score=stats['budget_score'],
            emergency_fund_score=stats['emergency_fund_score']
        ))
    safe_commit()
    
    # Fetch trend (past 6 score points)
    history = (FinancialHealth.query
               .filter_by(user_id=current_user.id)
               .order_by(FinancialHealth.created_at.asc())
               .all())
    history_trend = history[-6:]
    trend_keys = [h.created_at.strftime('%b %d') for h in history_trend]
    trend_vals = [h.score for h in history_trend]
    
    return render_template('financial_health.html',
                           stats=stats,
                           recommendations=recommendations,
                           trend_keys=trend_keys,
                           trend_vals=trend_vals,
                           lang=lang,
                           now=ist_now())


@app.route('/financial-health/update-income', methods=['POST'])
@login_required
def update_income():
    try:
        income = float(request.form.get('monthly_income', 0))
        if income > 0:
            current_user.monthly_income = round(income, 2)
            safe_commit()
    except ValueError:
        pass
    return redirect('/financial-health')


@app.route('/api/financial-health')
@login_required
def api_financial_health():
    from chatbot import generate_health_suggestions
    stats = compute_financial_health(current_user.id)
    recommendations = generate_health_suggestions(stats, lang=current_user.language)
    return jsonify({
        "score": stats['score'],
        "status": stats['status'],
        "recommendations": recommendations
    })


@app.route('/savings-prediction')
@login_required
def savings_prediction():
    from chatbot import generate_savings_suggestions
    
    # Get parameters from query string
    try:
        sal_growth = float(request.args.get('salary_growth', 8.0))
        inflation = float(request.args.get('inflation', 6.0))
        mod_return = float(request.args.get('moderate_return', 10.0))
    except ValueError:
        sal_growth = 8.0
        inflation = 6.0
        mod_return = 10.0

    forecast = compute_savings_prediction(
        user_id=current_user.id,
        salary_growth=sal_growth,
        inflation=inflation,
        moderate_return=mod_return
    )

    stats = compute_financial_health(current_user.id)
    lang = current_user.language
    recommendations = generate_savings_suggestions(stats, forecast, lang=lang)

    # Fetch recent prediction histories
    history = (PredictionHistory.query
               .filter_by(user_id=current_user.id)
               .order_by(PredictionHistory.created_at.desc())
               .limit(5).all())

    # Format history records for display
    saved_runs = []
    import json
    for h in history:
        try:
            pred_data = json.loads(h.prediction)
            saved_runs.append({
                'id': h.id,
                'created_at': h.created_at.strftime('%Y-%m-%d %H:%M'),
                'moderate_1y': pred_data.get('moderate', {}).get('savings_1y', 0),
                'moderate_5y': pred_data.get('moderate', {}).get('savings_5y', 0),
                'sal_growth': pred_data.get('salary_growth', 8.0),
                'inflation': pred_data.get('inflation', 6.0),
                'moderate_return': pred_data.get('moderate_return', 10.0)
            })
        except Exception:
            pass

    return render_template('savings_prediction.html',
                           forecast=forecast,
                           recommendations=recommendations,
                           saved_runs=saved_runs,
                           lang=lang,
                           now=ist_now())


@app.route('/api/savings-prediction/save', methods=['POST'])
@login_required
def save_prediction():
    import json
    try:
        sal_growth = float(request.form.get('salary_growth', 8.0))
        inflation = float(request.form.get('inflation', 6.0))
        mod_return = float(request.form.get('moderate_return', 10.0))
    except ValueError:
        return jsonify({'error': 'Invalid parameters'}), 400

    forecast = compute_savings_prediction(
        user_id=current_user.id,
        salary_growth=sal_growth,
        inflation=inflation,
        moderate_return=mod_return
    )

    # Save to history
    record = PredictionHistory(
        user_id=current_user.id,
        prediction=json.dumps(forecast),
        period=60  # 5-year simulation
    )
    db.session.add(record)
    if safe_commit():
        return jsonify({
            'success': True,
            'message': 'Projection configuration saved successfully!',
            'run': {
                'id': record.id,
                'created_at': record.created_at.strftime('%Y-%m-%d %H:%M'),
                'moderate_1y': forecast['moderate']['savings_1y'],
                'moderate_5y': forecast['moderate']['savings_5y'],
                'sal_growth': sal_growth,
                'inflation': inflation,
                'moderate_return': mod_return
            }
        })
    return jsonify({'error': 'Failed to save configuration'}), 500


@app.route('/loan-eligibility')
@login_required
def loan_eligibility():
    from services.loan_prediction import predict_loan_eligibility
    
    # Get parameters from query string
    try:
        amount = float(request.args.get('requested_amount', 500000.0))
        tenure = int(request.args.get('tenure_months', 36))
        credit = int(request.args.get('credit_score', 700))
        emp = int(request.args.get('employment_status', 1))
    except ValueError:
        amount = 500000.0
        tenure = 36
        credit = 700
        emp = 1

    res = predict_loan_eligibility(
        current_user.id,
        requested_amount=amount,
        tenure_months=tenure,
        credit_score=credit,
        employment_status=emp,
        lang=current_user.language
    )

    # Fetch recent history
    history = (LoanPredictionHistory.query
               .filter_by(user_id=current_user.id)
               .order_by(LoanPredictionHistory.created_at.desc())
               .limit(5).all())

    saved_runs = []
    for h in history:
        saved_runs.append({
            'id': h.id,
            'created_at': h.created_at.strftime('%Y-%m-%d %H:%M'),
            'requested_amount': h.requested_amount,
            'tenure_months': h.tenure_months,
            'approval_probability': h.approval_probability,
            'eligible_amount': h.eligible_amount,
            'estimated_emi': h.estimated_emi,
            'risk_level': h.risk_level,
            'is_eligible': h.is_eligible
        })

    return render_template('loan_eligibility.html',
                           result=res,
                           saved_runs=saved_runs,
                           lang=current_user.language,
                           now=ist_now())


@app.route('/api/loan-eligibility', methods=['POST'])
@login_required
def api_loan_eligibility():
    from services.loan_prediction import predict_loan_eligibility
    try:
        amount = float(request.form.get('requested_amount', 500000.0))
        tenure = int(request.form.get('tenure_months', 36))
        credit = int(request.form.get('credit_score', 700))
        emp = int(request.form.get('employment_status', 1))
    except ValueError:
        return jsonify({'error': 'Invalid input parameters'}), 400

    res = predict_loan_eligibility(
        current_user.id,
        requested_amount=amount,
        tenure_months=tenure,
        credit_score=credit,
        employment_status=emp,
        lang=current_user.language
    )

    # Save to history
    record = LoanPredictionHistory(
        user_id=current_user.id,
        requested_amount=amount,
        tenure_months=tenure,
        approval_probability=res['approval_probability'],
        eligible_amount=res['eligible_amount'],
        estimated_emi=res['estimated_emi'],
        risk_level=res['risk_level'],
        is_eligible=res['is_eligible']
    )
    db.session.add(record)
    if safe_commit():
        return jsonify({
            'success': True,
            'result': {
                'is_eligible': res['is_eligible'],
                'approval_probability': res['approval_probability'],
                'eligible_amount': res['eligible_amount'],
                'estimated_emi': res['estimated_emi'],
                'debt_to_income': res['debt_to_income'],
                'risk_level': res['risk_level'],
                'suggestions': res['suggestions'],
                'created_at': record.created_at.strftime('%Y-%m-%d %H:%M')
            }
        })
    return jsonify({'error': 'Failed to save prediction record'}), 500


# ── Financial Command Center ───────────────────────────────────────────────────

@app.route('/command-center')
@login_required
def command_center():
    from services.bill_service import auto_generate_recurring_bills, get_user_bills
    from services.notification_service import generate_financial_alerts, get_user_notifications
    from services.payment_service import get_user_payment_history
    
    # 1. Automations & Alerts
    auto_generate_recurring_bills(current_user.id)
    generate_financial_alerts(current_user.id)
    
    # 2. Fetch data
    bills = get_user_bills(current_user.id)
    notifications = get_user_notifications(current_user.id)
    payment_history = get_user_payment_history(current_user.id)
    
    return render_template('command_center.html',
                           bills=bills,
                           notifications=notifications,
                           payment_history=payment_history,
                           lang=current_user.language,
                           now=ist_now(),
                           category_icons=CATEGORY_ICONS)


@app.route('/api/bills', methods=['GET', 'POST'])
@login_required
def api_bills():
    from services.bill_service import get_user_bills, create_bill
    if request.method == 'GET':
        bills = get_user_bills(current_user.id)
        result = []
        for b in bills:
            result.append({
                'id': b.id,
                'name': b.name,
                'amount': b.amount,
                'due_day': b.due_day,
                'due_date': b.due_date.isoformat() if b.due_date else None,
                'category': b.category,
                'is_recurring': b.is_recurring,
                'is_paid': b.is_paid,
                'priority': b.priority,
                'auto_pay': b.auto_pay,
                'payment_method': b.payment_method,
                'note': b.note
            })
        return jsonify(result)
        
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        amount = float(request.form.get('amount', 0))
        category = request.form.get('category', 'Bills')
        due_day = int(request.form.get('due_day', 1))
        is_recurring = request.form.get('is_recurring') == 'on' or request.form.get('is_recurring') == 'true'
        due_date_str = request.form.get('due_date', '').strip() or None
        priority = request.form.get('priority', 'Medium')
        auto_pay = request.form.get('auto_pay') == 'on' or request.form.get('auto_pay') == 'true'
        payment_method = request.form.get('payment_method', 'UPI')
        note = request.form.get('note', '').strip()
        
        if not name or amount <= 0:
            return jsonify({'success': False, 'error': 'Invalid parameters'}), 400
            
        res = create_bill(
            user_id=current_user.id,
            name=name,
            amount=amount,
            category=category,
            due_day=due_day,
            is_recurring=is_recurring,
            due_date_str=due_date_str,
            priority=priority,
            auto_pay=auto_pay,
            payment_method=payment_method,
            note=note
        )
        return jsonify({'success': True, 'bill': res})


@app.route('/api/bills/<int:bid>', methods=['PUT', 'DELETE'])
@login_required
def api_bill_detail(bid):
    from services.bill_service import update_bill, delete_bill
    if request.method == 'DELETE':
        success = delete_bill(current_user.id, bid)
        return jsonify({'success': success})
        
    if request.method == 'PUT':
        name = request.form.get('name', '').strip()
        amount = float(request.form.get('amount', 0))
        category = request.form.get('category', 'Bills')
        due_day = int(request.form.get('due_day', 1))
        is_recurring = request.form.get('is_recurring') == 'on' or request.form.get('is_recurring') == 'true'
        due_date_str = request.form.get('due_date', '').strip() or None
        priority = request.form.get('priority', 'Medium')
        auto_pay = request.form.get('auto_pay') == 'on' or request.form.get('auto_pay') == 'true'
        payment_method = request.form.get('payment_method', 'UPI')
        note = request.form.get('note', '').strip()
        is_paid = request.form.get('is_paid') == 'on' or request.form.get('is_paid') == 'true'
        
        if not name or amount <= 0:
            return jsonify({'success': False, 'error': 'Invalid parameters'}), 400
            
        res = update_bill(
            user_id=current_user.id,
            bill_id=bid,
            name=name,
            amount=amount,
            category=category,
            due_day=due_day,
            is_recurring=is_recurring,
            due_date_str=due_date_str,
            priority=priority,
            auto_pay=auto_pay,
            payment_method=payment_method,
            note=note,
            is_paid=is_paid
        )
        if not res:
            return jsonify({'success': False, 'error': 'Bill not found'}), 404
        return jsonify({'success': True, 'bill': res})


@app.route('/api/reminders')
@login_required
def api_reminders():
    from services.bill_service import get_user_bills
    bills = get_user_bills(current_user.id)
    reminders = []
    for b in bills:
        if not b.is_paid:
            reminders.append({
                'id': b.id,
                'name': b.name,
                'amount': b.amount,
                'category': b.category,
                'due_day': b.due_day,
                'priority': b.priority
            })
    return jsonify(reminders)


@app.route('/api/notifications')
@login_required
def api_notifications():
    from services.notification_service import get_user_notifications
    notifications = get_user_notifications(current_user.id)
    res = []
    for n in notifications:
        res.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'category': n.category,
            'priority': n.priority,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M')
        })
    return jsonify(res)


@app.route('/api/notifications/read-all', methods=['POST'])
@login_required
def api_notifications_read_all():
    from services.notification_service import mark_all_notifications_read
    success = mark_all_notifications_read(current_user.id)
    return jsonify({'success': success})


@app.route('/api/notifications/read/<int:nid>', methods=['POST'])
@login_required
def api_notifications_read(nid):
    from services.notification_service import mark_notification_read
    success = mark_notification_read(current_user.id, nid)
    return jsonify({'success': success})


@app.route('/api/pay', methods=['POST'])
@login_required
def api_pay():
    from services.payment_service import pay_bill_service
    bill_id = int(request.form.get('bill_id', 0))
    payment_mode = request.form.get('payment_mode', 'UPI')
    
    if not bill_id:
        return jsonify({'success': False, 'error': 'Invalid bill ID'}), 400
        
    res = pay_bill_service(current_user.id, bill_id, payment_mode)
    return jsonify(res)


@app.route('/api/calendar')
@login_required
def api_calendar():
    from services.calendar_service import get_monthly_calendar_events
    try:
        year = int(request.args.get('year', ist_now().year))
        month = int(request.args.get('month', ist_now().month))
    except ValueError:
        year = ist_now().year
        month = ist_now().month
        
    events = get_monthly_calendar_events(current_user.id, year, month)
    return jsonify(events)


@app.route('/api/dashboard-summary')
@login_required
def api_dashboard_summary():
    from services.bill_service import get_user_bills
    from services.notification_service import get_user_notifications
    
    bills = get_user_bills(current_user.id)
    notifications = get_user_notifications(current_user.id)
    
    unpaid = [b for b in bills if not b.is_paid]
    
    return jsonify({
        'unread_notifications_count': len(notifications),
        'unpaid_bills_count': len(unpaid),
        'total_unpaid_amount': sum(b.amount for b in unpaid)
    })


# ── Smart Financial Report Studio (Premium) ────────────────────────────────────

@app.route('/report-studio')
@login_required
def report_studio():
    from services.report_service import get_report_data, get_storage_stats
    now = ist_now()
    preview = get_report_data(current_user.id, now.year, now.month)
    stats = get_storage_stats(current_user.id)
    # Search & filter support
    search = request.args.get('search', '').strip()
    ftype  = request.args.get('filter', '').strip()   # Monthly, Yearly, etc.
    query = ReportHistory.query.filter_by(user_id=current_user.id)
    if search:
        query = query.filter(ReportHistory.report_name.ilike(f'%{search}%'))
    if ftype:
        query = query.filter(ReportHistory.report_type.ilike(f'%{ftype}%'))
    reports = query.order_by(ReportHistory.created_at.desc()).all()
    all_reports = ReportHistory.query.filter_by(user_id=current_user.id).order_by(ReportHistory.created_at.desc()).all()
    return render_template('report_studio.html',
                           reports=reports,
                           all_reports=all_reports,
                           preview=preview,
                           stats=stats,
                           search=search,
                           ftype=ftype,
                           lang=current_user.language,
                           now=now)


# ── Primary generate route (old path kept for backward compat) ─────────────────
@app.route('/api/report/generate', methods=['POST'])
@app.route('/api/reports/generate',  methods=['POST'])
@login_required
def api_reports_generate():
    from services.report_service import (
        generate_pdf_report, generate_excel_report,
        get_report_data, make_report_name,
        get_next_version_filepath, REPORTS_DIR
    )
    report_type = request.form.get('report_type', 'Monthly')
    fmt = request.form.get('format', 'PDF')
    try:
        year  = int(request.form.get('year',  ist_now().year))
        month = int(request.form.get('month', ist_now().month))
    except ValueError:
        year, month = ist_now().year, ist_now().month

    # Build base file path and check for versioning
    os.makedirs(REPORTS_DIR, exist_ok=True)
    username = current_user.username
    ext      = 'pdf' if fmt == 'PDF' else 'xlsx'
    base_filename = f"WalletIQ_Report_{username}_{year}_{month}.{ext}"
    base_path     = os.path.join(REPORTS_DIR, base_filename)
    filepath, version = get_next_version_filepath(base_path, ext)

    # Generate
    if fmt == 'PDF':
        generate_pdf_report(current_user.id, year, month)
        # Override to versioned path if needed
        if version > 1:
            import shutil
            shutil.move(base_path, filepath)
    else:
        generate_excel_report(current_user.id, year, month)
        if version > 1:
            import shutil
            shutil.move(base_path, filepath)

    if not os.path.exists(filepath):
        # If versioned path not found, fall back to base
        filepath = base_path

    if not os.path.exists(filepath):
        return jsonify({'success': False, 'error': 'Report compilation failed'}), 500

    file_size = os.path.getsize(filepath)
    filename  = os.path.basename(filepath)
    rname     = make_report_name(report_type, year, month)
    if version > 1:
        rname += f' (v{version})'

    report = ReportHistory(
        user_id=current_user.id,
        report_name=rname,
        report_type=f'{report_type} ({fmt})',
        file_name=filename,
        file_path=filepath,
        file_size=file_size,
        version=version
    )
    db.session.add(report)
    db.session.commit()

    rep_data = get_report_data(current_user.id, year, month)
    return jsonify({
        'success': True,
        'report_id':    report.id,
        'report_name':  rname,
        'file_name':    filename,
        'file_size_kb': round(file_size / 1024, 1),
        'version':      version,
        'ai_commentary': rep_data.get('ai_commentary', '')
    })


# ── List all reports (with search/filter) ──────────────────────────────────────
@app.route('/api/reports')
@login_required
def api_reports_list():
    search = request.args.get('search', '').strip()
    ftype  = request.args.get('filter', '').strip()
    fav    = request.args.get('favorites', '').lower() == 'true'
    query  = ReportHistory.query.filter_by(user_id=current_user.id)
    if search:
        query = query.filter(ReportHistory.report_name.ilike(f'%{search}%'))
    if ftype:
        query = query.filter(ReportHistory.report_type.ilike(f'%{ftype}%'))
    if fav:
        query = query.filter_by(is_favorite=True)
    reports = query.order_by(ReportHistory.created_at.desc()).all()
    return jsonify([_report_to_dict(r) for r in reports])


# ── Single report detail ───────────────────────────────────────────────────────
@app.route('/api/reports/<int:rid>')
@login_required
def api_reports_get(rid):
    r = ReportHistory.query.filter_by(id=rid, user_id=current_user.id).first_or_404()
    return jsonify(_report_to_dict(r))


# ── Download (new path) ────────────────────────────────────────────────────────
@app.route('/api/report/download/<int:rid>')
@app.route('/api/reports/download/<int:rid>')
@login_required
def api_reports_download(rid):
    report = ReportHistory.query.filter_by(id=rid, user_id=current_user.id).first_or_404()
    reports_dir = os.path.join(app.instance_path, 'reports')
    filepath = report.file_path or os.path.join(reports_dir, report.file_name)
    if not os.path.exists(filepath):
        filepath = os.path.join(reports_dir, report.file_name)
    if not os.path.exists(filepath):
        return abort(404)
    report.download_count += 1
    report.last_downloaded = ist_now()
    db.session.commit()
    return send_from_directory(os.path.dirname(filepath),
                               os.path.basename(filepath),
                               as_attachment=True)


# ── Delete (new path) ─────────────────────────────────────────────────────────
@app.route('/api/report/delete/<int:rid>', methods=['DELETE'])
@app.route('/api/reports/<int:rid>',       methods=['DELETE'])
@login_required
def api_reports_delete(rid):
    report = ReportHistory.query.filter_by(id=rid, user_id=current_user.id).first()
    if not report:
        return jsonify({'success': False, 'error': 'Report not found'}), 404
    fp = report.file_path or os.path.join(app.instance_path, 'reports', report.file_name)
    if os.path.exists(fp):
        try:
            os.remove(fp)
        except OSError:
            pass
    db.session.delete(report)
    db.session.commit()
    return jsonify({'success': True})


# ── Toggle favorite ────────────────────────────────────────────────────────────
@app.route('/api/reports/favorite', methods=['POST'])
@login_required
def api_reports_favorite():
    rid = int(request.form.get('report_id', 0))
    report = ReportHistory.query.filter_by(id=rid, user_id=current_user.id).first()
    if not report:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    report.is_favorite = not report.is_favorite
    db.session.commit()
    return jsonify({'success': True, 'is_favorite': report.is_favorite})


# ── Generate / revoke share link ───────────────────────────────────────────────
@app.route('/api/reports/share', methods=['POST'])
@login_required
def api_reports_share():
    import secrets
    rid = int(request.form.get('report_id', 0))
    report = ReportHistory.query.filter_by(id=rid, user_id=current_user.id).first()
    if not report:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    if report.share_key:
        # Revoke existing link
        report.share_key = None
        db.session.commit()
        return jsonify({'success': True, 'revoked': True, 'share_url': None})
    # Generate new secure token
    token = secrets.token_urlsafe(32)
    report.share_key = token
    db.session.commit()
    share_url = request.host_url.rstrip('/') + f'/shared/report/{token}'
    return jsonify({'success': True, 'share_url': share_url, 'share_key': token})


# ── Public shared report viewer ────────────────────────────────────────────────
@app.route('/shared/report/<string:key>')
def public_shared_report(key):
    report = ReportHistory.query.filter_by(share_key=key).first_or_404()
    from services.report_service import get_report_data
    import re
    def extract_ym(name):
        month_map = {m.lower(): i+1 for i,m in enumerate(
            ['january','february','march','april','may','june',
             'july','august','september','october','november','december'])}
        parts = name.lower().split()
        m = next((month_map[p] for p in parts if p in month_map), ist_now().month)
        y = next((int(p) for p in parts if re.match(r'^\d{4}$', p)), ist_now().year)
        return y, m
    year, month = extract_ym(report.report_name)
    data = get_report_data(report.user_id, year, month)
    return render_template('shared_report.html', report=report, data=data)


# ── AI Report Comparison ───────────────────────────────────────────────────────
@app.route('/api/reports/compare', methods=['POST'])
@login_required
def api_reports_compare():
    from services.report_service import generate_ai_comparison
    try:
        rid_a = int(request.form.get('report_a_id', 0))
        rid_b = int(request.form.get('report_b_id', 0))
    except ValueError:
        return jsonify({'error': 'Invalid report IDs'}), 400
    if not rid_a or not rid_b:
        return jsonify({'error': 'Both report IDs are required'}), 400
    result = generate_ai_comparison(current_user.id, rid_a, rid_b)
    return jsonify(result)


# ── Storage Stats ──────────────────────────────────────────────────────────────
@app.route('/api/reports/stats')
@login_required
def api_reports_stats():
    from services.report_service import get_storage_stats
    return jsonify(get_storage_stats(current_user.id))


# ── Backward-compat history list ───────────────────────────────────────────────
@app.route('/api/report/history')
@login_required
def api_report_history():
    reports = ReportHistory.query.filter_by(user_id=current_user.id).order_by(ReportHistory.created_at.desc()).all()
    return jsonify([_report_to_dict(r) for r in reports])


def _report_to_dict(r):
    """Shared serialiser for ReportHistory ORM objects"""
    return {
        'id':             r.id,
        'report_name':    r.report_name,
        'report_type':    r.report_type,
        'file_name':      r.file_name,
        'file_size_kb':   round((r.file_size or 0) / 1024, 1),
        'version':        r.version or 1,
        'is_favorite':    r.is_favorite,
        'share_key':      r.share_key,
        'download_count': r.download_count,
        'last_downloaded': r.last_downloaded.strftime('%d %b %Y') if r.last_downloaded else '—',
        'generated_date': r.generated_date.strftime('%d %b %Y, %I:%M %p')
    }


# ── Auth ───────────────────────────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
@rate_limit(max_calls=20, window=60, template='register.html')
def register():
    import re
    if current_user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')
        email    = request.form.get('email', '').strip() or None
        fullname = request.form.get('full_name', '').strip()
        language = request.form.get('language', 'en')
        recovery_pin = request.form.get('recovery_pin', '').strip()

        # Validation
        if not username:
            return render_template('register.html', error='Username is required.')
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            return render_template('register.html', error='Username must be 3-20 characters and contain only letters, numbers, and underscores.')
        
        if email and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            return render_template('register.html', error='Invalid email address format.')

        is_ok, err_msg = is_strong_password(password)
        if not is_ok:
            return render_template('register.html', error=err_msg)

        if password != confirm:
            return render_template('register.html', error='Passwords do not match.')

        if not recovery_pin or len(recovery_pin) != 6 or not recovery_pin.isdigit():
            return render_template('register.html', error='Recovery PIN must be exactly 6 digits.')

        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already taken. Choose another.')
        
        if email:
            existing = User.query.filter(User.email == email).first()
            if existing:
                return render_template('register.html', error='Email already registered.')

        user = User(
            username=username,
            email=email,
            full_name=fullname,
            language=language,
            password=generate_password_hash(password, method='pbkdf2:sha256', salt_length=16),
            recovery_pin=generate_password_hash(recovery_pin, method='pbkdf2:sha256', salt_length=16)
        )
        db.session.add(user)
        if safe_commit():
            log.info(f"New user registered: {username}")
            login_user(user, remember=True)
            return redirect('/')
        else:
            return render_template('register.html', error='Registration failed. Please try again.')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
@rate_limit(max_calls=15, window=60)
def login():
    if current_user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        language = request.form.get('language', 'en')
        remember = request.form.get('remember') == 'on'

        if not username_or_email or not password:
            return render_template('login.html', error='Username/Email and Password are required.')

        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()

        if user and check_password_hash(user.password, password):
            user.language  = language
            user.last_seen = ist_now()
            safe_commit()
            login_user(user, remember=remember)
            log.info(f"Login: {user.username} lang={language}")

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):  # prevent open redirect
                return redirect(next_page)
            return redirect('/')

        log.warning(f"Failed login attempt: {username_or_email} from {request.remote_addr}")
        return render_template('login.html', error='Invalid username/email or password.')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    log.info(f"Logout: {username}")
    return redirect('/login')


@app.route('/forgot-password', methods=['GET', 'POST'])
@rate_limit(max_calls=10, window=60, template='forgot_password.html')
def forgot_password():
    if current_user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        recovery_pin = request.form.get('recovery_pin', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username_or_email or not recovery_pin or not new_password:
            return render_template('forgot_password.html', error='All fields are required.')

        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()
        
        if not user:
            return render_template('forgot_password.html', error='User not found.')

        if not user.recovery_pin or not check_password_hash(user.recovery_pin, recovery_pin):
            return render_template('forgot_password.html', error='Invalid recovery PIN.')

        is_ok, err_msg = is_strong_password(new_password)
        if not is_ok:
            return render_template('forgot_password.html', error=err_msg)

        if new_password != confirm_password:
            return render_template('forgot_password.html', error='Passwords do not match.')

        user.password = generate_password_hash(new_password, method='pbkdf2:sha256', salt_length=16)
        db.session.commit()
        log.info(f"Password reset success for user: {user.username}")
        return render_template('login.html', success='Password reset successful. Sign in with your new password.')

    return render_template('forgot_password.html')



# ── Error Handlers ─────────────────────────────────────────────────────────────
@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, title='Access Forbidden', message='You do not have permission to access this resource.'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, title='Page Not Found', message='The page you are looking for does not exist or has been moved.'), 404

@app.errorhandler(429)
def too_many(e):
    return render_template('error.html', code=429, title='Too Many Requests', message='Rate limit exceeded. Please wait a moment and try again.'), 429

@app.errorhandler(500)
def server_error(e):
    db.session.rollback()
    log.exception("500 error occurred")
    return render_template('error.html', code=500, title='Internal Server Error', message='A temporary database or server error occurred. Our engineers have been notified.'), 500



# ── Bootstrap ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    # Production schema management should be handled by Flask-Migrate/Alembic.
    # DO NOT call db.create_all() here.
    with app.app_context():
        log.info("WalletIQ v2.0 — App starting (use migrations to manage schema)")

    # Avoid accidental duplicate dev servers on Windows (SO_REUSEADDR).
    use_reloader = '--reload' in sys.argv
    app.run(
        debug=False,
        host='127.0.0.1',
        port=5000,
        threaded=True,
        use_reloader=use_reloader,
    )

