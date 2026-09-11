"""
api_v1.py — Complete Modular REST API Blueprint for WalletIQ (v1)
Conforms to strict production REST API standards:
- JSON envelopes: { "success": true, "data": ..., "message": ... }
- Safe HTTP status codes
- Full user data isolation (ownership checks on every read/write)
- Dual-mode authentication (Session Cookies + Authorization: Bearer tokens)
"""

import os
import io
import csv
import json
import logging
import base64
from datetime import datetime, date
from urllib.parse import quote_plus

from flask import Blueprint, request, jsonify, send_file, current_app, abort
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from api_response import success_response, error_response
from auth_token import generate_auth_token, api_login_required, get_authenticated_user
from db_resilience import safe_commit

log = logging.getLogger('walletiq.api_v1')
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')


def _get_user():
    return get_authenticated_user()


def _owned(model, record_id, user_id):
    from app import db
    record = model.query.filter_by(id=record_id, user_id=user_id).first()
    return record


# ══════════════════════════════════════════════════════════════════════════════
# 1. AUTHENTICATION & PROFILE
# ══════════════════════════════════════════════════════════════════════════════

@api_v1.route('/auth/register', methods=['POST'])
def api_register():
    from app import db, User, is_strong_password, ist_now

    data = request.get_json(silent=True) or request.form
    username = (data.get('username') or '').strip().lower()
    password = data.get('password') or ''
    email = (data.get('email') or '').strip().lower() or None
    full_name = (data.get('full_name') or '').strip()
    language = data.get('language', 'en')
    recovery_pin = (data.get('recovery_pin') or '').strip() or None

    if not username or not password:
        return error_response("VALIDATION_ERROR", "Username and password are required.", 400)

    import re
    if not re.match(r'^[a-zA-Z0-9_]{3,50}$', username):
        return error_response("VALIDATION_ERROR", "Username must be 3-50 characters containing letters, numbers, or underscores.", 400)

    is_valid, msg = is_strong_password(password)
    if not is_valid:
        return error_response("WEAK_PASSWORD", msg, 400)

    try:
        if User.query.filter_by(username=username).first():
            return error_response("CONFLICT", "Username is already taken.", 409)

        if email and User.query.filter_by(email=email).first():
            return error_response("CONFLICT", "An account with that email already exists.", 409)
    except Exception as exc:
        log.warning(f"Database unavailable during register check: {exc}")
        return error_response("DATABASE_UNAVAILABLE", "The cloud database is currently unreachable or waking up. Please verify the database status and try again.", 503)

    user = User(
        username=username,
        email=email,
        password=generate_password_hash(password),
        full_name=full_name,
        language=language,
        recovery_pin=generate_password_hash(recovery_pin) if recovery_pin else None,
        monthly_income=float(data.get('monthly_income', 50000.0)),
        monthly_budget=float(data.get('monthly_budget', 0.0)),
        created_at=ist_now(),
        last_seen=ist_now(),
    )
    db.session.add(user)
    try:
        safe_commit(db.session)
    except Exception as exc:
        db.session.rollback()
        log.error(f"Registration DB error: {exc}")
        return error_response("DB_ERROR", "Failed to register user account.", 500)

    login_user(user, remember=True)
    token = generate_auth_token(user.id)

    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'language': user.language,
        'monthly_budget': user.monthly_budget,
        'monthly_income': user.monthly_income,
    }
    return success_response({'user': user_data, 'token': token}, "Registration successful", 201)


@api_v1.route('/auth/login', methods=['POST'])
def api_login():
    from app import db, User, _rate_store

    # Simple in-process rate limiting on login
    import time
    ip = request.remote_addr or 'unknown'
    now = time.time()
    calls = [t for t in _rate_store[ip] if now - t < 60]
    if len(calls) >= 15:
        return error_response("RATE_LIMITED", "Too many login attempts. Please wait a minute.", 429)
    calls.append(now)
    _rate_store[ip] = calls

    data = request.get_json(silent=True) or request.form
    login_id = (data.get('username') or '').strip().lower()
    password = data.get('password') or ''
    remember = str(data.get('remember', 'true')).lower() in ('true', '1')

    if not login_id or not password:
        return error_response("VALIDATION_ERROR", "Username/email and password are required.", 400)

    try:
        user = User.query.filter(
            (User.username == login_id) | (User.email == login_id)
        ).first()
    except Exception as exc:
        log.warning(f"Database error during login: {exc}")
        return error_response(
            "DATABASE_UNAVAILABLE",
            "The cloud database is currently unreachable or waking up. If using Aiven Cloud MySQL, please verify 'walletiq-db' is powered on at console.aiven.io.",
            503
        )

    if not user or not check_password_hash(user.password, password):
        return error_response("UNAUTHORIZED", "Invalid username or password.", 401)

    user.touch()
    try:
        safe_commit(db.session)
    except Exception:
        db.session.rollback()

    login_user(user, remember=remember)
    token = generate_auth_token(user.id)

    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'language': user.language,
        'monthly_budget': user.monthly_budget,
        'monthly_income': user.monthly_income,
    }
    return success_response({'user': user_data, 'token': token}, "Login successful", 200)


@api_v1.route('/auth/logout', methods=['POST', 'GET'])
def api_logout():
    try:
        logout_user()
    except Exception:
        pass
    return success_response(None, "Logged out successfully", 200)


@api_v1.route('/auth/me', methods=['GET'])
@api_login_required
def api_me():
    user = _get_user()
    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'language': user.language,
        'monthly_budget': user.monthly_budget,
        'monthly_income': user.monthly_income,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'last_seen': user.last_seen.isoformat() if user.last_seen else None,
    }
    return success_response({'user': user_data}, "Current user profile fetched", 200)


@api_v1.route('/auth/update-profile', methods=['POST'])
@api_login_required
def api_update_profile():
    from app import db, is_strong_password
    user = _get_user()
    data = request.get_json(silent=True) or request.form

    if 'full_name' in data:
        user.full_name = str(data['full_name']).strip()
    if 'language' in data and data['language'] in ('en', 'ta'):
        user.language = data['language']
    if 'monthly_budget' in data:
        try:
            user.monthly_budget = max(0.0, float(data['monthly_budget']))
        except ValueError:
            pass
    if 'monthly_income' in data:
        try:
            user.monthly_income = max(0.0, float(data['monthly_income']))
        except ValueError:
            pass
    if 'recovery_pin' in data and data['recovery_pin']:
        user.recovery_pin = generate_password_hash(str(data['recovery_pin']).strip())

    # Optional password update
    old_pwd = data.get('old_password')
    new_pwd = data.get('new_password')
    if old_pwd and new_pwd:
        if not check_password_hash(user.password, old_pwd):
            return error_response("VALIDATION_ERROR", "Current password is incorrect.", 400)
        is_valid, msg = is_strong_password(new_pwd)
        if not is_valid:
            return error_response("WEAK_PASSWORD", msg, 400)
        user.password = generate_password_hash(new_pwd)

    try:
        safe_commit(db.session)
    except Exception as exc:
        db.session.rollback()
        return error_response("DB_ERROR", f"Failed to update profile: {exc}", 500)

    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'language': user.language,
        'monthly_budget': user.monthly_budget,
        'monthly_income': user.monthly_income,
    }
    return success_response({'user': user_data}, "Profile updated successfully", 200)


