"""Tests for the markdown chunker: sections, ids, hashing, splitting, frontmatter."""

from app.chunker import MAX_WORDS, chunk_document, split_frontmatter

SAMPLE = """# Jane Doe

Short intro paragraph about Jane.

## Background

Jane has worked in software for years.

## Expertise

Deep knowledge of distributed systems and cloud.
"""

FRONTMATTER = """---
title: System Design
category: expertise
tags:
  - architecture
  - scaling
priority: 2
---

# Ignored Heading

## Overview

Body text here.
"""


def test_splits_intro_and_sections():
    chunks = chunk_document("knowledge/knowledge.md", SAMPLE)
    headings = [c.heading_path for c in chunks]
    assert ("Jane Doe",) in headings
    assert ("Jane Doe", "Background") in headings
    assert ("Jane Doe", "Expertise") in headings


def test_deterministic_ids_and_index():
    chunks = chunk_document("knowledge/knowledge.md", SAMPLE)
    ids = [c.id for c in chunks]
    assert [c.chunk_index for c in chunks] == [0, 1, 2]
    assert chunks[0].id.endswith("--000")
    assert chunks[2].id.endswith("--002")
    # Re-chunking the same input yields identical ids and hashes.
    again = chunk_document("knowledge/knowledge.md", SAMPLE)
    assert [c.id for c in again] == ids
    assert [c.content_hash for c in again] == [c.content_hash for c in chunks]


def test_id_strips_knowledge_prefix_and_extension():
    chunks = chunk_document("knowledge/expertise/system-design.md", SAMPLE)
    assert chunks[1].id.startswith("expertise-system-design--background--")


def test_content_hash_changes_with_content():
    a = chunk_document("knowledge/k.md", SAMPLE)[0]
    b = chunk_document("knowledge/k.md", SAMPLE.replace("Short intro", "Different intro"))[0]
    assert a.content_hash != b.content_hash


def test_frontmatter_drives_metadata_and_title():
    chunks = chunk_document("knowledge/anything.md", FRONTMATTER)
    chunk = chunks[0]
    assert chunk.title == "System Design"
    assert chunk.category == "expertise"
    assert chunk.tags == ("architecture", "scaling")
    assert chunk.priority == 2


def test_split_frontmatter_absent():
    data, body = split_frontmatter("# No frontmatter\n\ntext")
    assert data == {}
    assert body.startswith("# No frontmatter")


def test_embed_text_includes_metadata():
    chunk = chunk_document("knowledge/anything.md", FRONTMATTER)[0]
    assert "Title: System Design" in chunk.embed_text
    assert "Category: expertise" in chunk.embed_text
    assert "Section: Overview" in chunk.embed_text


def test_prompt_text_renders_heading_path():
    chunk = chunk_document("knowledge/k.md", SAMPLE)[1]
    assert chunk.prompt_text.startswith("## Jane Doe\n### Background")


def test_large_section_splits_by_paragraphs():
    paras = "\n\n".join(["word " * 200 for _ in range(6)])  # ~1200 words
    text = f"# Title\n\n## Big\n\n{paras}\n"
    chunks = chunk_document("knowledge/k.md", text)
    big = [c for c in chunks if c.heading_path == ("Title", "Big")]
    assert len(big) > 1
    assert all(c.word_count <= MAX_WORDS for c in big)
