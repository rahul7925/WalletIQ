# WalletIQ X — Production Deployment Guide

This guide describes how to deploy the WalletIQ X personal finance platform to production. The codebase is configured to be cloud-native and deployable on **Render**, **Railway**, or any **VPS/Docker** environment.

---

## 📋 Table of Contents
1. [Environment Variables Reference](#-environment-variables-reference)
2. [Option A: Deploying on Render (Recommended)](#option-a-deploying-on-render-recommended)
3. [Option B: Deploying on Railway](#option-b-deploying-on-railway)
4. [Option C: Deploying on Docker / VPS (DigitalOcean, AWS, Linode)](#option-c-deploying-on-docker--vps)
5. [Database Migrations & First Run Setup](#%EF%B8%8F-database-migrations--first-run-setup)

---

## ⚙️ Environment Variables Reference

Configure these variables in your deployment dashboard or `.env` file:

| Environment Variable | Description | Example / Recommended Value |
| :--- | :--- | :--- |
| `SECRET_KEY` | Flask session secret key | A secure random hex key (e.g. `openssl rand -hex 32`) |
| `FLASK_ENV` | Application environment | `production` |
| `SESSION_COOKIE_SECURE` | Enforces cookies over HTTPS only | `true` |
| `GEMINI_API_KEY` | Google Gemini AI Key | Obtained from [Google AI Studio](https://aistudio.google.com/apikey) |
| `DATABASE_URL` | Unified Database Connection String | `mysql+pymysql://user:password@host:port/dbname` |
| `MYSQL_SSL_CA` | Path to SSL CA certificate (if required by DB) | `/app/ca-cert.pem` |
| `GUNICORN_ACCESSLOG` | Gunicorn access logs path | `-` (standard output stream) |
| `GUNICORN_ERRORLOG` | Gunicorn error logs path | `-` (standard error stream) |

---

## Option A: Deploying on Render (Recommended)

Render can parse the repository's `render.yaml` configuration to spin up the web service and database automatically (Blueprint), or you can configure it manually.

### Using Render Blueprints (Automatic)
1. Go to the [Render Dashboard](https://dashboard.render.com/) and click **New** ➜ **Blueprint**.
2. Connect your GitHub repository `rahul7925/WalletIQ`.
3. Render will read the `render.yaml` file to provision the services automatically.
4. Input your `GEMINI_API_KEY` and other credentials when prompted.
5. Click **Apply**.

### Manual Setup on Render
If you prefer setting up services individually:
1. **Create a MySQL Database**:
   - Click **New** ➜ **SQL Database** (or provision external databases like Aiven/DigitalOcean).
   - Retrieve the database connection URL (e.g., `mysql://user:pass@host:port/db`).
2. **Create a Web Service**:
   - Click **New** ➜ **Web Service** and connect the `WalletIQ` GitHub repository.
   - Set the following settings:
     - **Runtime**: `Python`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn --config gunicorn.conf.py app:app`
   - Under **Environment Variables**, add:
     - `DATABASE_URL`: Set to the connection URL (automatic conversion from `mysql://` to `mysql+pymysql://` is handled in code).
     - `SECRET_KEY`: A secure hex string.
     - `FLASK_ENV`: `production`
     - `SESSION_COOKIE_SECURE`: `true`
     - `GEMINI_API_KEY`: Your Google AI Studio API key.
3. Click **Deploy Web Service**.

---

## Option B: Deploying on Railway

Railway uses Nixpacks to auto-configure deployments or builds directly from the `Dockerfile`.

1. Go to the [Railway Dashboard](https://railway.app/) and click **New Project**.
2. Select **Deploy from GitHub repo** and choose `rahul7925/WalletIQ`.
3. Select **Add Variable** to configure variables:
   - `GEMINI_API_KEY`
   - `SECRET_KEY`
   - `FLASK_ENV = production`
   - `SESSION_COOKIE_SECURE = true`
4. **Add a MySQL Database**:
   - In the project canvas, click **New** ➜ **Database** ➜ **Add MySQL**.
   - Railway will automatically link the database to your web service and inject `DATABASE_URL` environment variables! No manual DB copy-paste required.
5. Railway will automatically build and launch the service using the command from `railway.json`: `gunicorn --config gunicorn.conf.py app:app`.

---

## Option C: Deploying on Docker / VPS

If you own a Virtual Private Server (VPS) running Ubuntu/Debian:

### 1. Install Docker & Docker Compose
```bash
sudo apt update
sudo apt install docker.io docker-compose -y
```

### 2. Configure Environment
Create a `.env` file on your server in the app directory:
```env
SECRET_KEY=use_a_secure_random_key_here
FLASK_ENV=production
SESSION_COOKIE_SECURE=true

# Database (automatic link in docker-compose)
MYSQL_HOST=db
MYSQL_PORT=3306
MYSQL_USER=walletiq_user
MYSQL_PASSWORD=secure_mysql_db_password
MYSQL_DATABASE=walletiqdb

GEMINI_API_KEY=AIzaSy...
```

### 3. Launch Services
Run the container orchestration in detached mode:
```bash
docker-compose up -d --build
```
This launches:
- **MySQL Container (`db`)**: Exposing port `3306` internally.
- **Web App Container (`web`)**: Built from `Dockerfile`, running Gunicorn on port `5000`.

---

## 🛠️ Database Migrations & First Run Setup

To create database schemas or upgrade databases after deployment:

### On Render / Railway (Shell console)
1. Open the **Console** or **Shell** tab on the platform's service dashboard.
2. Run the migration command:
   ```bash
   flask db upgrade
   ```
   *Note: In Docker, you can enter the running container to run it: `docker-compose exec web flask db upgrade`.*