@api_v1.route('/auth/forgot-password', methods=['POST'])
def api_forgot_password():
    from app import db, User, is_strong_password

    data = request.get_json(silent=True) or request.form
    username = (data.get('username') or '').strip().lower()
    pin = (data.get('recovery_pin') or '').strip()
    new_password = data.get('new_password') or ''

    if not username or not pin or not new_password:
        return error_response("VALIDATION_ERROR", "Username, recovery PIN, and new password are required.", 400)

    user = User.query.filter_by(username=username).first()
    if not user or not user.recovery_pin or not check_password_hash(user.recovery_pin, pin):
        return error_response("UNAUTHORIZED", "Invalid username or recovery PIN.", 401)

    is_valid, msg = is_strong_password(new_password)
    if not is_valid:
        return error_response("WEAK_PASSWORD", msg, 400)

    user.password = generate_password_hash(new_password)
    try:
        safe_commit(db.session)
    except Exception as exc:
        db.session.rollback()
        return error_response("DB_ERROR", f"Failed to reset password: {exc}", 500)

    return success_response(None, "Password has been successfully reset. Please log in.", 200)


# ══════════════════════════════════════════════════════════════════════════════
# 2. DASHBOARD & ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

@api_v1.route('/dashboard/summary', methods=['GET'])
@api_login_required
def api_dashboard_summary():
    from app import get_user_stats, Notification, ist_now
    from services.financial_health import compute_financial_health

    user = _get_user()
    stats, records = get_user_stats(user.id, return_records=True)

    # Recent transactions sliced directly in memory from user expenses
    sorted_expenses = sorted(records['expenses'], key=lambda x: x.created_at, reverse=True)
    recent_data = [{
        'id': e.id,
        'title': e.title,
        'description': e.title,
        'amount': e.amount,
        'category': e.category,
        'date': e.created_at.strftime('%Y-%m-%d') if e.created_at else None,
        'created_at': e.created_at.isoformat() if e.created_at else None,
    } for e in sorted_expenses[:10]]

    # Health score computed in-memory reusing already-fetched records
    health = compute_financial_health(
        user.id,
        preloaded_expenses=records['expenses'],
        preloaded_investments=records['investments'],
        preloaded_budgets=records['budgets'],
    )

    # Unread notifications count
    unread_notifs = Notification.query.filter_by(user_id=user.id, is_read=False).count()

    month_spent = float(stats.get('month_total', 0.0))
    monthly_budget = float(user.monthly_budget or 0.0)
    monthly_income = float(user.monthly_income or 0.0)
    budget_progress = round((month_spent / monthly_budget * 100), 1) if monthly_budget > 0 else 0

    return success_response({
        'stats': stats,
        'total_spent': month_spent,
        'monthly_budget': monthly_budget,
        'monthly_income': monthly_income,
        'budget_progress': budget_progress,
        'overdue_bills_count': stats.get('overdue_bills', 0),
        'category_spending': stats.get('cat_totals', {}),
        'recent_expenses': recent_data,
        'transactions': recent_data,
        'health': health,
        'unread_notifications': unread_notifs,
        'user': {
            'username': user.username,
            'full_name': user.full_name,
            'language': user.language,
            'monthly_budget': monthly_budget,
            'monthly_income': monthly_income,
        }
    }, "Dashboard summary fetched", 200)


@api_v1.route('/dashboard/stats', methods=['GET'])
@api_login_required
def api_dashboard_stats():
    from app import get_user_stats
    user = _get_user()
    stats = get_user_stats(user.id)
    stats['total_spent'] = stats.get('month_total', 0)
    stats['monthly_budget'] = float(user.monthly_budget or 0.0)
    stats['monthly_income'] = float(user.monthly_income or 0.0)
    stats['category_spending'] = stats.get('cat_totals', {})
    return success_response(stats, "User stats fetched", 200)


# ══════════════════════════════════════════════════════════════════════════════
# 3. EXPENSES CRUD & CATEGORIZATION
# ══════════════════════════════════════════════════════════════════════════════

