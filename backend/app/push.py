"""Pushover notification sender for human-in-the-loop alerts."""

import logging

import requests

from app.config import get_settings

logger = logging.getLogger(__name__)
PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


def push(message: str) -> str:
    """Send a push notification to the human owner and return a status string."""
    settings = get_settings()
    payload = {"user": settings.pushover_user, "token": settings.pushover_token, "message": message}
    response = requests.post(PUSHOVER_URL, data=payload)
    if response.status_code != 200 or response.json().get("status") != 1:
        logger.error("Pushover rejected notification: %s %s", response.status_code, response.text)
        return "Notification could not be delivered to the human owner."
    return "Message delivered to the human owner."
