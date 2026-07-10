import unittest
from datetime import date
from app import app, db, User, Bill, Notification, PaymentHistory, Expense
from services.bill_service import create_bill, get_user_bills, auto_generate_recurring_bills
from services.notification_service import generate_financial_alerts, get_user_notifications
from services.payment_service import pay_bill_service, get_user_payment_history

class TestFinancialCommandCenter(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Override the binding manually to use SQLite
        from sqlalchemy import create_engine
        self.engine = create_engine('sqlite:///:memory:')
        db._app_engines[app][None] = self.engine
        db.create_all()
        
        # Create a test user
        self.user = User(
            username='command_tester',
            password='pbkdf2:sha256:16$dummyhash',
            full_name='Command Tester',
            monthly_income=50000.0,
            monthly_budget=30000.0
        )
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.close()
        # Do NOT call db.drop_all() to avoid dropping the MySQL dev database table bindings
        self.app_context.pop()

    def test_bill_crud_operations(self):
        # Create a recurring bill
        res = create_bill(
            user_id=self.user.id,
            name='Electricity Bill',
            amount=2500.0,
            category='Electricity',
            due_day=15,
            is_recurring=True,
            priority='High',
            payment_method='UPI',
            note='Ref 12345'
        )
        self.assertIn('id', res)
        self.assertEqual(res['name'], 'Electricity Bill')
        
        # Get bills list
        bills = get_user_bills(self.user.id)
        self.assertEqual(len(bills), 1)
        self.assertEqual(bills[0].name, 'Electricity Bill')
        self.assertFalse(bills[0].is_paid)

    def test_alerts_generation(self):
        # 1. Create duplicate subscriptions to trigger notification
        create_bill(self.user.id, 'Netflix Sub', 649.0, 'Netflix', 5)
        create_bill(self.user.id, 'Spotify Premium', 119.0, 'Spotify', 10)
        create_bill(self.user.id, 'Prime Video', 299.0, 'Amazon Prime', 15)
        
        generate_financial_alerts(self.user.id)
        
        notifs = get_user_notifications(self.user.id)
        # Should have a duplicate subscriptions alert
        self.assertTrue(len(notifs) > 0)
        sub_notif = [n for n in notifs if n.category == 'Savings']
        self.assertEqual(len(sub_notif), 1)
        self.assertIn('Multiple Subscriptions', sub_notif[0].title)

    def test_bill_payment_synchronization(self):
        # Create a bill
        bill_data = create_bill(
            user_id=self.user.id,
            name='House Rent',
            amount=15000.0,
            category='House Rent',
            due_day=1
        )
        bill_id = bill_data['id']
        
        # Trigger payment service
        res = pay_bill_service(self.user.id, bill_id, payment_mode='UPI')
        self.assertTrue(res['success'])
        
        # Check that bill is marked paid
        bill = Bill.query.get(bill_id)
        self.assertTrue(bill.is_paid)
        self.assertIsNotNone(bill.paid_date)
        
        # Verify payment history record is logged
        history = get_user_payment_history(self.user.id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].name, 'House Rent')
        
        # Verify that an Expense transaction is automatically created
        expenses = Expense.query.filter_by(user_id=self.user.id).all()
        self.assertEqual(len(expenses), 1)
        self.assertEqual(expenses[0].title, 'Paid: House Rent')
        self.assertEqual(expenses[0].amount, 15000.0)

if __name__ == '__main__':
    unittest.main()
