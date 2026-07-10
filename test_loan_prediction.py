import unittest
from app import app, db, User, Investment, LoanPredictionHistory
from services.loan_prediction import predict_loan_eligibility, train_loan_model

class TestLoanPrediction(unittest.TestCase):
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
            monthly_income=80000.0,
            monthly_budget=30000.0
        )
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.close()
        # Do NOT call db.drop_all() to avoid dropping the MySQL dev database table bindings
        self.app_context.pop()

    def test_default_prediction_works(self):
        # Predict loan eligibility
        res = predict_loan_eligibility(
            user_id=self.user.id,
            requested_amount=300000.0,
            tenure_months=36,
            credit_score=750,
            employment_status=1,
            lang='en'
        )
        
        self.assertIn('approval_probability', res)
        self.assertIn('eligible_amount', res)
        self.assertIn('risk_level', res)
        self.assertIn('is_eligible', res)
        
        # A credit score of 750 with good income and reasonable loan request should have higher approval probability
        self.assertGreater(res['approval_probability'], 50.0)
        self.assertEqual(res['risk_level'], 'Low')

    def test_poor_credit_and_unemployment(self):
        # Unemployed applicant with poor credit
        res = predict_loan_eligibility(
            user_id=self.user.id,
            requested_amount=1000000.0,
            tenure_months=24,
            credit_score=500,
            employment_status=0,
            lang='en'
        )
        
        # Unemployed poor credit score should have very low approval probability
        self.assertFalse(res['is_eligible'])
        self.assertLess(res['approval_probability'], 40.0)
        self.assertEqual(res['risk_level'], 'High')
        
        # Should have suggestions to improve
        self.assertTrue(len(res['suggestions']) > 0)

if __name__ == '__main__':
    unittest.main()