@api_v1.route('/expenses', methods=['GET'])
@api_login_required
def api_get_expenses():
    from app import Expense

    user = _get_user()
    category = request.args.get('category')
    search = request.args.get('search', '').strip()
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    page = request.args.get('page', 1, type=int)
    per_page_arg = request.args.get('per_page', type=int)
    limit = min(request.args.get('limit', per_page_arg or 20, type=int), 100)

    query = Expense.query.filter_by(user_id=user.id)
    if category and category != 'All':
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Expense.title.ilike(f'%{search}%'))
    if month and year:
        from sqlalchemy import extract
        query = query.filter(
            extract('month', Expense.created_at) == month,
            extract('year', Expense.created_at) == year
        )

    total = query.count()
    expenses = query.order_by(Expense.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    items = [{
        'id': e.id,
        'title': e.title,
        'description': e.title,
        'amount': e.amount,
        'category': e.category,
        'created_at': e.created_at.isoformat() if e.created_at else None,
        'date': e.created_at.strftime('%Y-%m-%d') if e.created_at else None,
    } for e in expenses]

    total_pages = (total + limit - 1) // limit if limit else 1

    return success_response({
        'items': items,
        'expenses': items,
        'total': total,
        'page': page,
        'limit': limit,
        'per_page': limit,
        'pages': total_pages,
        'total_pages': total_pages,
    }, "Expenses fetched", 200)


@api_v1.route('/expenses', methods=['POST'])
@api_login_required
def api_create_expense():
    from app import db, Expense, predict_category, ist_now

    user = _get_user()
    data = request.get_json(silent=True) or request.form

    title = (data.get('title') or data.get('description') or data.get('desc') or '').strip()
    category = (data.get('category') or '').strip()
    if not title:
        title = f"{category or 'General'} Expense"

    try:
        amount = float(data.get('amount', 0))
    except (TypeError, ValueError):
        return error_response("VALIDATION_ERROR", "Invalid amount.", 400)

    if amount <= 0:
        return error_response("VALIDATION_ERROR", "A positive amount is required.", 400)

    if not category or category.lower() in ('auto', 'auto-detect', ''):
        category = predict_category(title)

    exp_date = ist_now()
    date_str = data.get('date')
    if date_str:
        try:
            parsed_d = datetime.strptime(date_str, '%Y-%m-%d')
            exp_date = exp_date.replace(year=parsed_d.year, month=parsed_d.month, day=parsed_d.day)
        except ValueError:
            pass

    expense = Expense(
        user_id=user.id,
        title=title,
        amount=round(amount, 2),
        category=category,
        created_at=exp_date
    )
    db.session.add(expense)
    try:
        safe_commit(db.session)
    except Exception as exc:
        db.session.rollback()
        return error_response("DB_ERROR", f"Failed to save expense: {exc}", 500)

    return success_response({
        'id': expense.id,
        'title': expense.title,
        'amount': expense.amount,
        'category': expense.category,
        'date': expense.created_at.strftime('%Y-%m-%d'),
        'created_at': expense.created_at.isoformat()
    }, "Expense added successfully", 201)


@api_v1.route('/expenses/<int:eid>', methods=['PUT'])
@api_login_required
def api_update_expense(eid):
    from app import db, Expense

    user = _get_user()
    expense = _owned(Expense, eid, user.id)
    if not expense:
        return error_response("NOT_FOUND", "Expense not found.", 404)

    data = request.get_json(silent=True) or request.form or {}
    new_title = data.get('title') or data.get('description') or data.get('desc')
    if new_title:
        expense.title = str(new_title).strip()
    if 'amount' in data:
        try:
            amt = float(data['amount'])
            if amt > 0:
                expense.amount = round(amt, 2)
        except ValueError:
            pass
    if 'category' in data and data['category']:
        expense.category = str(data['category']).strip()
    if 'date' in data and data['date']:
        try:
            parsed_d = datetime.strptime(data['date'], '%Y-%m-%d')
            expense.created_at = expense.created_at.replace(
                year=parsed_d.year, month=parsed_d.month, day=parsed_d.day
            )
        except ValueError:
            pass

    try:
        safe_commit(db.session)
    except Exception as exc:
        db.session.rollback()
        return error_response("DB_ERROR", f"Failed to update expense: {exc}", 500)

    return success_response({
        'id': expense.id,
        'title': expense.title,
        'amount': expense.amount,
        'category': expense.category,
        'date': expense.created_at.strftime('%Y-%m-%d'),
        'created_at': expense.created_at.isoformat()
    }, "Expense updated successfully", 200)


@api_v1.route('/expenses/<int:eid>', methods=['DELETE'])
@api_login_required
def api_delete_expense(eid):
    from app import db, Expense

    user = _get_user()
    expense = _owned(Expense, eid, user.id)
    if not expense:
        return error_response("NOT_FOUND", "Expense not found.", 404)

    db.session.delete(expense)
    try:
        safe_commit(db.session)
    except Exception as exc:
        db.session.rollback()
        return error_response("DB_ERROR", f"Failed to delete expense: {exc}", 500)

    return success_response({'id': eid}, "Expense deleted successfully", 200)


# ══════════════════════════════════════════════════════════════════════════════
# 4. BUDGETS
# ══════════════════════════════════════════════════════════════════════════════

@api_v1.route('/budgets', methods=['GET'])
@api_login_required
def api_get_budgets():
    from app import Budget, Expense, ist_now

    user = _get_user()
    now = ist_now()
    month = request.args.get('month', now.month, type=int)
    year = request.args.get('year', now.year, type=int)

    budgets = Budget.query.filter_by(user_id=user.id, month=month, year=year).all()

    # Calculate actual spend for this month
    expenses = Expense.query.filter_by(user_id=user.id).all()
    this_month_exp = [
        e for e in expenses
        if e.created_at.month == month and e.created_at.year == year
    ]

    items = []
    for b in budgets:
        spent = sum(e.amount for e in this_month_exp if e.category == b.category)
        pct = min(round((spent / b.amount) * 100, 1), 100.0) if b.amount > 0 else 0.0
        items.append({
            'id': b.id,
            'category': b.category,
            'amount': b.amount,
            'spent': round(spent, 2),
            'remaining': round(max(b.amount - spent, 0), 2),
            'percentage': pct,
            'is_over': spent > b.amount,
            'month': b.month,
            'year': b.year,
        })

    return success_response({'budgets': items, 'month': month, 'year': year}, "Budgets fetched", 200)


@api_v1.route('/budgets', methods=['POST'])
@api_login_required
def api_create_budget():
    from app import db, Budget, ist_now

    user = _get_user()
    data = request.get_json(silent=True) or request.form
    category = (data.get('category') or '').strip()

    try:
        amount = float(data.get('amount', 0))
    except (TypeError, ValueError):
        return error_response("VALIDATION_ERROR", "Invalid budget amount.", 400)

    if not category or amount <= 0:
        return error_response("VALIDATION_ERROR", "Category and positive amount required.", 400)

    now = ist_now()
    month = int(data.get('month') or now.month)
    year = int(data.get('year') or now.year)

    # Check if budget already exists for this category this month
    existing = Budget.query.filter_by(
        user_id=user.id, category=category, month=month, year=year
    ).first()

    if existing:
        existing.amount = round(amount, 2)
        budget = existing
    else:
        budget = Budget(
            user_id=user.id,
            category=category,
            amount=round(amount, 2),
            month=month,
            year=year
        )
        db.session.add(budget)

    try:
        safe_commit(db.session)
    except Exception as exc:
        db.session.rollback()
        return error_response("DB_ERROR", f"Failed to save budget: {exc}", 500)

    return success_response({
        'id': budget.id,
        'category': budget.category,
        'amount': budget.amount,
        'month': budget.month,
        'year': budget.year,
    }, "Budget set successfully", 201)


@api_v1.route('/budgets/<int:bid>', methods=['DELETE'])
@api_login_required
def api_delete_budget(bid):
    from app import db, Budget

    user = _get_user()
    budget = _owned(Budget, bid, user.id)
    if not budget:
        return error_response("NOT_FOUND", "Budget not found.", 404)

    db.session.delete(budget)
    try:
        safe_commit(db.session)
    except Exception as exc:
        db.session.rollback()
        return error_response("DB_ERROR", f"Failed to delete budget: {exc}", 500)

    return success_response({'id': bid}, "Budget deleted successfully", 200)


# ══════════════════════════════════════════════════════════════════════════════
# 5. INVESTMENTS
# ══════════════════════════════════════════════════════════════════════════════

@api_v1.route('/investments', methods=['GET'])
@api_login_required
def api_get_investments():
    from app import Investment

    user = _get_user()
    investments = Investment.query.filter_by(user_id=user.id).order_by(
        Investment.created_at.desc()
    ).all()

    total_invested = sum(i.invested for i in investments)
    total_current = sum(i.current_value for i in investments)
    total_gain = total_current - total_invested
    gain_pct = round((total_gain / total_invested * 100), 2) if total_invested > 0 else 0.0

    items = [{
        'id': i.id,
        'name': i.name,
        'type': i.type,
        'category': i.type,
        'amount': i.invested,
        'invested': i.invested,
        'current_value': i.current_value,
        'gain_loss': round(i.current_value - i.invested, 2),
        'gain_loss_pct': round(((i.current_value - i.invested) / i.invested * 100), 2) if i.invested > 0 else 0.0,
        'notes': getattr(i, 'notes', '') or '',
        'created_at': i.created_at.isoformat() if i.created_at else None,
    } for i in investments]

    return success_response({
        'items': items,
        'investments': items,
        'total_invested': round(total_invested, 2),
        'total_current': round(total_current, 2),
        'current_value': round(total_current, 2),
        'total_gain': round(total_gain, 2),
        'total_gain_loss': round(total_gain, 2),
        'gain_pct': gain_pct,
        'gain_loss_pct': gain_pct,
    }, "Investments fetched", 200)


@api_v1.route('/investments', methods=['POST'])
@api_login_required
def api_create_investment():
    from app import db, Investment

    user = _get_user()
    data = request.get_json(silent=True) or request.form
    name = (data.get('name') or '').strip()
    inv_type = (data.get('type') or data.get('category') or 'Mutual Funds').strip()

    try:
        raw_invested = data.get('invested') if data.get('invested') is not None else data.get('amount', 0)
        invested = float(raw_invested or 0)
        raw_current = data.get('current_value') if data.get('current_value') is not None else invested
        current_val = float(raw_current or invested)
    except (TypeError, ValueError):
        return error_response("VALIDATION_ERROR", "Invalid numbers for invested/current value.", 400)

    if not name or invested <= 0:
        return error_response("VALIDATION_ERROR", "Investment name and positive invested amount required.", 400)

    inv = Investment(
        user_id=user.id,
        name=name,
        type=inv_type,
        invested=round(invested, 2),
        current_value=round(current_val, 2),
    )
    db.session.add(inv)
    try:
        safe_commit(db.session)
    except Exception as exc:
        db.session.rollback()
        return error_response("DB_ERROR", f"Failed to save investment: {exc}", 500)

    return success_response({
        'id': inv.id,
        'name': inv.name,
        'type': inv.type,
        'category': inv.type,
        'amount': inv.invested,
        'invested': inv.invested,
        'current_value': inv.current_value,
    }, "Investment added successfully", 201)


@api_v1.route('/investments/<int:iid>', methods=['PUT'])
@api_login_required
def api_update_investment(iid):
    from app import db, Investment

    user = _get_user()
    inv = _owned(Investment, iid, user.id)
    if not inv:
        return error_response("NOT_FOUND", "Investment not found.", 404)

    data = request.get_json(silent=True) or request.form
    if 'current_value' in data:
        try:
            inv.current_value = round(float(data['current_value']), 2)
        except ValueError:
            pass
    raw_invested = data.get('invested') if 'invested' in data else data.get('amount')
    if raw_invested is not None:
        try:
            inv.invested = round(float(raw_invested), 2)
        except ValueError:
            pass
    if 'name' in data and data['name']:
        inv.name = str(data['name']).strip()
    if 'type' in data and data['type']:
        inv.type = str(data['type']).strip()
    elif 'category' in data and data['category']:
        inv.type = str(data['category']).strip()

    try:
        safe_commit(db.session)
    except Exception as exc:
        db.session.rollback()
        return error_response("DB_ERROR", f"Failed to update investment: {exc}", 500)

    return success_response({
        'id': inv.id,
        'name': inv.name,
        'type': inv.type,
        'category': inv.type,
        'amount': inv.invested,
        'invested': inv.invested,
        'current_value': inv.current_value,
    }, "Investment updated successfully", 200)


@api_v1.route('/investments/<int:iid>', methods=['DELETE'])
@api_login_required
def api_delete_investment(iid):
    from app import db, Investment

    user = _get_user()
    inv = _owned(Investment, iid, user.id)
    if not inv:
        return error_response("NOT_FOUND", "Investment not found.", 404)

    db.session.delete(inv)
    try:
        safe_commit(db.session)
    except Exception as exc:
        db.session.rollback()
        return error_response("DB_ERROR", f"Failed to delete investment: {exc}", 500)

    return success_response({'id': iid}, "Investment deleted successfully", 200)


# ══════════════════════════════════════════════════════════════════════════════
# 6. BILLS & COMMAND CENTER
# ══════════════════════════════════════════════════════════════════════════════

@api_v1.route('/bills', methods=['GET'])
@api_login_required
def api_get_bills():
    from services.bill_service import get_user_bills
    user = _get_user()
    bills = get_user_bills(user.id)
    bill_items = [{
        'id': b.id,
        'name': b.name,
        'amount': b.amount,
        'category': b.category,
        'due_day': b.due_day,
        'due_date': b.due_date.isoformat() if b.due_date else None,
        'is_recurring': b.is_recurring,
        'priority': b.priority,
        'auto_pay': b.auto_pay,
        'payment_method': b.payment_method,
        'note': b.note,
        'is_paid': b.is_paid,
        'created_at': b.created_at.isoformat() if b.created_at else None,
    } for b in bills]
    return success_response({'bills': bill_items}, "Bills fetched", 200)


@api_v1.route('/bills', methods=['POST'])
@api_login_required
def api_create_bill():
    from services.bill_service import create_bill
    user = _get_user()
    data = request.get_json(silent=True) or request.form

    name = (data.get('name') or '').strip()
    try:
        amount = float(data.get('amount', 0))
        due_day = int(data.get('due_day', 1))
    except (TypeError, ValueError):
        return error_response("VALIDATION_ERROR", "Invalid amount or due day.", 400)

    if not name or amount <= 0 or not (1 <= due_day <= 31):
        return error_response("VALIDATION_ERROR", "Valid name, positive amount, and due day (1-31) required.", 400)

    res = create_bill(
        user_id=user.id,
        name=name,
        amount=amount,
        category=data.get('category', 'Utilities'),
        due_day=due_day,
        is_recurring=str(data.get('is_recurring', 'false')).lower() in ('true', '1'),
        priority=data.get('priority', 'Medium'),
        payment_method=data.get('payment_method', 'UPI'),
        note=data.get('note', '')
    )
    return success_response(res, "Bill created successfully", 201)


@api_v1.route('/bills/<int:bid>', methods=['PUT'])
@api_login_required
def api_update_bill(bid):
    from services.bill_service import update_bill
    user = _get_user()
    data = request.get_json(silent=True) or request.form

    name = data.get('name', '')
    amount = float(data.get('amount', 0))
    category = data.get('category', '')
    due_day = int(data.get('due_day', 1))
    is_recurring = str(data.get('is_recurring', 'false')).lower() in ('true', '1')
    priority = data.get('priority', 'Medium')
    payment_method = data.get('payment_method', 'UPI')
    note = data.get('note', '')

    res = update_bill(
        user_id=user.id,
        bill_id=bid,
        name=name,
        amount=amount,
        category=category,
        due_day=due_day,
        is_recurring=is_recurring,
        priority=priority,
        payment_method=payment_method,
        note=note
    )
    if not res:
        return error_response("NOT_FOUND", "Bill not found.", 404)
    return success_response(res, "Bill updated successfully", 200)


@api_v1.route('/bills/<int:bid>', methods=['DELETE'])
@api_login_required
def api_delete_bill(bid):
    from services.bill_service import delete_bill
    user = _get_user()
    success = delete_bill(user.id, bid)
    if not success:
        return error_response("NOT_FOUND", "Bill not found.", 404)
    return success_response({'id': bid}, "Bill deleted successfully", 200)


@api_v1.route('/bills/pay', methods=['POST'])
@api_login_required
def api_pay_bill():
    from services.payment_service import pay_bill_service
    user = _get_user()
    data = request.get_json(silent=True) or request.form

    try:
        bill_id = int(data.get('bill_id', 0))
    except (TypeError, ValueError):
        return error_response("VALIDATION_ERROR", "Valid bill_id is required.", 400)

    payment_mode = data.get('payment_mode', 'UPI')
    res = pay_bill_service(user.id, bill_id, payment_mode)
    if not res.get('success'):
        return error_response("PAYMENT_FAILED", res.get('error', 'Payment processing failed'), 400)
    return success_response(res, "Bill payment recorded successfully", 200)


@api_v1.route('/calendar', methods=['GET'])
@api_login_required
def api_calendar():
    from services.calendar_service import get_monthly_calendar_events
    from app import ist_now
    user = _get_user()
    now = ist_now()
    year = request.args.get('year', now.year, type=int)
    month = request.args.get('month', now.month, type=int)

    events = get_monthly_calendar_events(user.id, year, month)
    return success_response({'events': events, 'year': year, 'month': month}, "Calendar events fetched", 200)


@api_v1.route('/reminders', methods=['GET'])
@api_login_required
def api_reminders():
    from app import Bill, ist_now
    user = _get_user()
    now = ist_now()
    bills = Bill.query.filter_by(user_id=user.id, is_paid=False).all()

    reminders = []
    for b in bills:
        days_diff = b.due_day - now.day
        if -5 <= days_diff <= 7:
            reminders.append({
                'id': b.id,
                'name': b.name,
                'amount': b.amount,
                'due_day': b.due_day,
                'days_left': days_diff,
                'is_overdue': days_diff < 0,
            })
    return success_response({'reminders': reminders}, "Reminders fetched", 200)


# ══════════════════════════════════════════════════════════════════════════════
# 7. AI ADVISOR & GEMINI CHAT
# ══════════════════════════════════════════════════════════════════════════════

@api_v1.route('/ai/chat', methods=['POST'])
@api_login_required
def api_ai_chat():
    from chatbot import ask_ai, build_financial_context

    user = _get_user()
    data = request.get_json(silent=True) or request.form or {}
    question = (data.get('question') or data.get('message') or data.get('prompt') or data.get('query') or '').strip()
    lang = data.get('lang', user.language or 'en')
    session_id = data.get('session_id') or f"user_{user.id}"

    if not question:
        return error_response("VALIDATION_ERROR", "Question cannot be empty.", 400)

    user_context = build_financial_context(user.id)
    response_text = ask_ai(
        question=question,
        lang=lang,
        session_id=session_id,
        user_id=user.id,
        user_context=user_context
    )

    return success_response({
        'reply': response_text,
        'response': response_text,
        'message': response_text,
        'session_id': session_id,
        'lang': lang,
    }, "AI response generated", 200)


@api_v1.route('/ai/context', methods=['GET'])
@api_login_required
def api_ai_context():
    from chatbot import build_financial_context
    user = _get_user()
    ctx = build_financial_context(user.id)
    return success_response({'context': ctx}, "User financial context generated", 200)


@api_v1.route('/ai/clear', methods=['POST'])
@api_login_required
def api_ai_clear():
    from chatbot import clear_session
    user = _get_user()
    data = request.get_json(silent=True) or request.form
    session_id = data.get('session_id') or f"user_{user.id}"
    lang = data.get('lang', user.language or 'en')

    clear_session(session_id, lang)
    return success_response(None, "Chat session cleared", 200)


@api_v1.route('/ai/recommendations', methods=['GET'])
@api_login_required
def api_ai_recommendations():
    from services.recommendation_service import generate_user_recommendations
    user = _get_user()
    recos = generate_user_recommendations(user.id)
    return success_response({'recommendations': recos}, "Recommendations fetched", 200)


# ══════════════════════════════════════════════════════════════════════════════
# 8. FINANCIAL HEALTH & PROJECTIONS
# ══════════════════════════════════════════════════════════════════════════════

@api_v1.route('/financial-health', methods=['GET'])
@api_login_required
def api_financial_health():
    from services.financial_health import compute_financial_health
    user = _get_user()
    health = compute_financial_health(user.id)
    return success_response(health, "Financial health calculated", 200)


@api_v1.route('/financial-health/income', methods=['POST'])
@api_login_required
def api_financial_health_income():
    from app import db
    from services.financial_health import compute_financial_health

    user = _get_user()
    data = request.get_json(silent=True) or request.form
    try:
        new_inc = max(0.0, float(data.get('monthly_income', 0)))
        user.monthly_income = new_inc
        safe_commit(db.session)
    except Exception as exc:
        db.session.rollback()
        return error_response("DB_ERROR", f"Failed to update income: {exc}", 500)

    health = compute_financial_health(user.id)
    return success_response({'monthly_income': user.monthly_income, 'health': health}, "Income updated", 200)


@api_v1.route('/predictions/savings', methods=['GET'])
@api_login_required
def api_predictions_savings():
    from services.savings_prediction import compute_savings_prediction

    user = _get_user()
    salary_growth = request.args.get('salary_growth', 8.0, type=float)
    inflation = request.args.get('inflation', 6.0, type=float)
    moderate_return = request.args.get('moderate_return', 10.0, type=float)

    pred = compute_savings_prediction(user.id, salary_growth, inflation, moderate_return)
    return success_response(pred, "Savings prediction computed", 200)


@api_v1.route('/predictions/savings/save', methods=['POST'])
@api_login_required
def api_predictions_savings_save():
    from app import db, PredictionHistory, ist_now

    user = _get_user()
    data = request.get_json(silent=True) or request.form

    try:
        record = PredictionHistory(
            user_id=user.id,
            projected_savings=float(data.get('final_savings', 0)),
            future_net_worth=float(data.get('final_net_worth', 0)),
            horizon_years=int(data.get('horizon_years', 5)),
            salary_growth=float(data.get('salary_growth', 8.0)),
            inflation_rate=float(data.get('inflation_rate', 6.0)),
            created_at=ist_now()
        )
        db.session.add(record)
        safe_commit(db.session)
    except Exception as exc:
        db.session.rollback()
        return error_response("DB_ERROR", f"Failed to save prediction: {exc}", 500)

    return success_response({'id': record.id}, "Prediction record saved", 201)


@api_v1.route('/predictions/loan', methods=['POST'])
@api_login_required
def api_predictions_loan():
    from services.loan_prediction import predict_loan_eligibility

    user = _get_user()
    data = request.get_json(silent=True) or request.form

    try:
        amount = float(data.get('requested_amount', 100000))
        tenure = int(data.get('tenure_months', 24))
        score = int(data.get('credit_score', 750))
        emp_status = int(data.get('employment_status', 1))
        lang = data.get('lang', user.language or 'en')
    except (TypeError, ValueError):
        return error_response("VALIDATION_ERROR", "Invalid input parameters for loan prediction.", 400)

    result = predict_loan_eligibility(user.id, amount, tenure, score, emp_status, lang)
    return success_response(result, "Loan eligibility evaluated", 200)


# ══════════════════════════════════════════════════════════════════════════════
# 9. GOALS & ROADMAP
# ══════════════════════════════════════════════════════════════════════════════

@api_v1.route('/goals', methods=['GET'])
@api_login_required
def api_get_goals():
    from app import Goal
    from services.goal_prediction_service import calculate_goal_progress_analytics

    user = _get_user()
    goals = Goal.query.filter_by(user_id=user.id).order_by(Goal.created_at.desc()).all()

    items = []
    for g in goals:
        analytics = calculate_goal_progress_analytics(g)
        items.append({
            'id': g.id,
            'name': g.name,
            'category': g.category,
            'target_amount': g.target_amount,
            'current_savings': g.current_savings,
            'deadline': g.deadline.strftime('%Y-%m-%d') if g.deadline else None,
            'priority': g.priority,
            'status': g.status,
            'notes': g.notes,
            'monthly_contribution': g.monthly_contribution,
            'analytics': analytics,
        })
    return success_response({'goals': items}, "Goals fetched", 200)


@api_v1.route('/goals', methods=['POST'])
@api_login_required
def api_create_goal():
    from services.goal_service import create_user_goal

    user = _get_user()
    data = request.get_json(silent=True) or request.form

    name = (data.get('name') or '').strip()
    category = (data.get('category') or 'Custom Goal').strip()
    deadline = data.get('deadline', '')

    try:
        target = float(data.get('target_amount', 0))
        current_sav = float(data.get('current_savings', 0))
    except (TypeError, ValueError):
        return error_response("VALIDATION_ERROR", "Invalid goal amounts.", 400)

    if not name or target <= 0 or not deadline:
        return error_response("VALIDATION_ERROR", "Goal name, positive target, and deadline required.", 400)

    try:
        goal = create_user_goal(
            user_id=user.id,
            name=name,
            category=category,
            target_amount=target,
            current_savings=current_sav,
            deadline_str=deadline,
            priority=data.get('priority', 'Medium'),
            notes=data.get('notes', '')
        )
    except Exception as exc:
        return error_response("ERROR", f"Failed to create goal: {exc}", 500)

    return success_response({'id': goal.id, 'name': goal.name}, "Goal created successfully", 201)


@api_v1.route('/goals/<int:gid>', methods=['PUT'])
@api_v1.route('/goals/<int:gid>/savings', methods=['PUT'])
@api_login_required
def api_update_goal(gid):
    from services.goal_service import update_user_goal_savings
    user = _get_user()
    data = request.get_json(silent=True) or request.form

    if 'current_savings' in data:
        try:
            sav = float(data['current_savings'])
            goal = update_user_goal_savings(gid, user.id, sav)
            if not goal:
                return error_response("NOT_FOUND", "Goal not found.", 404)
            return success_response({'id': goal.id, 'current_savings': goal.current_savings}, "Goal savings updated", 200)
        except ValueError:
            return error_response("VALIDATION_ERROR", "Invalid savings number.", 400)

    return error_response("BAD_REQUEST", "No valid update fields provided.", 400)


@api_v1.route('/goals/<int:gid>', methods=['DELETE'])
@api_login_required
def api_delete_goal(gid):
    from app import db, Goal

    user = _get_user()
    goal = _owned(Goal, gid, user.id)
    if not goal:
        return error_response("NOT_FOUND", "Goal not found.", 404)

    db.session.delete(goal)
    try:
        safe_commit(db.session)
    except Exception as exc:
        db.session.rollback()
        return error_response("DB_ERROR", f"Failed to delete goal: {exc}", 500)

    return success_response({'id': gid}, "Goal deleted successfully", 200)


@api_v1.route('/goals/recommendations', methods=['GET'])
@api_login_required
def api_goal_recommendations():
    from app import Goal
    from services.goal_ai_service import generate_goal_ai_recommendations

    user = _get_user()
    goals = Goal.query.filter_by(user_id=user.id, status='Active').all()

    all_recos = []
    for g in goals:
        recos = generate_goal_ai_recommendations(user.id, g.id)
        if recos:
            all_recos.extend(recos)

    return success_response({'recommendations': all_recos}, "Goal recommendations fetched", 200)


# ══════════════════════════════════════════════════════════════════════════════
# 10. NOTIFICATIONS & COMMAND CENTER
# ══════════════════════════════════════════════════════════════════════════════

@api_v1.route('/notifications', methods=['GET'])
@api_login_required
def api_get_notifications():
    from services.notification_service import get_user_notifications
    user = _get_user()
    notifs = get_user_notifications(user.id)
    return success_response({'notifications': notifs}, "Notifications fetched", 200)


@api_v1.route('/notifications/read/<int:nid>', methods=['POST'])
@api_login_required
def api_notification_read(nid):
    from services.notification_service import mark_notification_read
    user = _get_user()
    ok = mark_notification_read(user.id, nid)
    if not ok:
        return error_response("NOT_FOUND", "Notification not found.", 404)
    return success_response({'id': nid}, "Notification marked as read", 200)


@api_v1.route('/notifications/read-all', methods=['POST'])
@api_login_required
def api_notification_read_all():
    from services.notification_service import mark_all_notifications_read
    user = _get_user()
    mark_all_notifications_read(user.id)
    return success_response(None, "All notifications marked as read", 200)


# ══════════════════════════════════════════════════════════════════════════════
# 11. SPENDING INSIGHTS & BEHAVIORAL PATTERNS
# ══════════════════════════════════════════════════════════════════════════════

@api_v1.route('/insights/spending', methods=['GET'])
@api_v1.route('/spending-insights', methods=['GET'])
@api_login_required
def api_spending_insights():
    from services.insight_service import generate_spending_insights_data
    user = _get_user()
    data = generate_spending_insights_data(user.id)
    return success_response(data, "Spending insights retrieved", 200)


# ══════════════════════════════════════════════════════════════════════════════
# 12. REPORTS STUDIO
# ══════════════════════════════════════════════════════════════════════════════

@api_v1.route('/reports', methods=['GET'])
@api_login_required
def api_get_reports():
    from app import ReportHistory, ist_now
    from services.report_service import get_storage_stats
    import re

    user = _get_user()
    reports = ReportHistory.query.filter_by(user_id=user.id).order_by(
        ReportHistory.id.desc()
    ).all()

    month_map = {m.lower(): i + 1 for i, m in enumerate(
        ['january', 'february', 'march', 'april', 'may', 'june',
         'july', 'august', 'september', 'october', 'november', 'december'])}

    items = []
    for r in reports:
        # Extract month & year from report_name or file_name if possible
        parts = (r.report_name or '').lower().replace('—', ' ').replace('-', ' ').split()
        m = next((month_map[p] for p in parts if p in month_map), None)
        y = next((int(p) for p in parts if re.match(r'^\d{4}$', p)), None)
        if not m or not y:
            fn_parts = (r.file_name or '').replace('.', '_').split('_')
            for idx, p in enumerate(fn_parts):
                if re.match(r'^\d{4}$', p) and idx + 1 < len(fn_parts):
                    try:
                        cand_y = int(p)
                        cand_m = int(fn_parts[idx + 1])
                        if 1 <= cand_m <= 12:
                            y = cand_y
                            m = cand_m
                    except ValueError:
                        pass
        if not m:
            m = (r.generated_date or r.created_at or ist_now()).month
        if not y:
            y = (r.generated_date or r.created_at or ist_now()).year

        is_excel = 'EXCEL' in (r.report_type or '').upper() or (r.file_name or '').endswith('.xlsx')
        fmt = 'excel' if is_excel else 'pdf'

        items.append({
            'id': r.id,
            'report_name': r.report_name,
            'title': r.report_name,
            'name': r.report_name,
            'report_type': r.report_type,
            'format': fmt,
            'file_name': r.file_name,
            'file_size': r.file_size or 0,
            'month': m,
            'year': y,
            'version': r.version or 1,
            'is_favorite': r.is_favorite or False,
            'share_key': r.share_key,
            'generated_date': r.generated_date.isoformat() if r.generated_date else None,
            'created_at': r.created_at.isoformat() if r.created_at else (r.generated_date.isoformat() if r.generated_date else None),
            'download_count': r.download_count or 0,
        })

    stats = get_storage_stats(user.id)
    return success_response({'reports': items, 'stats': stats}, "Reports fetched", 200)


@api_v1.route('/reports/generate', methods=['POST'])
@api_login_required
def api_generate_report():
    from services.report_service import generate_pdf_report, generate_excel_report, make_report_name
    from app import db, ReportHistory, ist_now

    user = _get_user()
    data = request.get_json(silent=True) or request.form

    raw_format = str(data.get('format') or data.get('report_type') or 'PDF').strip().upper()
    is_excel = 'EXCEL' in raw_format or 'XLSX' in raw_format
    report_type_clean = 'EXCEL' if is_excel else 'PDF'
    
    now = ist_now()
    try:
        year = int(data.get('year') or now.year)
        month = int(data.get('month') or now.month)
    except (TypeError, ValueError):
        year, month = now.year, now.month

    try:
        if is_excel:
            filepath = generate_excel_report(user.id, year, month)
        else:
            filepath = generate_pdf_report(user.id, year, month)
    except Exception as exc:
        log.error(f"Report generation error: {exc}")
        return error_response("REPORT_ERROR", f"Report generation failed: {exc}", 500)

    if not filepath or not os.path.exists(filepath):
        return error_response("REPORT_ERROR", "Failed to compile report document on disk.", 500)

    file_size = os.path.getsize(filepath)
    file_name = os.path.basename(filepath)
    base_name = make_report_name("Monthly", year, month)

    prev_count = ReportHistory.query.filter_by(
        user_id=user.id,
        file_name=file_name
    ).count()
    version = prev_count + 1

    report_name = base_name if version == 1 else f"{base_name} (v{version})"

    report_record = ReportHistory(
        user_id=user.id,
        report_name=report_name,
        report_type=report_type_clean,
        file_name=file_name,
        file_path=filepath,
        file_size=file_size,
        version=version,
        generated_date=ist_now(),
        created_at=ist_now(),
    )
    db.session.add(report_record)
    try:
        safe_commit(db.session)
    except Exception as exc:
        db.session.rollback()
        return error_response("DB_ERROR", f"Failed to persist report record: {exc}", 500)

    return success_response({
        'id': report_record.id,
        'report_name': report_record.report_name,
        'title': report_record.report_name,
        'name': report_record.report_name,
        'file_name': report_record.file_name,
        'file_size': report_record.file_size,
        'report_type': report_record.report_type,
        'format': 'excel' if is_excel else 'pdf',
        'month': month,
        'year': year,
        'created_at': report_record.created_at.isoformat() if report_record.created_at else None,
    }, "Report generated successfully", 201)


@api_v1.route('/reports/<int:rid>/download', methods=['GET'])
@api_v1.route('/reports/download/<int:rid>', methods=['GET'])
@api_login_required
def api_download_report(rid):
    from app import db, ReportHistory, ist_now
    from services.report_service import generate_pdf_report, generate_excel_report
    import re

    user = _get_user()
    report = _owned(ReportHistory, rid, user.id)
    if not report:
        return error_response("NOT_FOUND", "Report not found.", 404)

    # If physical file missing on ephemeral container filesystem, regenerate on the fly
    if not report.file_path or not os.path.exists(report.file_path):
        month_map = {m.lower(): i + 1 for i, m in enumerate(
            ['january', 'february', 'march', 'april', 'may', 'june',
             'july', 'august', 'september', 'october', 'november', 'december'])}
        parts = (report.report_name or '').lower().replace('—', ' ').replace('-', ' ').split()
        m = next((month_map[p] for p in parts if p in month_map), None)
        y = next((int(p) for p in parts if re.match(r'^\d{4}$', p)), None)
        if not m or not y:
            fn_parts = (report.file_name or '').replace('.', '_').split('_')
            for idx, p in enumerate(fn_parts):
                if re.match(r'^\d{4}$', p) and idx + 1 < len(fn_parts):
                    try:
                        cand_y = int(p)
                        cand_m = int(fn_parts[idx + 1])
                        if 1 <= cand_m <= 12:
                            y = cand_y
                            m = cand_m
                    except ValueError:
                        pass
        if not m:
            m = (report.generated_date or report.created_at or ist_now()).month
        if not y:
            y = (report.generated_date or report.created_at or ist_now()).year

        is_excel = 'EXCEL' in (report.report_type or '').upper() or (report.file_name or '').endswith('.xlsx')
        try:
            if is_excel:
                filepath = generate_excel_report(user.id, y, m)
            else:
                filepath = generate_pdf_report(user.id, y, m)
            if filepath and os.path.exists(filepath):
                report.file_path = filepath
                report.file_size = os.path.getsize(filepath)
                safe_commit(db.session)
        except Exception as exc:
            log.error(f"Failed to regenerate report {rid} on the fly: {exc}")

    if not report.file_path or not os.path.exists(report.file_path):
        return error_response("NOT_FOUND", "Report file could not be loaded from storage.", 404)

    report.download_count = (report.download_count or 0) + 1
    report.last_downloaded = ist_now()
    try:
        safe_commit(db.session)
    except Exception:
        db.session.rollback()

    return send_file(report.file_path, as_attachment=True, download_name=report.file_name)


@api_v1.route('/reports/<int:rid>', methods=['DELETE'])
@api_login_required
def api_delete_report(rid):
    from app import db, ReportHistory

    user = _get_user()
    report = _owned(ReportHistory, rid, user.id)
    if not report:
        return error_response("NOT_FOUND", "Report not found.", 404)

    # Remove physical file if present
    if report.file_path and os.path.exists(report.file_path):
        try:
            os.remove(report.file_path)
        except OSError:
            pass

    db.session.delete(report)
    try:
        safe_commit(db.session)
    except Exception as exc:
        db.session.rollback()
        return error_response("DB_ERROR", f"Failed to delete report: {exc}", 500)

    return success_response({'id': rid}, "Report deleted successfully", 200)


@api_v1.route('/reports/share', methods=['POST'])
@api_v1.route('/reports/share/<int:rid>', methods=['POST'])
@api_login_required
def api_share_report(rid=None):
    import secrets
    from app import db, ReportHistory

    user = _get_user()
    if rid is None:
        data = request.get_json(silent=True) or request.form
        rid = int(data.get('report_id', 0))

    report = _owned(ReportHistory, rid, user.id)
    if not report:
        return error_response("NOT_FOUND", "Report not found.", 404)

    if not report.share_key:
        report.share_key = secrets.token_urlsafe(16)
        try:
            safe_commit(db.session)
        except Exception as exc:
            db.session.rollback()
            return error_response("DB_ERROR", f"Failed to generate share link: {exc}", 500)

    return success_response({
        'share_key': report.share_key,
        'share_url': f"/shared/report/{report.share_key}"
    }, "Share link generated", 200)


@api_v1.route('/reports/shared/<string:key>', methods=['GET'])
@api_v1.route('/shared/report/<string:key>', methods=['GET'])
def api_get_shared_report(key):
    from app import ReportHistory, ist_now
    from services.report_service import get_report_data
    import re

    report = ReportHistory.query.filter_by(share_key=key).first()
    if not report:
        return error_response("NOT_FOUND", "Shared report not found or link has expired.", 404)

    month_map = {m.lower(): i + 1 for i, m in enumerate(
        ['january', 'february', 'march', 'april', 'may', 'june',
         'july', 'august', 'september', 'october', 'november', 'december'])}
    parts = (report.report_name or '').lower().split()
    m = next((month_map[p] for p in parts if p in month_map), ist_now().month)
    y = next((int(p) for p in parts if re.match(r'^\d{4}$', p)), ist_now().year)

    data = get_report_data(report.user_id, y, m)
    return success_response({
        'report': {
            'id': report.id,
            'title': report.report_name,
            'format': report.report_type,
            'month': m,
            'year': y,
            'created_at': report.created_at.isoformat() if report.created_at else None,
            'total_income': data.get('total_income', 0),
            'total_expenses': data.get('total_expenses', 0),
            'net_savings': data.get('net_savings', 0),
            'summary': data.get('summary', {}),
        },
        'data': data
    }, "Shared report loaded", 200)


@api_v1.route('/reports/compare', methods=['POST'])
@api_login_required
def api_compare_reports():
    from services.report_service import generate_ai_comparison
    user = _get_user()
    data = request.get_json(silent=True) or request.form

    try:
        report_a = int(data.get('report_a') or data.get('report_id_1') or data.get('report_a_id') or 0)
        report_b = int(data.get('report_b') or data.get('report_id_2') or data.get('report_b_id') or 0)
    except (TypeError, ValueError):
        return error_response("VALIDATION_ERROR", "Two valid report IDs required.", 400)

    if not report_a or not report_b:
        return error_response("VALIDATION_ERROR", "Two valid report IDs required.", 400)

    comp = generate_ai_comparison(user.id, report_a, report_b)
    return success_response(comp, "Report comparison generated", 200)


# ══════════════════════════════════════════════════════════════════════════════
# 13. RECEIPT OCR VIA GEMINI MULTIMODAL VISION
# ══════════════════════════════════════════════════════════════════════════════

@api_v1.route('/ocr/receipt', methods=['POST'])
@api_login_required
def api_ocr_receipt():
    """
    Accepts uploaded receipt image or PDF and uses Google Gemini vision
    to parse and extract merchant, total, date, category, and line items.
    """
    user = _get_user()
    file = request.files.get('receipt') or request.files.get('file')

    if not file or not file.filename:
        return error_response("VALIDATION_ERROR", "No receipt file uploaded.", 400)

    allowed_extensions = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return error_response("INVALID_FILE_TYPE", f"File type .{ext} not supported. Use PNG, JPG, WEBP, or PDF.", 400)

    # Read bytes and determine mime
    file_bytes = file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10 MB limit
        return error_response("FILE_TOO_LARGE", "File size exceeds 10MB limit.", 413)

    mime_map = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'webp': 'image/webp',
        'pdf': 'application/pdf',
    }
    mime_type = mime_map.get(ext, 'image/jpeg')

    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    extracted_data = None

    if api_key and api_key not in ("CHANGE_ME", "your_gemini_api_key_here"):
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            prompt = """You are an expert financial receipt OCR parser for an Indian personal finance platform.
Analyze this receipt image or document and extract the transaction details into clean JSON format.

Return ONLY a valid JSON object with these EXACT keys:
{
  "merchant": "Name of store, restaurant, or business",
  "date": "YYYY-MM-DD (format date if found, otherwise use today's date)",
  "total_amount": 0.0,
  "currency": "INR",
  "category": "Food|Travel|Entertainment|Bills|Shopping|Health|Education|Savings|General",
  "confidence_score": 0.95,
  "items": [
    {"name": "Item description", "amount": 0.0}
  ],
  "notes": "Short summary or invoice number"
}

Do NOT wrap the response in markdown code fences or backticks. Return ONLY the raw JSON string."""

            contents = [
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                prompt
            ]

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents,
            )

            raw_text = response.text.strip()
            if raw_text.startswith('```json'):
                raw_text = raw_text[7:]
            if raw_text.startswith('```'):
                raw_text = raw_text[3:]
            if raw_text.endswith('```'):
                raw_text = raw_text[:-3]

            extracted_data = json.loads(raw_text.strip())

        except Exception as exc:
            log.warning(f"Gemini OCR extraction failed: {exc}")

    # Fallback if Gemini failed or was unavailable
    if not extracted_data:
        today_str = date.today().strftime('%Y-%m-%d')
        extracted_data = {
            "merchant": file.filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title(),
            "date": today_str,
            "total_amount": 0.0,
            "currency": "INR",
            "category": "Shopping",
            "confidence_score": 0.50,
            "items": [],
            "notes": f"Scanned file: {file.filename} (Manual verification recommended)"
        }

    return success_response(extracted_data, "Receipt parsed successfully", 200)


# ══════════════════════════════════════════════════════════════════════════════
# 13. DATA EXPORTS (CSV / PDF)
# ══════════════════════════════════════════════════════════════════════════════

@api_v1.route('/export/csv', methods=['GET'])
@api_login_required
def api_export_csv():
    from app import Expense

    user = _get_user()
    expenses = Expense.query.filter_by(user_id=user.id).order_by(
        Expense.created_at.desc()
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Title', 'Amount (INR)', 'Category', 'Date', 'Created At'])

    for e in expenses:
        writer.writerow([
            e.id,
            e.title,
            e.amount,
            e.category,
            e.created_at.strftime('%Y-%m-%d') if e.created_at else '',
            e.created_at.isoformat() if e.created_at else '',
        ])

    mem = io.BytesIO(output.getvalue().encode('utf-8-sig'))
    filename = f"WalletIQ_Expenses_{date.today().strftime('%Y%m%d')}.csv"
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name=filename)
