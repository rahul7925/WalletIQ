"""
test_database_resilience.py — Comprehensive Tests for Database Resiliency & Optimization
Verifies:
1. ping_database: Health status, latency timing, dialect detection, and pool stats.
2. db_transaction: Context manager commits on success and cleanly rolls back on exceptions.
3. safe_commit: Resilient commit with transient failure classification.
4. is_transient_db_error: Accurate detection of MySQL disconnects, deadlocks, and network timeouts.
5. Composite Indexes: Verification that compound indexes exist on Expense, Bill, Budget, Investment, Notification.
6. Health Check Telemetry: /health probe returns database_diagnostics with latency_ms.
7. SQLAlchemy 2.0 Compliance: Verifies zero legacy .query.get() invocations remain in the codebase.
"""

import unittest
import os
import glob
from app import app, db, User, Expense, Budget, Investment, Bill, Notification
from db_resilience import (
    ping_database,
    safe_commit,
    db_transaction,
    is_transient_db_error,
    get_connection_pool_stats,
)
from sqlalchemy.exc import OperationalError


class TestDatabaseResilience(unittest.TestCase):
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

    def test_ping_database_healthy(self):
        """ping_database must execute SELECT 1, measure latency, and return dialect."""
        diag = ping_database(self.engine)
        self.assertTrue(diag['healthy'])
        self.assertIsInstance(diag['latency_ms'], (int, float))
        self.assertGreaterEqual(diag['latency_ms'], 0)
        self.assertIn('sqlite', diag['dialect'].lower())
        self.assertIn('pool', diag)

    def test_ping_database_invalid_engine(self):
        """ping_database on a closed/failing engine must return healthy=False without throwing."""
        from sqlalchemy import create_engine
        bad_engine = create_engine('sqlite:////non_existent_path_dir/cannot_create.db')
        diag = ping_database(bad_engine)
        self.assertFalse(diag['healthy'])
        self.assertIn('error', diag)

    def test_db_transaction_commits_on_success(self):
        """db_transaction context manager should commit clean operations."""
        with db_transaction(db.session):
            user = User(
                username="tx_user_ok",
                password="hashpassword",
                email="tx_ok@example.com",
            )
            db.session.add(user)

        found = db.session.query(User).filter_by(username="tx_user_ok").first()
        self.assertIsNotNone(found)
        self.assertEqual(found.email, "tx_ok@example.com")

    def test_db_transaction_rolls_back_on_error(self):
        """db_transaction context manager must rollback on exception without polluting session."""
        try:
            with db_transaction(db.session):
                user = User(
                    username="tx_user_fail",
                    password="hashpassword",
                    email="tx_fail@example.com",
                )
                db.session.add(user)
                # Intentionally trigger an unhandled error inside transaction
                raise ValueError("Simulated unexpected business logic failure")
        except ValueError:
            pass

        found = db.session.query(User).filter_by(username="tx_user_fail").first()
        self.assertIsNone(found)

    def test_safe_commit_success(self):
        """safe_commit must successfully persist active session state."""
        user = User(
            username="commit_user",
            password="hashpassword",
            email="commit@example.com",
        )
        db.session.add(user)
        result = safe_commit(db.session)
        self.assertTrue(result)

        found = db.session.get(User, user.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.username, "commit_user")

    def test_is_transient_db_error_classification(self):
        """Verifies transient error detector recognizes disconnects and deadlocks."""
        # Non-DB exception
        self.assertFalse(is_transient_db_error(ValueError("Invalid argument")))

        # DB exception with transient string
        exc_gone_away = OperationalError("SELECT 1", {}, Exception("MySQL server has gone away"))
        self.assertTrue(is_transient_db_error(exc_gone_away))

        exc_deadlock = OperationalError("UPDATE...", {}, Exception("Deadlock found when trying to get lock"))
        self.assertTrue(is_transient_db_error(exc_deadlock))

        exc_lost = OperationalError("SELECT...", {}, Exception("Lost connection to MySQL server"))
        self.assertTrue(is_transient_db_error(exc_lost))

        # Fatal non-transient error (e.g. syntax error or constraint error)
        exc_syntax = OperationalError("BAD SQL", {}, Exception("Table 'xyz' does not exist"))
        self.assertFalse(is_transient_db_error(exc_syntax))

    def test_composite_indexes_configured_on_models(self):
        """Verifies that high-performance composite indexes are registered on SQLAlchemy models."""
        from sqlalchemy import inspect

        # 1. Expense composite indexes
        expense_indexes = [idx.name for idx in Expense.__table__.indexes]
        self.assertIn('idx_expense_user_date', expense_indexes)
        self.assertIn('idx_expense_user_cat', expense_indexes)

        # 2. Budget composite indexes
        budget_indexes = [idx.name for idx in Budget.__table__.indexes]
        self.assertIn('idx_budget_user_month_year', budget_indexes)

        # 3. Investment composite indexes
        inv_indexes = [idx.name for idx in Investment.__table__.indexes]
        self.assertIn('idx_investment_user_type', inv_indexes)

        # 4. Bill composite indexes
        bill_indexes = [idx.name for idx in Bill.__table__.indexes]
        self.assertIn('idx_bill_user_paid_due', bill_indexes)

        # 5. Notification composite indexes
        notif_indexes = [idx.name for idx in Notification.__table__.indexes]
        self.assertIn('idx_notification_user_unread', notif_indexes)

    def test_health_check_endpoint_telemetry(self):
        """Verifies /health probe returns database_diagnostics with latency_ms."""
        res = self.client.get('/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['database'], 'connected')
        self.assertIn('database_diagnostics', data)
        self.assertIn('latency_ms', data['database_diagnostics'])
        self.assertIn('dialect', data['database_diagnostics'])

    def test_zero_legacy_query_get_calls_in_codebase(self):
        """Verifies that NO legacy .query.get() calls exist in the Python codebase."""
        root_dir = os.path.dirname(os.path.abspath(__file__))
        py_files = []
        for dirpath, _, filenames in os.walk(root_dir):
            if '.venv' in dirpath or '__pycache__' in dirpath or '.git' in dirpath or 'instance' in dirpath:
                continue
            for f in filenames:
                if f.endswith('.py'):
                    py_files.append(os.path.join(dirpath, f))

        target_needle = ".query." + "get("
        violations = []
        for fpath in py_files:
            if os.path.basename(fpath) == 'test_database_resilience.py':
                continue
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                for line_idx, line in enumerate(f, 1):
                    if target_needle in line and not line.strip().startswith('#'):
                        rel_path = os.path.relpath(fpath, root_dir)
                        violations.append(f"{rel_path}:{line_idx}: {line.strip()}")

        self.assertEqual(violations, [], f"Found legacy .query.get() calls: {violations}")


if __name__ == '__main__':
    unittest.main()
