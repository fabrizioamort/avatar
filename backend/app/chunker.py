"""Split owner-knowledge markdown into embeddable chunks by heading.

One chunk per ``##`` section (plus the intro under the ``#`` title). Sections
larger than the word target are split on paragraph boundaries. Each chunk gets a
deterministic id and a content hash so re-ingestion can skip unchanged chunks.
"""

import hashlib
import re
from dataclasses import dataclass

import yaml

MAX_WORDS = 800


@dataclass(frozen=True)
class Chunk:
    """One embeddable unit of owner knowledge."""

    id: str
    source_file: str
    chunk_index: int
    title: str
    category: str
    tags: tuple[str, ...]
    priority: int
    heading_path: tuple[str, ...]
    content: str
    embed_text: str
    prompt_text: str
    content_hash: str
    word_count: int


def _slug(text: str) -> str:
    """Lowercase, hyphen-separated slug suitable for a chunk id segment."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body); empty dict when no YAML frontmatter."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not match:
        return {}, text
    data = yaml.safe_load(match.group(1))
    return (data if isinstance(data, dict) else {}), match.group(2)


def _split_sections(body: str) -> tuple[str | None, list[tuple[str | None, str]]]:
    """Return (h1_title, [(h2_heading_or_None, section_body), ...])."""
    h1: str | None = None
    segments: list[tuple[str | None, str]] = []
    heading: str | None = None
    lines: list[str] = []

    def flush() -> None:
        text = "\n".join(lines).strip()
        if text:
            segments.append((heading, text))

    for line in body.splitlines():
        h1_match = re.match(r"^#\s+(.+)$", line)
        h2_match = re.match(r"^##\s+(.+)$", line)
        seen_content = bool(segments) or any(candidate.strip() for candidate in lines)
        if h1_match and h1 is None and not seen_content:
            h1 = h1_match.group(1).strip()
        elif h2_match:
            flush()
            heading = h2_match.group(1).strip()
            lines = []
        else:
            lines.append(line)
    flush()
    return h1, segments


def _split_by_paragraphs(text: str, max_words: int) -> list[str]:
    """Group blank-line-separated paragraphs into pieces under the word budget."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: list[str] = []
    current: list[str] = []
    count = 0
    for para in paragraphs:
        words = len(para.split())
        if current and count + words > max_words:
            pieces.append("\n\n".join(current))
            current, count = [], 0
        current.append(para)
        count += words
    if current:
        pieces.append("\n\n".join(current))
    return pieces or [text]


def _embed_text(title: str, category: str, tags: tuple[str, ...], heading: str, content: str) -> str:
    """Metadata-prefixed text that is actually embedded for retrieval."""
    lines = [f"Title: {title}"]
    if category:
        lines.append(f"Category: {category}")
    if tags:
        lines.append(f"Tags: {', '.join(tags)}")
    lines.append(f"Section: {heading}")
    lines.append("")
    lines.append(content)
    return "\n".join(lines)


def _prompt_text(heading_path: tuple[str, ...], content: str) -> str:
    """Markdown rendering used for prompt context and attribution."""
    heads = [f"## {heading_path[0]}"]
    heads += [f"### {h}" for h in heading_path[1:]]
    return "\n".join(heads) + "\n" + content


def chunk_document(source_file: str, text: str) -> list[Chunk]:
    """Chunk one markdown document into ``Chunk`` objects.

    ``source_file`` is the path stored on each chunk (e.g. ``knowledge/foo.md``);
    a leading ``knowledge/`` and the ``.md`` suffix are stripped for the id slug.
    """
    frontmatter, body = split_frontmatter(text)
    h1, segments = _split_sections(body)

    rel = re.sub(r"^knowledge/", "", source_file)
    rel = re.sub(r"\.md$", "", rel)
    default_title = rel.rsplit("/", 1)[-1].replace("-", " ").title()
    title = str(frontmatter.get("title") or h1 or default_title)

    category = str(frontmatter.get("category") or (rel.split("/")[0] if "/" in rel else "general"))
    tags = tuple(str(t) for t in (frontmatter.get("tags") or []))
    priority = int(frontmatter.get("priority") or 0)

    chunks: list[Chunk] = []
    index = 0
    for heading, section_body in segments:
        heading_label = heading or "Overview"
        for piece in _split_by_paragraphs(section_body, MAX_WORDS):
            heading_path = (title,) if heading is None else (title, heading)
            embed_text = _embed_text(title, category, tags, heading_label, piece)
            chunks.append(
                Chunk(
                    id=f"{_slug(rel)}--{_slug(heading_label)}--{index:03d}",
                    source_file=source_file,
                    chunk_index=index,
                    title=title,
                    category=category,
                    tags=tags,
                    priority=priority,
                    heading_path=heading_path,
                    content=piece,
                    embed_text=embed_text,
                    prompt_text=_prompt_text(heading_path, piece),
                    content_hash=hashlib.sha256(embed_text.encode("utf-8")).hexdigest(),
                    word_count=len(piece.split()),
                )
            )
            index += 1
    return chunks
