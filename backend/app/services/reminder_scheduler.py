"""JanMitra Assist - Application Reminder Background Scheduler

Handles statutory deadlines, document submission milestones, and citizen reminders.
Ensures duplicate-safe idempotency via atomic worker claiming, time-bounded leases,
database-backed deduplication, and PostgreSQL row-level locks (SKIP LOCKED).
"""

import threading
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.core.logging import logger
from app.core.security import ensure_utc
from app.models.application import ApplicationReminder
from app.models.notification import Notification
from app.services.fcm_service import FCMService


class ReminderSchedulerService:
    """Service responsible for scanning statutory/citizen deadlines and dispatching notifications."""

    _sweep_lock = threading.Lock()
    MAX_RETRIES = 3
    LEASE_DURATION_SECONDS = 300  # 5 minutes

    @classmethod
    def claim_reminder(
        cls,
        db: Session,
        reminder_id: uuid.UUID,
        worker_token: str,
        now: datetime,
    ) -> bool:
        """Atomically claim a reminder for exclusive dispatch by this worker.

        Concurrency & Crash Safety:
        1. On PostgreSQL: Uses SELECT ... FOR UPDATE SKIP LOCKED to prevent multi-worker races.
        2. On SQLite / Portable: Uses atomic conditional UPDATE matching unclaimed or expired leases.
        3. If an earlier worker crashed while holding a lease, it can be reclaimed once
           now > dispatch_lease_until (auto-healing).
        4. Respects MAX_RETRIES to prevent endless dispatch loops on persistent failure.

        Returns:
            bool: True if this worker successfully acquired the exclusive claim, False otherwise.
        """
        now_utc = ensure_utc(now)
        lease_until = now_utc + timedelta(seconds=cls.LEASE_DURATION_SECONDS)

        bind = db.get_bind()
        if bind and bind.dialect.name == "postgresql":
            # PostgreSQL row-level lock with SKIP LOCKED
            rem = (
                db.query(ApplicationReminder)
                .filter(
                    ApplicationReminder.id == reminder_id,
                    ApplicationReminder.is_completed == False,
                    ApplicationReminder.last_dispatched_at.is_(None),
                    or_(
                        ApplicationReminder.dispatch_lease_until.is_(None),
                        ApplicationReminder.dispatch_lease_until < now_utc,
                    ),
                    ApplicationReminder.retry_count < cls.MAX_RETRIES,
                )
                .with_for_update(skip_locked=True)
                .first()
            )
            if not rem:
                return False

            rem.dispatch_token = worker_token
            rem.dispatch_lease_until = lease_until
            db.commit()
            return True
        else:
            # Portable atomic conditional UPDATE
            rows_updated = (
                db.query(ApplicationReminder)
                .filter(
                    ApplicationReminder.id == reminder_id,
                    ApplicationReminder.is_completed == False,
                    ApplicationReminder.last_dispatched_at.is_(None),
                    or_(
                        ApplicationReminder.dispatch_lease_until.is_(None),
                        ApplicationReminder.dispatch_lease_until < now_utc,
                    ),
                    ApplicationReminder.retry_count < cls.MAX_RETRIES,
                )
                .update(
                    {
                        "dispatch_token": worker_token,
                        "dispatch_lease_until": lease_until,
                    },
                    synchronize_session=False,
                )
            )
            db.commit()
            return rows_updated > 0

    @classmethod
    def finalize_dispatch(
        cls,
        db: Session,
        reminder_id: uuid.UUID,
        worker_token: str,
        success: bool,
        now: datetime,
    ) -> None:
        """Finalize the reminder claim after dispatch attempt."""
        now_utc = ensure_utc(now)
        rem = (
            db.query(ApplicationReminder)
            .filter(
                ApplicationReminder.id == reminder_id,
                ApplicationReminder.dispatch_token == worker_token,
            )
            .first()
        )
        if not rem:
            return

        if success:
            rem.last_dispatched_at = now_utc
            rem.dispatch_token = None
            rem.dispatch_lease_until = None
        else:
            rem.retry_count += 1
            rem.dispatch_token = None
            # Release lease to allow retry by subsequent sweeps (up to MAX_RETRIES)
            rem.dispatch_lease_until = None

        db.commit()

    @classmethod
    def process_due_reminders(
        cls,
        db: Session,
        worker_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Scan active application reminders due at or before current time and dispatch FCM/in-app notifications.

        Multi-Worker Architecture:
        1. Single-process lock (_sweep_lock) prevents overlapping sweeps within the same thread.
        2. Across separate worker processes, atomic claim_reminder() guarantees that each reminder
           is claimed by exactly one worker. Competitors skip already-claimed reminders.
        3. Double-dispatch is prevented by checking last_dispatched_at and Notification table.
        4. Citizen completion status (is_completed) is NEVER modified by the scheduler.
        """
        if not cls._sweep_lock.acquire(blocking=False):
            logger.warning("Reminder sweep is already running in this process; skipping concurrent execution.")
            return {
                "evaluated_count": 0,
                "dispatched_count": 0,
                "skipped_already_notified": 0,
                "skipped_claimed_by_other": 0,
                "errors_count": 0,
                "status": "skipped_locked",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        worker_id = worker_token or f"worker_{uuid.uuid4().hex[:8]}"

        try:
            now = datetime.now(timezone.utc)

            # Query due reminders that are uncompleted, not yet dispatched, and have remaining retries
            query = (
                db.query(ApplicationReminder)
                .filter(
                    ApplicationReminder.is_completed == False,
                    ApplicationReminder.reminder_date <= now,
                    ApplicationReminder.last_dispatched_at.is_(None),
                    or_(
                        ApplicationReminder.dispatch_lease_until.is_(None),
                        ApplicationReminder.dispatch_lease_until < now,
                    ),
                    ApplicationReminder.retry_count < cls.MAX_RETRIES,
                )
            )

            bind = db.get_bind()
            if bind and bind.dialect.name == "postgresql":
                query = query.with_for_update(skip_locked=True)

            due_reminders: List[ApplicationReminder] = query.all()

            dispatched_count = 0
            skipped_already_notified = 0
            skipped_claimed_by_other = 0
            errors_count = 0

            for reminder in due_reminders:
                # 1. Attempt atomic lease claim
                claimed = cls.claim_reminder(
                    db=db,
                    reminder_id=reminder.id,
                    worker_token=worker_id,
                    now=now,
                )
                if not claimed:
                    skipped_claimed_by_other += 1
                    continue

                # 2. Database deduplication check: verify whether notification was already recorded
                ref_marker = f"[Ref:{reminder.id}]"
                already_notified = (
                    db.query(Notification)
                    .filter(
                        Notification.user_id == reminder.user_id,
                        Notification.notification_type == "application_reminder",
                        Notification.message.like(f"%{ref_marker}%"),
                    )
                    .first()
                )

                if already_notified:
                    skipped_already_notified += 1
                    # Mark permanently dispatched to prevent redundant scans
                    cls.finalize_dispatch(db=db, reminder_id=reminder.id, worker_token=worker_id, success=True, now=now)
                    continue

                # 3. Dispatch Notification via FCM and In-App Ledger
                try:
                    msg_body = reminder.description or "You have a statutory deadline or document submission task due."
                    annotated_msg = f"{msg_body} {ref_marker}"

                    notification_record = FCMService.dispatch_notification(
                        db=db,
                        user_id=reminder.user_id,
                        title=f"Application Deadline: {reminder.title}",
                        message=annotated_msg,
                        notification_type="application_reminder",
                        data={
                            "application_id": str(reminder.application_id),
                            "reminder_id": str(reminder.id),
                            "action_url": f"/applications/{reminder.application_id}",
                        },
                    )

                    # Mark dispatch successfully finalized
                    cls.finalize_dispatch(db=db, reminder_id=reminder.id, worker_token=worker_id, success=True, now=now)
                    dispatched_count += 1
                    logger.info(
                        f"[Scheduler] Reminder {reminder.id} claimed by {worker_id} and dispatched. "
                        f"Notification ID: {notification_record.id}"
                    )
                except Exception as e:
                    errors_count += 1
                    logger.error(f"[Scheduler] Dispatch failed for reminder {reminder.id}: {e}")
                    # Release claim with retry count incremented
                    cls.finalize_dispatch(db=db, reminder_id=reminder.id, worker_token=worker_id, success=False, now=now)

            logger.info(
                f"Reminder sweep completed: {dispatched_count} dispatched, "
                f"{skipped_already_notified} previously notified, "
                f"{skipped_claimed_by_other} claimed by other workers, "
                f"{errors_count} errors, {len(due_reminders)} total evaluated."
            )

            return {
                "evaluated_count": len(due_reminders),
                "dispatched_count": dispatched_count,
                "skipped_already_notified": skipped_already_notified,
                "skipped_claimed_by_other": skipped_claimed_by_other,
                "errors_count": errors_count,
                "status": "completed",
                "timestamp": now.isoformat(),
            }
        finally:
            cls._sweep_lock.release()
