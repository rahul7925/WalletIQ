import unittest
import json
from app import app, db, User, Investment, PredictionHistory, compute_savings_prediction
from datetime import datetime

class TestSavingsPrediction(unittest.TestCase):
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
            monthly_income=60000.0,
            monthly_budget=40000.0
        )
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        self.app_context.pop()

    def test_default_prediction_runs(self):
        # Predict using standard parameters
        res = compute_savings_prediction(self.user.id, salary_growth=10.0, inflation=5.0, moderate_return=12.0)
        
        # Check that moderate, conservative, aggressive structures are present
        self.assertIn('moderate', res)
        self.assertIn('conservative', res)
        self.assertIn('aggressive', res)
        
        moderate = res['moderate']
        # Check that we have exactly 61 data points (month 0 to month 60)
        self.assertEqual(len(moderate['months']), 61)
        self.assertEqual(len(moderate['net_worth']), 61)
        self.assertEqual(len(moderate['income']), 61)
        self.assertEqual(len(moderate['expenses']), 61)
        self.assertEqual(len(moderate['savings']), 61)
        
        # At month 0, net worth should equal current savings (0 since no investments)
        self.assertEqual(moderate['net_worth'][0], 0.0)
        
        # At month 12 (1 year), moderate net worth should be positive (accumulating monthly savings)
        self.assertGreater(moderate['savings_1y'], 0.0)
        
        # Best-case (Aggressive) 1-year savings should be greater than Moderate due to lower expenses and higher returns
        self.assertGreater(res['aggressive']['savings_1y'], res['moderate']['savings_1y'])
        
        # Moderate 1-year savings should be greater than Conservative due to lower inflation and higher returns
        self.assertGreater(res['moderate']['savings_1y'], res['conservative']['savings_1y'])

    def test_prediction_with_investments(self):
        # Add a starting investment portfolio of 100,000
        inv = Investment(
            name='Mutual Fund A',
            type='Equity',
            invested=100000.0,
            current_value=100000.0,
            user_id=self.user.id
        )
        db.session.add(inv)
        db.session.commit()
        
        res = compute_savings_prediction(self.user.id, salary_growth=8.0, inflation=6.0, moderate_return=10.0)
        
        self.assertEqual(res['current_savings'], 100000.0)
        # Month 0 net worth starts at 100,000
        self.assertEqual(res['moderate']['net_worth'][0], 100000.0)
        # Verify 3 months net worth is higher
        self.assertGreater(res['moderate']['savings_3m'], 100000.0)

if __name__ == '__main__':
    unittest.main()
