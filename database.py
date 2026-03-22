"""
QuarterCharts – Database Layer
===============================
Multi-tenant PostgreSQL database for user management, company data,
and role-based access control.

Security:
- All queries use parameterized statements (no string interpolation)
- Per-company data isolation via company_id foreign keys
- Connection pooling for performance
- Encrypted connections (sslmode=require in production)

Schema:
- users: Firebase UID linked accounts
- companies: B2B client companies
- company_members: Maps users → companies with roles
- audit_log: Tracks all data access for compliance

Environment:
- DATABASE_URL: PostgreSQL connection string
  e.g., postgresql://user:pass@host:5432/quartercharts?sslmode=require
"""

import os
import logging
from datetime import datetime, timezone
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# ─── Database Connection ─────────────────────────────────────────────────────

_pool = None

def _get_connection_string() -> str | None:
    """Get database URL from environment."""
    return os.getenv("DATABASE_URL")


def _get_pool():
    """Get or create a connection pool (singleton)."""
    global _pool
    if _pool is not None:
        return _pool

    db_url = _get_connection_string()
    if not db_url:
        logger.warning("DATABASE_URL not set. Database features disabled.")
        return None

    try:
        import psycopg2
        from psycopg2 import pool as pg_pool

        _pool = pg_pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=db_url,
        )
        logger.info("Database connection pool created.")
        return _pool

    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None


@contextmanager
def get_connection():
    """Context manager for database connections with auto-commit/rollback."""
    pool = _get_pool()
    if pool is None:
        yield None
        return

    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def is_db_ready() -> bool:
    """Check if the database is configured and reachable."""
    return _get_pool() is not None


# ─── Schema Creation ─────────────────────────────────────────────────────────

def initialize_schema():
    """
    Create all tables if they don't exist.
    Safe to call on every app startup (idempotent).
    """
    if not is_db_ready():
        logger.warning("Skipping schema init — no database configured.")
        return False

    schema_sql = """
    -- Users table: links Firebase UID to app-level user data
    CREATE TABLE IF NOT EXISTS users (
        id              SERIAL PRIMARY KEY,
        firebase_uid    VARCHAR(128) UNIQUE NOT NULL,
        email           VARCHAR(255) UNIQUE NOT NULL,
        display_name    VARCHAR(255) DEFAULT '',
        avatar_url      VARCHAR(512) DEFAULT '',
        is_active       BOOLEAN DEFAULT TRUE,
        created_at      TIMESTAMPTZ DEFAULT NOW(),
        updated_at      TIMESTAMPTZ DEFAULT NOW(),
        last_login_at   TIMESTAMPTZ
    );

    -- Companies table: B2B client organizations
    CREATE TABLE IF NOT EXISTS companies (
        id              SERIAL PRIMARY KEY,
        name            VARCHAR(255) NOT NULL,
        ruc             VARCHAR(20) UNIQUE,          -- Ecuador tax ID (RUC)
        ein             VARCHAR(20),                  -- US tax ID (EIN)
        industry        VARCHAR(100) DEFAULT '',
        country         VARCHAR(2) DEFAULT 'EC',      -- ISO 3166-1 alpha-2
        plan            VARCHAR(50) DEFAULT 'free',   -- free, basic, pro, enterprise
        is_active       BOOLEAN DEFAULT TRUE,
        created_at      TIMESTAMPTZ DEFAULT NOW(),
        updated_at      TIMESTAMPTZ DEFAULT NOW()
    );

    -- Company members: maps users to companies with roles
    CREATE TABLE IF NOT EXISTS company_members (
        id              SERIAL PRIMARY KEY,
        user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
        role            VARCHAR(50) NOT NULL DEFAULT 'viewer',
        -- Roles: owner, admin, analyst, accountant, viewer
        invited_by      INTEGER REFERENCES users(id),
        is_active       BOOLEAN DEFAULT TRUE,
        created_at      TIMESTAMPTZ DEFAULT NOW(),
        updated_at      TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(user_id, company_id)
    );

    -- Audit log: tracks all sensitive operations (ISO 27001 requirement)
    CREATE TABLE IF NOT EXISTS audit_log (
        id              SERIAL PRIMARY KEY,
        user_id         INTEGER REFERENCES users(id),
        company_id      INTEGER REFERENCES companies(id),
        action          VARCHAR(100) NOT NULL,
        -- e.g., "login", "view_invoices", "export_data", "invite_user"
        resource_type   VARCHAR(100) DEFAULT '',
        resource_id     VARCHAR(255) DEFAULT '',
        ip_address      VARCHAR(45) DEFAULT '',
        details         TEXT DEFAULT '',
        created_at      TIMESTAMPTZ DEFAULT NOW()
    );

    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_users_firebase_uid ON users(firebase_uid);
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    CREATE INDEX IF NOT EXISTS idx_company_members_user ON company_members(user_id);
    CREATE INDEX IF NOT EXISTS idx_company_members_company ON company_members(company_id);
    CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
    CREATE INDEX IF NOT EXISTS idx_audit_log_company ON audit_log(company_id);
    CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at);
    """

    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        logger.info("Database schema initialized.")
        return True


