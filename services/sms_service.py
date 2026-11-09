"""SMS delivery providers used for one-time passwords."""
import base64
import json
import logging
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app


def send_otp(mobile: str, code: str) -> None:
    """Send an OTP through the configured development or production provider."""
    provider = current_app.config.get("SMS_PROVIDER", "console").lower()
    if provider == "console":
        if not current_app.debug:
            raise RuntimeError("Console SMS provider is disabled outside development.")
        logging.warning("Development OTP for %s: %s", mobile, code)
        return
    if provider != "twilio":
        raise RuntimeError("Unsupported SMS provider.")

    account_sid = current_app.config.get("TWILIO_ACCOUNT_SID")
    auth_token = current_app.config.get("TWILIO_AUTH_TOKEN")
    from_number = current_app.config.get("TWILIO_FROM_NUMBER")
    template_id = current_app.config.get("SMS_TEMPLATE_ID")
    if not all((account_sid, auth_token, from_number, template_id)):
        raise RuntimeError("Twilio SMS configuration is incomplete.")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    body = urlencode({
        "To": mobile,
        "From": from_number,
        "ContentSid": template_id,
        "ContentVariables": json.dumps({"1": code}),
    }).encode()
    token = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
    request = Request(url, data=body, headers={"Authorization": f"Basic {token}"}, method="POST")
    with urlopen(request, timeout=10) as response:
        if response.status >= 300:
            raise RuntimeError("SMS provider rejected the message.")
        json.load(response)
