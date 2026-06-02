"""Chunk owner-knowledge markdown, embed changed chunks, and upsert to Firestore.

Stale chunks (from deleted files or removed sections) are soft-disabled with
``is_active=false`` rather than deleted, so a bad ingest is corrected by fixing
the source and re-running.

Usage:
    cd backend
    uv run python scripts/ingest_knowledge.py --dry-run
    uv run python scripts/ingest_knowledge.py --verbose
    uv run python scripts/ingest_knowledge.py --force-reembed
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.cloud.firestore_v1.base_query import FieldFilter  # noqa: E402
from google.cloud.firestore_v1.vector import Vector  # noqa: E402

from app import db, embeddings  # noqa: E402
from app.chunker import Chunk, chunk_document  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.rag_service import KNOWLEDGE_CHUNKS  # noqa: E402

INGEST_RUNS = "knowledge_ingest_runs"
EXCLUDED_NAMES = {"style.md"}


def discover_files(knowledge_dir: Path, include_style: bool) -> list[Path]:
    """All markdown under the knowledge dir, excluding style.md by default."""
    files = sorted(knowledge_dir.rglob("*.md"))
    if include_style:
        return files
    return [f for f in files if f.name not in EXCLUDED_NAMES]


def collect_chunks(knowledge_dir: Path, files: list[Path], verbose: bool) -> list[Chunk]:
    """Chunk every discovered file into a flat list of chunks."""
    chunks: list[Chunk] = []
    for path in files:
        source_file = "knowledge/" + path.relative_to(knowledge_dir).as_posix()
        file_chunks = chunk_document(source_file, path.read_text(encoding="utf-8"))
        chunks.extend(file_chunks)
        if verbose:
            print(f"  {source_file}: {len(file_chunks)} chunks")
    return chunks


def upsert_chunk(chunk: Chunk, ingest_run_id: str, now: str, is_new: bool) -> None:
    """Write or update a chunk doc, embedding its text first."""
    settings = get_settings()
    vector = embeddings.embed_document(chunk.embed_text)
    doc = {
        "id": chunk.id,
        "source_file": chunk.source_file,
        "content_hash": chunk.content_hash,
        "chunk_index": chunk.chunk_index,
        "title": chunk.title,
        "heading_path": list(chunk.heading_path),
        "content": chunk.content,
        "prompt_text": chunk.prompt_text,
        "embedding": Vector(vector),
        "embedding_model": settings.rag_embedding_model,
        "embedding_dim": settings.rag_embedding_dim,
        "embedding_task_type": "RETRIEVAL_DOCUMENT",
        "category": chunk.category,
        "tags": list(chunk.tags),
        "priority": chunk.priority,
        "word_count": chunk.word_count,
        "is_active": True,
        "ingest_run_id": ingest_run_id,
        "updated_at": now,
    }
    if is_new:
        doc["created_at"] = now
    db.get_client().collection(KNOWLEDGE_CHUNKS).document(chunk.id).set(doc, merge=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest knowledge markdown into Firestore.")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without embedding or writing.")
    parser.add_argument("--verbose", action="store_true", help="Print per-file and per-chunk detail.")
    parser.add_argument("--force-reembed", action="store_true", help="Re-embed all chunks, ignoring hashes.")
    parser.add_argument("--include-style", action="store_true", help="Also ingest style.md (excluded by default).")
    args = parser.parse_args()

    settings = get_settings()
    knowledge_dir = settings.knowledge_dir
    files = discover_files(knowledge_dir, args.include_style)
    print(f"Discovered {len(files)} markdown file(s) under {knowledge_dir}")

    chunks = collect_chunks(knowledge_dir, files, args.verbose)
    print(f"Produced {len(chunks)} chunk(s)")

    client = db.get_client()
    collection = client.collection(KNOWLEDGE_CHUNKS)
    seen_ids = {c.id for c in chunks}

    # Fetch existing docs for the chunks we have, to compare hashes.
    refs = [collection.document(c.id) for c in chunks]
    existing = {}
    if refs:
        for snap in client.get_all(refs):
            if snap.exists:
                existing[snap.id] = snap.to_dict()

    to_embed = []
    skipped = 0
    for chunk in chunks:
        prior = existing.get(chunk.id)
        unchanged = (
            prior is not None
            and prior.get("content_hash") == chunk.content_hash
            and prior.get("embedding_model") == settings.rag_embedding_model
            and prior.get("embedding_dim") == settings.rag_embedding_dim
            and prior.get("is_active") is True
        )
        if unchanged and not args.force_reembed:
            skipped += 1
        else:
            to_embed.append(chunk)

    # Active docs whose ids are no longer produced -> mark inactive.
    stale_ids = []
    for snap in collection.where(filter=FieldFilter("is_active", "==", True)).stream():
        if snap.id not in seen_ids:
            stale_ids.append(snap.id)

    ingest_run_id = "ingest-" + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    now = datetime.now(timezone.utc).isoformat()

    print(f"  to embed/upsert: {len(to_embed)}")
    print(f"  skipped unchanged: {skipped}")
    print(f"  to mark inactive: {len(stale_ids)}")

    if args.dry_run:
        print("Dry run: no embeddings generated and nothing written.")
        if args.verbose:
            for chunk in to_embed:
                print(f"    would embed {chunk.id}")
            for stale in stale_ids:
                print(f"    would deactivate {stale}")
        return 0

    for chunk in to_embed:
        if args.verbose:
            print(f"    embedding {chunk.id}")
        upsert_chunk(chunk, ingest_run_id, now, is_new=chunk.id not in existing)

    if stale_ids:
        batch = client.batch()
        for stale in stale_ids:
            batch.update(collection.document(stale), {"is_active": False, "updated_at": now})
        batch.commit()

    client.collection(INGEST_RUNS).document(ingest_run_id).set(
        {
            "id": ingest_run_id,
            "status": "success",
            "finished_at": now,
            "files_seen": len(files),
            "chunks_seen": len(chunks),
            "chunks_embedded": len(to_embed),
            "chunks_skipped_unchanged": skipped,
            "chunks_marked_inactive": len(stale_ids),
            "embedding_model": settings.rag_embedding_model,
            "embedding_dim": settings.rag_embedding_dim,
            "errors": [],
        }
    )
    print(f"Ingest run {ingest_run_id} complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
