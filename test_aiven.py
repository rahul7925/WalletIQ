import os
import sys
from urllib.parse import urlparse, unquote, quote_plus
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

def test_connection():
    print("=" * 60)
    print("  WalletIQ -> Aiven MySQL Connectivity Test")
    print("=" * 60)

    db_url = os.getenv("DATABASE_URL")
    host = os.getenv("DB_HOST") or os.getenv("MYSQL_HOST")
    port = int(os.getenv("DB_PORT") or os.getenv("MYSQL_PORT") or "24222")
    user = os.getenv("DB_USER") or os.getenv("MYSQL_USER")
    password = os.getenv("DB_PASSWORD") or os.getenv("MYSQL_PASSWORD")
    database = os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE") or "defaultdb"

    if db_url:
        print("[*] Detected DATABASE_URL in environment.")
        parsed = urlparse(db_url)
        host = parsed.hostname or host
        port = parsed.port or port
        user = unquote(parsed.username or "") if parsed.username else user
        password = unquote(parsed.password or "") if parsed.password else password
        if parsed.path and len(parsed.path) > 1:
            database = parsed.path.lstrip("/").split("?")[0]

    if not host or not user or not password:
        print("[ERROR] Missing database credentials in .env!")
        print("Please check your .env file and ensure either DATABASE_URL or DB_HOST/DB_PASSWORD is set.")
        sys.exit(1)

    masked_pw = password[:2] + ("*" * max(1, len(password) - 4)) + password[-2:] if len(password) > 4 else "****"
    print(f"Connecting to:")
    print(f"  * Host:     {host}")
    print(f"  * Port:     {port}")
    print(f"  * User:     {user}")
    print(f"  * Database: {database}")
    print(f"  * Password: {masked_pw}")
    print(f"  * SSL:      REQUIRED (Auto-configured)")
    print("-" * 60)

    try:
        import pymysql
        print("[1/2] Testing direct PyMySQL connection with SSL...")
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset="utf8mb4",
            connect_timeout=10,
            ssl={"ssl": True, "check_hostname": False}
        )
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION(), CURRENT_USER(), DATABASE()")
            row = cur.fetchone()
            print("  [SUCCESS] PyMySQL direct connection OK!")
            print(f"     MySQL Version : {row[0]}")
            print(f"     Connected User: {row[1]}")
            print(f"     Database Name : {row[2]}")
        conn.close()
    except Exception as e:
        print("  [FAILED] PyMySQL direct connection failed:")
        print(f"     {type(e).__name__}: {e}")
        sys.exit(1)

    try:
        from sqlalchemy import create_engine, text
        print("\n[2/2] Testing SQLAlchemy connection (WalletIQ Engine)...")
        user_enc = quote_plus(user)
        pwd_enc = quote_plus(password)
        sqlalchemy_uri = f"mysql+pymysql://{user_enc}:{pwd_enc}@{host}:{port}/{database}?charset=utf8mb4"
        engine = create_engine(
            sqlalchemy_uri,
            pool_pre_ping=True,
            connect_args={"ssl": {"ssl": True, "check_hostname": False}}
        )
        with engine.connect() as conn:
            res = conn.execute(text("SELECT 1 AS ok")).fetchone()
            if res and res[0] == 1:
                print("  [SUCCESS] SQLAlchemy connection OK!")
    except Exception as e:
        print("  [FAILED] SQLAlchemy connection failed:")
        print(f"     {type(e).__name__}: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  [ALL PASSED] All Aiven connection tests SUCCESSFUL!")
    print("  You are ready to run: flask db upgrade")
    print("=" * 60)

if __name__ == "__main__":
    test_connection()
