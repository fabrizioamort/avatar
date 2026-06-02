"""Connectivity check for Firestore.

Verifies that Application Default Credentials and the default Firestore database
are reachable and writable through the app's db layer, using the same row shape
the rest of the app expects.
"""

import os
import uuid

import pytest

from app import db
from app.config import get_settings

EXPECTED_KEYS = {
    "id",
    "conversation_id",
    "conversation_name",
    "role",
    "content",
    "tool_calls",
    "needs_attention",
    "read",
    "created_at",
}


def test_project_resolvable():
    """A project id is available, either explicitly or via ADC."""
    from google.auth import default

    settings = get_settings()
    if settings.gcp_project_id:
        return
    _, project = default()
    assert project, "No GOOGLE_CLOUD_PROJECT and ADC could not infer a project"


def test_default_database():
    """The free quota only applies to the default database."""
    assert os.environ.get("FIRESTORE_DATABASE", "(default)") == "(default)"
    assert get_settings().firestore_database == "(default)"


def test_insert_read_delete_roundtrip():
    """A full write/read/delete cycle works and stores the expected keys."""
    cid = str(uuid.uuid4())
    try:
        row = db.insert_message(cid, "visitor", "connectivity test")
        assert EXPECTED_KEYS.issubset(row.keys())
        assert row["id"] == 1
        assert row["role"] == "visitor"
        assert row["needs_attention"] is False
        assert row["read"] is False

        rows = db.get_messages(cid)
        assert len(rows) == 1
        assert rows[0]["content"] == "connectivity test"
    finally:
        db.delete_conversation(cid)

    assert db.get_messages(cid) == []
