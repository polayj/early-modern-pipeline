#!/usr/bin/env python3
"""
04_graph/run_atom.py
Build a temporal knowledge graph from OCR + import record documents using ATOM
(itext2kg), then push the result to Neo4j.

ATOM extracts 5-tuples: (subject, relation, object, t_start, t_end)
Observation timestamps come from document metadata (Archive.org year field,
EEBO filename, or import record year range).

Usage:
    # Test on 50 docs first
    python pipeline/04_graph/run_atom.py --limit 50

    # Full run (resume-safe)
    python pipeline/04_graph/run_atom.py

    # Override Neo4j connection
    python pipeline/04_graph/run_atom.py \\
        --neo4j-uri bolt://192.168.1.100:7687 \\
        --neo4j-user neo4j --neo4j-password yourpassword

    # Use a smaller model for faster testing
    python pipeline/04_graph/run_atom.py --model qwen3:30b-a3b --limit 100

Config is saved to atom_config.yaml (gitignored) after first run.
Subsequent runs read defaults from that file.
"""

import argparse
import asyncio
import json
import os
import re
import sys
import yaml
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH  = PROJECT_ROOT / "atom_config.yaml"

DEFAULTS = {
    "neo4j_uri":       "bolt://localhost:7687",
    "neo4j_user":      "neo4j",
    "neo4j_password":  "password",
    "ollama_url":      os.environ.get("OLLAMA_URL",
                           f"http://{os.environ['OLLAMA_HOST']}" if "OLLAMA_HOST" in os.environ
                           else "http://localhost:11434"),
    "model":           "qwen3.5:35b",
    "embed_model":     "Qwen/Qwen3-Embedding-8B",
    "ocr_dir":         str(PROJECT_ROOT / "output/ocr_md"),
    "import_docs_dir": str(PROJECT_ROOT / "output/lightrag_input/import_docs"),
    "output_dir":      str(PROJECT_ROOT / "output/atom_output"),
    "chunk_size":      3000,   # chars — keeps each item under LLM context
    "chunk_overlap":   200,
    "max_workers":     4,      # parallel ATOM threads; match Ollama concurrency
    "ent_threshold":   0.8,
    "rel_threshold":   0.7,
}


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            loaded = yaml.safe_load(CONFIG_PATH.read_text()) or {}
            cfg.update(loaded)
        except Exception:
            pass
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(yaml.dump(cfg, default_flow_style=False))
    print(f"Config saved to {CONFIG_PATH}")


# ── Year extraction ───────────────────────────────────────────────────────────

_YEAR_RE = re.compile(r"\b(1[4-9]\d\d|20[0-2]\d)\b")


def _extract_year(text: str) -> int | None:
    m = _YEAR_RE.search(str(text))
    return int(m.group(1)) if m else None


def year_to_date_str(year: int | None) -> str:
    """Convert integer year to ISO date string for ATOM timestamps."""
    if year and 1400 <= year <= 2100:
        return f"{year}-01-01"
    return "unknown"


# ── Metadata loading (reused from build_graph.py logic) ──────────────────────

