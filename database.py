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
    -- Users table: supports email/password and Google sign-in with account linking
    CREATE TABLE IF NOT EXISTS users (
        id              SERIAL PRIMARY KEY,
        email           VARCHAR(255) UNIQUE NOT NULL,
        display_name    VARCHAR(255) DEFAULT '',
        avatar_url      VARCHAR(512) DEFAULT '',
        password_hash   VARCHAR(255),               -- bcrypt hash (NULL if Google-only)
        google_id       VARCHAR(255) UNIQUE,         -- Google sub claim (NULL if email-only)
        auth_provider   VARCHAR(50) DEFAULT 'email', -- email, google, both
        firebase_uid    VARCHAR(128) UNIQUE,          -- legacy, nullable
        is_active       BOOLEAN DEFAULT TRUE,
        login_count     INTEGER DEFAULT 0,
        created_at      TIMESTAMPTZ DEFAULT NOW(),
        updated_at      TIMESTAMPTZ DEFAULT NOW(),
        last_login_at   TIMESTAMPTZ
    );

    -- ── Migration: add new columns to existing users table ──
    -- These are safe to run repeatedly (IF NOT EXISTS / OR REPLACE).
    DO $$
    BEGIN
        -- Add password_hash if missing
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_name = 'users' AND column_name = 'password_hash') THEN
            ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);
        END IF;

        -- Add google_id if missing
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_name = 'users' AND column_name = 'google_id') THEN
            ALTER TABLE users ADD COLUMN google_id VARCHAR(255) UNIQUE;
        END IF;

        -- Add auth_provider if missing
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_name = 'users' AND column_name = 'auth_provider') THEN
            ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'email';
        END IF;

        -- Add avatar_url if missing
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_name = 'users' AND column_name = 'avatar_url') THEN
            ALTER TABLE users ADD COLUMN avatar_url VARCHAR(512) DEFAULT '';
        END IF;

        -- Add display_name if missing
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_name = 'users' AND column_name = 'display_name') THEN
            ALTER TABLE users ADD COLUMN display_name VARCHAR(255) DEFAULT '';
        END IF;

        -- Add last_login_at if missing
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_name = 'users' AND column_name = 'last_login_at') THEN
            ALTER TABLE users ADD COLUMN last_login_at TIMESTAMPTZ;
        END IF;

        -- Add updated_at if missing
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_name = 'users' AND column_name = 'updated_at') THEN
            ALTER TABLE users ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
        END IF;

        -- Add login_count if missing
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_name = 'users' AND column_name = 'login_count') THEN
            ALTER TABLE users ADD COLUMN login_count INTEGER DEFAULT 0;
        END IF;

        -- Make firebase_uid nullable (was NOT NULL in old schema)
        ALTER TABLE users ALTER COLUMN firebase_uid DROP NOT NULL;
    EXCEPTION WHEN others THEN
        NULL;  -- Ignore errors (e.g., column already nullable)
    END $$;

    -- Server-side sessions: persist login across Streamlit page reloads
    CREATE TABLE IF NOT EXISTS sessions (
        token           VARCHAR(128) PRIMARY KEY,
        user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at      TIMESTAMPTZ DEFAULT NOW(),
        expires_at      TIMESTAMPTZ NOT NULL
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

    -- Pricing plans: admin-managed, drives the public pricing page and Stripe integration
    CREATE TABLE IF NOT EXISTS pricing_plans (
        id              SERIAL PRIMARY KEY,
        slug            VARCHAR(50) UNIQUE NOT NULL,       -- e.g. "free", "pro", "enterprise"
        name            VARCHAR(100) NOT NULL,             -- Display name: "Free", "Pro", "Enterprise"
        description     VARCHAR(255) DEFAULT '',           -- Subtitle shown on card
        price_monthly   NUMERIC(10,2) DEFAULT 0,           -- Monthly price in USD
        price_annual    NUMERIC(10,2) DEFAULT 0,           -- Annual price per month in USD
        features        TEXT DEFAULT '[]',                  -- JSON array of feature strings
        cta_text        VARCHAR(100) DEFAULT 'Get Started', -- Button label
        cta_url         VARCHAR(255) DEFAULT '',            -- Custom URL (optional override)
        is_popular      BOOLEAN DEFAULT FALSE,              -- Show "Most Popular" badge
        is_active       BOOLEAN DEFAULT TRUE,               -- Hide plan without deleting
        sort_order      INTEGER DEFAULT 0,                  -- Display order (low = left)
        stripe_product_id   VARCHAR(255) DEFAULT '',        -- Stripe Product ID
        stripe_price_monthly VARCHAR(255) DEFAULT '',       -- Stripe Price ID (monthly)
        stripe_price_annual  VARCHAR(255) DEFAULT '',       -- Stripe Price ID (annual)
        allowed_tickers TEXT DEFAULT 'ALL',                 -- "ALL" or comma-separated tickers e.g. "AAPL,TSLA,NVDA"
        redirect_allowed  VARCHAR(50) DEFAULT 'charts',   -- page to go when ticker IS allowed
        redirect_blocked  VARCHAR(50) DEFAULT 'pricing',  -- page to go when ticker NOT allowed
        created_at      TIMESTAMPTZ DEFAULT NOW(),
        updated_at      TIMESTAMPTZ DEFAULT NOW()
    );

    -- Subscriptions: tracks which user is on which plan via Stripe
    CREATE TABLE IF NOT EXISTS subscriptions (
        id              SERIAL PRIMARY KEY,
        user_id         INTEGER REFERENCES users(id) NOT NULL,
        plan_id         INTEGER REFERENCES pricing_plans(id),
        stripe_customer_id      VARCHAR(255) DEFAULT '',
        stripe_subscription_id  VARCHAR(255) DEFAULT '',
        status          VARCHAR(50) DEFAULT 'active',      -- active, canceled, past_due, trialing
        billing_cycle   VARCHAR(20) DEFAULT 'monthly',     -- monthly, annual
        current_period_start TIMESTAMPTZ,
        current_period_end   TIMESTAMPTZ,
        created_at      TIMESTAMPTZ DEFAULT NOW(),
        updated_at      TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS app_config (
        key             VARCHAR(255) PRIMARY KEY,
        value           TEXT NOT NULL,
        updated_at      TIMESTAMPTZ DEFAULT NOW()
    );

    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    CREATE INDEX IF NOT EXISTS idx_pricing_plans_slug ON pricing_plans(slug);
    CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
    CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe ON subscriptions(stripe_subscription_id);
    CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
    CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
    CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
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

def _row_to_user(row) -> dict:
    """Convert a user row tuple to dict."""
    return {
        "id": row[0], "email": row[1], "display_name": row[2],
        "avatar_url": row[3], "password_hash": row[4], "google_id": row[5],
        "auth_provider": row[6], "is_active": row[7], "created_at": row[8],
    }

_USER_COLS = "id, email, display_name, avatar_url, password_hash, google_id, auth_provider, is_active, created_at"


def get_user_by_email(email: str) -> dict | None:
    """Look up a user by email."""
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_USER_COLS} FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
            return _row_to_user(row) if row else None


def get_user_by_google_id(google_id: str) -> dict | None:
    """Look up a user by their Google sub claim."""
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_USER_COLS} FROM users WHERE google_id = %s", (google_id,))
            row = cur.fetchone()
            return _row_to_user(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    """Look up a user by primary key."""
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_USER_COLS} FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return _row_to_user(row) if row else None


