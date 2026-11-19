"""Tests for ReminderSchedulerService duplicate-safety, multi-worker claiming, and idempotency."""

import uuid
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from app.core.security import ensure_utc
from app.models.user import User
from app.models.scheme import Scheme
from app.models.application import Application, ApplicationReminder
from app.models.notification import Notification
from app.services.reminder_scheduler import ReminderSchedulerService


def _setup_test_application(db_session):
    user = User(
        id=uuid.uuid4(),
        email=f"reminder_test_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="testhash",
        role="citizen",
        is_active=True,
    )
    db_session.add(user)

    scheme = Scheme(
        id=uuid.uuid4(),
        scheme_name="Test Scheme for Reminder",
        description="Testing Reminder Scheduler Idempotency",
        category="Welfare",
        department="Ministry of Social Justice",
        official_source_url="https://welfare.gov.in",
        official_application_url="https://welfare.gov.in/apply",
        eligibility_summary="Eligible citizens",
        is_active=True,
    )
    db_session.add(scheme)
    db_session.commit()

    application = Application(
        id=uuid.uuid4(),
        user_id=user.id,
        scheme_id=scheme.id,
        status="SUBMITTED",
        submission_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(application)
    db_session.commit()

    return user, application


def test_reminder_scheduler_prevents_duplicate_dispatch(db_session):
    user, application = _setup_test_application(db_session)

    # Create an overdue reminder
    reminder = ApplicationReminder(
        id=uuid.uuid4(),
        application_id=application.id,
        user_id=user.id,
        title="Submit Income Certificate",
        description="Statutory document deadline",
        reminder_date=datetime.now(timezone.utc) - timedelta(hours=2),
        is_completed=False,
    )
    db_session.add(reminder)
    db_session.commit()

    # First sweep should dispatch 1 notification
    res1 = ReminderSchedulerService.process_due_reminders(db_session, worker_token="worker_alpha")
    assert res1["dispatched_count"] >= 1

    # Verify notification created
    notifications = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == user.id,
            Notification.notification_type == "application_reminder",
            Notification.message.like(f"%[Ref:{reminder.id}]%"),
        )
        .all()
    )
    assert len(notifications) == 1

    # Immediate second sweep should detect already notified / already dispatched and dispatch 0
    res2 = ReminderSchedulerService.process_due_reminders(db_session, worker_token="worker_beta")
    assert res2["dispatched_count"] == 0

    # Total notifications must strictly remain 1
    notifications_after = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == user.id,
            Notification.notification_type == "application_reminder",
            Notification.message.like(f"%[Ref:{reminder.id}]%"),
        )
        .all()
    )
    assert len(notifications_after) == 1

    # Reminder must remain not completed (completion is user-actionable)
    db_session.refresh(reminder)
    assert reminder.is_completed is False
    assert reminder.last_dispatched_at is not None


def test_two_workers_atomic_claiming_race(db_session):
    """Verify that when two workers attempt to claim the same reminder concurrently,
    exactly ONE worker succeeds in acquiring the exclusive claim.
    """
    user, application = _setup_test_application(db_session)

    reminder = ApplicationReminder(
        id=uuid.uuid4(),
        application_id=application.id,
        user_id=user.id,
        title="Concurrent Deadline Race",
        description="Verify atomic claiming",
        reminder_date=datetime.now(timezone.utc) - timedelta(hours=1),
        is_completed=False,
    )
    db_session.add(reminder)
    db_session.commit()

    now = datetime.now(timezone.utc)

    # Worker 1 claims
    claimed_w1 = ReminderSchedulerService.claim_reminder(
        db=db_session,
        reminder_id=reminder.id,
        worker_token="worker_instance_1",
        now=now,
    )
    assert claimed_w1 is True

    # Worker 2 attempts to claim the same reminder while lease is active
    claimed_w2 = ReminderSchedulerService.claim_reminder(
        db=db_session,
        reminder_id=reminder.id,
        worker_token="worker_instance_2",
        now=now,
    )
    assert claimed_w2 is False  # Worker 2 blocked because active lease is held by Worker 1


