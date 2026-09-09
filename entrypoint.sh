#!/bin/sh
set -e

echo "=== Starting WalletIQ Application Container ==="

# Wait for database if configured
if [ "$WAIT_FOR_DB" = "true" ] || [ -n "$MYSQL_HOST" ] || [ -n "$DATABASE_URL" ]; then
    echo "Checking database connectivity..."
    max_retries=${DB_CONNECT_RETRIES:-30}
    count=0
    until python -c "
import os, sys
from sqlalchemy import create_engine, text

url = os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_URL')
if url:
    if url.startswith('mysql://'):
        url = url.replace('mysql://', 'mysql+pymysql://', 1)
    elif url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
else:
    host = os.environ.get('MYSQL_HOST')
    if not host:
        sys.exit(0)
    port = os.environ.get('MYSQL_PORT', '3306')
    user = os.environ.get('MYSQL_USER', 'root')
    pwd = os.environ.get('MYSQL_PASSWORD', '')
    db = os.environ.get('MYSQL_DATABASE', 'walletiqdb')
    url = f'mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?charset=utf8mb4'

try:
    engine = create_engine(url, connect_args={'connect_timeout': 3})
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
        count=$((count + 1))
        if [ "$count" -ge "$max_retries" ]; then
            echo "Warning: Database not reachable after $max_retries attempts. Proceeding anyway..."
            break
        fi
        echo "Waiting for database to accept connections ($count/$max_retries)..."
        sleep 2
    done
    echo "Database connectivity check complete."
fi

# Apply database migrations if AUTO_MIGRATE is not explicitly disabled
if [ "${AUTO_MIGRATE:-true}" != "false" ]; then
    echo "Applying database migrations (flask db upgrade)..."
    flask db upgrade || echo "Warning: Migration check completed with warnings or no-op."
fi

echo "Launching application: $@"
exec "$@"