def create_user_email(email: str, password_hash: str, display_name: str = "") -> dict | None:
    """Create a new user with email + hashed password."""
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO users (email, password_hash, display_name, auth_provider, last_login_at)
                VALUES (%s, %s, %s, 'email', NOW())
                RETURNING {_USER_COLS}
            """, (email, password_hash, display_name))
            row = cur.fetchone()
            return _row_to_user(row) if row else None


def create_user_google(email: str, google_id: str, display_name: str = "",
                       avatar_url: str = "") -> dict | None:
    """Create a new user from Google sign-in."""
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO users (email, google_id, display_name, avatar_url,
                                   auth_provider, last_login_at)
                VALUES (%s, %s, %s, %s, 'google', NOW())
                RETURNING {_USER_COLS}
            """, (email, google_id, display_name, avatar_url))
            row = cur.fetchone()
            return _row_to_user(row) if row else None


def link_google_to_user(user_id: int, google_id: str, avatar_url: str = "") -> bool:
    """Link a Google account to an existing email user."""
    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users SET google_id = %s, auth_provider = 'both',
                    avatar_url = CASE WHEN avatar_url = '' THEN %s ELSE avatar_url END,
                    updated_at = NOW()
                WHERE id = %s
            """, (google_id, avatar_url, user_id))
            return cur.rowcount > 0


def link_password_to_user(user_id: int, password_hash: str) -> bool:
    """Add a password to a Google-only user (account linking)."""
    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users SET password_hash = %s, auth_provider = 'both',
                    updated_at = NOW()
                WHERE id = %s
            """, (password_hash, user_id))
            return cur.rowcount > 0