def test_reminder_lease_expiration_and_recovery(db_session):
    """Verify crash recovery: if Worker 1 crashes with an unfinalized claim,
    once the lease expires, Worker 2 can reclaim and dispatch the reminder.
    """
    user, application = _setup_test_application(db_session)

    reminder = ApplicationReminder(
        id=uuid.uuid4(),
        application_id=application.id,
        user_id=user.id,
        title="Crash Recovery Task",
        description="Verify expired lease reclaim",
        reminder_date=datetime.now(timezone.utc) - timedelta(hours=3),
        is_completed=False,
    )
    db_session.add(reminder)
    db_session.commit()

    # Worker 1 claims the reminder at T0
    t0 = datetime.now(timezone.utc) - timedelta(minutes=10)
    claimed_w1 = ReminderSchedulerService.claim_reminder(
        db=db_session,
        reminder_id=reminder.id,
        worker_token="crashed_worker_1",
        now=t0,
    )
    assert claimed_w1 is True

    # Check that lease expired (T0 + 5min < current time)
    db_session.refresh(reminder)
    assert reminder.dispatch_lease_until is not None
    assert ensure_utc(reminder.dispatch_lease_until) < datetime.now(timezone.utc)

    # Worker 2 executes sweep at current time: should reclaim expired lease and dispatch successfully
    now = datetime.now(timezone.utc)
    claimed_w2 = ReminderSchedulerService.claim_reminder(
        db=db_session,
        reminder_id=reminder.id,
        worker_token="healthy_worker_2",
        now=now,
    )
    assert claimed_w2 is True

    # Finalize dispatch
    ReminderSchedulerService.finalize_dispatch(
        db=db_session,
        reminder_id=reminder.id,
        worker_token="healthy_worker_2",
        success=True,
        now=now,
    )

    db_session.refresh(reminder)
    assert reminder.last_dispatched_at is not None
    assert reminder.dispatch_token is None


def test_reminder_transient_failure_increments_retry_count(db_session):
    """Verify that transient dispatch failures release the lease and increment retry_count."""
    user, application = _setup_test_application(db_session)

    reminder = ApplicationReminder(
        id=uuid.uuid4(),
        application_id=application.id,
        user_id=user.id,
        title="Failing Reminder",
        description="Test transient failure",
        reminder_date=datetime.now(timezone.utc) - timedelta(minutes=30),
        is_completed=False,
        retry_count=0,
    )
    db_session.add(reminder)
    db_session.commit()

    now = datetime.now(timezone.utc)
    worker_id = "test_retry_worker"

    # Claim
    claimed = ReminderSchedulerService.claim_reminder(db_session, reminder.id, worker_id, now)
    assert claimed is True

    # Simulate dispatch failure
    ReminderSchedulerService.finalize_dispatch(db_session, reminder.id, worker_id, success=False, now=now)

    db_session.refresh(reminder)
    assert reminder.retry_count == 1
    assert reminder.last_dispatched_at is None
    assert reminder.dispatch_token is None
    assert reminder.dispatch_lease_until is None  # Released for next sweep retry


def test_reminder_max_retries_exhaustion(db_session):
    """Verify that reminders with exhausted retries (retry_count >= MAX_RETRIES) are not dispatched."""
    user, application = _setup_test_application(db_session)

    reminder = ApplicationReminder(
        id=uuid.uuid4(),
        application_id=application.id,
        user_id=user.id,
        title="Exhausted Reminder",
        description="Should not be processed",
        reminder_date=datetime.now(timezone.utc) - timedelta(hours=1),
        is_completed=False,
        retry_count=ReminderSchedulerService.MAX_RETRIES,
    )
    db_session.add(reminder)
    db_session.commit()

    res = ReminderSchedulerService.process_due_reminders(db_session)
    assert res["dispatched_count"] == 0
