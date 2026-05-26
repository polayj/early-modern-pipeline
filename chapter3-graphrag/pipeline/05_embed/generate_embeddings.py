#!/usr/bin/env python3
"""
05_embed/generate_embeddings.py
Embed OCR + import record documents with Qwen3-Embedding-8B and store in
ChromaDB for semantic vector search.

ChromaDB can run in two modes:
  - Server mode (recommended): ChromaDB running on Unraid, accessible over LAN
  - Local persistent mode: fallback if server is not reachable

Usage:
    # Test on 50 docs (local mode fallback)
    python pipeline/05_embed/generate_embeddings.py --limit 50

    # Full run against Unraid server
    python pipeline/05_embed/generate_embeddings.py \\
        --chroma-host 192.168.1.100 --chroma-port 8000

    # Local persistent mode (no server)
    python pipeline/05_embed/generate_embeddings.py --chroma-local

Resume-safe: already-embedded doc IDs are tracked in ChromaDB metadata and
skipped on re-run.
"""

import argparse
import re
import sys
import time
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULTS = {
    "chroma_host":      "localhost",
    "chroma_port":      8000,
    "chroma_local_dir": str(PROJECT_ROOT / "output/chromadb"),
    "collection":       "emgraphrag",
    "embed_model":      "Qwen/Qwen3-Embedding-8B",
    "chunk_size":       1200,    # tokens (approximate via chars ÷ 4)
    "chunk_overlap":    100,
    "batch_size":       32,      # docs to embed per batch
}

# ── Text chunking ─────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_chars: int, overlap_chars: int) -> list[str]:
    if len(text) <= chunk_chars:
        return [text.strip()] if text.strip() else []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_chars
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_chars - overlap_chars
    return chunks


# ── Document loading ──────────────────────────────────────────────────────────

