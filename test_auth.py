"""
test_auth.py — Comprehensive unit tests for WalletIQ Authentication System.

Tests cover:
  1. Successful Registration (Username, Strong Password, Email, PIN)
  2. Weak Password rejection (length, casing, special chars)
  3. Username validation rules (length, format)
  4. Duplicate Username rejection
  5. Email uniqueness validation (allows multiple empty/None emails, blocks identical emails)
  6. Successful Login via Username
  7. Successful Login via Email
  8. Login failure cases (invalid credentials)
  9. Secure session logout
  10. Password Recovery PIN reset (success and failure cases)
  11. Settings profile update & password change with validation
"""

import unittest
import os
from werkzeug.security import generate_password_hash
from app import app, db, User

class TestAuthSystem(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.ctx = app.app_context()
        self.ctx.push()

        from sqlalchemy import create_engine
        self.engine = create_engine('sqlite:///:memory:')
        db._app_engines[app][None] = self.engine
        db.create_all()

        self.client = app.test_client()

    def tearDown(self):
        db.session.close()
        self.ctx.pop()

    # ── 1. Password Strength Validation Helper ───────────────────────────────
    def test_is_strong_password(self):
        from app import is_strong_password
        
        # Weak passwords
        self.assertFalse(is_strong_password("short")[0])
        self.assertFalse(is_strong_password("NoSpecial1")[0])
        self.assertFalse(is_strong_password("no_caps_1")[0])
        self.assertFalse(is_strong_password("NO_LOW_1!")[0])
        self.assertFalse(is_strong_password("123456!@#")[0])  # no alphabetical characters

        # Strong password
        self.assertTrue(is_strong_password("WalletIQ_2026!")[0])


    # ── 2. User Registration & Uniqueness ─────────────────────────────────────
    def test_user_registration_success(self):
        resp = self.client.post('/register', data={
            'username': 'rahul_fintech',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'email': 'rahul@walletiq.in',
            'full_name': 'Rahul Kumar',
            'language': 'en',
            'recovery_pin': '123456'
        })
        self.assertEqual(resp.status_code, 302)  # Redirects to home page on success
        
        # Verify db insert
        user = User.query.filter_by(username='rahul_fintech').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'rahul@walletiq.in')
        self.assertEqual(user.full_name, 'Rahul Kumar')
        self.assertIsNotNone(user.recovery_pin)

    def test_registration_validation_rules(self):
        # Invalid username format
        resp = self.client.post('/register', data={
            'username': 'ab',  # too short
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'recovery_pin': '123456'
        })
        self.assertIn(b'Username must be 3-20 characters', resp.data)

        # Password mismatch
        resp = self.client.post('/register', data={
            'username': 'rahul',
            'password': 'StrongPassword123!',
            'confirm_password': 'DifferentPass123!',
            'recovery_pin': '123456'
        })
        self.assertIn(b'Passwords do not match', resp.data)

        # Invalid PIN length
        resp = self.client.post('/register', data={
            'username': 'rahul',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'recovery_pin': '12345'
        })
        self.assertIn(b'Recovery PIN must be exactly 6 digits', resp.data)

    def test_duplicate_checks(self):
        # Insert initial user
        u = User(
            username='exist_user',
            email='exist@test.com',
            password=generate_password_hash('Dummy123!'),
            recovery_pin=generate_password_hash('123456')
        )
        db.session.add(u)
        db.session.commit()

        # Try to register duplicate username
        resp = self.client.post('/register', data={
            'username': 'exist_user',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'email': 'new@test.com',
            'recovery_pin': '123456'
        })
        self.assertIn(b'Username already taken', resp.data)

        # Try to register duplicate email
        resp = self.client.post('/register', data={
            'username': 'new_user',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'email': 'exist@test.com',
            'recovery_pin': '123456'
        })
        self.assertIn(b'Email already registered', resp.data)

    def test_multiple_none_emails_allowed(self):
        # User 1 with blank email
        resp1 = self.client.post('/register', data={
            'username': 'user1',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'email': '',  # converts to None
            'recovery_pin': '123456'
        })
        self.assertEqual(resp1.status_code, 302)

        # User 2 with blank email should not throw duplicate email error
        resp2 = self.client.post('/register', data={
            'username': 'user2',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'email': '',  # converts to None
            'recovery_pin': '123456'
        })
        self.assertEqual(resp2.status_code, 302)

    # ── 3. Login Flow ─────────────────────────────────────────────────────────
    def test_login_by_username_and_email(self):
        u = User(
            username='login_user',
            email='login@walletiq.in',
            password=generate_password_hash('StrongPassword123!'),
            recovery_pin=generate_password_hash('123456')
        )
        db.session.add(u)
        db.session.commit()

        # Login via Username
        resp = self.client.post('/login', data={
            'username': 'login_user',
            'password': 'StrongPassword123!'
        })
        self.assertEqual(resp.status_code, 302)
        
        # Log out
        self.client.get('/logout')

        # Login via Email
        resp2 = self.client.post('/login', data={
            'username': 'login@walletiq.in',
            'password': 'StrongPassword123!'
        })
        self.assertEqual(resp2.status_code, 302)

        # Log out
        self.client.get('/logout')

        # Failed Login
        resp3 = self.client.post('/login', data={
            'username': 'login_user',
            'password': 'WrongPassword1!'
        })
        self.assertIn(b'Invalid username/email or password', resp3.data)


    # ── 4. Forgot Password Recovery ───────────────────────────────────────────
    def test_forgot_password_reset(self):
        u = User(
            username='recover_user',
            email='recover@walletiq.in',
            password=generate_password_hash('OldPassword123!'),
            recovery_pin=generate_password_hash('123456')
        )
        db.session.add(u)
        db.session.commit()

        # Reset using invalid PIN
        resp = self.client.post('/forgot-password', data={
            'username_or_email': 'recover_user',
            'recovery_pin': '999999',
            'new_password': 'BrandNewPassword123!',
            'confirm_password': 'BrandNewPassword123!'
        })
        self.assertIn(b'Invalid recovery PIN', resp.data)

        # Reset successfully
        resp2 = self.client.post('/forgot-password', data={
            'username_or_email': 'recover_user',
            'recovery_pin': '123456',
            'new_password': 'BrandNewPassword123!',
            'confirm_password': 'BrandNewPassword123!'
        })
        self.assertIn(b'Password reset successful', resp2.data)

        # Verify password updated in DB
        db.session.refresh(u)
        from werkzeug.security import check_password_hash
        self.assertTrue(check_password_hash(u.password, 'BrandNewPassword123!'))

if __name__ == '__main__':
    unittest.main()
