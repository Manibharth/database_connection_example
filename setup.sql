-- ═══════════════════════════════════════════════════════════
--  Nexora — MySQL Setup
--  Run once:  mysql -u root -p < setup.sql
-- ═══════════════════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS nexora_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE nexora_db;

CREATE TABLE IF NOT EXISTS users (
    id            INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    full_name     VARCHAR(120)    NOT NULL,
    email         VARCHAR(180)    NOT NULL,
    password_hash VARCHAR(255)    NOT NULL,
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
