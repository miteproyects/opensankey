#!/usr/bin/env python3
"""
Quick diagnostic script to check database connectivity and user status.
Run from the miteproyects directory:
    python check_db.py
"""
import os
import sys

# Load .env
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.isfile(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

db_url = os.getenv("DATABASE_URL")
print(f"[1] DATABASE_URL: {'SET (' + db_url[:40] + '...)' if db_url else 'NOT SET ❌'}")

# Check psycopg2
try:
    import psycopg2
    print(f"[2] psycopg2: installed ✅ (version {psycopg2.__version__})")
except ImportError:
    print("[2] psycopg2: NOT INSTALLED ❌")
    print("    Fix: pip install psycopg2-binary")
    sys.exit(1)

# Check bcrypt
try:
    import bcrypt
    print(f"[3] bcrypt: installed ✅")
except ImportError:
    print("[3] bcrypt: NOT INSTALLED ❌")
    print("    Fix: pip install bcrypt")

# Try connecting
try:
    conn = psycopg2.connect(db_url)
    print("[4] Database connection: OK ✅")
except Exception as e:
    print(f"[4] Database connection: FAILED ❌ ({e})")
    sys.exit(1)

# Check user
cur = conn.cursor()
cur.execute("""
    SELECT id, email, display_name, password_hash IS NOT NULL as has_pw,
           google_id IS NOT NULL as has_google, auth_provider, is_active
    FROM users WHERE email = 'info@quartercharts.com'
""")
row = cur.fetchone()
if row:
    print(f"[5] User info@quartercharts.com: FOUND ✅")
    print(f"    id={row[0]}, name='{row[2]}', has_password={row[3]}, has_google={row[4]}, provider={row[5]}, active={row[6]}")
    if not row[3]:
        print("    ⚠️  No password hash — this account was created via Google only.")
        print("    → Use 'Create an account' on the login page to add a password, or use Google Sign-In.")
else:
    print("[5] User info@quartercharts.com: NOT FOUND")
    cur.execute("SELECT count(*) FROM users")
    total = cur.fetchone()[0]
    print(f"    Total users in database: {total}")
    if total > 0:
        cur.execute("SELECT email FROM users LIMIT 5")
        emails = [r[0] for r in cur.fetchall()]
        print(f"    Sample emails: {emails}")
    print("    → You need to register first via 'Create an account'")

# Check sessions table
cur.execute("SELECT count(*) FROM sessions")
sessions = cur.fetchone()[0]
print(f"[6] Active sessions: {sessions}")

conn.close()
print("\nDone! If everything is ✅, the login should work.")
