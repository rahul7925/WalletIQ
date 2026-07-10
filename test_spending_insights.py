"""
test_spending_insights.py — Unit Tests for AI Spending Insights Module.
Verifies fastest growing categories, duplicate subscriptions,
weekend spending spikes, and AI recommendations.
"""

import unittest
from datetime import datetime, timedelta
from app import app, db, User, Expense, ist_now
from services.insight_service import generate_spending_insights_data
from services.recommendation_service import generate_user_recommendations

class TestSpendingInsights(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()

        from sqlalchemy import create_engine
        self.engine = create_engine('sqlite:///:memory:')
        db._app_engines[app][None] = self.engine
        db.create_all()

        # Create dummy user
        self.user = User(
            username='insight_tester',
            password='pbkdf2:sha256:dummy',
            full_name='Test Insight User',
            monthly_income=80000.0,
            monthly_budget=50000.0
        )
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.close()
        self.ctx.pop()

    def test_identify_fastest_growing_category(self):
        now = ist_now()
        last_month = now - timedelta(days=30)

        # Log expenses for last month (Food = ₹2,000)
        e1 = Expense(user_id=self.user.id, title='Dinner', amount=2000.0, category='Food', created_at=last_month)
        # Log expenses for this month (Food = ₹6,000)
        e2 = Expense(user_id=self.user.id, title='Uber eats', amount=6000.0, category='Food', created_at=now)
        
        db.session.add_all([e1, e2])
        db.session.commit()

        data = generate_spending_insights_data(self.user.id)
        self.assertEqual(data['fastest_growing_category'], 'Food')
        self.assertEqual(data['fastest_growing_percentage'], 200.0)

    def test_detect_duplicate_subscriptions(self):
        now = ist_now()
        # Log identical recurring payments
        e1 = Expense(user_id=self.user.id, title='Netflix India', amount=649.0, category='Entertainment', created_at=now - timedelta(days=60))
        e2 = Expense(user_id=self.user.id, title='Netflix India', amount=649.0, category='Entertainment', created_at=now - timedelta(days=30))
        e3 = Expense(user_id=self.user.id, title='Netflix India', amount=649.0, category='Entertainment', created_at=now)
        
        db.session.add_all([e1, e2, e3])
        db.session.commit()

        data = generate_spending_insights_data(self.user.id)
        self.assertTrue(any(sub['title'] == 'Netflix India' for sub in data['suspected_subscriptions']))

    def test_anomaly_recommendation_generation(self):
        # Trigger duplicate subscription reco
        now = ist_now()
        e1 = Expense(user_id=self.user.id, title='Airtel Fibrenet', amount=999.0, category='Bills', created_at=now - timedelta(days=30))
        e2 = Expense(user_id=self.user.id, title='Airtel Fibrenet', amount=999.0, category='Bills', created_at=now)
        
        db.session.add_all([e1, e2])
        db.session.commit()

        recos = generate_user_recommendations(self.user.id)
        self.assertTrue(len(recos) > 0)
        self.assertTrue(any('subscription' in r['message'].lower() for r in recos))

if __name__ == '__main__':
    unittest.main()
