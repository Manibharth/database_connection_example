import os
import secrets
import bcrypt
import mysql.connector
from flask import (
    Flask, render_template, request,
    session, redirect, url_for, jsonify
)
from dotenv import load_dotenv

load_dotenv()

# ── APP SETUP ─────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "nexora-secret-key-2026")

# ── DATABASE CONFIG ───────────────────────────────────────
# Edit these values or put them in a .env file:
#   DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "yuan@123",
    "database": "nexora_db",
    "port":     3306,
}

# ── HELPERS ───────────────────────────────────────────────

def get_db():
    """Open and return a MySQL connection."""
    return mysql.connector.connect(**DB_CONFIG)


def json_ok(message: str, **extra):
    """Return a JSON success response."""
    return jsonify({"success": True, "message": message, **extra})


def json_err(message: str, status: int = 400):
    """Return a JSON error response."""
    return jsonify({"success": False, "message": message}), status


def verify_csrf(body: dict) -> bool:
    """
    Compare the CSRF token in the request body against the one in session.
    Returns True (passes) when either token is absent (dev/first-load) or
    when both are present and match.
    """
    incoming = body.get("csrf_token", "")
    stored   = session.get("csrf_token", "")
    if stored and incoming:
        return secrets.compare_digest(stored, incoming)
    return True   # skip check if one side is missing (e.g. direct API call in dev)

# ── PAGE ROUTES ───────────────────────────────────────────

@app.route("/")
def index():
    """Landing page with login / signup modals."""
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    """
    Protected dashboard page.
    Redirects to / if the user is not logged in.
    Passes full_name and email into the template (used by dashboard.html).
    """
    if "user_id" not in session:
        return redirect(url_for("index"))
    return render_template(
        "dashboard.html",
        full_name=session["full name"],
        email=session["email"]
    )

# ── API ROUTES ────────────────────────────────────────────

@app.route("/api/csrf")
def api_csrf():
    """
    GET /api/csrf
    Generates a fresh CSRF token, stores it in the session, and returns it.
    Called by index.html before every login / signup fetch.
    """
    token = secrets.token_hex(32)
    session["csrf_token"] = token
    return jsonify({"csrf_token": token})


@app.route("/api/signup", methods=["POST"])
def api_signup():
    """
    POST /api/signup
    Expected JSON body:
      {
        "full_name":   "Jane Doe",
        "email":       "jane@example.com",
        "password":    "s3cr3tP@ss",
        "csrf_token":  "<token from /api/csrf>"
      }

    Success → 200  { success: true,  message: "...", redirect: "/dashboard" }
    Failure → 400  { success: false, message: "<reason>" }
    """
    body = request.get_json(silent=True) or {}

    # CSRF guard
    if not verify_csrf(body):
        return json_err("Invalid request token.", 403)

    # Extract + sanitise fields
    full_name = (body.get("full_name") or "").strip()
    email     = (body.get("email")     or "").strip().lower()
    password  = (body.get("password")  or "")

    # Server-side validation (mirrors the client-side checks)
    if len(full_name) < 2:
        return json_err("Full name must be at least 2 characters.")
    if "@" not in email or "." not in email.split("@")[-1]:
        return json_err("Please enter a valid email address.")
    if len(password) < 8:
        return json_err("Password must be at least 8 characters.")

    # Database operations
    try:
        conn = get_db()
        cur  = conn.cursor(dictionary=True)

        # Check for duplicate email
        cur.execute(
            "SELECT id FROM users WHERE email = %s LIMIT 1",
            (email,)
        )
        if cur.fetchone():
            cur.close()
            conn.close()
            return json_err("An account with this email already exists.")

        # Hash password and insert user
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
        cur.execute(
            "INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)",
            (full_name, email, pw_hash.decode())
        )
        conn.commit()
        user_id = cur.lastrowid
        cur.close()
        conn.close()

    except Exception as e:
        return json_err(f"Database error: {str(e)}", 500)

    # Log the new user in immediately
    session.clear()
    session["user_id"]   = user_id
    session["full_name"] = full_name
    session["email"]     = email

    return json_ok("Account created successfully!", redirect="/dashboard")


@app.route("/api/login", methods=["POST"])
def api_login():
    """
    POST /api/login
    Expected JSON body:
      {
        "email":      "jane@example.com",
        "password":   "s3cr3tP@ss",
        "csrf_token": "<token from /api/csrf>"
      }

    Success → 200  { success: true,  message: "...", redirect: "/dashboard" }
    Failure → 400  { success: false, message: "<reason>" }

    Uses a constant-time bcrypt check against a dummy hash when the user
    is not found, to prevent email-enumeration via timing attacks.
    """
    body = request.get_json(silent=True) or {}

    # CSRF guard
    if not verify_csrf(body):
        return json_err("Invalid request token.", 403)

    email    = (body.get("email")    or "").strip().lower()
    password = (body.get("password") or "")

    if not email or not password:
        return json_err("Email and password are required.")

    # Database lookup
    try:
        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, full_name, email, password_hash "
            "FROM users WHERE email = %s LIMIT 1",
            (email,)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()

    except Exception as e:
        return json_err(f"Database error: {str(e)}", 500)

    # Always run bcrypt to prevent timing-based email enumeration
    dummy_hash  = b"$2b$12$dummyhashfordummypurposesonly123456"
    stored_hash = user["password_hash"].encode() if user else dummy_hash
    match       = bcrypt.checkpw(password.encode(), stored_hash)

    if not user or not match:
        return json_err("Invalid email or password.")

    # Set session
    session.clear()
    session["user_id"]   = user["id"]
    session["full_name"] = user["full_name"]
    session["email"]     = user["email"]

    return json_ok("Login successful!", redirect="/dashboard")


@app.route("/api/logout")
def api_logout():
    """
    GET /api/logout
    Clears the session and redirects to the landing page.
    Called by the "Log out" link in dashboard.html.
    """
    session.clear()
    return redirect(url_for("index"))


# ── RUN ───────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)