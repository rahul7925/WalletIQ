# WalletIQ v2.0 — Production Deployment Guide

This guide provides complete instructions to deploy the WalletIQ personal finance platform to production across **Render**, **Railway**, **Docker / Docker Compose**, **Fly.io**, **Heroku**, and **VPS / Cloud VMs (AWS, DigitalOcean, GCP)**.

---

## 📋 Table of Contents
1. [Production Features & Hardening](#-production-features--hardening)
2. [Environment Variables Reference](#-environment-variables-reference)
3. [Health Check & Monitoring](#-health-check--monitoring)
4. [Option A: Deploying on Render (Recommended)](#option-a-deploying-on-render-recommended)
5. [Option B: Deploying on Railway](#option-b-deploying-on-railway)
6. [Option C: Deploying with Docker & Docker Compose](#option-c-deploying-with-docker--docker-compose)
7. [Option D: Deploying on Heroku / Dokku / Fly.io](#option-d-deploying-on-heroku--dokku--flyio)
8. [Database Migrations & Operations](#-database-migrations--operations)
9. [Troubleshooting & Production FAQ](#-troubleshooting--production-faq)

---

## 🛡️ Production Features & Hardening

WalletIQ is built following 12-factor cloud-native practices:
* **Health Probes**: Built-in `/health` (and `/healthz`) endpoint verifying DB connection and uptime for orchestrators and load balancers.
* **Non-Root Container Security**: Dockerfile executes under a dedicated unprivileged user (`appuser`, UID 1000) with least-privilege permissions.
* **Reverse Proxy Trust (`ProxyFix`)**: Correctly extracts real client IPs (`X-Forwarded-For`) and protocols (`X-Forwarded-Proto`) behind cloud load balancers, ensuring login rate limiters and HTTPS cookies function properly.
* **HTTP Security Headers**: Automatically applies `X-Content-Type-Options`, `X-Frame-Options: SAMEORIGIN`, `X-XSS-Protection`, `Referrer-Policy`, and HSTS.
* **OOM-Safe Concurrency**: Gunicorn worker counts are clamped to avoid container Out-Of-Memory crashes on multi-core host nodes, with native `WEB_CONCURRENCY` support.
* **Automatic Migrations**: Entrypoint scripts run `flask db upgrade` on container startup, eliminating manual database setup steps.
* **Unified Database Support**: Seamlessly supports `DATABASE_URL` with auto-normalization for MySQL (`mysql+pymysql`), PostgreSQL, and SQLite.

---

## ⚙️ Environment Variables Reference

Configure these variables in your deployment dashboard or `.env` file:

| Environment Variable | Description | Recommended / Example Value |
| :--- | :--- | :--- |
| `SECRET_KEY` | Flask session secret key (Required in prod) | 64-char random hex (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `FLASK_ENV` | Application environment | `production` |
| `SESSION_COOKIE_SECURE` | Enforces cookies over HTTPS only | `true` |
| `BEHIND_PROXY` | Enables ProxyFix for client IP & HTTPS | `true` |
| `PORT` | Web server listening port | `5000` (or injected by platform) |
| `DATABASE_URL` | Unified DB connection string | `mysql+pymysql://user:pass@host:port/dbname` |
| `MYSQL_HOST` | Fallback DB host (if DATABASE_URL unset) | `localhost` or `db` |
| `MYSQL_PORT` | Fallback DB port | `3306` |
| `MYSQL_USER` | Fallback DB username | `walletiq` |
| `MYSQL_PASSWORD` | Fallback DB password | `your_secure_password` |
| `MYSQL_DATABASE` | Fallback DB name | `walletiqdb` |
| `MYSQL_SSL_CA` | Path to SSL CA certificate (if needed) | `/app/ca-cert.pem` |
| `AUTO_MIGRATE` | Run `flask db upgrade` on startup | `true` |
| `WAIT_FOR_DB` | Wait for DB connectivity in entrypoint | `true` |
| `WEB_CONCURRENCY` | Gunicorn worker process count | `2` (recommended for 512MB-1GB RAM) |
| `GEMINI_API_KEY` | Google Gemini AI Key | Obtain from [Google AI Studio](https://aistudio.google.com/apikey) |

---

## 💓 Health Check & Monitoring

WalletIQ exposes an unauthenticated health probe at:
* **Endpoint**: `GET /health` (aliases: `/healthz`, `/api/health`)
* **Healthy Response (200 OK)**:
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-09-09T14:00:00.000000+05:30",
    "database": "connected",
    "environment": "production",
    "version": "2.0.0"
  }
  ```
* **Degraded Response (503 Service Unavailable)**:
  Returned when the database connection fails or cannot be reached.

Configure your cloud platform's Health Check Path to `/health`.

---

## Option A: Deploying on Render (Recommended)

Render uses the included `render.yaml` Blueprint to provision the service with health checks and zero-downtime migrations.

### Using Render Blueprints (1-Click Automated)
1. Navigate to the [Render Dashboard](https://dashboard.render.com/) and click **New ➜ Blueprint**.
2. Connect your Git repository.
3. Render automatically reads `render.yaml`, configures the Python runtime, sets `/health` as the health check path, and sets `preDeployCommand: flask db upgrade`.
4. Provide `GEMINI_API_KEY` and your database credentials when prompted.
5. Click **Apply**.

### Manual Web Service Setup on Render
1. Click **New ➜ Web Service** and select your repository.
2. Configure:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Pre-Deploy Command**: `flask db upgrade`
   - **Start Command**: `gunicorn --config gunicorn.conf.py app:app`
   - **Health Check Path**: `/health`
3. Add Environment Variables:
   - `DATABASE_URL`: Your MySQL connection string (e.g. `mysql://user:pass@host:3306/walletiqdb`).
   - `SECRET_KEY`: A secure 64-character random string.
   - `FLASK_ENV`: `production`
   - `SESSION_COOKIE_SECURE`: `true`
   - `BEHIND_PROXY`: `true`
   - `GEMINI_API_KEY`: Your Gemini API key.
4. Click **Create Web Service**.

---

## Option B: Deploying on Railway

Railway builds directly using Nixpacks or the `Dockerfile`, managed via `railway.json`.

1. Go to the [Railway Dashboard](https://railway.app/) and select **New Project ➜ Deploy from GitHub repo**.
2. **Add a MySQL Database**:
   - In the canvas, click **New ➜ Database ➜ Add MySQL**.
   - Railway injects `DATABASE_URL` directly into linked services.
3. Configure Environment Variables in your Web Service:
   - `SECRET_KEY`: A secure random hex string.
   - `FLASK_ENV`: `production`
   - `SESSION_COOKIE_SECURE`: `true`
   - `BEHIND_PROXY`: `true`
   - `GEMINI_API_KEY`: Your Google AI Studio API key.
4. Railway will execute the start command specified in `railway.json`:
   `flask db upgrade && gunicorn --config gunicorn.conf.py app:app`
   and monitor health at `/health`.

---

## Option C: Deploying with Docker & Docker Compose

For Virtual Private Servers (VPS on AWS EC2, DigitalOcean Droplet, Linode, Hetzner, etc.):

### 1. Prerequisites
Install Docker and Docker Compose:
```bash
sudo apt update && sudo apt install docker.io docker-compose -y
```

### 2. Configure Environment
Create a `.env` file in the project root:
```env
FLASK_ENV=production
SECRET_KEY=generate_a_random_64_char_hex_key_here
SESSION_COOKIE_SECURE=true
BEHIND_PROXY=true
PORT=5000

MYSQL_ROOT_PASSWORD=strong_root_password
MYSQL_DATABASE=walletiqdb
MYSQL_USER=walletiq
MYSQL_PASSWORD=strong_user_password

GEMINI_API_KEY=AIzaSy...
```

### 3. Launch with Docker Compose
```bash
docker-compose up -d --build
```

The stack will:
1. Launch MySQL and wait for its health check (`mysqladmin ping`).
2. Launch the `web` container, execute `entrypoint.sh`, run `flask db upgrade`, and start Gunicorn with 2 workers.
3. Mount persistent volumes for database data, logs, and user reports.

Check container status and logs:
```bash
docker-compose ps
docker-compose logs -f web
```

---

## Option D: Deploying on Heroku / Dokku / Fly.io

### Heroku / Dokku
The repository includes a `Procfile` with a `release` phase:
```procfile
release: flask db upgrade
web: gunicorn --config gunicorn.conf.py app:app
```
When you push to Heroku, Heroku will automatically execute the release command to upgrade database tables before launching the web worker.

### Fly.io
Launch via Fly CLI:
```bash
fly launch
fly secrets set SECRET_KEY=$(openssl rand -hex 32) GEMINI_API_KEY=...
fly deploy
```

---

## 🛠️ Database Migrations & Operations

WalletIQ manages its database schema through Flask-Migrate (Alembic).

### Automatic Migrations (Default)
In Docker, Render, Railway, and Heroku, migrations are applied automatically during deployment via `entrypoint.sh` or `preDeployCommand`.

### Running Migrations Manually
* **Locally / Virtualenv**:
  ```bash
  flask db upgrade
  ```
* **Inside running Docker container**:
  ```bash
  docker-compose exec web flask db upgrade
  ```
* **Creating a new migration** (after editing models in `app.py`):
  ```bash
  flask db migrate -m "Description of schema changes"
  flask db upgrade
  ```

---

## ❓ Troubleshooting & Production FAQ

#### 1. "Too many attempts. Please wait a minute."
* **Cause**: Requests are behind a reverse proxy (Render, Cloudflare, ALB) and all requests appear to come from `127.0.0.1`.
* **Fix**: Ensure `BEHIND_PROXY=true` or `FLASK_ENV=production` is set in your environment variables to activate `ProxyFix`.

#### 2. Container crashes with Out-Of-Memory (OOM / exit code 137)
* **Cause**: Too many Gunicorn workers allocated on a high-core host machine with limited memory.
* **Fix**: Set `WEB_CONCURRENCY=2` in your platform's environment variables.

#### 3. Database connection SSL errors
* **Cause**: Managed cloud databases (AWS RDS, GCP Cloud SQL, Aiven) require SSL certificates.
* **Fix**: Provide the path to your CA certificate in `MYSQL_SSL_CA` or append `?ssl_ca=/path/to/cert.pem` to `DATABASE_URL`.