def update_last_login(user_id: int):
    """Update last_login_at timestamp."""
    with get_connection() as conn:
        if conn is None:
            return
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET last_login_at = NOW(), login_count = COALESCE(login_count, 0) + 1 WHERE id = %s", (user_id,))


def update_user_display_name(user_id: int, display_name: str) -> bool:
    """Update user display name."""
    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET display_name = %s, updated_at = NOW() WHERE id = %s",
                        (display_name, user_id))
            return cur.rowcount > 0


def update_user_password(user_id: int, password_hash: str) -> bool:
    """Update user password hash."""
    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s",
                        (password_hash, user_id))
            return cur.rowcount > 0


# ─── Session Operations ─────────────────────────────────────────────────────

def create_session(token: str, user_id: int, expires_at) -> bool:
    """Store a new session token in the DB."""
    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sessions (token, user_id, expires_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (token) DO UPDATE SET user_id = EXCLUDED.user_id,
                    expires_at = EXCLUDED.expires_at, created_at = NOW()
            """, (token, user_id, expires_at))
            return True


def get_session(token: str) -> dict | None:
    """Look up a session by token. Returns None if expired."""
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute("""
                SELECT token, user_id, created_at, expires_at
                FROM sessions WHERE token = %s AND expires_at > NOW()
            """, (token,))
            row = cur.fetchone()
            if row:
                return {"token": row[0], "user_id": row[1],
                        "created_at": row[2], "expires_at": row[3]}
    return None


def delete_session(token: str):
    """Delete a session (logout)."""
    with get_connection() as conn:
        if conn is None:
            return
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE token = %s", (token,))


def cleanup_expired_sessions():
    """Remove all expired sessions."""
    with get_connection() as conn:
        if conn is None:
            return
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE expires_at < NOW()")


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


# ─── Pricing Plans CRUD ──────────────────────────────────────────────────────

_PLAN_COLS = ("id, slug, name, description, price_monthly, price_annual, features, "
              "cta_text, cta_url, is_popular, is_active, sort_order, "
              "stripe_product_id, stripe_price_monthly, stripe_price_annual, "
              "allowed_tickers, redirect_allowed, redirect_blocked, "
              "blocked_charts, "
              "created_at, updated_at")


def _row_to_plan(row) -> dict:
    """Convert a pricing_plans row to dict."""
    import json
    features_raw = row[6] or "[]"
    try:
        features = json.loads(features_raw) if isinstance(features_raw, str) else features_raw
    except (json.JSONDecodeError, TypeError):
        features = []
    return {
        "id": row[0], "slug": row[1], "name": row[2], "description": row[3],
        "price_monthly": float(row[4] or 0), "price_annual": float(row[5] or 0),
        "features": features, "cta_text": row[7] or "Get Started",
        "cta_url": row[8] or "", "is_popular": row[9], "is_active": row[10],
        "sort_order": row[11] or 0,
        "stripe_product_id": row[12] or "", "stripe_price_monthly": row[13] or "",
        "stripe_price_annual": row[14] or "",
        "allowed_tickers": row[15] or "ALL",
        "redirect_allowed": row[16] or "charts",
        "redirect_blocked": row[17] or "pricing",
        "blocked_charts": row[18] or "",
        "created_at": row[19], "updated_at": row[20],
    }


def get_all_plans(active_only: bool = False) -> list[dict]:
    """Get all pricing plans, ordered by sort_order."""
    with get_connection() as conn:
        if conn is None:
            return []
        with conn.cursor() as cur:
            sql = f"SELECT {_PLAN_COLS} FROM pricing_plans"
            if active_only:
                sql += " WHERE is_active = TRUE"
            sql += " ORDER BY sort_order, id"
            cur.execute(sql)
            return [_row_to_plan(r) for r in cur.fetchall()]


def get_plan_by_id(plan_id: int) -> dict | None:
    """Get a single plan by ID."""
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PLAN_COLS} FROM pricing_plans WHERE id = %s", (plan_id,))
            row = cur.fetchone()
            return _row_to_plan(row) if row else None


def get_plan_by_slug(slug: str) -> dict | None:
    """Get a single plan by slug."""
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PLAN_COLS} FROM pricing_plans WHERE slug = %s", (slug,))
            row = cur.fetchone()
            return _row_to_plan(row) if row else None


def create_plan(slug: str, name: str, description: str = "",
                price_monthly: float = 0, price_annual: float = 0,
                features: list = None, cta_text: str = "Get Started",
                cta_url: str = "", is_popular: bool = False,
                is_active: bool = True, sort_order: int = 0,
                stripe_product_id: str = "", stripe_price_monthly: str = "",
                stripe_price_annual: str = "",
                allowed_tickers: str = "ALL",
                redirect_allowed: str = "charts",
                redirect_blocked: str = "pricing") -> dict | None:
    """Create a new pricing plan."""
    import json
    features_json = json.dumps(features or [])
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO pricing_plans
                    (slug, name, description, price_monthly, price_annual, features,
                     cta_text, cta_url, is_popular, is_active, sort_order,
                     stripe_product_id, stripe_price_monthly, stripe_price_annual,
                     allowed_tickers, redirect_allowed, redirect_blocked)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING {_PLAN_COLS}
            """, (slug, name, description, price_monthly, price_annual, features_json,
                  cta_text, cta_url, is_popular, is_active, sort_order,
                  stripe_product_id, stripe_price_monthly, stripe_price_annual,
                  allowed_tickers, redirect_allowed, redirect_blocked))
            row = cur.fetchone()
            return _row_to_plan(row) if row else None


