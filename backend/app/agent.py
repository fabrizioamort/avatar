"""The Avatar agent: OpenRouter wiring, tools, system prompt, and streaming.

The conversation is three-way (visitor, avatar, human). The transcript is
rendered into a single task string passed to the agent; the agent always
replies only as the Avatar.
"""

import re
from collections.abc import AsyncIterator
from contextvars import ContextVar, Token

from agents import (
    Agent,
    Runner,
    function_tool,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
)
from openai import AsyncOpenAI
from openai.types.responses import ResponseTextDeltaEvent

from app import knowledge
from app import abuse
from app.config import get_settings
from app.models import ChatLanguage, Message
from app.push import push

_push_context: ContextVar[tuple[str, str] | None] = ContextVar("push_context", default=None)
_push_used: ContextVar[bool] = ContextVar("push_used", default=False)

_CONTACT_DETAIL_RE = re.compile(
    r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"
    r"|(?:\+?\d[\d\s().-]{6,}\d)"
    r"|linkedin\.com/\S+"
    r"|github\.com/\S+",
    re.IGNORECASE,
)
_CONTACT_INTENT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(get in touch|reach out|connect with|talk to|speak to|schedule (?:a )?(?:call|meeting)|book (?:a )?(?:call|meeting))\b",
        r"\b(contact|reach|email|e-mail|mail|message|call|phone|speak|talk|connect|meet)\b.{0,80}\b(fabrizio|owner|human|you|him)\b",
        r"\b(fabrizio|owner|human|you|him)\b.{0,80}\b(contact|reach|email|e-mail|mail|message|call|phone|speak|talk|connect|meet)\b",
        r"\b(contact|reach|email|e-mail|mail|message|call|phone)\b.{0,80}\b(me|us)\b",
        r"\b(email|e-mail|message|call|phone)\s+me\b",
        r"\b(my email|my e-mail|email is|e-mail is|contact me at|reach me at|call me at|my number)\b",
        r"\b(mettermi in contatto|metterci in contatto|entrare in contatto|restare in contatto|fissare una call|prenotare una call|fissare una chiamata|prenotare una chiamata|parlare con fabrizio|parlare con te|sentire fabrizio|mandami una mail|la mia email|la mia mail)\b",
        r"\b(contattarmi|contattarti|contattarla|ricontattarmi|ricontattarti|scrivimi|scriverti|chiamami|chiamarti|telefonarmi|telefonarti)\b",
        r"\b(contatt\w*|ricontatt\w*|scriv\w*|chiam\w*|telefon\w*)\b.{0,80}\b(me|mi|fabrizio|te|tu|lei|lui)\b",
        r"\b(mi|me|ti|le)\b.{0,80}\b(contatt\w*|ricontatt\w*|scriv\w*|chiam\w*|telefon\w*)\b",
    )
)


def configure_openrouter() -> None:
    """Point the Agents SDK at OpenRouter using the chat-completions API."""
    settings = get_settings()
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )
    set_default_openai_client(client)
    set_default_openai_api("chat_completions")
    set_tracing_disabled(True)


@function_tool
def faq_tool(number: int) -> str:
    """Look up the answer to a frequently asked question by its number.

    Args:
        number: The FAQ number to retrieve.
    """
    return knowledge.find_faq(number)


def handle_push_tool(message: str) -> str:
    """Handle push_tool execution with per-turn and quota guards."""
    context = _push_context.get()
    if context is None:
        return "Notification could not be delivered to the human owner."
    if _push_used.get():
        return "Notification already sent for this turn."
    conversation_id, source_ip = context
    identity = abuse.RequestIdentity(source_ip=source_ip)
    if not abuse.enforce_push_request(identity, conversation_id):
        return "Notification rate limit reached; the human owner was not notified."
    _push_used.set(True)
    return push(message)


@function_tool
def push_tool(message: str) -> str:
    """Send a push notification to the human owner (your human twin) so they can follow up.

    Args:
        message: The note to send to the human owner.
    """
    return handle_push_tool(message)


