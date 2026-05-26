#!/usr/bin/env python3
"""
05_lightrag/ingest.py
Ingest all documents into LightRAG (OCR markdown + import record docs).

LightRAG builds a knowledge graph + vector index using the local Ollama LLM
and embedding model specified in lightrag_config.yaml.

Inputs:
    output/lightrag_input/import_docs/*.md   (from step 01 or 04)
    output/ocr_md/*.md                       (from step 02)

Usage:
    python pipeline/05_lightrag/ingest.py
    python pipeline/05_lightrag/ingest.py --config lightrag_config.yaml
    python pipeline/05_lightrag/ingest.py --limit 100 --dry-run
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from tqdm import tqdm

# ── Load config ────────────────────────────────────────────────────────────────
def load_config(config_path: Path) -> dict:
    """Load lightrag_config.yaml (simple key: value parser, no pyyaml needed)."""
    config = {}
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        print("  Run pipeline/05_lightrag/setup.py first.")
        sys.exit(1)

    for line in config_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            config[key.strip()] = value.strip()

    return config


def get_lightrag(config: dict):
    """Initialise and return a LightRAG instance."""
    try:
        from lightrag import LightRAG, QueryParam
        from lightrag.llm.ollama import ollama_model_complete, ollama_embed
        from lightrag.utils import EmbeddingFunc
    except ImportError:
        print("ERROR: lightrag-hku not installed. Run: pip install lightrag-hku")
        sys.exit(1)

    working_dir = config.get("working_dir", "output/lightrag_storage")
    Path(working_dir).mkdir(parents=True, exist_ok=True)

    llm_model = config.get("llm_model", "qwen3.5:35b")
    embed_model = config.get("embedding_model", "nomic-embed-text")
    ollama_url = config.get("ollama_base_url", "http://localhost:11434")
    max_tokens = int(config.get("max_tokens", 32768))
    max_async = int(config.get("max_async", 4))
    chunk_size = int(config.get("chunk_size", 1200))
    chunk_overlap = int(config.get("chunk_overlap", 100))

    rag = LightRAG(
        working_dir=working_dir,
        llm_model_func=lambda prompt, **kw: ollama_model_complete(
            prompt,
            model=llm_model,
            host=ollama_url,
            **kw,
        ),
        embedding_func=EmbeddingFunc(
            embedding_dim=768,
            max_token_size=8192,
            func=lambda texts: ollama_embed(
                texts,
                embed_model=embed_model,
                host=ollama_url,
            ),
        ),
        chunk_token_size=chunk_size,
        chunk_overlap_token_size=chunk_overlap,
        llm_model_max_token_size=max_tokens,
        max_async=max_async,
    )
    return rag


def collect_docs(import_docs_dir: Path, ocr_dir: Path, limit: int = 0) -> list[Path]:
    """Collect all markdown files to ingest."""
    docs = []

    if import_docs_dir.exists():
        docs.extend(sorted(import_docs_dir.glob("*.md")))
    else:
        print(f"WARN: Import docs dir not found: {import_docs_dir}")
        print("  Run pipeline/01_parse_import_records.py or pipeline/04_graph/import_records_to_docs.py")

    if ocr_dir.exists():
        docs.extend(sorted(ocr_dir.glob("*.md")))
    else:
        print(f"WARN: OCR markdown dir not found: {ocr_dir}")
        print("  Run pipeline/02_ocr/run_ocr.sh on the school computer first.")

    if limit > 0:
        docs = docs[:limit]

    return docs


def load_progress(progress_file: Path) -> set[str]:
    """Load set of already-ingested doc IDs (resume support)."""
    if not progress_file.exists():
        return set()
    done = set()
    for line in progress_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            done.add(line)
    return done


def save_progress(progress_file: Path, doc_id: str):
    with open(progress_file, "a", encoding="utf-8") as f:
        f.write(doc_id + "\n")


async def ingest_batch(rag, texts: list[str]):
    """Ingest a batch of text documents asynchronously."""
    await rag.ainsert(texts)


def main():
    parser = argparse.ArgumentParser(
        description="Ingest documents into LightRAG."
    )
    parser.add_argument(
        "--config", default="lightrag_config.yaml",
        help="Path to lightrag_config.yaml"
    )
    parser.add_argument(
        "--import-docs", default="output/lightrag_input/import_docs",
        help="Import record markdown docs directory"
    )
    parser.add_argument(
        "--ocr-dir", default="output/ocr_md",
        help="OCR markdown directory"
    )
    parser.add_argument(
        "--batch-size", type=int, default=10,
        help="Documents per async batch (default: 10)"
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Only ingest first N docs (0 = all)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List docs that would be ingested, without actually ingesting"
    )
    args = parser.parse_args()

    config = load_config(Path(args.config))
    working_dir = config.get("working_dir", "output/lightrag_storage")
    progress_file = Path(working_dir) / "ingested_docs.txt"

    docs = collect_docs(
        Path(args.import_docs),
        Path(args.ocr_dir),
        limit=args.limit,
    )

    if not docs:
        print("No documents found to ingest.")
        sys.exit(0)

    done = load_progress(progress_file)
    pending = [d for d in docs if d.stem not in done]

    print(f"Documents found:    {len(docs)}")
    print(f"Already ingested:   {len(done)}")
    print(f"Pending:            {len(pending)}")

    if args.dry_run:
        print("\n-- DRY RUN -- (first 20 pending docs)")
        for d in pending[:20]:
            print(f"  {d}")
        return

    if not pending:
        print("All documents already ingested.")
        return

    print(f"\nInitialising LightRAG (working dir: {working_dir})...")
    rag = get_lightrag(config)

    # Process in batches
    total_ingested = 0
    total_failed = 0
    batch_size = args.batch_size

    for i in tqdm(range(0, len(pending), batch_size), desc="Ingesting batches"):
        batch_paths = pending[i : i + batch_size]
        texts = []
        path_stems = []

        for p in batch_paths:
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
                if text.strip():
                    texts.append(text)
                    path_stems.append(p.stem)
            except Exception as e:
                print(f"\nWARN: Could not read {p}: {e}")
                total_failed += 1

        if not texts:
            continue

        try:
            asyncio.run(ingest_batch(rag, texts))
            for stem in path_stems:
                save_progress(progress_file, stem)
            total_ingested += len(texts)
        except Exception as e:
            print(f"\nERROR ingesting batch {i // batch_size + 1}: {e}")
            total_failed += len(texts)

    print(f"\n── Ingestion complete ──────────────────────────────")
    print(f"  Ingested: {total_ingested}")
    print(f"  Failed:   {total_failed}")
    print(f"  Storage:  {working_dir}")
    print(f"────────────────────────────────────────────────────")
    print(f"\nRun queries with:")
    print(f"  python pipeline/05_lightrag/query.py 'Your question here'")


if __name__ == "__main__":
    main()
