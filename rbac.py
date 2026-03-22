"""
QuarterCharts – Role-Based Access Control (RBAC)
=================================================
Defines permissions for each role and provides decorators/guards
for protecting pages and actions.

Role Hierarchy (highest to lowest):
- owner:      Full control — billing, delete company, manage all members
- admin:      Manage members, view all data, export, configure dashboards
- analyst:    View all financial data, create charts, export reports
- accountant: View/upload invoices and financial documents only
- viewer:     Read-only access to dashboards shared with them

Security:
- Permissions are checked server-side on every request
- Role changes are audit-logged
- No client-side permission checks (all enforced in Python)
"""

import streamlit as st
import logging
from typing import Set

logger = logging.getLogger(__name__)


# ─── Permission Definitions ──────────────────────────────────────────────────

# Each permission is a string like "action:resource"
PERMISSIONS = {
    "owner": {
        "company:delete",
        "company:edit",
        "company:billing",
        "members:invite",
        "members:remove",
        "members:change_role",
        "data:view_all",
        "data:upload",
        "data:export",
        "data:delete",
        "dashboard:view",
        "dashboard:create",
        "dashboard:edit",
        "dashboard:share",
        "audit:view",
    },
    "admin": {
        "company:edit",
        "members:invite",
        "members:remove",
        "members:change_role",
        "data:view_all",
        "data:upload",
        "data:export",
        "dashboard:view",
        "dashboard:create",
        "dashboard:edit",
        "dashboard:share",
        "audit:view",
    },
    "analyst": {
        "data:view_all",
        "data:export",
        "dashboard:view",
        "dashboard:create",
        "dashboard:edit",
    },
    "accountant": {
        "data:view_financial",
        "data:upload",
        "dashboard:view",
    },
    "viewer": {
        "dashboard:view",
    },
}


def get_permissions(role: str) -> Set[str]:
    """Get all permissions for a given role."""
    return PERMISSIONS.get(role, set())


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    return permission in get_permissions(role)


# ─── Access Guards ───────────────────────────────────────────────────────────

def require_permission(permission: str) -> bool:
    """
    Check if the current user has a specific permission.

    Usage:
        if not require_permission("data:export"):
            st.error("You don't have permission to export data.")
            st.stop()
    """
    role = st.session_state.get("user_role")
    if not role:
        return False
    return has_permission(role, permission)


def require_role(minimum_role: str) -> bool:
    """
    Check if the current user's role is at least the minimum required.

    Role hierarchy: owner > admin > analyst > accountant > viewer

    Usage:
        if not require_role("admin"):
            st.error("Admin access required.")
            st.stop()
    """
    hierarchy = ["viewer", "accountant", "analyst", "admin", "owner"]
    user_role = st.session_state.get("user_role")

    if not user_role:
        return False

    try:
        user_level = hierarchy.index(user_role)
        required_level = hierarchy.index(minimum_role)
        return user_level >= required_level
    except ValueError:
        return False


def require_company_access(company_id: int) -> bool:
    """
    Check if the current user has access to a specific company.
    Returns True if the user is a member of the company.
    """
    user_company_id = st.session_state.get("user_company_id")
    return user_company_id == company_id


# ─── Role Display Helpers ────────────────────────────────────────────────────

ROLE_LABELS = {
    "owner": "Owner",
    "admin": "Administrator",
    "analyst": "Analyst",
    "accountant": "Accountant",
    "viewer": "Viewer",
}

ROLE_COLORS = {
    "owner": "#ef4444",       # red
    "admin": "#f59e0b",       # amber
    "analyst": "#3b82f6",     # blue
    "accountant": "#10b981",  # green
    "viewer": "#6b7280",      # gray
}

ROLE_DESCRIPTIONS = {
    "owner": "Full control over company settings, billing, and all data.",
    "admin": "Manage team members, view all data, and configure dashboards.",
    "analyst": "View all financial data, create charts, and export reports.",
    "accountant": "Upload and view invoices, receipts, and financial documents.",
    "viewer": "Read-only access to shared dashboards and reports.",
}


def get_role_badge_html(role: str) -> str:
    """Generate an HTML badge for a role."""
    label = ROLE_LABELS.get(role, role.title())
    color = ROLE_COLORS.get(role, "#6b7280")
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;'
        f'font-size:0.78rem;font-weight:600;color:#fff;background:{color};">'
        f'{label}</span>'
    )


def get_available_roles_for_assigner(assigner_role: str) -> list:
    """
    Get which roles an assigner can grant.
    - Owners can assign any role except owner
    - Admins can assign analyst, accountant, viewer
    - Others can't assign roles
    """
    if assigner_role == "owner":
        return ["admin", "analyst", "accountant", "viewer"]
    elif assigner_role == "admin":
        return ["analyst", "accountant", "viewer"]
    else:
        return []