def set_push_context(conversation_id: str, source_ip: str) -> tuple[Token, Token]:
    """Scope push quotas to the active chat turn."""
    return (
        _push_context.set((conversation_id, source_ip)),
        _push_used.set(False),
    )


def reset_push_context(tokens: tuple[Token, Token]) -> None:
    """Restore push context after a chat turn."""
    context_token, used_token = tokens
    _push_context.reset(context_token)
    _push_used.reset(used_token)


def response_language_instruction(language: ChatLanguage = "en") -> str:
    """Return prompt guidance for the visitor-selected response language."""
    if language == "it":
        return (
            "Reply in Italian unless the visitor explicitly asks you to use another language. "
            "Keep names, links, product names, company names, and technical terms in their "
            "natural form when translating them would sound forced."
        )
    return (
        "Reply in English unless the visitor explicitly asks you to use another language. "
        "Keep names, links, product names, company names, and technical terms in their "
        "natural form."
    )


def is_contact_intent(message: str) -> bool:
    """Return True when the visitor is trying to contact the human owner."""
    normalized = " ".join(message.strip().split())
    if not normalized or re.fullmatch(r"q\d+", normalized, flags=re.IGNORECASE):
        return False
    return any(pattern.search(normalized) for pattern in _CONTACT_INTENT_PATTERNS)


def has_contact_detail(message: str) -> bool:
    """Return True when the visitor included an email, phone, or profile link."""
    return bool(_CONTACT_DETAIL_RE.search(message))


def build_contact_notification_message(message: str, visitor_name: str | None = None) -> str:
    """Build the immediate owner notification for a contact request."""
    visitor = visitor_name.strip() if visitor_name and visitor_name.strip() else "A visitor"
    compact = " ".join(message.strip().split())
    return f"{visitor} asked to contact you: {compact}"


def contact_intent_reply(
    owner: str,
    language: ChatLanguage,
    *,
    has_detail: bool,
    delivered: bool,
) -> str:
    """Return the deterministic reply after the backend handles contact intent."""
    if language == "it":
        if delivered:
            if has_detail:
                return f"Ho avvisato {owner} e gli ho passato il contesto che hai condiviso."
            return (
                f"Ho avvisato {owner} che vuoi metterti in contatto. "
                "Lascia anche la tua email e un po' di contesto per il follow-up diretto."
            )
        if has_detail:
            return f"Ho segnalato questa conversazione a {owner} con il contesto che hai condiviso."
        return (
            f"Ho segnalato questa conversazione a {owner}. "
            "Lascia anche la tua email e un po' di contesto per il follow-up diretto."
        )

    if delivered:
        if has_detail:
            return f"I've notified {owner} and included the context you shared."
        return (
            f"I've notified {owner} that you'd like to get in touch. "
            f"Leave your email and a bit of context if you want {owner} to follow up directly."
        )
    if has_detail:
        return f"I've flagged this conversation for {owner} with the context you shared."
    return (
        f"I've flagged this conversation for {owner}. "
        f"Leave your email and a bit of context if you want {owner} to follow up directly."
    )


