"""Pushover notification sender for human-in-the-loop alerts."""

import logging

import requests

from app.config import get_settings

logger = logging.getLogger(__name__)
PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


def push(message: str) -> str:
    """Send a push notification to the human owner and return a status string."""
    settings = get_settings()
    text = message.strip()
    if len(text) > settings.pushover_message_max_chars:
        text = text[: settings.pushover_message_max_chars] + "..."
    payload = {"user": settings.pushover_user, "token": settings.pushover_token, "message": text}
    timeout = (
        settings.pushover_timeout_connect_seconds,
        settings.pushover_timeout_read_seconds,
    )
    try:
        response = requests.post(PUSHOVER_URL, data=payload, timeout=timeout)
        accepted = response.status_code == 200 and response.json().get("status") == 1
    except requests.RequestException:
        logger.exception("Pushover notification request failed")
        return "Notification could not be delivered to the human owner."
    if not accepted:
        logger.error("Pushover rejected notification: status=%s", response.status_code)
        return "Notification could not be delivered to the human owner."
    return "Message delivered to the human owner."