def update_plan(plan_id: int, **kwargs) -> dict | None:
    """Update a pricing plan. Pass only the fields you want to change."""
    import json
    allowed = {"slug", "name", "description", "price_monthly", "price_annual",
               "features", "cta_text", "cta_url", "is_popular", "is_active",
               "sort_order", "stripe_product_id", "stripe_price_monthly",
               "stripe_price_annual", "allowed_tickers",
               "redirect_allowed", "redirect_blocked", "blocked_charts"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return get_plan_by_id(plan_id)
    if "features" in updates and isinstance(updates["features"], list):
        updates["features"] = json.dumps(updates["features"])
    set_parts = [f"{k} = %s" for k in updates]
    set_parts.append("updated_at = NOW()")
    values = list(updates.values()) + [plan_id]
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute(f"""
                UPDATE pricing_plans SET {', '.join(set_parts)}
                WHERE id = %s RETURNING {_PLAN_COLS}
            """, values)
            row = cur.fetchone()
            return _row_to_plan(row) if row else None


def delete_plan(plan_id: int) -> bool:
    """Permanently delete a pricing plan."""
    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pricing_plans WHERE id = %s", (plan_id,))
            return cur.rowcount > 0


def seed_default_plans():
    """Insert default plans if the table is empty. Safe to call on every startup."""
    existing = get_all_plans()
    if existing:
        return
    defaults = [
        {"slug": "no-login", "name": "No Login", "description": "Browse without an account",
         "price_monthly": 0, "price_annual": 0, "sort_order": 0,
         "features": ["3 ticker lookups per day", "Income statement Sankey (view only)",
                       "Basic company profile", "Earnings calendar", "Limited chart access"],
         "cta_text": "Create Free Account", "cta_url": "?page=login", "is_popular": False,
         "allowed_tickers": "AAPL,TSLA,NVDA,MSFT,AMZN,GOOG,META"},
        {"slug": "free", "name": "Free", "description": "Perfect for exploring financial data",
         "price_monthly": 0, "price_annual": 0, "sort_order": 1,
         "features": ["5 ticker lookups per day", "Income statement Sankey",
                       "Basic financial charts", "Company profile page", "Community support"],
         "cta_text": "Get Started Free", "is_popular": False,
         "allowed_tickers": "AAPL,TSLA,NVDA,MSFT,AMZN,GOOG,META"},
        {"slug": "pro", "name": "Pro", "description": "For serious investors & analysts",
         "price_monthly": 15, "price_annual": 12, "sort_order": 2,
         "features": ["Unlimited ticker lookups", "Income + Balance Sankey",
                       "All financial charts", "Quarterly & Annual data",
                       "Historical trends (1Y\u20134Y+MAX)", "Analyst forecast overlay",
                       "PDF export", "Watchlist (unlimited tickers)", "Priority support"],
         "cta_text": "Start Free Trial", "is_popular": True,
         "allowed_tickers": "ALL"},
        {"slug": "enterprise", "name": "Enterprise", "description": "For teams & organizations",
         "price_monthly": 49, "price_annual": 39, "sort_order": 3,
         "features": ["Everything in Pro", "API access", "Custom data integrations",
                       "Team workspaces (up to 25)", "White-label embedding",
                       "SSO / SAML authentication", "Dedicated account manager", "Custom SLA"],
         "cta_text": "Contact Sales", "is_popular": False,
         "allowed_tickers": "ALL"},
    ]
    for p in defaults:
        create_plan(**p)


def ensure_no_login_plan():
    """Ensure the 'No Login' plan exists (safe to call on every startup)."""
    if not get_plan_by_slug("no-login"):
        create_plan(
            slug="no-login", name="No Login",
            description="Browse without an account",
            price_monthly=0, price_annual=0, sort_order=0,
            features=["3 ticker lookups per day", "Income statement Sankey (view only)",
                       "Basic company profile", "Earnings calendar", "Limited chart access"],
            cta_text="Create Free Account", cta_url="?page=login", is_popular=False,
            allowed_tickers="AAPL,TSLA,NVDA,MSFT,AMZN,GOOG,META",
        )


def ensure_pricing_plan_columns():
    """Add new columns to pricing_plans if they don't exist (safe migration)."""
    _cols = [
        ("allowed_tickers", "TEXT DEFAULT 'ALL'"),
        ("redirect_allowed", "VARCHAR(50) DEFAULT 'charts'"),
        ("redirect_blocked", "VARCHAR(50) DEFAULT 'pricing'"),
        ("blocked_charts", "TEXT DEFAULT ''"),
    ]
    with get_connection() as conn:
        if conn is None:
            return
        with conn.cursor() as cur:
            for col_name, col_def in _cols:
                cur.execute("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'pricing_plans' AND column_name = %s
                """, (col_name,))
                if not cur.fetchone():
                    cur.execute(f"ALTER TABLE pricing_plans ADD COLUMN {col_name} {col_def}")


def _parse_blocked_charts(raw: str) -> set:
    """Parse blocked_charts string into a set of chart keys."""
    if not raw or not raw.strip():
        return set()
    return {c.strip() for c in raw.split(",") if c.strip()}


def get_user_plan_access(user_id: int | None = None) -> dict:
    """Return ticker access info for a user based on their plan.

    Returns dict with keys:
        allowed_tickers: set | None  (None = ALL tickers)
        redirect_allowed: str  (page slug when ticker IS allowed)
        redirect_blocked: str  (page slug when ticker NOT allowed)
        blocked_charts: set   (set of chart keys that are blocked)
    """
    _default = {"allowed_tickers": {"AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOG", "META"},
                "redirect_allowed": "charts", "redirect_blocked": "pricing",
                "blocked_charts": set()}

    if user_id is None:
        # Only consider ACTIVE plans for non-logged-in users
        _nologin = get_plan_by_slug("no-login")
        if _nologin and _nologin.get("is_active"):
            plan = _nologin
        else:
            _free = get_plan_by_slug("free")
            plan = _free if (_free and _free.get("is_active")) else None
    else:
        plan = None
        with get_connection() as conn:
            if conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT pp.allowed_tickers, pp.redirect_allowed,
                               pp.redirect_blocked, pp.blocked_charts
                        FROM subscriptions s
                        JOIN pricing_plans pp ON pp.id = s.plan_id
                        WHERE s.user_id = %s AND s.status IN ('active', 'trialing')
                        ORDER BY pp.sort_order DESC LIMIT 1
                    """, (user_id,))
                    row = cur.fetchone()
                    if row:
                        tickers_str = row[0] or "ALL"
                        r_allowed = row[1] or "charts"
                        r_blocked = row[2] or "pricing"
                        b_charts = _parse_blocked_charts(row[3] or "")
                        if tickers_str.strip().upper() == "ALL":
                            return {"allowed_tickers": None,
                                    "redirect_allowed": r_allowed,
                                    "redirect_blocked": r_blocked,
                                    "blocked_charts": b_charts}
                        return {"allowed_tickers": {t.strip().upper() for t in tickers_str.split(",") if t.strip()},
                                "redirect_allowed": r_allowed,
                                "redirect_blocked": r_blocked,
                                "blocked_charts": b_charts}
        _free = get_plan_by_slug("free")
        plan = _free if (_free and _free.get("is_active")) else None

    if plan is None:
        return _default

    tickers_str = plan.get("allowed_tickers", "ALL")
    r_allowed = plan.get("redirect_allowed", "charts")
    r_blocked = plan.get("redirect_blocked", "pricing")
    b_charts = _parse_blocked_charts(plan.get("blocked_charts", ""))
    if tickers_str.strip().upper() == "ALL":
        return {"allowed_tickers": None, "redirect_allowed": r_allowed,
                "redirect_blocked": r_blocked, "blocked_charts": b_charts}
    return {"allowed_tickers": {t.strip().upper() for t in tickers_str.split(",") if t.strip()},
            "redirect_allowed": r_allowed, "redirect_blocked": r_blocked,
            "blocked_charts": b_charts}


def get_allowed_tickers_for_user(user_id: int | None = None) -> set | None:
    """Convenience wrapper: returns just the allowed tickers set (None = ALL)."""
    return get_user_plan_access(user_id)["allowed_tickers"]


# ─── Admin: User management ──────────────────────────────────────────────

def get_all_users_admin() -> list[dict]:
    """Get all users with their subscription/plan info for the admin dashboard."""
    with get_connection() as conn:
        if conn is None:
            return []
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.email, u.display_name, u.avatar_url,
                       u.auth_provider, u.is_active, u.login_count,
                       u.created_at, u.last_login_at,
                       pp.name AS plan_name, pp.slug AS plan_slug,
                       s.status AS sub_status, s.billing_cycle,
                       s.current_period_end
                FROM users u
                LEFT JOIN subscriptions s ON s.user_id = u.id
                    AND s.status IN ('active', 'trialing')
                LEFT JOIN pricing_plans pp ON pp.id = s.plan_id
                ORDER BY u.last_login_at DESC NULLS LAST, u.created_at DESC
            """)
            rows = cur.fetchall()
            return [{
                "id": r[0], "email": r[1], "display_name": r[2] or "",
                "avatar_url": r[3] or "", "auth_provider": r[4] or "email",
                "is_active": r[5], "login_count": r[6] or 0,
                "created_at": r[7], "last_login_at": r[8],
                "plan_name": r[9] or "Free", "plan_slug": r[10] or "free",
                "sub_status": r[11] or "none", "billing_cycle": r[12] or "",
                "period_end": r[13],
            } for r in rows]


def assign_user_plan(user_id: int, plan_slug: str) -> bool:
    """Assign a plan to a user (admin override). Creates or updates subscription."""
    plan = get_plan_by_slug(plan_slug)
    if not plan:
        return False
    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            # Check for existing subscription
            cur.execute("SELECT id FROM subscriptions WHERE user_id = %s", (user_id,))
            existing = cur.fetchone()
            if existing:
                cur.execute("""
                    UPDATE subscriptions SET plan_id = %s, status = 'active',
                        billing_cycle = 'admin', updated_at = NOW(),
                        current_period_start = NOW(),
                        current_period_end = NOW() + INTERVAL '100 years'
                    WHERE user_id = %s
                """, (plan["id"], user_id))
            else:
                cur.execute("""
                    INSERT INTO subscriptions
                        (user_id, plan_id, status, billing_cycle,
                         current_period_start, current_period_end)
                    VALUES (%s, %s, 'active', 'admin', NOW(), NOW() + INTERVAL '100 years')
                """, (user_id, plan["id"]))
            return True


def toggle_user_active(user_id: int, is_active: bool) -> bool:
    """Enable or disable a user account."""
    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET is_active = %s, updated_at = NOW() WHERE id = %s",
                        (is_active, user_id))
            return cur.rowcount > 0


def get_user_stats() -> dict:
    """Get aggregate user statistics for the dashboard header."""
    with get_connection() as conn:
        if conn is None:
            return {"total": 0, "active_today": 0, "active_week": 0, "google_users": 0}
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE last_login_at >= NOW() - INTERVAL '1 day') AS active_today,
                    COUNT(*) FILTER (WHERE last_login_at >= NOW() - INTERVAL '7 days') AS active_week,
                    COUNT(*) FILTER (WHERE auth_provider IN ('google', 'both')) AS google_users
                FROM users
            """)
            r = cur.fetchone()
            return {"total": r[0], "active_today": r[1], "active_week": r[2], "google_users": r[3]}


# ── App Config helpers ──────────────────────────────────────────────────

_DEFAULT_TICKER_POOL = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOG", "META"]


def get_config(key: str, default: str = "") -> str:
    """Read a value from app_config table."""
    with get_connection() as conn:
        if conn is None:
            return default
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM app_config WHERE key = %s", (key,))
            row = cur.fetchone()
            return row[0] if row else default


def set_config(key: str, value: str) -> bool:
    """Write a value to app_config table (upsert)."""
    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO app_config (key, value, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
            """, (key, value))
            return True


def get_ticker_pool() -> list[str]:
    """Return the admin-managed ticker pool from DB."""
    raw = get_config("ticker_pool", "")
    if not raw.strip():
        return list(_DEFAULT_TICKER_POOL)
    return [t.strip().upper() for t in raw.split(",") if t.strip()]


def set_ticker_pool(tickers: list[str]) -> bool:
    """Persist the ticker pool to DB."""
    return set_config("ticker_pool", ",".join(sorted(t.strip().upper() for t in tickers if t.strip())))
