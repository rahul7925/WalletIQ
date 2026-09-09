"""
test_deployment.py — Tests for production deployment readiness:
1. Health check probes (/health, /healthz, /api/health)
2. Database connection status reporting (healthy vs degraded)
3. HTTP security headers injection
4. Reverse proxy header handling (ProxyFix / X-Forwarded-For)
5. Gunicorn configuration worker clamping and environment overrides
6. Database URL normalization (mysql://, postgres://)
7. Predict script database engine configuration
"""

import unittest
import os
import runpy
from unittest.mock import patch, MagicMock
from app import app, db


class TestDeploymentReadiness(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app_context = app.app_context()
        self.app_context.push()

        # In-memory database for testing
        from sqlalchemy import create_engine
        self.engine = create_engine('sqlite:///:memory:')
        db._app_engines[app][None] = self.engine
        db.create_all()

        self.client = app.test_client()

    def tearDown(self):
        db.session.close()
        self.app_context.pop()

    def test_health_check_healthy(self):
        """Test /health probe returns 200 OK with proper status payload."""
        for path in ['/health', '/healthz', '/api/health']:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Failed on path {path}")
            data = res.get_json()
            self.assertIn(data['status'], ('ok', 'healthy'))
            self.assertEqual(data['database'], 'connected')
            self.assertIn('version', data)
            self.assertIn('timestamp', data)

    def test_health_check_db_failure(self):
        """Test /health probe returns 503 degraded when database connectivity fails."""
        with patch.object(db.session, 'execute', side_effect=Exception("Database connection timeout")):
            res = self.client.get('/health')
            self.assertEqual(res.status_code, 503)
            data = res.get_json()
            self.assertEqual(data['status'], 'degraded')
            self.assertEqual(data['database'], 'disconnected')

    def test_security_headers_present(self):
        """Test essential security headers are injected into HTTP responses."""
        res = self.client.get('/health')
        self.assertEqual(res.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(res.headers.get('X-Frame-Options'), 'SAMEORIGIN')
        self.assertEqual(res.headers.get('X-XSS-Protection'), '1; mode=block')
        self.assertEqual(res.headers.get('Referrer-Policy'), 'strict-origin-when-cross-origin')

    def test_gunicorn_config_worker_clamping(self):
        """Test gunicorn.conf.py clamps worker counts safely to prevent OOM kills."""
        cfg = runpy.run_path('gunicorn.conf.py')
        self.assertIn('workers', cfg)
        self.assertIn('bind', cfg)
        self.assertIn('timeout', cfg)
        self.assertIn('graceful_timeout', cfg)
        # Default workers must not exceed 4 to prevent container OOM
        self.assertLessEqual(cfg['workers'], 4)
        self.assertGreaterEqual(cfg['workers'], 2)

    def test_gunicorn_config_web_concurrency_override(self):
        """Test that WEB_CONCURRENCY environment variable overrides gunicorn workers."""
        with patch.dict(os.environ, {'WEB_CONCURRENCY': '3'}):
            cfg = runpy.run_path('gunicorn.conf.py')
            self.assertEqual(cfg['workers'], 3)

    @patch('predict.create_engine')
    def test_database_url_schemes_in_predict(self, mock_create_engine):
        """Test predict.py database engine supports DATABASE_URL with auto-normalization."""
        from predict import _get_db_engine

        # Test mysql:// conversion
        with patch.dict(os.environ, {'DATABASE_URL': 'mysql://user:pass@localhost:3306/db'}, clear=False):
            _get_db_engine()
            call_url = str(mock_create_engine.call_args[0][0])
            self.assertTrue(call_url.startswith('mysql+pymysql://'))

        # Test postgres:// conversion
        with patch.dict(os.environ, {'DATABASE_URL': 'postgres://user:pass@localhost:5432/db'}, clear=False):
            _get_db_engine()
            call_url = str(mock_create_engine.call_args[0][0])
            self.assertTrue(call_url.startswith('postgresql://'))

        # Test Aiven mysql:// with ssl-mode stripping and connect_args
        with patch.dict(os.environ, {'DATABASE_URL': 'mysql://avnadmin:pwd@mysql-walletiq-test.aivencloud.com:12345/defaultdb?ssl-mode=REQUIRED'}, clear=False):
            _get_db_engine()
            call_url = str(mock_create_engine.call_args[0][0])
            self.assertNotIn('ssl-mode', call_url)
            self.assertIn('charset=utf8mb4', call_url)
            self.assertTrue(mock_create_engine.call_args[1]['connect_args']['ssl']['ssl'])


if __name__ == '__main__':
    unittest.main()
