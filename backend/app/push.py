"""Pushover notification sender for human-in-the-loop alerts."""

import logging

import requests

from app.config import get_settings

logger = logging.getLogger(__name__)
PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


def push(message: str) -> str:
    """Send a push notification to the human owner and return a status string."""
    settings = get_settings()
    if not settings.pushover_user.strip() or not settings.pushover_token.strip():
        logger.error("Pushover credentials are missing")
        return "Notification could not be delivered to the human owner."

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
        try:
            body = response.json()
        except ValueError:
            logger.error(
                "Pushover returned a non-JSON response: status=%s body=%r",
                response.status_code,
                response.text[:500],
            )
            return "Notification could not be delivered to the human owner."
    except requests.RequestException:
        logger.exception("Pushover notification request failed")
        return "Notification could not be delivered to the human owner."

    if response.status_code != 200 or body.get("status") != 1:
        logger.error(
            "Pushover rejected notification: status=%s body=%s",
            response.status_code,
            body,
        )
        return "Notification could not be delivered to the human owner."
    return "Message delivered to the human owner."
