# WalletIQ: SQLite ➜ MySQL Migration Guide (Flask + SQLAlchemy)

This guide migrates the backend configuration from SQLite to MySQL while keeping the app functionality intact:
- User Registration/Login/Logout (Flask-Login)
- Expense tracking + deletion
- Budget / Investments / Bills screens
- Analytics dashboard + JSON stats endpoint
- AI advisor (Gemini chatbot)

## 0) Prerequisites
- MySQL Server running
- MySQL Workbench (or any MySQL client)
- VS Code project opened

## 1) Configure environment variables
Edit/create: `.env`

Required variables:
- `SECRET_KEY`
- `GEMINI_API_KEY`
- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`

Example (already created in repo):
```env
SECRET_KEY=CHANGE_ME
GEMINI_API_KEY=CHANGE_ME

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=walletiq_user
MYSQL_PASSWORD=CHANGE_ME
MYSQL_DATABASE=walletiq
```

## 2) Install backend dependencies
```bat
pip install -r requirements.txt
```

## 3) Create MySQL database + tables
Run the generated schema script:
- `mysql_schema_walletiq.sql`

### Option A: MySQL Workbench
1. Open MySQL Workbench
2. Connect to your MySQL instance
3. Run the entire contents of:
   - `e:/project/AI Financial Assistant v2/mysql_schema_walletiq.sql`

This creates:
- database: `walletiq`
- tables: `user`, `expense`, `budget`, `investment`, `bill`

## 4) Update app configuration (already applied)
`app.py` now uses:
- `mysql+pymysql://...` SQLAlchemy URI
- removed SQLite-only PRAGMA/WAL logic

It reads MySQL settings from `.env`.

## 5) Run the Flask app
```bat
python run.py
```

On startup, the app calls `db.create_all()` which will reconcile ORM tables as needed.

## 6) Smoke test checklist (must work)
1. Register a user
2. Login with the new user
3. Add an expense
4. Delete an expense
5. Open dashboard (analytics)
6. Add/view/update Budget, Investments, Bills
7. Use AI Advisor chat
8. Logout

## Notes
- Table name `user` is kept to match SQLAlchemy `__tablename__ = 'user'`.
- All per-user data access is filtered by `user_id`, preserving isolation.

