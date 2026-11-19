"""JanMitra Assist - Safe SQLite to PostgreSQL 16 Data Migration Utility.

Migrates useful development records from SQLite (janmitra_dev.db) to PostgreSQL 16:
- Preserves all primary keys, UUIDs, and foreign key relationships.
- Parses JSON strings to native JSONB objects.
- Normalizes integer booleans (0/1) to native PostgreSQL booleans.
- Preserves exact ISO timestamps with timezone awareness.
- Inserts in topological order to satisfy foreign key constraints.
- Prevents duplication using primary key conflict checking.
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import create_engine, inspect, text, Table, MetaData
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import Base

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("sqlite_to_pg_migrator")

# Topological table order to preserve foreign key constraints
TABLE_MIGRATION_ORDER = [
    "users",
    "user_profiles",
    "user_sessions",
    "password_reset_tokens",
    "account_deletion_requests",
    "otp_challenges",
    "device_tokens",
    "notifications",
    "user_monthly_quotas",
    "subscriptions",
    "payment_transactions",
    "webhook_events",
    "schemes",
    "scheme_category_rules",
    "scheme_category_documents",
    "document_guides",
    "scheme_knowledge_chunks",
    "scheme_analytics_datasets",
    "scheme_analytics_breakdowns",
    "scheme_analytics_audit_logs",
    "document_metadata",
    "assessments",
    "applications",
    "application_status_history",
    "application_reminders",
]


def clean_value(col_name: str, val: Any, col_type: str) -> Any:
    """Normalize SQLite values for PostgreSQL 16 strict types."""
    if val is None:
        return None

    type_str = str(col_type).upper()

    # UUID conversions
    if "UUID" in type_str or col_name.endswith("_id") or col_name == "id":
        if isinstance(val, str):
            try:
                return uuid.UUID(val)
            except ValueError:
                pass

    # JSON / JSONB conversions
    if "JSON" in type_str:
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return val

    # Boolean conversions
    if "BOOL" in type_str:
        if isinstance(val, int):
            return bool(val)
        if isinstance(val, str):
            return val.lower() in ("1", "true", "t", "yes")

    # Datetime conversions
    if "DATETIME" in type_str or "TIMESTAMP" in type_str:
        if isinstance(val, str):
            try:
                # Handle standard ISO formats
                val_clean = val.replace("Z", "+00:00")
                return datetime.fromisoformat(val_clean)
            except Exception:
                try:
                    return datetime.strptime(val, "%Y-%m-%d %H:%M:%S.%f")
                except Exception:
                    try:
                        return datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        return val

    return val


def migrate_sqlite_to_postgres(sqlite_db_path: str, pg_url: str) -> Dict[str, int]:
    """Execute topological data migration from SQLite to PostgreSQL 16."""
    if not os.path.exists(sqlite_db_path):
        raise FileNotFoundError(f"SQLite database not found at: {sqlite_db_path}")

    # Standardize PostgreSQL URL for psycopg3 driver
    if pg_url.startswith("postgresql://"):
        pg_url = pg_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif pg_url.startswith("postgres://"):
        pg_url = pg_url.replace("postgres://", "postgresql+psycopg://", 1)

    logger.info("Initializing migration...")
    logger.info("Source SQLite: %s (Size: %s bytes)", sqlite_db_path, os.path.getsize(sqlite_db_path))
    redacted_pg = pg_url.split("@")[-1] if "@" in pg_url else "configured target"
    logger.info("Target PostgreSQL: %s", redacted_pg)

    sqlite_engine = create_engine(f"sqlite:///{os.path.abspath(sqlite_db_path)}")
    pg_engine = create_engine(pg_url, echo=False)

    # Inspect destination tables to confirm Alembic migrations were executed
    pg_inspector = inspect(pg_engine)
    pg_tables = set(pg_inspector.get_table_names())
    logger.info("Target PostgreSQL contains %d tables.", len(pg_tables))

    results: Dict[str, int] = {}
    skipped_tables: List[str] = []

    sqlite_meta = MetaData()
    sqlite_meta.reflect(bind=sqlite_engine)

    pg_meta = MetaData()
    pg_meta.reflect(bind=pg_engine)

    with pg_engine.begin() as pg_conn:
        # Disable trigger constraints temporarily if needed, or rely on topological ordering
        for table_name in TABLE_MIGRATION_ORDER:
            if table_name not in sqlite_meta.tables:
                logger.info("Skipping '%s' (not in SQLite source)", table_name)
                continue

            if table_name not in pg_tables:
                logger.warning("Target table '%s' missing from PostgreSQL! Ensure Alembic upgraded to head.", table_name)
                skipped_tables.append(table_name)
                continue

            src_table = sqlite_meta.tables[table_name]
            dst_table = pg_meta.tables[table_name]

            # Read source rows
            with sqlite_engine.connect() as src_conn:
                rows = src_conn.execute(src_table.select()).fetchall()

            if not rows:
                logger.info("Table '%s': 0 rows to migrate.", table_name)
                results[table_name] = 0
                continue

            logger.info("Migrating '%s' (%d rows)...", table_name, len(rows))
            migrated_count = 0

            # Get target primary key column names
            pk_cols = [c.name for c in dst_table.primary_key.columns]

            for row in rows:
                row_dict = dict(row._mapping)
                cleaned_row: Dict[str, Any] = {}

                for col in dst_table.columns:
                    col_name = col.name
                    if col_name in row_dict:
                        raw_val = row_dict[col_name]
                        cleaned_row[col_name] = clean_value(col_name, raw_val, str(col.type))

                # Check if record already exists by primary key
                if pk_cols:
                    where_clauses = [dst_table.c[pk] == cleaned_row[pk] for pk in pk_cols if pk in cleaned_row]
                    if where_clauses:
                        exists_stmt = dst_table.select().where(*where_clauses)
                        existing_row = pg_conn.execute(exists_stmt).first()
                        if existing_row:
                            continue  # Skip existing record to avoid duplication

                pg_conn.execute(dst_table.insert().values(cleaned_row))
                migrated_count += 1

            logger.info("  ✓ Successfully inserted %d new rows into '%s'.", migrated_count, table_name)
            results[table_name] = migrated_count

    logger.info("Migration completed successfully across %d tables.", len(results))
    return results


if __name__ == "__main__":
    src_db = sys.argv[1] if len(sys.argv) > 1 else "janmitra_dev.db"
    target_url = sys.argv[2] if len(sys.argv) > 2 else settings.sync_database_url
    if "sqlite" in target_url:
        print("[ERROR] Target DATABASE_URL is SQLite. Please set PostgreSQL connection string.")
        sys.exit(1)

    res = migrate_sqlite_to_postgres(src_db, target_url)
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY:")
    for tbl, count in res.items():
        print(f"  {tbl}: {count} records")
    print("=" * 60)
