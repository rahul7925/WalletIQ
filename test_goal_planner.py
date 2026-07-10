"""
test_goal_planner.py — Unit Tests for AI Goal Planner Module.
Verifies goal creation, progress recalculations, target outputs, and AI roadmap predictions.
"""

import unittest
from datetime import date, timedelta
from app import app, db, User, Goal, GoalProgress, GoalNotifications, ist_now
from services.goal_service import create_user_goal, update_user_goal_savings
from services.goal_prediction_service import calculate_goal_progress_analytics

class TestGoalPlanner(unittest.TestCase):
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
            username='goal_tester',
            password='pbkdf2:sha256:dummy',
            full_name='Test Goal User',
            monthly_income=60000.0,
            monthly_budget=40000.0
        )
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.close()
        self.ctx.pop()

    def test_create_goal_calculates_correct_roadmap(self):
        # Goal target: 120,000 in 12 months, current 20,000
        deadline = (ist_now().date() + timedelta(days=365)).strftime("%Y-%m-%d")
        goal = create_user_goal(
            user_id=self.user.id,
            name='MacBook Pro',
            category='Laptop',
            target_amount=120000.0,
            current_savings=20000.0,
            deadline_str=deadline,
            priority='High'
        )

        self.assertIsNotNone(goal.id)
        self.assertEqual(goal.monthly_contribution, 8333.33)  # (120,000 - 20,000) / 12

        # Verify GoalProgress is generated
        prog = goal.progress.first()
        self.assertIsNotNone(prog)
        self.assertEqual(prog.monthly_target, 8333.33)
        self.assertGreater(prog.weekly_target, 0)
        self.assertGreater(prog.daily_target, 0)

    def test_update_savings_updates_progress_recalculation(self):
        deadline = (ist_now().date() + timedelta(days=365)).strftime("%Y-%m-%d")
        goal = create_user_goal(
            user_id=self.user.id,
            name='Travel Trip',
            category='Travel',
            target_amount=100000.0,
            current_savings=10000.0,
            deadline_str=deadline
        )
        
        # Save ₹20,000 more
        update_user_goal_savings(goal.id, self.user.id, 30000.0)
        
        db.session.refresh(goal)
        self.assertEqual(goal.current_savings, 30000.0)
        self.assertEqual(goal.monthly_contribution, 5833.33)  # (100,000 - 30,000) / 12

    def test_calculate_goal_progress_analytics(self):
        goal = Goal(
            user_id=self.user.id,
            name='Emergency Pool',
            category='Emergency Fund',
            target_amount=50000.0,
            current_savings=10000.0,
            deadline=ist_now().date() + timedelta(days=180),
            monthly_contribution=6666.67
        )
        db.session.add(goal)
        db.session.commit()

        pred = calculate_goal_progress_analytics(goal)
        self.assertIn('success_probability', pred)
        self.assertIn('est_completion_date', pred)

if __name__ == '__main__':
    unittest.main()
