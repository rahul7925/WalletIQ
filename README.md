# WalletIQ X — Intelligent Financial Operations Platform

WalletIQ X is an enterprise-ready, AI-native personal finance platform built on a decoupled cloud architecture:

```
┌────────────────────────────────────────┐
│             Vercel Edge                │
│       React 18 + Vite SPA Client       │
└───────────────────┬────────────────────┘
                    │ HTTPS / REST API (Bearer Token)
                    ▼
┌────────────────────────────────────────┐
│            Railway Service             │
│        Flask REST API (v1)             │
│   ├── Gunicorn WSGI Concurrency        │
│   ├── Google Gemini 2.5 AI Advisor     │
│   ├── Multimodal Receipt OCR Engine    │
│   ├── Scikit-Learn Predictive ML       │
│   └── ReportLab / OpenPyXL PDF & Excel │
└───────────────────┬────────────────────┘
                    │ PyMySQL / SQLAlchemy
                    ▼
┌────────────────────────────────────────┐
│             Railway MySQL              │
│       Relational Persistence &         │
│         Alembic DB Migrations          │
└────────────────────────────────────────┘
```

---

## 🌟 Key Features

1. **Decoupled Modern Frontend (Vercel)**
   - Fast React 18 + Vite SPA with instant navigation.
   - Elegant dark/gold fintech design system with Inter, JetBrains Mono, and Playfair Display typography.
   - Full responsive layout with collapsible sidebar, top navigation, quick transaction logger, and notification center.
2. **REST API Core (Railway Flask v1)**
   - Standardized JSON responses (`{ success: true, data: ..., message: ... }`).
   - Cryptographic `URLSafeTimedSerializer` session token manager supporting `Authorization: Bearer <token>` and session cookies.
   - Complete data isolation and strict user authorization (zero IDOR vulnerabilities).
3. **AI Financial Advisor (Gemini 2.5)**
   - Real-time conversational AI grounded in live personal transaction context, budgets, goals, and savings velocity.
4. **Multimodal Receipt OCR**
   - Direct receipt camera/upload scanning using Gemini Multimodal Vision to auto-extract merchant, date, amounts, and tax.
5. **Machine Learning Predictors**
   - Automated category classification with Scikit-Learn TF-IDF + Multinomial Naive Bayes.
   - Long-range savings velocity simulations with compounding yield curves.
   - ML loan underwriting risk model with credit risk probability scoring.
6. **Audit-Grade Reporting**
   - High-fidelity PDF financial statements and Excel workbooks.
   - Multi-period comparative AI variance analysis.
   - Secure token-based public statement sharing.

---

## 📁 Repository Structure

```
.
├── frontend/                # React 18 + Vite SPA (Vercel)
│   ├── src/
│   │   ├── components/      # Sidebar, Topbar, Modal, ReceiptScannerModal, StatCard, etc.
│   │   ├── context/         # AuthContext (token storage, active session synchronization)
│   │   ├── pages/           # Dashboard, Expenses, Budgets, Investments, Bills, AI Advisor, etc.
│   │   ├── services/        # api.js (centralized REST API client)
│   │   └── styles/          # index.css (fintech design variables, glassmorphism)
│   ├── package.json
│   ├── vite.config.js
│   └── vercel.json          # SPA rewrite rules and asset caching
│
├── services/                # Backend domain services
│   ├── auth_token.py        # Cryptographic Bearer token serializer & auth middleware
│   ├── api_response.py      # Standardized JSON success/error envelopes
│   ├── api_v1.py            # Complete REST API blueprint (/api/v1)
│   ├── chatbot.py           # Gemini conversation context engine
│   ├── forecaster.py        # ML regression & spending forecaster
│   ├── predict.py           # ML transaction classifier
│   └── ...                  # Financial health, goals, loans, reports, bill services
│
├── migrations/              # Alembic database migration versions
├── app.py                   # Flask application core, ORM models, CORS, error handlers
├── wsgi.py                  # Production WSGI entrypoint for Gunicorn
├── gunicorn.conf.py         # Clamped production worker pool & timeout configs
├── railway.json             # Railway Nixpacks deployment definition
├── Procfile                 # Process manifest (release: flask db upgrade, web: gunicorn)
└── requirements.txt         # Pinned Python backend dependencies
```

---

## ⚙️ Environment Variables

### Backend (`.env` on Railway)
```env
# Flask Core
FLASK_APP=wsgi.py
FLASK_ENV=production
SECRET_KEY=replace_with_a_secure_random_64_character_hex_key
PORT=5000
SESSION_COOKIE_SECURE=true
BEHIND_PROXY=true

# CORS Configuration (Allow Vercel frontend)
CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000

# Database Configuration (Railway MySQL)
DATABASE_URL=mysql+pymysql://root:password@mysql.railway.internal:3306/railway
# Or individual parameters:
# MYSQL_HOST=...
# MYSQL_PORT=3306
# MYSQL_USER=...
# MYSQL_PASSWORD=...
# MYSQL_DATABASE=...

# Gemini AI (Google AI Studio)
GEMINI_API_KEY=AIzaSy...

# Gunicorn tuning
WEB_CONCURRENCY=2
GUNICORN_THREADS=2
```

### Frontend (`.env` on Vercel)
```env
VITE_API_BASE_URL=https://your-backend.up.railway.app
```

---

## 🚀 Deployment Guide

### 1. Backend on Railway
1. Create a new project on [Railway](https://railway.app).
2. Add a **MySQL** database service.
3. Deploy the repository from GitHub.
4. Set environment variables in Railway:
   - `DATABASE_URL`: Set to `${{ MySQL.DATABASE_URL }}` (or provide host, user, password, database).
   - `SECRET_KEY`: Generate a random 64-char string.
   - `CORS_ORIGINS`: Add your Vercel deployment URL (e.g. `https://your-walletiq.vercel.app`).
   - `GEMINI_API_KEY`: Your Google Gemini API key.
5. Railway will detect `railway.json` / `Procfile`, automatically execute database migrations (`flask db upgrade`), and start Gunicorn on `wsgi:app`.
6. Note your Railway public URL (e.g., `https://walletiq-api.up.railway.app`).

### 2. Frontend on Vercel
1. Import your repository into [Vercel](https://vercel.com).
2. Set the **Root Directory** to `frontend`.
3. Framework Preset: **Vite**.
4. In Environment Variables, add:
   - `VITE_API_BASE_URL`: Set to your Railway backend URL (e.g. `https://walletiq-api.up.railway.app`).
5. Click **Deploy**. Vercel will build the SPA and route all traffic using `vercel.json`.

---

## 🧪 Testing & Verification

Run the full test suite (unit tests, integration tests, REST API endpoints, and IDOR isolation tests):

```bash
# Activate virtual environment
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1

# Run all 82 tests
pytest -v

# Run REST API suite specifically
pytest -v test_api_v1.py
```

---

## 📄 License
This project is licensed under the MIT License.
