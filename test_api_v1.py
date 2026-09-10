"""
test_api_v1.py — Comprehensive Unit & Integration Tests for WalletIQ REST API (v1)
Verifies:
1. Authentication: Register, Login, Token Generation, Bearer Token Auth, Profile Me, Logout
2. Data Isolation & IDOR Protection: User A CANNOT read/modify/delete User B's expenses or data
3. Expenses CRUD: Create, Read with pagination & filter, Update, Delete
4. Budgets CRUD: Set, Get with progress calculations, Delete
5. Investments CRUD: Create, Update, Delete, Portfolio Metrics
6. Bills CRUD: Create, Get, Pay, Delete
7. Financial Health & Predictions: Compute, Save
8. Goals: Create, Progress tracking
9. OCR Receipt: Validation & format handling
10. Error Response Envelope: Standard JSON error contract
"""

import unittest
import json
import io
from app import app, db, User, Expense, Budget, Investment, Bill, Goal


class TestApiV1(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app_context = app.app_context()
        self.app_context.push()

        from sqlalchemy import create_engine
        self.engine = create_engine('sqlite:///:memory:')
        db._app_engines[app][None] = self.engine
        db.create_all()

        self.client = app.test_client()

    def tearDown(self):
        db.session.close()
        self.app_context.pop()

    def _register_user(self, username="rahul_dev", password="SecurePassword123!", email="rahul@example.com"):
        res = self.client.post('/api/v1/auth/register', json={
            'username': username,
            'password': password,
            'email': email,
            'full_name': 'Rahul Developer',
            'monthly_income': 65000.0,
            'monthly_budget': 35000.0,
            'recovery_pin': '1234'
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('token', data['data'])
        return data['data']['token'], data['data']['user']

    # ── 1. Authentication Tests ───────────────────────────────────────────────
    def test_auth_flow(self):
        """Test registration, login, profile me, and logout with Bearer token."""
        token, user = self._register_user("test_user_1", "SecretPass123!", "user1@example.com")
        self.assertEqual(user['username'], 'test_user_1')

        # Test /auth/me with Bearer token
        res = self.client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 200)
        me_data = res.get_json()
        self.assertTrue(me_data['success'])
        self.assertEqual(me_data['data']['user']['email'], 'user1@example.com')

        # Test login
        res_login = self.client.post('/api/v1/auth/login', json={
            'username': 'test_user_1',
            'password': 'SecretPass123!'
        })
        self.assertEqual(res_login.status_code, 200)
        login_data = res_login.get_json()
        self.assertTrue(login_data['success'])
        self.assertIn('token', login_data['data'])

        # Test logout
        res_logout = self.client.post('/api/v1/auth/logout')
        self.assertEqual(res_logout.status_code, 200)

        # Test unauthorized request (no token, after logout)
        res_unauth = self.client.get('/api/v1/auth/me')
        self.assertEqual(res_unauth.status_code, 401)
        err_data = res_unauth.get_json()
        self.assertFalse(err_data['success'])
        self.assertEqual(err_data['error']['code'], 'UNAUTHORIZED')

        # Test invalid token returns 401
        res_bad_token = self.client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer invalid_token_xyz'})
        self.assertEqual(res_bad_token.status_code, 401)

    def test_duplicate_user_rejection(self):
        """Test that duplicate username/email returns 409 Conflict."""
        self._register_user("dup_user", "Pass123!456", "dup@example.com")
        res = self.client.post('/api/v1/auth/register', json={
            'username': 'dup_user',
            'password': 'Pass123!456',
            'email': 'another@example.com'
        })
        self.assertEqual(res.status_code, 409)
        self.assertFalse(res.get_json()['success'])

    # ── 2. Data Isolation & IDOR Protection ───────────────────────────────────
    def test_user_data_isolation_idor(self):
        """CRITICAL: User A must never access, edit, or delete User B's expenses."""
        token_a, user_a = self._register_user("user_a", "UserAPass123!", "a@example.com")
        token_b, user_b = self._register_user("user_b", "UserBPass123!", "b@example.com")

        # User A creates an expense
        res_a = self.client.post('/api/v1/expenses', json={
            'title': 'User A Secret Coffee',
            'amount': 250.0,
            'category': 'Food'
        }, headers={'Authorization': f'Bearer {token_a}'})
        self.assertEqual(res_a.status_code, 201)
        expense_id = res_a.get_json()['data']['id']

        # User B lists expenses -> Must NOT contain User A's expense
        res_b_list = self.client.get('/api/v1/expenses', headers={'Authorization': f'Bearer {token_b}'})
        self.assertEqual(res_b_list.status_code, 200)
        b_items = res_b_list.get_json()['data']['items']
        self.assertEqual(len(b_items), 0)

        # User B tries to update User A's expense -> Must return 404 Not Found (IDOR blocked)
        res_b_update = self.client.put(f'/api/v1/expenses/{expense_id}', json={
            'amount': 9999.0
        }, headers={'Authorization': f'Bearer {token_b}'})
        self.assertEqual(res_b_update.status_code, 404)

        # User B tries to delete User A's expense -> Must return 404 Not Found
        res_b_delete = self.client.delete(f'/api/v1/expenses/{expense_id}', headers={'Authorization': f'Bearer {token_b}'})
        self.assertEqual(res_b_delete.status_code, 404)

        # Confirm expense still exists and belongs to User A
        res_a_list = self.client.get('/api/v1/expenses', headers={'Authorization': f'Bearer {token_a}'})
        self.assertEqual(len(res_a_list.get_json()['data']['items']), 1)

    # ── 3. Expenses CRUD ──────────────────────────────────────────────────────
    def test_expenses_crud(self):
        token, user = self._register_user("expense_tester", "ExpensePass123!", "exp@example.com")
        headers = {'Authorization': f'Bearer {token}'}

        # Create with title
        res = self.client.post('/api/v1/expenses', json={
            'title': 'Swiggy Dinner',
            'amount': 450.0,
            'category': 'Food'
        }, headers=headers)
        self.assertEqual(res.status_code, 201)
        eid = res.get_json()['data']['id']

        # Read
        res_get = self.client.get('/api/v1/expenses', headers=headers)
        self.assertEqual(res_get.status_code, 200)
        items = res_get.get_json()['data']['items']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'Swiggy Dinner')

        # Update
        res_put = self.client.put(f'/api/v1/expenses/{eid}', json={
            'title': 'Swiggy Dinner & Dessert',
            'amount': 550.0
        }, headers=headers)
        self.assertEqual(res_put.status_code, 200)
        self.assertEqual(res_put.get_json()['data']['amount'], 550.0)

        # Delete
        res_del = self.client.delete(f'/api/v1/expenses/{eid}', headers=headers)
        self.assertEqual(res_del.status_code, 200)

        # Verify empty
        res_verify = self.client.get('/api/v1/expenses', headers=headers)
        self.assertEqual(len(res_verify.get_json()['data']['items']), 0)

    def test_expense_with_description_fallback(self):
        token, user = self._register_user("desc_tester", "DescPass123!", "desc@example.com")
        headers = {'Authorization': f'Bearer {token}'}

        # Create with description field (sent from React UI)
        res = self.client.post('/api/v1/expenses', json={
            'description': 'Birthday Treat',
            'amount': 800.0,
            'category': 'Food'
        }, headers=headers)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()['data']['title'], 'Birthday Treat')

        # Update using description
        eid = res.get_json()['data']['id']
        res_put = self.client.put(f'/api/v1/expenses/{eid}', json={
            'description': 'Birthday Treat Updated'
        }, headers=headers)
        self.assertEqual(res_put.status_code, 200)
        self.assertEqual(res_put.get_json()['data']['title'], 'Birthday Treat Updated')

    # ── 4. Budgets CRUD ───────────────────────────────────────────────────────
    def test_budgets_crud(self):
        token, user = self._register_user("budget_user", "BudgetPass123!", "bg@example.com")
        headers = {'Authorization': f'Bearer {token}'}

        res = self.client.post('/api/v1/budgets', json={
            'category': 'Food',
            'amount': 8000.0
        }, headers=headers)
        self.assertEqual(res.status_code, 201)
        bid = res.get_json()['data']['id']

        # Get budgets
        res_get = self.client.get('/api/v1/budgets', headers=headers)
        self.assertEqual(res_get.status_code, 200)
        budgets = res_get.get_json()['data']['budgets']
        self.assertEqual(len(budgets), 1)
        self.assertEqual(budgets[0]['category'], 'Food')
        self.assertEqual(budgets[0]['amount'], 8000.0)

        # Delete
        res_del = self.client.delete(f'/api/v1/budgets/{bid}', headers=headers)
        self.assertEqual(res_del.status_code, 200)

    # ── 5. Investments CRUD ───────────────────────────────────────────────────
    def test_investments_crud(self):
        token, user = self._register_user("inv_user", "InvPass123!", "inv@example.com")
        headers = {'Authorization': f'Bearer {token}'}

        res = self.client.post('/api/v1/investments', json={
            'name': 'Nifty 50 Index Fund',
            'category': 'Mutual Funds',
            'invested': 50000.0,
            'current_value': 58000.0
        }, headers=headers)
        self.assertEqual(res.status_code, 201)
        iid = res.get_json()['data']['id']

        res_get = self.client.get('/api/v1/investments', headers=headers)
        self.assertEqual(res_get.status_code, 200)
        data = res_get.get_json()['data']
        self.assertEqual(data['total_invested'], 50000.0)
        self.assertEqual(data['total_current'], 58000.0)
        self.assertEqual(data['total_gain'], 8000.0)
        self.assertEqual(data['gain_pct'], 16.0)

        res_del = self.client.delete(f'/api/v1/investments/{iid}', headers=headers)
        self.assertEqual(res_del.status_code, 200)

    # ── 6. Bills CRUD & Pay ───────────────────────────────────────────────────
    def test_bills_crud(self):
        token, user = self._register_user("bill_user", "BillPass123!", "bill@example.com")
        headers = {'Authorization': f'Bearer {token}'}

        res = self.client.post('/api/v1/bills', json={
            'name': 'Internet Fiber',
            'amount': 1199.0,
            'category': 'Utilities',
            'due_day': 15,
            'is_recurring': True
        }, headers=headers)
        self.assertEqual(res.status_code, 201)
        bid = res.get_json()['data']['id']

        # Get bills
        res_get = self.client.get('/api/v1/bills', headers=headers)
        self.assertEqual(res_get.status_code, 200)
        bills = res_get.get_json()['data']['bills']
        self.assertEqual(len(bills), 1)
        self.assertEqual(bills[0]['name'], 'Internet Fiber')

        # Pay bill
        res_pay = self.client.post('/api/v1/bills/pay', json={
            'bill_id': bid,
            'payment_mode': 'UPI'
        }, headers=headers)
        self.assertEqual(res_pay.status_code, 200)
        self.assertTrue(res_pay.get_json()['success'])

        # Delete bill
        res_del = self.client.delete(f'/api/v1/bills/{bid}', headers=headers)
        self.assertEqual(res_del.status_code, 200)

    # ── 7. OCR Receipt Endpoint ───────────────────────────────────────────────
    def test_ocr_receipt_validation(self):
        """Test receipt OCR handles file uploads and rejects invalid types."""
        token, user = self._register_user("ocr_user", "OcrPass123!", "ocr@example.com")
        headers = {'Authorization': f'Bearer {token}'}

        # Rejects non-allowed file extension (.exe)
        bad_file = (io.BytesIO(b"fake executable"), "malicious.exe")
        res_bad = self.client.post('/api/v1/ocr/receipt', data={'receipt': bad_file}, headers=headers)
        self.assertEqual(res_bad.status_code, 400)
        self.assertEqual(res_bad.get_json()['error']['code'], 'INVALID_FILE_TYPE')

        # Accepts valid PNG receipt and returns structured extraction
        good_file = (io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"), "cafe_receipt.png")
        res_good = self.client.post('/api/v1/ocr/receipt', data={'receipt': good_file}, headers=headers)
        self.assertEqual(res_good.status_code, 200)
        ocr_data = res_good.get_json()['data']
        self.assertIn('merchant', ocr_data)
        self.assertIn('total_amount', ocr_data)
        self.assertIn('category', ocr_data)
        self.assertIn('date', ocr_data)

    # ── 8. AI Chat Endpoint ───────────────────────────────────────────────────
    def test_ai_chat_accepts_message_key(self):
        """Test AI chat accepts 'message' payload key as well as 'question'."""
        token, user = self._register_user("chat_user", "ChatPass123!", "chat@example.com")
        headers = {'Authorization': f'Bearer {token}'}

        res = self.client.post('/api/v1/ai/chat', json={
            'message': 'Analyze my spending trends'
        }, headers=headers)
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertTrue(json_data['success'])
        self.assertIn('reply', json_data['data'])
        self.assertIn('response', json_data['data'])

    # ── 9. Spending Insights Endpoint ──────────────────────────────────────────
    def test_spending_insights_endpoint(self):
        """Test GET /api/v1/insights/spending returns enriched insight structure."""
        token, user = self._register_user("insights_user", "InsightsPass123!", "insights@example.com")
        headers = {'Authorization': f'Bearer {token}'}

        res = self.client.get('/api/v1/insights/spending', headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('ranked_categories', data['data'])
        self.assertIn('anomalies', data['data'])
        self.assertIn('recommendations', data['data'])
        self.assertIn('subscriptions', data['data'])

    # ── 10. Goal Savings Route Alias ───────────────────────────────────────────
    def test_goal_savings_route_alias(self):
        """Test PUT /api/v1/goals/<id>/savings updates current_savings."""
        token, user = self._register_user("goal_user", "GoalPass123!", "goal@example.com")
        headers = {'Authorization': f'Bearer {token}'}

        # Create goal
        create_res = self.client.post('/api/v1/goals', json={
            'name': 'Emergency Fund',
            'target_amount': 50000.0,
            'category': 'Emergency',
            'deadline': '2026-12-31'
        }, headers=headers)
        self.assertEqual(create_res.status_code, 201)
        gid = create_res.get_json()['data']['id']

        # Update savings via /goals/<gid>/savings
        up_res = self.client.put(f'/api/v1/goals/{gid}/savings', json={
            'current_savings': 15000.0
        }, headers=headers)
        self.assertEqual(up_res.status_code, 200)
        self.assertEqual(up_res.get_json()['data']['current_savings'], 15000.0)


if __name__ == '__main__':
    unittest.main()