def load_documents(input_dirs: list[Path], limit: int = 0) -> list[dict]:
    docs = []
    for d in input_dirs:
        if not d.exists():
            print(f"  Warning: {d} does not exist, skipping.")
            continue
        for md_path in sorted(d.glob("*.md")):
            text = md_path.read_text(encoding="utf-8", errors="replace").strip()
            if not text:
                continue
            docs.append({
                "doc_id": md_path.stem,
                "text":   text,
                "source": d.name,
            })
    if limit > 0:
        docs = docs[:limit]
    return docs


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Embed documents with Qwen3-Embedding-8B → ChromaDB"
    )
    parser.add_argument("--chroma-host",    default=DEFAULTS["chroma_host"])
    parser.add_argument("--chroma-port",    type=int, default=DEFAULTS["chroma_port"])
    parser.add_argument("--chroma-local",   action="store_true",
                        help="Use local persistent ChromaDB instead of server")
    parser.add_argument("--chroma-local-dir", default=DEFAULTS["chroma_local_dir"])
    parser.add_argument("--collection",     default=DEFAULTS["collection"])
    parser.add_argument("--embed-model",    default=DEFAULTS["embed_model"])
    parser.add_argument("--chunk-size",     type=int, default=DEFAULTS["chunk_size"],
                        help="Approximate tokens per chunk (chars ÷ 4)")
    parser.add_argument("--chunk-overlap",  type=int, default=DEFAULTS["chunk_overlap"])
    parser.add_argument("--batch-size",     type=int, default=DEFAULTS["batch_size"])
    parser.add_argument("--input-dirs",     nargs="+",
                        default=[
                            str(PROJECT_ROOT / "output/ocr_md"),
                            str(PROJECT_ROOT / "output/lightrag_input/import_docs"),
                        ])
    parser.add_argument("--limit",          type=int, default=0,
                        help="Process only first N docs (0 = all)")
    parser.add_argument("--watch",          action="store_true",
                        help="Watch mode: poll for new OCR/doc files as they appear")
    parser.add_argument("--done-sentinel",  default="output/ocr_complete.sentinel",
                        help="Sentinel file indicating OCR is done "
                             "(default: output/ocr_complete.sentinel)")
    parser.add_argument("--poll-interval",  type=int, default=60,
                        help="Seconds between polls in watch mode (default: 60)")
    args = parser.parse_args()

    chunk_chars   = args.chunk_size * 4   # rough chars-per-token conversion
    overlap_chars = args.chunk_overlap * 4

    # ── Lazy imports ─────────────────────────────────────────────────────────
    try:
        import chromadb
    except ImportError:
        print("ERROR: chromadb not installed. Run: pip install chromadb")
        sys.exit(1)

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("ERROR: sentence-transformers not installed. "
              "Run: pip install sentence-transformers")
        sys.exit(1)

    # ── Connect to ChromaDB ───────────────────────────────────────────────────
    if args.chroma_local:
        local_dir = Path(args.chroma_local_dir)
        local_dir.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(local_dir))
        print(f"ChromaDB: local persistent at {local_dir}")
    else:
        try:
            client = chromadb.HttpClient(host=args.chroma_host, port=args.chroma_port)
            client.heartbeat()
            print(f"ChromaDB: server at {args.chroma_host}:{args.chroma_port}")
        except Exception as e:
            print(f"WARNING: Could not connect to ChromaDB server ({e})")
            print(f"  Falling back to local persistent mode.")
            local_dir = Path(args.chroma_local_dir)
            local_dir.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(local_dir))
            print(f"  Local ChromaDB: {local_dir}")

    collection = client.get_or_create_collection(
        name=args.collection,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"Collection: '{args.collection}' ({collection.count()} existing chunks)")

    # ── Load documents ────────────────────────────────────────────────────────
    input_dirs = [Path(d) for d in args.input_dirs]
    print()
    print("Loading documents...")
    docs = load_documents(input_dirs, limit=args.limit)
    print(f"  {len(docs)} documents found")

    # ── Resume: skip already-embedded docs ───────────────────────────────────
    existing = set()
    try:
        # Query for all doc_ids already in the collection
        results = collection.get(include=["metadatas"])
        for meta in results["metadatas"]:
            if meta and "doc_id" in meta:
                existing.add(meta["doc_id"])
    except Exception:
        pass

    docs_to_process = [d for d in docs if d["doc_id"] not in existing]
    print(f"  Already embedded: {len(existing)} doc IDs")
    print(f"  To process: {len(docs_to_process)}")

    if not docs_to_process:
        print("Nothing to do.")
        return

    # ── Load embedding model ──────────────────────────────────────────────────
    print()
    print(f"Loading embedding model: {args.embed_model}")
    print("  (First run downloads ~16GB)")
    model = SentenceTransformer(args.embed_model, trust_remote_code=True)
    print("  Model loaded.")

    # ── Embed and store ───────────────────────────────────────────────────────
    print()
    total_chunks = 0
    processed_docs = 0

    for i in range(0, len(docs_to_process), args.batch_size):
        batch = docs_to_process[i : i + args.batch_size]
        batch_ids      = []
        batch_texts    = []
        batch_metas    = []

        for doc in batch:
            chunks = chunk_text(doc["text"], chunk_chars, overlap_chars)
            for j, chunk in enumerate(chunks):
                chunk_id = f"{doc['doc_id']}__chunk{j:04d}"
                batch_ids.append(chunk_id)
                batch_texts.append(chunk)
                batch_metas.append({
                    "doc_id":    doc["doc_id"],
                    "chunk_idx": j,
                    "source":    doc["source"],
                })

        if not batch_texts:
            continue

        # Embed — use no special prompt for documents (query prompt added at query time)
        embeddings = model.encode(
            batch_texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

        collection.add(
            ids=batch_ids,
            embeddings=embeddings,
            documents=batch_texts,
            metadatas=batch_metas,
        )

        total_chunks += len(batch_texts)
        processed_docs += len(batch)
        print(f"  [{processed_docs}/{len(docs_to_process)}] "
              f"Embedded {len(batch_texts)} chunks from {len(batch)} docs "
              f"(total chunks: {total_chunks})")

    # ── Watch mode: keep polling for new docs ─────────────────────────────
    if args.watch:
        sentinel = Path(args.done_sentinel)
        print(f"\nWatch mode: polling every {args.poll_interval}s for new docs...")
        print("  (Press Ctrl+C to stop manually)\n")

        while True:
            time.sleep(args.poll_interval)

            # Reload docs and check for new ones
            all_docs = load_documents(input_dirs, limit=0)
            # Refresh existing IDs from collection
            try:
                results = collection.get(include=["metadatas"])
                existing = set()
                for meta in results["metadatas"]:
                    if meta and "doc_id" in meta:
                        existing.add(meta["doc_id"])
            except Exception:
                pass

            new_docs = [d for d in all_docs if d["doc_id"] not in existing]

            if new_docs:
                print(f"  {len(new_docs)} new doc(s) found — embedding...")
                for i in range(0, len(new_docs), args.batch_size):
                    batch = new_docs[i : i + args.batch_size]
                    batch_ids      = []
                    batch_texts    = []
                    batch_metas    = []

                    for doc in batch:
                        chunks = chunk_text(doc["text"], chunk_chars, overlap_chars)
                        for j, chunk in enumerate(chunks):
                            chunk_id = f"{doc['doc_id']}__chunk{j:04d}"
                            batch_ids.append(chunk_id)
                            batch_texts.append(chunk)
                            batch_metas.append({
                                "doc_id":    doc["doc_id"],
                                "chunk_idx": j,
                                "source":    doc["source"],
                            })

                    if batch_texts:
                        embeddings = model.encode(
                            batch_texts,
                            normalize_embeddings=True,
                            show_progress_bar=False,
                        ).tolist()

                        collection.add(
                            ids=batch_ids,
                            embeddings=embeddings,
                            documents=batch_texts,
                            metadatas=batch_metas,
                        )

                        total_chunks += len(batch_texts)
                        processed_docs += len(batch)
                        print(f"    Embedded {len(batch_texts)} chunks from "
                              f"{len(batch)} docs (total: {collection.count()})")

            if sentinel.exists() and not new_docs:
                print("\nOCR sentinel found and queue empty — embedding complete.")
                Path("output/embeddings_complete.sentinel").write_text(
                    f"Embedding complete. {collection.count()} total chunks.\n"
                )
                break

    print()
    print("=" * 60)
    print("Embedding complete.")
    print(f"  Documents embedded: {processed_docs}")
    print(f"  Total chunks in collection: {collection.count()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