def load_doc_metadata(ocr_docs_dir: Path) -> dict[str, dict]:
    """
    Returns dict keyed by doc_id (e.g. archive_org__Some_Title) with
    fields: title, author, year (int or None).
    """
    meta = {}

    # archive_org: each doc in its own subdir with _metadata.json
    archive_dir = ocr_docs_dir / "archive_org"
    if archive_dir.exists():
        for subdir in archive_dir.iterdir():
            if not subdir.is_dir():
                continue
            doc_title = subdir.name
            candidates = list(subdir.glob("*_metadata.json"))
            if not candidates:
                continue
            try:
                data = json.loads(candidates[0].read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue

            safe_id = re.sub(r"[^\w\-.]", "_", doc_title)
            doc_id  = f"archive_org__{safe_id}"

            title = data.get("title") or data.get("Title") or doc_title
            if isinstance(title, list):
                title = title[0]

            creator = (data.get("creator") or data.get("Creator") or
                       data.get("author")  or data.get("Author") or "")
            if isinstance(creator, list):
                creator = creator[0]

            date = (data.get("date") or data.get("Date") or
                    data.get("year") or "")
            if isinstance(date, list):
                date = date[0]

            meta[doc_id] = {
                "title":  str(title).strip()[:200],
                "author": str(creator).strip()[:200],
                "year":   _extract_year(str(date)),
            }

    # EEBO: parse "Author - Year - Title.pdf" filenames
    eebo_dir = ocr_docs_dir / "EEBO"
    if eebo_dir.exists():
        for pdf in eebo_dir.glob("*.pdf"):
            stem = pdf.stem
            safe_base = re.sub(r"[^\w\-.]", "_", stem)
            doc_id    = f"EEBO__{safe_base}"
            parts = stem.split(" - ", 2)
            year = _extract_year(parts[1]) if len(parts) >= 2 else None
            meta[doc_id] = {
                "title":  parts[2].strip() if len(parts) >= 3 else stem,
                "author": parts[0].strip() if parts else "",
                "year":   year,
            }

    return meta


# ── Document loading ──────────────────────────────────────────────────────────

def load_documents(ocr_dir: Path, import_docs_dir: Path,
                   metadata: dict[str, dict],
                   limit: int = 0) -> list[dict]:
    """
    Returns list of dicts:
        {doc_id, text, year, date_str, source}
    """
    docs = []

    # Import record markdown docs — derive year from filename
    # Filename pattern: import__YYYY-YYYY__Location.md
    if import_docs_dir.exists():
        for md_path in sorted(import_docs_dir.glob("*.md")):
            m = re.search(r"import__(\d{4})-\d{4}__", md_path.name)
            year = int(m.group(1)) if m else None
            docs.append({
                "doc_id":   md_path.stem,
                "text":     md_path.read_text(encoding="utf-8", errors="replace"),
                "year":     year,
                "date_str": year_to_date_str(year),
                "source":   "import_records",
            })

    # OCR markdown docs
    if ocr_dir.exists():
        for md_path in sorted(ocr_dir.glob("*.md")):
            doc_id = md_path.stem
            m      = metadata.get(doc_id, {})
            year   = m.get("year")
            docs.append({
                "doc_id":   doc_id,
                "text":     md_path.read_text(encoding="utf-8", errors="replace"),
                "year":     year,
                "date_str": year_to_date_str(year),
                "source":   "ocr",
            })

    if limit > 0:
        docs = docs[:limit]

    return docs


# ── Text chunking ─────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping character-level chunks."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


# ── Resume tracking ───────────────────────────────────────────────────────────

def load_processed(output_dir: Path) -> set[str]:
    p = output_dir / "processed_docs.txt"
    if p.exists():
        return set(p.read_text().splitlines())
    return set()


def mark_processed(output_dir: Path, doc_id: str) -> None:
    p = output_dir / "processed_docs.txt"
    with p.open("a") as f:
        f.write(doc_id + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

async def run(args: argparse.Namespace, cfg: dict) -> None:
    # ── Lazy imports (require itext2kg, langchain) ────────────────────────────
    try:
        from itext2kg.atom import Atom
        from itext2kg import Neo4jStorage
    except ImportError:
        print("ERROR: itext2kg not installed. Run: pip install itext2kg")
        sys.exit(1)

    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        print("ERROR: langchain-ollama not installed. Run: pip install langchain-ollama")
        sys.exit(1)

    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        print("ERROR: langchain-huggingface not installed. "
              "Run: pip install langchain-huggingface sentence-transformers")
        sys.exit(1)

    output_dir = Path(cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    ocr_dir        = Path(cfg["ocr_dir"])
    import_docs_dir = Path(cfg["import_docs_dir"])
    ocr_docs_dir   = PROJECT_ROOT / "ocr_docs/unprocessed"

    print("=" * 60)
    print("emgraphrag — ATOM temporal KG extraction")
    print("=" * 60)
    print(f"OCR docs:      {ocr_dir}")
    print(f"Import docs:   {import_docs_dir}")
    print(f"Output:        {output_dir}")
    print(f"LLM:           {cfg['model']} via {cfg['ollama_url']}")
    print(f"Embed model:   {cfg['embed_model']}")
    print(f"Neo4j:         {cfg['neo4j_uri']}")
    print()

    # ── Load metadata + documents ─────────────────────────────────────────────
    print("Loading document metadata...")
    metadata = load_doc_metadata(ocr_docs_dir)
    print(f"  Metadata loaded for {len(metadata)} archive_org/EEBO docs")

    print("Loading documents...")
    all_docs = load_documents(ocr_dir, import_docs_dir, metadata, limit=args.limit)
    print(f"  Total docs: {len(all_docs)}")

    # ── Resume filtering ──────────────────────────────────────────────────────
    processed = load_processed(output_dir)
    docs = [d for d in all_docs if d["doc_id"] not in processed]
    print(f"  Already processed: {len(processed)}")
    print(f"  To process: {len(docs)}")

    if not docs:
        print("Nothing to do.")
        return

    # ── Initialise models ─────────────────────────────────────────────────────
    print()
    print(f"Loading embedding model: {cfg['embed_model']} ...")
    print("  (First run downloads ~16GB — subsequent runs load from cache)")
    embeddings_model = HuggingFaceEmbeddings(
        model_name=cfg["embed_model"],
        model_kwargs={"device": "cuda"},
        encode_kwargs={"normalize_embeddings": True},
    )

    print(f"Connecting to Ollama: {cfg['ollama_url']}")
    llm_model = ChatOllama(
        model=cfg["model"],
        base_url=cfg["ollama_url"],
        temperature=0,
    )

    atom = Atom(llm_model=llm_model, embeddings_model=embeddings_model)

    # ── Build atomic facts dict grouped by observation date ───────────────────
    # ATOM's input: {date_str: [text_chunk, text_chunk, ...]}
    # We chunk large documents so each item stays within LLM context limits.
    print()
    print("Chunking documents...")
    facts_by_date: dict[str, list[str]] = {}
    chunk_to_doc: dict[str, str] = {}   # for tracking which doc each chunk belongs to

    for doc in docs:
        chunks = chunk_text(doc["text"], cfg["chunk_size"], cfg["chunk_overlap"])
        date_str = doc["date_str"]
        if date_str not in facts_by_date:
            facts_by_date[date_str] = []
        for chunk in chunks:
            facts_by_date[date_str].append(chunk)

    total_chunks = sum(len(v) for v in facts_by_date.items())
    print(f"  {len(docs)} docs → chunks across {len(facts_by_date)} distinct dates")
    print()

    # ── Run ATOM ──────────────────────────────────────────────────────────────
    print("Running ATOM graph extraction...")
    print(f"  max_workers={cfg['max_workers']}, "
          f"ent_threshold={cfg['ent_threshold']}, "
          f"rel_threshold={cfg['rel_threshold']}")
    print("  (This will take a long time for large corpora — resume-safe)")
    print()

    kg = await atom.build_graph_from_different_obs_times(
        atomic_facts_with_obs_timestamps=facts_by_date,
        ent_threshold=cfg["ent_threshold"],
        rel_threshold=cfg["rel_threshold"],
        max_workers=cfg["max_workers"],
    )

    # ── Mark all docs as processed ────────────────────────────────────────────
    for doc in docs:
        mark_processed(output_dir, doc["doc_id"])

    print()
    print(f"KG built: {len(kg.entities)} entities, {len(kg.relations)} relations")

    # ── Push to Neo4j ─────────────────────────────────────────────────────────
    print()
    print(f"Pushing to Neo4j at {cfg['neo4j_uri']} ...")
    storage = Neo4jStorage(
        uri=cfg["neo4j_uri"],
        username=cfg["neo4j_user"],
        password=cfg["neo4j_password"],
    )
    storage.visualize_graph(knowledge_graph=kg)
    print("  Neo4j push complete.")
    print()
    print("=" * 60)
    print("ATOM extraction complete.")
    print(f"  View graph: http://<neo4j-host>:7474")
    print(f"  Login: {cfg['neo4j_user']} / {cfg['neo4j_password']}")
    print("=" * 60)


def main() -> None:
    cfg = load_config()

    parser = argparse.ArgumentParser(
        description="Build temporal knowledge graph with ATOM → Neo4j"
    )
    parser.add_argument("--limit",          type=int, default=0,
                        help="Process only first N docs (0 = all)")
    parser.add_argument("--neo4j-uri",      default=cfg["neo4j_uri"])
    parser.add_argument("--neo4j-user",     default=cfg["neo4j_user"])
    parser.add_argument("--neo4j-password", default=cfg["neo4j_password"])
    parser.add_argument("--ollama-url",     default=cfg["ollama_url"])
    parser.add_argument("--model",          default=cfg["model"])
    parser.add_argument("--embed-model",    default=cfg["embed_model"])
    parser.add_argument("--max-workers",    type=int, default=cfg["max_workers"])
    parser.add_argument("--chunk-size",     type=int, default=cfg["chunk_size"])
    parser.add_argument("--ocr-dir",        default=cfg["ocr_dir"])
    parser.add_argument("--import-docs-dir", default=cfg["import_docs_dir"])
    parser.add_argument("--output-dir",     default=cfg["output_dir"])
    parser.add_argument("--save-config",    action="store_true",
                        help="Save current settings to atom_config.yaml and exit")
    args = parser.parse_args()

    # Merge CLI args back into cfg
    cfg.update({
        "neo4j_uri":       args.neo4j_uri,
        "neo4j_user":      args.neo4j_user,
        "neo4j_password":  args.neo4j_password,
        "ollama_url":      args.ollama_url,
        "model":           args.model,
        "embed_model":     args.embed_model,
        "max_workers":     args.max_workers,
        "chunk_size":      args.chunk_size,
        "ocr_dir":         args.ocr_dir,
        "import_docs_dir": args.import_docs_dir,
        "output_dir":      args.output_dir,
    })

    save_config(cfg)
    if args.save_config:
        return

    asyncio.run(run(args, cfg))


if __name__ == "__main__":
    main()
