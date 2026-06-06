"""Firestore access layer: the only module that talks to the database.

Data model: a top-level ``conversations`` collection where each document holds
inbox-aggregate fields, plus a ``messages`` subcollection of the actual rows. The
parent aggregate lets ``list_conversations`` read one document per conversation
instead of scanning every message.
"""

from datetime import datetime, timezone
from functools import lru_cache

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.config import get_settings

CONVERSATIONS = "conversations"
MESSAGES = "messages"


@lru_cache
def get_client() -> firestore.Client:
    """Cached Firestore client on the default database."""
    settings = get_settings()
    kwargs: dict = {"database": settings.firestore_database}
    if settings.gcp_project_id:
        kwargs["project"] = settings.gcp_project_id
    return firestore.Client(**kwargs)


def _conversation_ref(conversation_id: str):
    return get_client().collection(CONVERSATIONS).document(conversation_id)


def insert_message(
    conversation_id: str,
    role: str,
    content: str,
    *,
    conversation_name: str | None = None,
    tool_calls: list | None = None,
    needs_attention: bool = False,
    read: bool = False,
) -> dict:
    """Insert one message row and return it.

    Runs in a transaction so the per-conversation sequence number and the parent
    aggregate stay consistent under concurrent writes.
    """
    conv_ref = _conversation_ref(conversation_id)
    transaction = get_client().transaction()
    return _insert_in_transaction(
        transaction,
        conv_ref,
        conversation_id,
        role,
        content,
        conversation_name,
        tool_calls,
        needs_attention,
        read,
    )


@firestore.transactional
def _insert_in_transaction(
    transaction,
    conv_ref,
    conversation_id: str,
    role: str,
    content: str,
    conversation_name: str | None,
    tool_calls: list | None,
    needs_attention: bool,
    read: bool,
) -> dict:
    parent = conv_ref.get(transaction=transaction).to_dict() or {}
    seq = parent.get("last_seq", 0) + 1
    created_at = datetime.now(timezone.utc).isoformat()

    row = {
        "id": seq,
        "conversation_id": conversation_id,
        "conversation_name": conversation_name,
        "role": role,
        "content": content,
        "tool_calls": tool_calls,
        "needs_attention": needs_attention,
        "read": read,
        "created_at": created_at,
    }
    msg_ref = conv_ref.collection(MESSAGES).document(str(seq).zfill(12))
    transaction.set(msg_ref, row)

    transaction.set(
        conv_ref,
        {
            "conversation_name": conversation_name or parent.get("conversation_name"),
            "preview": content[:120],
            "last_created_at": created_at,
            "last_id": seq,
            "last_seq": seq,
            "message_count": parent.get("message_count", 0) + 1,
            f"{role}_message_count": parent.get(f"{role}_message_count", 0) + 1,
            "unread": parent.get("unread", False) or (role != "human" and not read),
            "needs_attention": parent.get("needs_attention", False) or needs_attention,
        },
        merge=True,
    )
    return row


def get_messages(conversation_id: str, after_id: int | None = None) -> list[dict]:
    """All rows of a conversation ordered by id ascending, optionally after an id."""
    query = _conversation_ref(conversation_id).collection(MESSAGES).order_by("id")
    if after_id is not None:
        query = query.where(filter=FieldFilter("id", ">", after_id))
    return [doc.to_dict() for doc in query.stream()]


def get_conversation_meta(conversation_id: str) -> dict:
    """Parent aggregate for cheap preflight checks."""
    return _conversation_ref(conversation_id).get().to_dict() or {}


def list_conversations() -> list[dict]:
    """One summary per conversation, most recent first (one read per conversation)."""
    docs = (
        get_client()
        .collection(CONVERSATIONS)
        .order_by("last_created_at", direction=firestore.Query.DESCENDING)
        .stream()
    )
    summaries = []
    for doc in docs:
        data = doc.to_dict()
        summaries.append(
            {
                "conversation_id": doc.id,
                "conversation_name": data.get("conversation_name"),
                "preview": data.get("preview", ""),
                "last_created_at": data.get("last_created_at"),
                "last_id": data.get("last_id", 0),
                "message_count": data.get("message_count", 0),
                "unread": data.get("unread", False),
                "needs_attention": data.get("needs_attention", False),
            }
        )
    return summaries


def open_conversation(conversation_id: str) -> list[dict]:
    """Open a thread: mark every row read, clear attention, and return the rows.

    Only the rows that actually change are written, plus the parent aggregate.
    """
    conv_ref = _conversation_ref(conversation_id)
    docs = list(conv_ref.collection(MESSAGES).order_by("id").stream())
    if not docs:
        return []

    batch = get_client().batch()
    rows = []
    for doc in docs:
        data = doc.to_dict()
        if not data.get("read", False) or data.get("needs_attention", False):
            batch.update(doc.reference, {"read": True, "needs_attention": False})
            data["read"] = True
            data["needs_attention"] = False
        rows.append(data)
    batch.set(conv_ref, {"unread": False, "needs_attention": False}, merge=True)
    batch.commit()
    return rows


def clear_attention(conversation_id: str) -> None:
    """Clear the needs-attention flag across a conversation."""
    conv_ref = _conversation_ref(conversation_id)
    docs = (
        conv_ref.collection(MESSAGES)
        .where(filter=FieldFilter("needs_attention", "==", True))
        .stream()
    )
    batch = get_client().batch()
    for doc in docs:
        batch.update(doc.reference, {"needs_attention": False})
    batch.set(conv_ref, {"needs_attention": False}, merge=True)
    batch.commit()


def latest_name(rows: list[dict]) -> str | None:
    """Latest non-null conversation_name among already-fetched rows (no query)."""
    return next((r["conversation_name"] for r in reversed(rows) if r["conversation_name"]), None)


def delete_conversation(conversation_id: str) -> None:
    """Delete a conversation: all message docs in batches, then the parent doc."""
    conv_ref = _conversation_ref(conversation_id)
    messages = conv_ref.collection(MESSAGES)
    while True:
        docs = list(messages.limit(400).stream())
        if not docs:
            break
        batch = get_client().batch()
        for doc in docs:
            batch.delete(doc.reference)
        batch.commit()
    conv_ref.delete()
