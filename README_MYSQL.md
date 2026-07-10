# WalletIQ SQLite ➜ MySQL (Workbench/MySQL Server) Migration Notes

## 1) Create/update `.env`
File: `e:/project/AI Financial Assistant v2/.env`

```env
SECRET_KEY=CHANGE_ME
GEMINI_API_KEY=CHANGE_ME

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=walletiq_user
MYSQL_PASSWORD=CHANGE_ME
MYSQL_DATABASE=walletiq
```

## 2) Install dependencies
```bat
pip install -r requirements.txt
```

## 3) Create database + tables (production-ready)
Use the generated schema script:

- `e:/project/AI Financial Assistant v2/mysql_schema_walletiq.sql`

In MySQL Workbench / SQL editor, run:
- Entire contents of `mysql_schema_walletiq.sql`

This creates:
- `walletiq` database
- `user`, `expense`, `budget`, `investment`, `bill` tables

## 4) (Optional) Migrate existing SQLite data
Recommended approach:
- Export from SQLite (user/budget/investment/bill/expense)
- Import into MySQL in this order:
  1) `user`
  2) `expense`, `budget`, `investment`, `bill`
- Ensure foreign keys (`user_id`) match

## 5) Run Flask app
```bat
python run.py
```

## 6) Verify
Open the app and test:
- Register/Login/Logout
- Add/Delete Expense
- Budget / Investments / Bills screens
- Analytics (dashboard)
- AI Advisor chat




