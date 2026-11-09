"""Notification queue validation, idempotency, and retry coverage."""
from services import notify_service


def test_notification_enqueue_is_idempotent_and_requires_sender(app, monkeypatch):
    monkeypatch.setattr(notify_service, "_notifications", {})
    monkeypatch.setattr(notify_service, "_idempotency_keys", set())
    payload = dict(recipient="+919876543240", channel="sms", subject="Order update",
                   message="Order is processing", idempotency_key="order-1-processing")
    notify_service.queue_notification(**payload)
    notify_service.queue_notification(**payload)

    assert len(notify_service.get_queued_notifications()) == 1
    with app.app_context():
        assert notify_service.send_pending_notifications() == 0
    assert len(notify_service.get_queued_notifications()) == 1


def test_notification_delivery_retries_and_marks_success_once(app, monkeypatch):
    monkeypatch.setattr(notify_service, "_notifications", {})
    monkeypatch.setattr(notify_service, "_idempotency_keys", set())
    notify_service.queue_notification("+919876543240", "sms", "Receipt", "Order received",
                                      idempotency_key="receipt-2")
    deliveries = []

    def sender(item):
        deliveries.append(item["idempotency_key"])
        if len(deliveries) == 1:
            raise RuntimeError("temporary gateway failure")

    with app.app_context():
        app.config["NOTIFICATION_SENDER"] = sender
        assert notify_service.send_pending_notifications() == 0
        queued = notify_service.get_queued_notifications()
        assert queued[0]["attempts"] == 1
        notify_service._notifications["receipt-2"]["next_attempt_at"] = 0
        assert notify_service.send_pending_notifications() == 1
        assert notify_service.send_pending_notifications() == 0

    assert deliveries == ["receipt-2", "receipt-2"]
    assert notify_service.get_queued_notifications() == []
