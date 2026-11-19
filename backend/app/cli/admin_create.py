"""JanMitra Assist - Secure Administrator Provisioning CLI

Usage:
    python -m app.cli.admin_create --email <admin-email>

Security:
    Passwords are NEVER accepted as command-line arguments to prevent leakage into
    process lists or shell history files. Passwords must be entered securely via
    interactive getpass prompts or via the ADMIN_PROVISION_PASSWORD environment variable.
"""

import argparse
import getpass
import os
import re
import sys
import uuid
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password, validate_password_strength
from app.models.user import User


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_admin_email(email: str) -> str:
    """Validate administrator email format."""
    clean = email.strip().lower()
    if not clean or not EMAIL_REGEX.match(clean):
        raise ValueError(f"Invalid administrator email format: '{clean}'.")
    return clean


def provision_admin(email: str, password: str, db: Optional[Session] = None) -> User:
    """Provision a new administrator account or update credentials for an existing admin."""
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        email_clean = validate_admin_email(email)
        validate_password_strength(password)
        hashed_pw = hash_password(password)

        existing = db.query(User).filter(User.email == email_clean).first()
        if existing:
            if existing.role == "admin":
                existing.password_hash = hashed_pw
                existing.is_active = True
                db.commit()
                db.refresh(existing)
                print(f"[SUCCESS] Administrator credentials updated for: {email_clean} (ID: {existing.id})")
                return existing
            else:
                existing.role = "admin"
                existing.password_hash = hashed_pw
                existing.is_active = True
                db.commit()
                db.refresh(existing)
                print(f"[SUCCESS] Existing user promoted to administrator: {email_clean} (ID: {existing.id})")
                return existing
        else:
            admin_user = User(
                id=uuid.uuid4(),
                email=email_clean,
                password_hash=hashed_pw,
                role="admin",
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"[SUCCESS] New administrator created: {email_clean} (ID: {admin_user.id})")
            return admin_user
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Administrator provisioning failed: {exc}", file=sys.stderr)
        raise
    finally:
        if own_session:
            db.close()


def main():
    parser = argparse.ArgumentParser(description="Secure Administrator Account Provisioning")
    parser.add_argument("--email", required=True, help="Administrator email address")

    args = parser.parse_args()

    # Passwords are NOT accepted as CLI flags to prevent exposure in shell history.
    # Accepts environment variable for headless CI/CD, or prompts interactively.
    password = os.environ.get("ADMIN_PROVISION_PASSWORD")

    if not password:
        try:
            password = getpass.getpass("Enter Administrator Password: ")
            confirm = getpass.getpass("Confirm Administrator Password: ")
        except (EOFError, KeyboardInterrupt):
            print("\n[ABORTED] Provisioning cancelled by user.", file=sys.stderr)
            sys.exit(1)

        if password != confirm:
            print("[ERROR] Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    try:
        provision_admin(args.email, password)
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