def build_system_prompt(retrieved_knowledge: str = "", language: ChatLanguage = "en") -> str:
    """Assemble the full multi-way system prompt for the Avatar.

    ``retrieved_knowledge`` is the RAG-retrieved profile context for the current
    turn; it replaces the full static profile that used to be injected wholesale.
    """
    settings = get_settings()
    owner = settings.owner_name
    return f"""# Your role

You are the digital twin of {owner}, an AI chatting with visitors on {owner}'s website.
You represent {owner} professionally, as if speaking to a potential client or future employer.
If asked, say clearly that you are an AI digital twin of {owner}.

# Response language

{response_language_instruction(language)}

# Relevant knowledge about {owner}

The following first-person knowledge about {owner} was retrieved for this conversation. Speak as
{owner}'s digital twin, drawing on it to answer questions about their career, background, skills,
experience and courses. If it is insufficient, do not invent: say you do not know and use push_tool.

{retrieved_knowledge}

# Your style and voice

Match {owner}'s voice and follow these style and safety rules:

{knowledge.style_text()}

# The three-way conversation

The transcript may contain three speakers:
- Visitor: the guest you are talking to.
- Avatar: you, the digital twin.
- {owner} (the human): the real {owner}, who can join the conversation live from an admin panel.

When {owner} (the human) has posted a message, treat their words as authoritative and final.
Never contradict them, never impersonate them, and never pretend to be the human.
Continue the conversation naturally and do not repeat what the human already said.
You only ever speak as the Avatar.

# FAQ

Your faq_tool contains answers to common questions. Below is the list of questions by number.
If the visitor's question relates to one of these, call faq_tool with the number to retrieve the
original answer, and reply with that answer, keeping its Markdown links exactly as written so they
stay clickable (never flatten a link into a bare URL).

List of questions by number:
{knowledge.faq_list_text()}

# Rules

Stay on topic. Answer questions about {owner}, {owner}'s career, background, projects, skills,
experience, availability, AI/software architecture, and adjacent professional topics.
If the visitor asks a standalone question outside that scope, such as sports predictions,
politics, entertainment, generic trivia, or unrelated advice, briefly say you can only help with
questions about {owner}'s work and adjacent AI/software topics. Do not answer the off-topic
question, do not offer analysis or shortlists about it, and do not use push_tool for off-topic
questions unless the visitor also asks to contact {owner}.

If you do not know the answer, do not invent one: tell the visitor you do not know and call
push_tool to record the question for {owner}.

Contact capture: if the visitor wants to get in touch, call push_tool immediately with the context.
If they have not provided an email or other contact detail, ask for it after notifying {owner}.
Never wait for the email before notifying {owner}.

Do not use code blocks; the chat renders bold, links, inline `code` and short lists, but not code fences.
Output only the Avatar's next reply text. Do not prefix it with "Avatar:".
"""


def build_agent(retrieved_knowledge: str = "", language: ChatLanguage = "en") -> Agent:
    """Construct the Avatar agent with its tools and retrieved knowledge."""
    settings = get_settings()
    return Agent(
        name="Avatar",
        instructions=build_system_prompt(retrieved_knowledge, language),
        model=settings.model,
        tools=[faq_tool, push_tool],
    )


def render_transcript(rows: list[Message], owner_name: str, max_chars: int | None = None) -> str:
    """Render prior messages as labelled lines, ending with a reply instruction."""
    lines = []
    for row in rows:
        if row.role == "visitor":
            lines.append(f"Visitor: {row.content}")
        elif row.role == "avatar":
            lines.append(f"Avatar: {row.content}")
        else:
            lines.append(f"{owner_name} (the human): {row.content}")
    suffix = "\n\nReply as the Avatar:"
    transcript = "\n".join(lines)
    rendered = f"{transcript}{suffix}"
    limit = max_chars if max_chars is not None else get_settings().max_transcript_chars
    if len(rendered) <= limit:
        return rendered

    notice = "[...older conversation omitted...]\n"
    budget = max(limit - len(suffix), 0)
    selected: list[str] = []
    used = 0
    for line in reversed(lines):
        extra = len(line) + (1 if selected else 0)
        if used + extra > budget:
            break
        selected.append(line)
        used += extra
    if selected:
        body = "\n".join(reversed(selected))
    else:
        body = transcript[-budget:] if budget else ""
    if len(body) + len(notice) + len(suffix) <= limit:
        body = f"{notice}{body}"
    return f"{body}{suffix}"


async def stream_agent(
    transcript: str,
    retrieved_knowledge: str = "",
    language: ChatLanguage = "en",
) -> AsyncIterator[dict]:
    """Stream the Avatar's reply, yielding tool, token, and a final internal event."""
    agent = build_agent(retrieved_knowledge, language)
    result = Runner.run_streamed(agent, transcript)
    tool_calls: list[dict] = []
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            if event.data.delta:
                yield {"type": "token", "text": event.data.delta}
        elif event.type == "run_item_stream_event":
            if event.name == "tool_called":
                name = event.item.tool_name
                tool_calls.append({"tool": name})
                yield {"type": "tool", "phase": "called", "tool": name}
    yield {"type": "_final", "text": result.final_output, "tool_calls": tool_calls}
