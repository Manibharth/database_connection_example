"""
check_db.py — Run this to verify your MySQL connection before starting app.py

Usage:
    python check_db.py
"""

import sys

# ── Step 1: Check mysql-connector-python is installed ─────
try:
    import mysql.connector
    print("✅  mysql-connector-python  is installed")
except ImportError:
    print("❌  mysql-connector-python  NOT found")
    print("    Fix: pip install mysql-connector-python")
    sys.exit(1)

# ── Step 2: Check bcrypt is installed ─────────────────────
try:
    import bcrypt
    print("✅  bcrypt                  is installed")
except ImportError:
    print("❌  bcrypt  NOT found")
    print("    Fix: pip install bcrypt")
    sys.exit(1)

# ── Step 3: Check flask is installed ──────────────────────
try:
    import flask
    print(f"✅  flask                   is installed  (version {flask.__version__})")
except ImportError:
    print("❌  flask  NOT found")
    print("    Fix: pip install flask")
    sys.exit(1)

# ── Step 4: Check python-dotenv ───────────────────────────
try:
    import dotenv
    print("✅  python-dotenv           is installed")
except ImportError:
    print("❌  python-dotenv  NOT found")
    print("    Fix: pip install python-dotenv")
    sys.exit(1)

print()
print("─" * 50)
print("🔌  Testing MySQL connection...")
print("─" * 50)

# ── Step 5: Try connecting to MySQL ───────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "yuan@123",   # ← your password
    "port":     3306,
}

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    print("✅  Connected to MySQL server  (host: localhost, port: 3306)")
except mysql.connector.Error as e:
    print(f"❌  Could not connect to MySQL: {e}")
    print()
    print("Common fixes:")
    print("  • Make sure MySQL / XAMPP / WAMP is running")
    print("  • Check your password is correct in check_db.py")
    print("  • Check port 3306 is not blocked")
    sys.exit(1)

# ── Step 6: Check nexora_db database exists ───────────────
cur = conn.cursor()
cur.execute("SHOW DATABASES LIKE 'nexora_db'")
if cur.fetchone():
    print("✅  Database  'nexora_db'  exists")
else:
    print("❌  Database  'nexora_db'  NOT found")
    print("    Fix: run  mysql -u root -p < setup.sql")
    cur.close(); conn.close()
    sys.exit(1)

# ── Step 7: Switch to nexora_db and check users table ─────
cur.execute("USE nexora_db")
cur.execute("SHOW TABLES LIKE 'users'")
if cur.fetchone():
    print("✅  Table     'users'      exists")
else:
    print("❌  Table     'users'      NOT found")
    print("    Fix: run  mysql -u root -p < setup.sql")
    cur.close(); conn.close()
    sys.exit(1)

# ── Step 8: Check users table columns ─────────────────────
cur.execute("DESCRIBE users")
cols = {row[0] for row in cur.fetchall()}
required = {"id", "full_name", "email", "password_hash", "created_at"}
missing  = required - cols

if missing:
    print(f"❌  Missing columns in 'users': {missing}")
    print("    Fix: drop the table and re-run setup.sql")
else:
    print("✅  Table columns          look correct")

cur.execute("SELECT COUNT(*) FROM users")
count = cur.fetchone()[0]
print(f"✅  Users in database:     {count} row(s)")

cur.close()
conn.close()

print()
print("─" * 50)
print("🎉  All checks passed! You can now run:  python app.py")
print("─" * 50)