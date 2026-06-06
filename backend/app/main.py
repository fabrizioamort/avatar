"""FastAPI app: public + admin APIs, SSE chat, and static frontend serving."""

import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Cookie, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.sse import EventSourceResponse
from fastapi.staticfiles import StaticFiles

from app import abuse, agent, db, knowledge, rag_service
from app.auth import (
    clear_session_cookie,
    issue_visitor_token,
    is_authenticated,
    require_admin,
    set_session_cookie,
    verify_visitor_token,
    verify_password,
)
from app.config import get_settings
from app.models import (
    ChatRequest,
    ConfigResponse,
    ConversationSession,
    ConversationSummary,
    ConversationThread,
    HumanMessageRequest,
    LoginRequest,
    Message,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wire up OpenRouter once at startup."""
    agent.configure_openrouter()
    yield


app = FastAPI(title="Avatar", lifespan=lifespan)

# Dev only: let the static site's local dev origin call /api during development.
# Public visitor calls are not credentialed, so a plain (no-credentials) CORS
# allowance is enough. Set DEV_CORS_ORIGINS only in the local .env, never in prod.
_dev_origins = [o for o in os.getenv("DEV_CORS_ORIGINS", "").split(",") if o]
if _dev_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_dev_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

api = APIRouter(prefix="/api")
admin = APIRouter(prefix="/admin")


# ---- Abuse guards (cheap protection for the API key) ----

MAX_MESSAGE_CHARS = get_settings().max_message_chars
TRUNCATION_NOTE = (
    "[...message truncated as it's too long; ask the visitor to send something more concise]"
)


def clamp_message(text: str) -> str:
    """Cap over-long visitor input so a single paste can't run up LLM token spend."""
    limit = get_settings().max_message_chars
    if len(text) <= limit:
        return text
    return text[:limit] + " " + TRUNCATION_NOTE


async def enforce_public_chat_guard(request: Request) -> None:
    """Reject invalid or abusive chat before writes, RAG, or model calls."""
    body = await request.json()
    conversation_id = str(body.get("conversation_id", ""))
    token = body.get("conversation_token")
    if not verify_visitor_token(conversation_id, token if isinstance(token, str) else None):
        raise HTTPException(status_code=403, detail="Invalid conversation session.")

    identity = abuse.identify_request(request)
    abuse.enforce_chat_request(identity, conversation_id)

    meta = db.get_conversation_meta(conversation_id)
    if meta.get("message_count", 0) >= get_settings().max_conversation_messages:
        raise HTTPException(
            status_code=429,
            detail="This conversation is too long; please start a new one.",
        )
    request.state.source_ip = identity.source_ip


# ---- Public API ----


@api.get("/config", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    """Owner name and other public config."""
    return ConfigResponse(owner_name=get_settings().owner_name)


@api.post("/conversations", response_model=ConversationSession)
def create_conversation() -> ConversationSession:
    """Create a server-issued visitor conversation session."""
    conversation_id = str(uuid.uuid4())
    return ConversationSession(
        conversation_id=conversation_id,
        conversation_token=issue_visitor_token(conversation_id),
    )


@api.get("/conversations/{conversation_id}", response_model=ConversationThread)
def get_conversation(
    conversation_id: str,
    after: int | None = None,
    conversation_token: str | None = Header(default=None, alias="X-Avatar-Conversation-Token"),
) -> ConversationThread:
    """Full thread (all roles) for restore-from-cookie and visitor polling."""
    if not conversation_token:
        raise HTTPException(status_code=401, detail="Missing conversation session.")
    if not verify_visitor_token(conversation_id, conversation_token):
        raise HTTPException(status_code=403, detail="Invalid conversation session.")
    rows = db.get_messages(conversation_id, after_id=after)
    return ConversationThread(
        conversation_id=conversation_id,
        conversation_name=db.latest_name(rows),
        messages=[Message(**row) for row in rows],
    )


async def _chat_events(request: ChatRequest, source_ip: str) -> AsyncIterator[dict]:
    """Drive a chat turn and yield wire events for the SSE stream."""
    settings = get_settings()
    message = clamp_message(request.message)
    db.insert_message(
        request.conversation_id,
        "visitor",
        message,
        conversation_name=request.visitor_name,
        read=False,
    )

    instant = knowledge.instant_faq_number(message)
    if instant is not None:
        answer = knowledge.get_instant_answer(instant)
        row = db.insert_message(
            request.conversation_id,
            "avatar",
            answer,
            tool_calls=[{"type": "instant", "faq": instant}],
        )
        yield {"type": "instant", "faq": instant}
        yield {"type": "token", "text": answer}
        yield {"type": "done", "message_id": row["id"], "needs_attention": False}
        return

    retrieved_text = ""
    if settings.rag_enabled:
        yield {"type": "phase", "phase": "searching"}
        retrieved = rag_service.retrieve_knowledge(message)
        retrieved_text = rag_service.format_retrieved_context(retrieved)
    if not retrieved_text:
        # No confident chunk (or RAG disabled): fall back to the static profile.
        retrieved_text = knowledge.knowledge_text()

    rows = [Message(**r) for r in db.get_messages(request.conversation_id)]
    transcript = agent.render_transcript(rows, settings.owner_name, settings.max_transcript_chars)
    yield {"type": "phase", "phase": "thinking"}
    push_tokens = agent.set_push_context(request.conversation_id, source_ip)
    try:
        async for event in agent.stream_agent(transcript, retrieved_text):
            if event["type"] == "_final":
                tool_names = [tc["tool"] for tc in event["tool_calls"]]
                needs_attention = "push_tool" in tool_names
                row = db.insert_message(
                    request.conversation_id,
                    "avatar",
                    event["text"],
                    tool_calls=event["tool_calls"] or None,
                    needs_attention=needs_attention,
                    read=not needs_attention,
                )
                yield {"type": "done", "message_id": row["id"], "needs_attention": needs_attention}
            else:
                yield event
    finally:
        agent.reset_push_context(push_tokens)


@api.post("/chat", response_class=EventSourceResponse, dependencies=[Depends(enforce_public_chat_guard)])
async def chat(request: ChatRequest, http_request: Request) -> AsyncIterator[dict]:
    """Stream the Avatar's reply as Server-Sent Events."""
    try:
        source_ip = getattr(http_request.state, "source_ip", "unknown")
        async for event in _chat_events(request, source_ip):
            yield event
    except Exception as exc:  # noqa: BLE001 - surface failures to the client
        yield {"type": "error", "message": str(exc)}


# ---- Admin API ----


@admin.post("/login")
def login(request: LoginRequest, response: Response, http_request: Request) -> dict:
    """Validate the admin password and set a session cookie."""
    identity = abuse.identify_request(http_request)
    abuse.enforce_admin_login_request(identity)
    if not verify_password(request.password):
        import logging

        logging.getLogger(__name__).warning(
            "Failed admin login attempt from source=%s",
            identity.source_ip,
        )
        raise HTTPException(status_code=401, detail="Invalid password")
    set_session_cookie(response)
    return {"ok": True}


@admin.post("/logout")
def logout(response: Response) -> dict:
    """Clear the admin session cookie."""
    clear_session_cookie(response)
    return {"ok": True}


@admin.get("/me")
def me(avatar_admin: str | None = Cookie(default=None)) -> dict:
    """Login-gate probe: 200 when authenticated, else 401."""
    if not is_authenticated(avatar_admin):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"authenticated": True}


@admin.get("/conversations", response_model=list[ConversationSummary], dependencies=[Depends(require_admin)])
def admin_list_conversations() -> list[ConversationSummary]:
    """Inbox summaries, most recent first."""
    return [ConversationSummary(**s) for s in db.list_conversations()]


@admin.get(
    "/conversations/{conversation_id}",
    response_model=ConversationThread,
    dependencies=[Depends(require_admin)],
)
def admin_get_conversation(conversation_id: str) -> ConversationThread:
    """Open a thread in one round-trip: mark read + clear attention and return the rows."""
    rows = db.open_conversation(conversation_id)
    return ConversationThread(
        conversation_id=conversation_id,
        conversation_name=db.latest_name(rows),
        messages=[Message(**row) for row in rows],
    )


@admin.post(
    "/conversations/{conversation_id}/messages",
    response_model=Message,
    dependencies=[Depends(require_admin)],
)
def admin_post_message(conversation_id: str, request: HumanMessageRequest) -> Message:
    """Insert a human message (the Avatar does not react to it)."""
    row = db.insert_message(
        conversation_id,
        "human",
        request.content,
        read=True,
        needs_attention=False,
    )
    return Message(**row)


@admin.post("/conversations/{conversation_id}/resolve", dependencies=[Depends(require_admin)])
def admin_resolve(conversation_id: str) -> dict:
    """Clear the needs-attention flag for a conversation."""
    db.clear_attention(conversation_id)
    return {"ok": True}


app.include_router(api)
app.include_router(admin)


# ---- Static frontend ----

settings = get_settings()
DIST = settings.frontend_dist


@app.get("/")
def index() -> FileResponse:
    """Serve the visitor page."""
    target = DIST / "index.html"
    if not target.exists():
        raise HTTPException(status_code=404, detail="Frontend not built")
    return FileResponse(target)


@app.get("/admin")
def admin_page() -> FileResponse:
    """Serve the admin page."""
    target = DIST / "admin.html"
    if not target.exists():
        raise HTTPException(status_code=404, detail="Frontend not built")
    return FileResponse(target)


if (DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST), name="static")
