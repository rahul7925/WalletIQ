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

## 🚀 Free-Tier Deployment Guide ($0/Month Forever)

WalletIQ X is architected to run **100% free** without trial expirations or credit card requirements using:
- **Frontend**: **Vercel** (Free Hobby Tier)
- **Backend**: **Render** (Free Web Service Tier)
- **Database**: **TiDB Cloud Serverless** (Free 5GB MySQL 8.0) or **Neon** (Free 0.5GB PostgreSQL 16)

---

### Step 1: Provision Free Database (0 Cost, No Card Required)

#### Option A: TiDB Cloud Serverless (Recommended — 5 GB Free MySQL 8.0)
1. Sign up at [tidbcloud.com](https://tidbcloud.com) (No credit card required).
2. Create a **TiDB Cloud Starter (Serverless)** cluster.
3. Click **Connect** → Choose **PyMySQL** (or General Connection).
4. Copy the connection string. It looks like:
   `mysql+pymysql://<user>:<password>@gateway01.<region>.prod.aws.tidbcloud.com:4000/<db>?ssl_verify_cert=true&ssl_verify_identity=true`

#### Option B: Neon Serverless (0.5 GB Free PostgreSQL 16)
1. Sign up at [neon.tech](https://neon.tech) (No credit card required).
2. Create a project.
3. Copy your pooled connection string:
   `postgresql://<user>:<password>@<endpoint>.neon.tech/<db>?sslmode=require`

---

### Step 2: Deploy Backend on Render (Free Web Service)

1. Sign up at [render.com](https://render.com) using your GitHub account.
2. Click **New +** → **Web Service**.
3. Connect your **`WalletIQ`** repository.
4. Render will read [`render.yaml`](file:///c:/walletIQ/WalletIQ-main/render.yaml) or you can configure manually:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `flask db upgrade && gunicorn --config gunicorn.conf.py wsgi:app`
   - **Plan**: **Free** ($0/month)
5. Under **Environment Variables**, add:
   - `DATABASE_URL`: Your connection string from Step 1.
   - `SECRET_KEY`: Generate a random 64-character key (e.g. via `python -c "import secrets; print(secrets.token_hex(32))"`).
   - `GEMINI_API_KEY`: Your Google Gemini API key from [Google AI Studio](https://aistudio.google.com).
   - `CORS_ORIGINS`: `http://localhost:3000` *(you will update this with your Vercel URL in Step 4)*.
   - `SESSION_COOKIE_SECURE`: `true`
   - `BEHIND_PROXY`: `true`
   - `FLASK_ENV`: `production`
6. Click **Create Web Service**.
7. Once deployed, note your Render URL (e.g., `https://walletiq-api.onrender.com`).
8. Verify health check: `https://your-app.onrender.com/health`.

> [!NOTE]
> **Render Free Tier Cold Starts**: Render's free tier sleeps after 15 minutes of inactivity. When accessed after sleeping, the first request takes ~30–45s to spin up. The frontend includes an automatic `ServerWakeupBanner` notifying users while the container starts.

---

### Step 3: Deploy Frontend on Vercel ($0/Month)

1. Sign up at [vercel.com](https://vercel.com) using your GitHub account.
2. Click **Add New...** → **Project**.
3. Import the **`WalletIQ`** repository.
4. Configure:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
5. In **Environment Variables**, add:
   - `VITE_API_BASE_URL`: Your Render backend URL from Step 2 (e.g., `https://walletiq-api.onrender.com`).
6. Click **Deploy**.
7. Copy your live Vercel domain (e.g., `https://walletiq.vercel.app`).

---

### Step 4: Link Vercel to Render CORS

1. Go back to your [Render Dashboard](https://dashboard.render.com) → Backend Web Service → **Environment**.
2. Update `CORS_ORIGINS` to include your Vercel domain:
   ```env
   CORS_ORIGINS=https://walletiq.vercel.app,http://localhost:3000
   ```
3. Render will redeploy automatically.

---

## 🧪 Testing & Verification

Run the full regression test suite (all 91 tests passing):

```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1  # Linux/macOS: source .venv/bin/activate

# Run all 91 tests
pytest -v

# Run REST API and database resilience tests specifically
pytest -v test_api_v1.py test_database_resilience.py test_deployment.py
```

---

## 📄 License
This project is licensed under the MIT License.

