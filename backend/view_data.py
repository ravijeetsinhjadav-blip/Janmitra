import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import settings
from app.core.database import engine
from sqlalchemy import text

def print_header(title):
    print("\n" + "=" * 70)
    print(f" {title.upper()}")
    print("=" * 70)

print(f"\nActive Database: {engine.dialect.name.upper()} ({settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'local'})")

with engine.connect() as conn:
    # 1. Users
    print_header("1. Registered Users (users table)")
    rows = conn.execute(text("SELECT id, role, email, mobile_number, is_active, created_at FROM users ORDER BY created_at DESC LIMIT 10")).fetchall()
    if rows:
        for r in rows:
            print(f"[*] [{r.role.upper()}] Email: {r.email or 'N/A'} | Phone: {r.mobile_number or 'N/A'} | Active: {bool(r.is_active)} | Created: {r.created_at}")
    else:
        print("No users found.")

    # 2. Citizen Profiles
    print_header("2. Citizen Profiles (user_profiles table)")
    rows = conn.execute(text("SELECT full_name, date_of_birth, state, district, annual_family_income, occupation, education_level FROM user_profiles ORDER BY updated_at DESC LIMIT 10")).fetchall()
    if rows:
        for r in rows:
            print(f"[*] Name: {r.full_name} | State: {r.state} ({r.district}) | Income: INR {r.annual_family_income} | Occupation: {r.occupation}")
    else:
        print("No profiles found.")

    # 3. Documents & OCR
    print_header("3. Vault Documents & OCR Results (document_metadata table)")
    rows = conn.execute(text("SELECT document_type, original_filename, ocr_status, ocr_confidence, SUBSTR(ocr_extracted_text, 1, 60) AS text_preview, created_at FROM document_metadata ORDER BY created_at DESC LIMIT 10")).fetchall()
    if rows:
        for r in rows:
            preview = (r.text_preview or '').replace('\n', ' ')
            print(f"[*] Doc: {r.original_filename} ({r.document_type}) | Status: {r.ocr_status} (Conf: {r.ocr_confidence}) | Preview: {preview}...")
    else:
        print("No documents found.")

    # 4. Schemes
    print_header("4. Available Welfare Schemes (schemes table)")
    rows = conn.execute(text("SELECT scheme_name, category, department, is_active FROM schemes LIMIT 10")).fetchall()
    if rows:
        for r in rows:
            print(f"[*] {r.scheme_name} [{r.category}] - Dept: {r.department} (Active: {bool(r.is_active)})")
    else:
        print("No schemes found.")

# 5. Storage Directory
storage_dir = os.path.join(os.path.dirname(__file__), "storage", "documents")
print_header("5. Physical Document Storage Directory")
print(f"Location on your Computer:\n  -> {os.path.abspath(storage_dir)}")
if os.path.exists(storage_dir):
    user_folders = os.listdir(storage_dir)
    print(f"\nTotal citizen document folders stored: {len(user_folders)}")
else:
    print("Storage directory not initialized yet.")

print("\n" + "=" * 70 + "\n")
