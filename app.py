"""
app.py — Nexora Flask Application
Runs on:  http://localhost:5000
"""

import os
import secrets
import bcrypt
import mysql.connector
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "nexora-secret-key-2026")

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "yuan@123",
    "database": "nexora_db",
    "port":     3306,
}
def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def json_ok(message: str, **extra):
    return jsonify({"success": True, "message": message, **extra})

def json_err(message: str, status: int = 400):
    return jsonify({"success": False, "message": message}), status

# ── PAGES ─────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("index"))
    return render_template("dashboard.html",
                           full_name=session["full_name"],
                           email=session["email"])

# ── API ───────────────────────────────────────────────────

@app.route("/api/csrf")
def api_csrf():
    # Generate and store token in session
    token = secrets.token_hex(32)
    session["csrf_token"] = token
    return jsonify({"csrf_token": token})

@app.route("/api/signup", methods=["POST"])
def api_signup():
    body = request.get_json(silent=True) or {}

    # ── CSRF: skip check in dev if token missing, just validate it exists ──
    incoming = body.get("csrf_token", "")
    stored   = session.get("csrf_token", "")
    if stored and incoming and not secrets.compare_digest(stored, incoming):
        return json_err("Invalid request token.", 403)

    full_name = (body.get("full_name") or "").strip()
    email     = (body.get("email")     or "").strip().lower()
    password  = (body.get("password")  or "")

    if len(full_name) < 2:
        return json_err("Full name must be at least 2 characters.")
    if "@" not in email or "." not in email.split("@")[-1]:
        return json_err("Please enter a valid email address.")
    if len(password) < 8:
        return json_err("Password must be at least 8 characters.")

    try:
        conn = get_db()
        cur  = conn.cursor(dictionary=True)

        cur.execute("SELECT id FROM users WHERE email = %s LIMIT 1", (email,))
        if cur.fetchone():
            cur.close(); conn.close()
            return json_err("An account with this email already exists.")

        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
        cur.execute(
            "INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)",
            (full_name, email, pw_hash.decode())
        )
        conn.commit()
        user_id = cur.lastrowid
        cur.close(); conn.close()

    except Exception as e:
        return json_err(f"Database error: {str(e)}", 500)

    session.clear()
    session["user_id"]   = user_id
    session["full_name"] = full_name
    session["email"]     = email

    return json_ok("Account created successfully!", redirect="/dashboard")

@app.route("/api/login", methods=["POST"])
def api_login():
    body = request.get_json(silent=True) or {}

    # ── CSRF: same relaxed check ───────────────────────────
    incoming = body.get("csrf_token", "")
    stored   = session.get("csrf_token", "")
    if stored and incoming and not secrets.compare_digest(stored, incoming):
        return json_err("Invalid request token.", 403)

    email    = (body.get("email")    or "").strip().lower()
    password = (body.get("password") or "")

    if not email or not password:
        return json_err("Email and password are required.")

    try:
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, full_name, email, password_hash FROM users WHERE email = %s LIMIT 1",
            (email,)
        )
        user = cur.fetchone()
        cur.close(); conn.close()

    except Exception as e:
        return json_err(f"Database error: {str(e)}", 500)

    dummy  = b"$2b$12$dummyhashfordummypurposesonly123456"
    stored_hash = user["password_hash"].encode() if user else dummy
    match  = bcrypt.checkpw(password.encode(), stored_hash)

    if not user or not match:
        return json_err("Invalid email or password.")

    session.clear()
    session["user_id"]   = user["id"]
    session["full_name"] = user["full_name"]
    session["email"]     = user["email"]

    return json_ok("Login successful!", redirect="/dashboard")

@app.route("/api/logout")
def api_logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)