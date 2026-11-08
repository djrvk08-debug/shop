"""Notification service managing outgoing email and SMS delivery message queues."""
import copy
import hashlib
import json
import logging
import threading
import time
from typing import Any
from flask import current_app, has_app_context

_notifications: dict[str, dict[str, Any]] = {}
_idempotency_keys: set[str] = set()
_queue_lock = threading.Lock()


def queue_notification(
    recipient: str, channel: str, subject: str, message: str,
    context: dict[str, Any] | None = None, idempotency_key: str | None = None,
) -> None:
    """Enqueue a customer notification (email or SMS) for asynchronous delivery.

    :param recipient: Target email address or phone number.
    :param channel: Communication medium ('email' or 'sms').
    :param subject: Notification subject or title.
    :param message: Message body or rendered template content.
    :param context: Optional metadata or template payload.
    """
    if not isinstance(recipient, str) or not recipient.strip() or len(recipient) > 255:
        raise ValueError("A valid notification recipient is required.")
    if channel not in {"email", "sms"}:
        raise ValueError("Notification channel must be email or sms.")
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 255:
        raise ValueError("A valid notification subject is required.")
    if not isinstance(message, str) or not message.strip() or len(message) > 10000:
        raise ValueError("A valid notification message is required.")
    try:
        payload = json.dumps(context or {}, sort_keys=True, default=str)
    except (TypeError, ValueError) as error:
        raise ValueError("Notification context must be serializable.") from error
    if not isinstance(context or {}, dict):
        raise ValueError("Notification context must be an object.")
    key = idempotency_key or hashlib.sha256(
        f"{recipient.strip()}\0{channel}\0{subject.strip()}\0{message}\0{payload}".encode()
    ).hexdigest()
    if not isinstance(key, str) or not key or len(key) > 255:
        raise ValueError("A valid idempotency key is required.")
    with _queue_lock:
        if key in _idempotency_keys:
            return
        _idempotency_keys.add(key)
        _notifications[key] = {
            "idempotency_key": key,
            "recipient": recipient.strip(),
            "channel": channel,
            "subject": subject.strip(),
            "message": message,
            "context": json.loads(payload),
            "attempts": 0,
            "status": "pending",
            "next_attempt_at": 0.0,
            "last_error": None,
        }
    logging.info("Queued %s notification for %s", channel, recipient.strip())


def send_pending_notifications() -> int:
    """Process and dispatch pending messages from the delivery queue.

    :return: Number of notifications successfully dispatched.
    """
    sender = current_app.config.get("NOTIFICATION_SENDER") if has_app_context() else None
    if not callable(sender):
        return 0
    now = time.time()
    with _queue_lock:
        pending = [item for item in _notifications.values()
                   if item["status"] == "pending" and item["next_attempt_at"] <= now]
        for item in pending:
            item["status"] = "processing"
    sent = 0
    for item in pending:
        try:
            sender(copy.deepcopy(item))
        except Exception as error:
            with _queue_lock:
                item["attempts"] += 1
                item["status"] = "pending"
                item["last_error"] = str(error)[:1000]
                item["next_attempt_at"] = time.time() + min(2 ** item["attempts"], 3600)
        else:
            with _queue_lock:
                item["status"] = "sent"
                item["last_error"] = None
            sent += 1
    return sent


def get_queued_notifications() -> list[dict[str, Any]]:
    """Inspect current unhandled notification queue items.

    :return: List of queued notification message objects.
    """
    with _queue_lock:
        return [copy.deepcopy(item) for item in _notifications.values()
                if item["status"] == "pending"]
