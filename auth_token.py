"""
auth_token.py — Cryptographic Session Token Manager & Middleware
Enables cross-domain Bearer token authentication between Vercel and Railway,
in addition to standard HTTP-only session cookies.
"""

import os
import logging
from functools import wraps
from flask import request, current_app, g
from flask_login import current_user, login_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from api_response import error_response

log = logging.getLogger('walletiq.auth')

_TOKEN_SALT = 'walletiq-rest-auth-v1'
# 7-day token expiration by default (matching PERMANENT_SESSION_LIFETIME)
TOKEN_MAX_AGE = 86400 * 7


def _get_serializer():
    secret = current_app.secret_key or os.environ.get('SECRET_KEY', 'walletiq-fallback-token-key')
    return URLSafeTimedSerializer(secret, salt=_TOKEN_SALT)


def generate_auth_token(user_id: int) -> str:
    """Generate a tamper-proof cryptographically signed token for the user."""
    s = _get_serializer()
    return s.dumps({'user_id': user_id})


def verify_auth_token(token: str, max_age: int = TOKEN_MAX_AGE) -> int | None:
    """Verify signed token and return the user_id, or None if expired/invalid."""
    if not token:
        return None
    s = _get_serializer()
    try:
        data = s.loads(token, max_age=max_age)
        return data.get('user_id')
    except SignatureExpired:
        log.warning("Authentication token has expired")
        return None
    except BadSignature:
        log.warning("Authentication token signature is invalid")
        return None
    except Exception as exc:
        log.warning(f"Failed to verify auth token: {exc}")
        return None


def get_token_from_request() -> str | None:
    """Extract auth token from Authorization header or X-Session-Token."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:].strip()
    x_token = request.headers.get('X-Session-Token')
    if x_token:
        return x_token.strip()
    return None


def get_authenticated_user():
    """Retrieve the currently authenticated user from token or session."""
    # 1. If explicit Bearer token or X-Session-Token header is provided, it takes precedence
    token = get_token_from_request()
    if token:
        # Check cache for same token within this request context
        if getattr(g, 'api_token', None) == token and getattr(g, 'api_user', None):
            return g.api_user

        user_id = verify_auth_token(token)
        if user_id:
            from app import User, db
            user = db.session.get(User, user_id)
            if user:
                g.api_token = token
                g.api_user = user
                return user
        # If token was provided but invalid/expired, do not fall back to cookie
        return None

    # 2. Fall back to active Flask-Login session cookie (if no token header was provided)
    if current_user and current_user.is_authenticated:
        return current_user

    return None


def api_login_required(f):
    """
    Decorator for API endpoints requiring authentication.
    Supports both HTTP-only session cookies and Authorization: Bearer <token>.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_authenticated_user()
        if not user:
            return error_response(
                code="UNAUTHORIZED",
                message="Authentication required. Please provide a valid session or Bearer token.",
                status_code=401
            )
        return f(*args, **kwargs)
    return decorated_function