# ─── User Operations ─────────────────────────────────────────────────────────

def create_or_update_user(firebase_uid: str, email: str, display_name: str = "") -> dict | None:
    """
    Create a user record or update if already exists.
    Called after every successful Firebase login.
    Returns the user dict.
    """
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (firebase_uid, email, display_name, last_login_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (firebase_uid) DO UPDATE SET
                    email = EXCLUDED.email,
                    display_name = EXCLUDED.display_name,
                    last_login_at = NOW(),
                    updated_at = NOW()
                RETURNING id, firebase_uid, email, display_name, is_active, created_at
            """, (firebase_uid, email, display_name))
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "firebase_uid": row[1],
                    "email": row[2],
                    "display_name": row[3],
                    "is_active": row[4],
                    "created_at": row[5],
                }
    return None


def get_user_by_firebase_uid(firebase_uid: str) -> dict | None:
    """Look up a user by their Firebase UID."""
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, firebase_uid, email, display_name, is_active, created_at
                FROM users WHERE firebase_uid = %s
            """, (firebase_uid,))
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "firebase_uid": row[1],
                    "email": row[2],
                    "display_name": row[3],
                    "is_active": row[4],
                    "created_at": row[5],
                }
    return None


# ─── Company Operations ──────────────────────────────────────────────────────

def create_company(name: str, ruc: str = None, country: str = "EC",
                   owner_user_id: int = None) -> dict | None:
    """
    Create a new company and optionally assign an owner.
    """
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO companies (name, ruc, country)
                VALUES (%s, %s, %s)
                RETURNING id, name, ruc, country, plan, created_at
            """, (name, ruc, country))
            row = cur.fetchone()
            if row and owner_user_id:
                company_id = row[0]
                cur.execute("""
                    INSERT INTO company_members (user_id, company_id, role)
                    VALUES (%s, %s, 'owner')
                """, (owner_user_id, company_id))
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "ruc": row[2],
                    "country": row[3],
                    "plan": row[4],
                    "created_at": row[5],
                }
    return None


def get_user_companies(user_id: int) -> list:
    """Get all companies a user belongs to, with their role in each."""
    with get_connection() as conn:
        if conn is None:
            return []
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.name, c.ruc, c.country, c.plan,
                       cm.role, cm.is_active
                FROM companies c
                JOIN company_members cm ON cm.company_id = c.id
                WHERE cm.user_id = %s AND cm.is_active = TRUE AND c.is_active = TRUE
                ORDER BY c.name
            """, (user_id,))
            rows = cur.fetchall()
            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "ruc": row[2],
                    "country": row[3],
                    "plan": row[4],
                    "role": row[5],
                    "is_active": row[6],
                }
                for row in rows
            ]


def get_company_members(company_id: int) -> list:
    """Get all members of a company with their roles."""
    with get_connection() as conn:
        if conn is None:
            return []
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.email, u.display_name, cm.role, cm.created_at
                FROM users u
                JOIN company_members cm ON cm.user_id = u.id
                WHERE cm.company_id = %s AND cm.is_active = TRUE
                ORDER BY cm.role, u.display_name
            """, (company_id,))
            rows = cur.fetchall()
            return [
                {
                    "user_id": row[0],
                    "email": row[1],
                    "display_name": row[2],
                    "role": row[3],
                    "joined_at": row[4],
                }
                for row in rows
            ]


def add_company_member(company_id: int, user_id: int, role: str = "viewer",
                       invited_by: int = None) -> bool:
    """Add a user to a company with a specific role."""
    valid_roles = {"owner", "admin", "analyst", "accountant", "viewer"}
    if role not in valid_roles:
        logger.error(f"Invalid role: {role}")
        return False

    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO company_members (user_id, company_id, role, invited_by)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, company_id) DO UPDATE SET
                        role = EXCLUDED.role,
                        is_active = TRUE,
                        updated_at = NOW()
                """, (user_id, company_id, role, invited_by))
                return True
            except Exception as e:
                logger.error(f"Add member error: {e}")
                return False


def remove_company_member(company_id: int, user_id: int) -> bool:
    """Soft-remove a user from a company."""
    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE company_members
                SET is_active = FALSE, updated_at = NOW()
                WHERE company_id = %s AND user_id = %s
            """, (company_id, user_id))
            return cur.rowcount > 0


# ─── Audit Logging (ISO 27001 Compliance) ────────────────────────────────────

def log_action(user_id: int, action: str, company_id: int = None,
               resource_type: str = "", resource_id: str = "",
               ip_address: str = "", details: str = ""):
    """
    Record an auditable action.
    Call this for: logins, data views, exports, permission changes, etc.
    """
    with get_connection() as conn:
        if conn is None:
            return
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO audit_log
                    (user_id, company_id, action, resource_type, resource_id,
                     ip_address, details)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, company_id, action, resource_type, resource_id,
                  ip_address, details))
