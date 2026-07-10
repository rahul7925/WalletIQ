import unittest
from app import app, db, User, Expense, Budget, Investment, Bill, FinancialHealth, compute_financial_health
from datetime import datetime

class TestFinancialHealth(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Override the Flask-SQLAlchemy extension state engines map to direct binds to SQLite
        from sqlalchemy import create_engine
        self.engine = create_engine('sqlite:///:memory:')
        db._app_engines[app][None] = self.engine
        db.create_all()
        
        # Create a test user
        self.user = User(
            username='tester',
            password='pbkdf2:sha256:16$dummyhash',
            full_name='Test User',
            monthly_income=50000.0,
            monthly_budget=30000.0
        )
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        self.app_context.pop()

    def test_default_health_score(self):
        # Default user with 50,000 income, 0 expenses, 0 investments, 0 budgets
        stats = compute_financial_health(self.user.id)
        # savings_rate: 100% -> score = 100 * 0.3 = 30
        # expense_ratio: 0% -> score = 100 * 0.2 = 20
        # investment_ratio: 0% -> score = 0 * 0.2 = 0
        # budget_score: 75 (no budgets) -> score = 75 * 0.15 = 11.25
        # emergency_fund_score: 0 -> score = 0 * 0.1 = 0
        # debt_score: 100 (0 EMI) -> score = 100 * 0.05 = 5
        # Total: 30 + 20 + 11.25 + 5 = 66.25 -> rounds to 66
        self.assertEqual(stats['score'], 66)
        self.assertEqual(stats['status'], 'Average')

    def test_savings_and_expense_ratio(self):
        # Add an expense of 20,000.
        # Income = 50,000
        # Expenses = 20,000. Savings = 30,000. Savings Rate = 60%.
        # Expense Control: ratio = 40% <= 50% (score = 100)
        # Savings Score: rate = 60% >= 40% (score = 100)
        e = Expense(title='Rent', amount=20000.0, category='Bills', user_id=self.user.id)
        db.session.add(e)
        db.session.commit()
        
        stats = compute_financial_health(self.user.id)
        self.assertEqual(stats['savings_rate'], 60.0)
        self.assertEqual(stats['expense_ratio'], 40.0)
        self.assertEqual(stats['savings_score'], 100.0)
        self.assertEqual(stats['expense_score'], 100.0)

    def test_investment_score(self):
        # Add an investment of 10,000 in the current month
        # Income = 50,000. Ratio = 20% >= 20% (score = 100)
        inv = Investment(name='Index Fund SIP', type='SIP', invested=10000.0, current_value=10000.0, user_id=self.user.id)
        db.session.add(inv)
        db.session.commit()
        
        stats = compute_financial_health(self.user.id)
        self.assertEqual(stats['investment_ratio'], 20.0)
        self.assertEqual(stats['investment_score'], 100.0)

    def test_debt_score(self):
        # Add EMI expense of 25,000.
        # Income = 50,000. Debt Ratio = 50% >= 50% (score = 0)
        e = Expense(title='Home Loan EMI', amount=25000.0, category='EMI', user_id=self.user.id)
        db.session.add(e)
        db.session.commit()
        
        stats = compute_financial_health(self.user.id)
        self.assertEqual(stats['debt_ratio'], 50.0)
        self.assertEqual(stats['debt_score'], 0.0)

if __name__ == '__main__':
    unittest.main()
