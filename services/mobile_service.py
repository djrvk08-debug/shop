"""Mobile-number normalization and validation helpers."""
import re


_INDIA_LOCAL = re.compile(r"^[6-9]\d{9}$")
_E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_mobile(value: str, default_country: str = "+91") -> str:
    """Return a normalized E.164 mobile number or raise ValueError."""
    raw = str(value or "").strip()
    compact = re.sub(r"[\s().-]", "", raw)
    if compact.startswith("00"):
        compact = "+" + compact[2:]
    elif compact.startswith("0") and default_country == "+91":
        compact = default_country + compact[1:]
    elif compact.isdigit() and default_country == "+91" and len(compact) == 10:
        compact = default_country + compact
    elif compact.isdigit() and default_country == "+91" and len(compact) == 12 and compact.startswith("91"):
        compact = "+" + compact
    if not _E164.fullmatch(compact):
        raise ValueError("Enter a valid mobile number.")
    if compact.startswith("+91") and not _INDIA_LOCAL.fullmatch(compact[3:]):
        raise ValueError("Enter a valid mobile number.")
    return compact
