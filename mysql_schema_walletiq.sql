-- WalletIQ: MySQL schema + migration script
-- Creates database + tables used by current Flask/SQLAlchemy models
-- Tested for compatibility with Flask-SQLAlchemy definitions in app.py

-- 1) Create database
CREATE DATABASE IF NOT EXISTS walletiq
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE walletiq;

-- 2) Table: user
-- Note: `user` is a common SQL identifier; keeping it to match SQLAlchemy __tablename__ = 'user'
-- If your MySQL configuration treats USER as a strict keyword, enable identifier quoting
-- in SQLAlchemy (this project keeps naming as-is).
CREATE TABLE IF NOT EXISTS `user` (
  id INT NOT NULL AUTO_INCREMENT,
  username VARCHAR(100) NOT NULL,
  email VARCHAR(200) NULL,
  password VARCHAR(200) NOT NULL,
  full_name VARCHAR(200) NOT NULL DEFAULT '',
  language VARCHAR(10) NOT NULL DEFAULT 'en',
  monthly_budget DOUBLE NOT NULL DEFAULT 0.0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_user_username (username),
  UNIQUE KEY uq_user_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3) Table: expense
CREATE TABLE IF NOT EXISTS expense (
  id INT NOT NULL AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  amount DOUBLE NOT NULL,
  category VARCHAR(100) NOT NULL DEFAULT 'General',
  note VARCHAR(500) NOT NULL DEFAULT '',
  payment_mode VARCHAR(50) NOT NULL DEFAULT 'UPI',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_id INT NOT NULL,
  PRIMARY KEY (id),
  KEY idx_expense_user_date (user_id, created_at),
  CONSTRAINT fk_expense_user
    FOREIGN KEY (user_id) REFERENCES `user`(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4) Table: budget
CREATE TABLE IF NOT EXISTS budget (
  id INT NOT NULL AUTO_INCREMENT,
  category VARCHAR(100) NOT NULL,
  amount DOUBLE NOT NULL,
  month INT NOT NULL,
  year INT NOT NULL,
  user_id INT NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_budget_user_cat_month (user_id, category, month, year),
  KEY idx_budget_user (user_id),
  CONSTRAINT fk_budget_user
    FOREIGN KEY (user_id) REFERENCES `user`(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5) Table: investment
CREATE TABLE IF NOT EXISTS investment (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(200) NOT NULL,
  type VARCHAR(100) NOT NULL,
  invested DOUBLE NOT NULL,
  current_value DOUBLE NOT NULL,
  start_date DATE NULL,
  maturity_date DATE NULL,
  note VARCHAR(500) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_id INT NOT NULL,
  PRIMARY KEY (id),
  KEY idx_investment_user (user_id),
  CONSTRAINT fk_investment_user
    FOREIGN KEY (user_id) REFERENCES `user`(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6) Table: bill
CREATE TABLE IF NOT EXISTS bill (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(200) NOT NULL,
  amount DOUBLE NOT NULL,
  due_day INT NOT NULL,
  category VARCHAR(100) NOT NULL DEFAULT 'Bills',
  is_recurring TINYINT(1) NOT NULL DEFAULT 1,
  is_paid TINYINT(1) NOT NULL DEFAULT 0,
  paid_date DATE NULL,
  note VARCHAR(500) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_id INT NOT NULL,
  PRIMARY KEY (id),
  KEY idx_bill_user (user_id),
  CONSTRAINT fk_bill_user
    FOREIGN KEY (user_id) REFERENCES `user`(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- End

