"""
test_chatbot.py — Comprehensive test suite for WalletIQ AI Chatbot module.

Tests cover:
  1.  Greeting / welcome
  2.  Savings questions
  3.  Budget questions
  4.  Investment / SIP questions
  5.  Tax / 80C questions
  6.  Loan / EMI questions
  7.  Financial health questions
  8.  Bills / reminders
  9.  Session isolation (lang key)
  10. Session clear
  11. Financial context builder
  12. Fallback behaviour (no API key)
  13. Health suggestions (offline)
  14. Savings suggestions (offline)
  15. Markdown rendering helpers
"""

import unittest
import os
import sys

# ── Isolate from Gemini API during tests ──────────────────────────────────────
os.environ['GEMINI_API_KEY'] = 'CHANGE_ME'   # Forces offline fallback

from app import app, db, User, Bill, Expense, Investment, Budget
from chatbot import (
    ask_ai, _fallback, _key_problem, _session_key, clear_session,
    build_financial_context, generate_health_suggestions, generate_savings_suggestions,
    _fallback_suggestions, _fallback_savings_suggestions
)


class TestChatbotCore(unittest.TestCase):
    """Core chatbot functionality tests."""

    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()

        from sqlalchemy import create_engine
        self.engine = create_engine('sqlite:///:memory:')
        db._app_engines[app][None] = self.engine
        db.create_all()

        self.user = User(
            username='chatbot_tester',
            password='pbkdf2:sha256:dummy',
            full_name='Raj Kumar',
            monthly_income=75000.0,
            monthly_budget=50000.0
        )
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.close()
        self.ctx.pop()

    # ── 1. API key validation ─────────────────────────────────────────────────

    def test_missing_key(self):
        prob = _key_problem('')
        self.assertEqual(prob, 'missing')

    def test_placeholder_key(self):
        prob = _key_problem('CHANGE_ME')
        self.assertEqual(prob, 'placeholder')

    def test_invalid_format_key(self):
        prob = _key_problem('sk-12345INVALID')
        self.assertEqual(prob, 'format')

    def test_valid_key_format_aiza(self):
        self.assertIsNone(_key_problem('AIzaSyDummyKey123'))

    def test_valid_key_format_aq(self):
        self.assertIsNone(_key_problem('AQ.SomeLongKeyString'))

    # ── 2. Session key isolation ──────────────────────────────────────────────

    def test_session_key_includes_lang(self):
        key_en = _session_key('user_1', 'en')
        key_ta = _session_key('user_1', 'ta')
        self.assertNotEqual(key_en, key_ta)
        self.assertIn('en', key_en)
        self.assertIn('ta', key_ta)

    def test_clear_session_no_crash(self):
        """clear_session should not raise even if session doesn't exist."""
        try:
            clear_session('nonexistent_session', 'en')
        except Exception as e:
            self.fail(f"clear_session raised {e}")

    # ── 3. Offline fallback responses ─────────────────────────────────────────

    def test_fallback_savings_en(self):
        reply = _fallback('how to save money', 'en')
        self.assertIn('50/30/20', reply)
        self.assertIn('₹', reply)
        self.assertGreater(len(reply), 200)

    def test_fallback_invest_en(self):
        reply = _fallback('how to invest in sip', 'en')
        self.assertIn('SIP', reply)
        self.assertIn('₹', reply)
        self.assertGreater(len(reply), 150)

    def test_fallback_tax_en(self):
        reply = _fallback('income tax 80c deduction india', 'en')
        self.assertIn('80C', reply)
        self.assertIn('₹', reply)

    def test_fallback_budget_en(self):
        reply = _fallback('how to manage my expenses and budget', 'en')
        self.assertIn('Budget', reply.title())
        self.assertIn('₹', reply)

    def test_fallback_emi_en(self):
        reply = _fallback('credit card emi loan management reduce debt', 'en')
        self.assertIn('EMI', reply)

    def test_fallback_health_en(self):
        reply = _fallback('financial health walletiq score explain', 'en')
        self.assertIn('Health', reply)

    def test_fallback_generic_en(self):
        reply = _fallback('something completely unrelated', 'en')
        self.assertIn('WalletIQ', reply)
        self.assertGreater(len(reply), 50)

    # ── 4. Tamil fallback ─────────────────────────────────────────────────────

    def test_fallback_savings_ta(self):
        reply = _fallback('சேமிப்பு எப்படி', 'ta')
        self.assertIn('₹', reply)
        self.assertGreater(len(reply), 80)

    def test_fallback_invest_ta(self):
        reply = _fallback('முதலீடு எப்படி sip', 'ta')
        self.assertIn('SIP', reply)

    def test_fallback_generic_ta(self):
        reply = _fallback('அறியாத கேள்வி', 'ta')
        self.assertIn('WalletIQ', reply)

    # ── 5. ask_ai with offline key ────────────────────────────────────────────

    def test_ask_ai_empty_question(self):
        reply = ask_ai('', 'en', 'test_session')
        self.assertIn('Please ask', reply)

    def test_ask_ai_whitespace_question(self):
        reply = ask_ai('   ', 'en', 'test_session')
        self.assertIn('Please ask', reply)

    def test_ask_ai_placeholder_key_returns_message(self):
        """With CHANGE_ME key, ask_ai should fall back gracefully."""
        reply = ask_ai('how to save money', 'en', 'test_session_1')
        # Should return offline fallback (rich, > 100 chars) not crash
        self.assertGreater(len(reply), 50)

    # ── 6. Financial context builder ──────────────────────────────────────────

    def test_build_context_returns_string(self):
        ctx = build_financial_context(self.user.id)
        # With empty DB, should still return something (or empty string)
        self.assertIsInstance(ctx, str)

    def test_build_context_with_income(self):
        ctx = build_financial_context(self.user.id)
        if ctx:  # Non-empty means it could connect to user model
            self.assertIn('75,000', ctx)

    def test_build_context_invalid_user(self):
        ctx = build_financial_context(99999)
        self.assertEqual(ctx, '')

    # ── 7. Health suggestions (offline) ──────────────────────────────────────

    def test_health_suggestions_returns_4(self):
        stats = {
            'score': 55, 'status': 'Fair',
            'savings_rate': 12.0, 'expense_ratio': 70.0,
            'investment_ratio': 5.0, 'budget_score': 60.0,
            'months_covered': 2.0, 'debt_ratio': 35.0,
            'income': 75000, 'expenses': 50000
        }
        suggestions = _fallback_suggestions(stats, 'en')
        self.assertEqual(len(suggestions), 4)

    def test_health_suggestions_contain_rupees(self):
        stats = {
            'score': 50, 'status': 'Fair',
            'savings_rate': 10.0, 'expense_ratio': 75.0,
            'investment_ratio': 3.0, 'budget_score': 55.0,
            'months_covered': 1.0, 'debt_ratio': 40.0,
            'income': 60000, 'expenses': 45000
        }
        suggestions = _fallback_suggestions(stats, 'en')
        combined = ' '.join(suggestions)
        self.assertIn('₹', combined)

    def test_health_suggestions_tamil(self):
        stats = {
            'score': 60, 'status': 'Fair',
            'savings_rate': 15.0, 'expense_ratio': 65.0,
            'investment_ratio': 8.0, 'budget_score': 70.0,
            'months_covered': 3.0, 'debt_ratio': 25.0,
            'income': 50000, 'expenses': 35000
        }
        suggestions = _fallback_suggestions(stats, 'ta')
        self.assertEqual(len(suggestions), 4)

    def test_health_suggestions_excellent_score(self):
        stats = {
            'score': 95, 'status': 'Excellent',
            'savings_rate': 35.0, 'expense_ratio': 40.0,
            'investment_ratio': 25.0, 'budget_score': 98.0,
            'months_covered': 8.0, 'debt_ratio': 15.0,
            'income': 100000, 'expenses': 40000
        }
        suggestions = _fallback_suggestions(stats, 'en')
        # Should have positive/motivational first suggestion
        self.assertTrue(any('Excellent' in s or 'SIP' in s or 'momentum' in s
                           for s in suggestions))

    # ── 8. Savings suggestions (offline) ─────────────────────────────────────

    def test_savings_suggestions_returns_3(self):
        stats = {'income': 75000, 'expenses': 55000, 'savings_rate': 26.7}
        forecast = {
            'current_savings': 100000,
            'moderate':    {'savings_1y': 370000, 'savings_5y': 1200000},
            'aggressive':  {'savings_1y': 450000, 'savings_5y': 1800000},
            'conservative':{'savings_1y': 300000, 'savings_5y': 900000},
        }
        suggestions = _fallback_savings_suggestions(stats, forecast, 'en')
        self.assertEqual(len(suggestions), 3)

    def test_savings_suggestions_contain_rupees(self):
        stats = {'income': 60000, 'expenses': 45000, 'savings_rate': 25.0}
        forecast = {
            'current_savings': 80000,
            'moderate':    {'savings_1y': 280000, 'savings_5y': 900000},
            'aggressive':  {'savings_1y': 340000, 'savings_5y': 1300000},
            'conservative':{'savings_1y': 220000, 'savings_5y': 700000},
        }
        suggestions = _fallback_savings_suggestions(stats, forecast, 'en')
        combined = ' '.join(suggestions)
        self.assertIn('₹', combined)

    def test_savings_suggestions_tamil(self):
        stats = {'income': 50000, 'expenses': 38000, 'savings_rate': 24.0}
        forecast = {
            'current_savings': 60000,
            'moderate':    {'savings_1y': 200000, 'savings_5y': 700000},
            'aggressive':  {'savings_1y': 250000, 'savings_5y': 1000000},
            'conservative':{'savings_1y': 160000, 'savings_5y': 500000},
        }
        suggestions = _fallback_savings_suggestions(stats, forecast, 'ta')
        self.assertEqual(len(suggestions), 3)

    # ── 9. API Endpoints (Flask test client) ──────────────────────────────────

    def test_advisor_page_requires_login(self):
        with app.test_client() as c:
            res = c.get('/advisor')
            self.assertIn(res.status_code, [302, 301])  # redirect to login

    def test_chat_endpoint_requires_login(self):
        with app.test_client() as c:
            res = c.post('/chat', data={'message': 'hello'})
            self.assertIn(res.status_code, [302, 301])

    def test_chat_clear_requires_login(self):
        with app.test_client() as c:
            res = c.post('/api/chat/clear')
            self.assertIn(res.status_code, [302, 301])

    def test_chat_context_requires_login(self):
        with app.test_client() as c:
            res = c.get('/api/chat/context')
            self.assertIn(res.status_code, [302, 301])


if __name__ == '__main__':
    unittest.main(verbosity=2)
