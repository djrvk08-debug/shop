"""Secure, rate-limited, single-use mobile OTP challenges."""
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import hashlib
import hmac
import secrets

from flask import current_app

from extensions import db
from models import OTPChallenge
from services.mobile_service import normalize_mobile
from services.sms_service import send_otp


GENERIC_ERROR = "We could not verify that request. Please try again."
_verify_events = defaultdict(list)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(code: str) -> str:
    secret = current_app.config["OTP_SECRET"].encode()
    return hmac.new(secret, code.encode(), hashlib.sha256).hexdigest()


def _check_limits(mobile: str, request_ip: str) -> None:
    cutoff = _now() - timedelta(hours=1)
    mobile_count = OTPChallenge.query.filter(
        OTPChallenge.mobile == mobile, OTPChallenge.created_at >= cutoff
    ).count()
    ip_count = OTPChallenge.query.filter(
        OTPChallenge.request_ip == request_ip, OTPChallenge.created_at >= cutoff
    ).count()
    if mobile_count >= current_app.config["OTP_HOURLY_LIMIT"] or ip_count >= current_app.config["OTP_IP_HOURLY_LIMIT"]:
        raise ValueError(GENERIC_ERROR)
    latest = OTPChallenge.query.filter_by(mobile=mobile, used=False).order_by(
        OTPChallenge.created_at.desc()
    ).first()
    if latest and (_now() - latest.created_at.replace(tzinfo=timezone.utc)).total_seconds() < current_app.config["OTP_RESEND_COOLDOWN_SECONDS"]:
        raise ValueError(GENERIC_ERROR)


def issue_otp(user_id: int, mobile: str, purpose: str, request_ip: str) -> None:
    """Create and send an OTP without persisting its plain value."""
    mobile = normalize_mobile(mobile)
    if purpose not in {"login", "register", "reset"}:
        raise ValueError(GENERIC_ERROR)
    _check_limits(mobile, request_ip or "unknown")
    OTPChallenge.query.filter_by(user_id=user_id, purpose=purpose, used=False).update({"used": True})
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = OTPChallenge(
        user_id=user_id,
        mobile=mobile,
        purpose=purpose,
        code_hash=_hash(code),
        expires_at=_now() + timedelta(seconds=current_app.config["OTP_EXPIRY_SECONDS"]),
        request_ip=request_ip or "unknown",
    )
    db.session.add(challenge)
    db.session.commit()
    try:
        send_otp(mobile, code)
    except Exception:
        challenge.used = True
        db.session.commit()
        raise ValueError(GENERIC_ERROR)


def _check_verify_limit(mobile: str, request_ip: str) -> bool:
    cutoff = _now() - timedelta(hours=1)
    key = (mobile, request_ip or "unknown")
    _verify_events[key] = [event for event in _verify_events[key] if event >= cutoff]
    mobile_count = sum(
        len(events) for (event_mobile, _), events in _verify_events.items()
        if event_mobile == mobile
    )
    if mobile_count >= current_app.config["OTP_VERIFY_HOURLY_LIMIT"]:
        return False
    if len(_verify_events[key]) >= current_app.config["OTP_VERIFY_IP_HOURLY_LIMIT"]:
        return False
    _verify_events[key].append(_now())
    return True


def verify_otp(user_id: int, purpose: str, code: str, request_ip: str = "unknown") -> bool:
    """Verify the newest challenge with constant-time comparison."""
    challenge = OTPChallenge.query.filter_by(user_id=user_id, purpose=purpose, used=False).order_by(
        OTPChallenge.created_at.desc()
    ).first()
    if challenge is None or challenge.expires_at.replace(tzinfo=timezone.utc) < _now():
        if challenge:
            challenge.used = True
            db.session.commit()
        return False
    if not _check_verify_limit(challenge.mobile, request_ip):
        return False
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit() or not hmac.compare_digest(
        challenge.code_hash, _hash(code)
    ):
        challenge.attempt_count += 1
        if challenge.attempt_count >= 5:
            challenge.used = True
        db.session.commit()
        return False
    challenge.used = True
    db.session.commit()
    return True
