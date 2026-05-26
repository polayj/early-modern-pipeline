#!/usr/bin/env python3
"""
03_ner/link_entities.py
Link NER-extracted entities to Linked Open Data authority records.

Conforms to LINCS (Linked Infrastructure for Networked Cultural Heritage) practices:
- CIDOC-CRM ontology for entity class mapping
- Standard vocabularies: GeoNames, Wikidata, Getty AAT, VIAF

Two-pass architecture (batch mode):
  Pass 1: Collect unique entities → resolve each once → cache in SQLite
  Pass 2: Enrich per-doc NER files with cached results

Watch mode:
  Processes NER files as they appear, resolving new entities on-the-fly
  and enriching per-doc files incrementally. Stops when NER sentinel
  appears and queue is empty.

Output:
    output/entity_linking/per_doc/<doc_id>.jsonl     — enriched per-doc entities
    output/entity_linking/linked_entities.jsonl       — aggregate
    output/entity_linking/lookup_cache.db             — SQLite cache
    output/entity_linking/linking_summary.json        — statistics

Resume-safe: skips docs that already have a per-doc output file.

Usage:
    # Batch mode (NER already finished):
    python pipeline/03_ner/link_entities.py

    # Watch mode (run alongside NER — processes docs as they appear):
    python pipeline/03_ner/link_entities.py --watch
    python pipeline/03_ner/link_entities.py --watch --done-sentinel output/ner_complete.sentinel

    # Options:
    python pipeline/03_ner/link_entities.py --limit 50
    python pipeline/03_ner/link_entities.py --geonames-user myuser
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from tqdm import tqdm

# Local imports (same directory)
sys.path.insert(0, str(Path(__file__).parent))
from lod_lookups import LookupCache, get_cidoc_crm, lookup_entity
from normalizations import normalize_entity


def resolve_entity_cached(
    text: str,
    entity_type: str,
    cache: LookupCache,
    geonames_username: str = "",
    llm_url: str = "",
    llm_model: str = "",
) -> dict:
    """Resolve a single entity, using cache. Returns enrichment dict."""
    normalized = normalize_entity(text, entity_type)
    key_text = normalized.lower()

    # Check if already resolved
    cached = cache.get(key_text, entity_type, "resolved")
    if cached is not None:
        crm_class, crm_uri = get_cidoc_crm(entity_type)
        return {
            "normalized_text": normalized,
            "authority_uri": cached["authority_uri"],
            "authority_label": cached["authority_label"],
            "authority_source": cached["authority_source"],
            "cidoc_crm_class": crm_class,
            "cidoc_crm_uri": crm_uri,
            "confidence": cached["confidence"],
            "linked": cached["linked"],
        }

    try:
        result = lookup_entity(
            normalized_text=normalized,
            entity_type=entity_type,
            cache=cache,
            geonames_username=geonames_username,
            llm_url=llm_url,
            llm_model=llm_model,
            context_passage="",
        )
    except Exception as e:
        print(f"\n  ERROR resolving '{normalized}' ({entity_type}): {e}",
              file=sys.stderr)
        result = {"authority_uri": None, "authority_label": None,
                  "authority_source": None, "confidence": 0.0, "linked": False}

    crm_class, crm_uri = get_cidoc_crm(entity_type)
    return {
        "normalized_text": normalized,
        "authority_uri": result["authority_uri"],
        "authority_label": result["authority_label"],
        "authority_source": result["authority_source"],
        "cidoc_crm_class": crm_class,
        "cidoc_crm_uri": crm_uri,
        "confidence": result["confidence"],
        "linked": result["linked"],
    }


def enrich_single_doc(
    ner_path: Path,
    output_dir: Path,
    cache: LookupCache,
    agg_file,
    geonames_username: str = "",
    llm_url: str = "",
    llm_model: str = "",
) -> tuple[int, int]:
    """
    Enrich a single per-doc NER file. Resolves new entities on the fly.
    Returns (entities_enriched, entities_linked).
    """
    doc_id = ner_path.stem
    per_doc_out = output_dir / "per_doc"
    out_path = per_doc_out / f"{doc_id}.jsonl"

    # Resume-safe
    if out_path.exists() and out_path.stat().st_size > 0:
        return 0, 0

    enriched_entities = []
    linked_count = 0

    for line in ner_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue

        text = e.get("entity_text", "").strip()
        etype = e.get("entity_type", "").upper()
        if not text or not etype:
            continue

        enrichment = resolve_entity_cached(
            text, etype, cache,
            geonames_username, llm_url, llm_model,
        )

        enriched = {
            "doc_id": e.get("doc_id", doc_id),
            "entity_text": text,
            "entity_type": etype,
            "start": e.get("start"),
            "end": e.get("end"),
            "normalized_text": enrichment["normalized_text"],
            "authority_uri": enrichment["authority_uri"],
            "authority_label": enrichment["authority_label"],
            "authority_source": enrichment["authority_source"],
            "cidoc_crm_class": enrichment["cidoc_crm_class"],
            "cidoc_crm_uri": enrichment["cidoc_crm_uri"],
            "confidence": enrichment["confidence"],
            "linked": enrichment["linked"],
        }
        enriched_entities.append(enriched)
        if enrichment["linked"]:
            linked_count += 1

    # Write per-doc file
    with open(out_path, "w", encoding="utf-8") as f:
        for ent in enriched_entities:
            line = json.dumps(ent, ensure_ascii=False)
            f.write(line + "\n")
            agg_file.write(line + "\n")

    return len(enriched_entities), linked_count


def main():
    parser = argparse.ArgumentParser(
        description="Link NER entities to LOD authority records (LINCS/CIDOC-CRM compliant)."
    )
    parser.add_argument("--ner", default="output/ner_output/per_doc",
                        help="Directory of per-doc NER JSONL files (default: output/ner_output/per_doc)")
    parser.add_argument("--output", default="output/entity_linking",
                        help="Output directory (default: output/entity_linking)")
    parser.add_argument("--geonames-user", default=os.environ.get("GEONAMES_USERNAME", ""),
                        help="GeoNames API username (or set GEONAMES_USERNAME env var)")
    parser.add_argument("--llm-url",
                        default=os.environ.get("LLM_URL",
                            os.environ.get("OLLAMA_URL",
                                f"http://{os.environ['OLLAMA_HOST']}" if "OLLAMA_HOST" in os.environ
                                else "http://localhost:8000")),
                        help="LLM API base URL — OpenAI-compatible (vLLM, Ollama, etc). "
                             "Default: $LLM_URL or $OLLAMA_HOST or localhost:8000")
    parser.add_argument("--llm-model", default="",
                        help="Model name (default: auto-detect from config, or Qwen/Qwen3.5-35B-A3B)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Process only first N per-doc files (0 = all)")
    parser.add_argument("--watch", action="store_true",
                        help="Watch mode: poll for new NER files as they appear")
    parser.add_argument("--done-sentinel", default="output/ner_complete.sentinel",
                        help="Sentinel file from NER indicating completion "
                             "(default: output/ner_complete.sentinel)")
    parser.add_argument("--poll-interval", type=int, default=30,
                        help="Seconds between polls in watch mode (default: 30)")
    args = parser.parse_args()

    ner_dir = Path(args.ner)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    per_doc_out = output_dir / "per_doc"
    per_doc_out.mkdir(parents=True, exist_ok=True)
    sentinel = Path(args.done_sentinel)

    # Watch mode: wait for input dir
    if args.watch and not ner_dir.exists():
        print(f"Watch mode: waiting for '{ner_dir}' to appear...")
        while not ner_dir.exists():
            time.sleep(args.poll_interval)
        print(f"  '{ner_dir}' found — starting.")
    elif not ner_dir.exists():
        print(f"ERROR: NER directory '{ner_dir}' not found.", file=sys.stderr)
        print("  Run pipeline/03_ner/run_ner.py first, or use --watch to wait.", file=sys.stderr)
        sys.exit(1)

    # Warn about GeoNames
    if not args.geonames_user:
        print("NOTE: No GeoNames username provided. Place lookups will use Wikidata only.")
        print("  Register free at geonames.org, then use --geonames-user USERNAME\n")

    # Auto-detect LLM model
    llm_model = args.llm_model
    if not llm_model:
        config_path = Path("lightrag_config.yaml")
        if config_path.exists():
            for line in config_path.read_text().splitlines():
                if "llm_model" in line and ":" in line:
                    llm_model = line.split(":", 1)[1].strip().strip('"').strip("'")
                    break
        if not llm_model:
            llm_model = "Qwen/Qwen3.5-35B-A3B"

    print(f"NER dir:       {ner_dir}")
    print(f"Output dir:    {output_dir}")
    print(f"GeoNames user: {args.geonames_user or '(not set)'}")
    print(f"LLM model:     {llm_model}")
    print(f"LLM URL:       {args.llm_url}")
    if args.watch:
        print(f"Watch mode:    ON (poll every {args.poll_interval}s)")
        print(f"  Sentinel:    '{sentinel}'")
    if args.limit:
        print(f"Limit:         {args.limit} files")
    print()

    # Initialize cache
    cache_path = output_dir / "lookup_cache.db"
    cache = LookupCache(cache_path)

    # Track processed docs
    processed_stems: set[str] = set()
    # Load already-processed from output per_doc dir
    for p in per_doc_out.glob("*.jsonl"):
        processed_stems.add(p.stem)

    total_entities = 0
    total_linked = 0
    aggregate_path = output_dir / "linked_entities.jsonl"

    # ── Process current files (batch pass) ────────────────────────────────
    with open(aggregate_path, "a", encoding="utf-8") as agg:
        ner_files = sorted(
            f for f in ner_dir.glob("*.jsonl") if f.stem not in processed_stems
        )
        if args.limit > 0:
            ner_files = ner_files[:args.limit]

        if ner_files:
            print(f"Processing {len(ner_files)} NER files...")
            for ner_path in tqdm(ner_files, desc="Entity linking"):
                n_ent, n_linked = enrich_single_doc(
                    ner_path, output_dir, cache, agg,
                    args.geonames_user, args.llm_url, llm_model,
                )
                processed_stems.add(ner_path.stem)
                total_entities += n_ent
                total_linked += n_linked
            agg.flush()
        else:
            print("No new files to process in initial pass.")

        # ── Watch mode: keep polling ──────────────────────────────────────
        if args.watch:
            print(f"\nWatch mode: polling every {args.poll_interval}s for new NER files...")
            print("  (Press Ctrl+C to stop manually)\n")

            while True:
                time.sleep(args.poll_interval)

                new_files = sorted(
                    f for f in ner_dir.glob("*.jsonl")
                    if f.stem not in processed_stems
                )

                if new_files:
                    print(f"  {len(new_files)} new file(s) found — processing...")
                    for ner_path in new_files:
                        n_ent, n_linked = enrich_single_doc(
                            ner_path, output_dir, cache, agg,
                            args.geonames_user, args.llm_url, llm_model,
                        )
                        processed_stems.add(ner_path.stem)
                        total_entities += n_ent
                        total_linked += n_linked
                        print(f"    [{len(processed_stems)}] {ner_path.stem} "
                              f"({n_ent} entities, {n_linked} linked)")
                    agg.flush()

                if sentinel.exists() and not new_files:
                    print("\nNER sentinel found and queue empty — entity linking complete.")
                    # Write our own sentinel
                    Path("output/entity_linking_complete.sentinel").write_text(
                        f"Entity linking complete. {len(processed_stems)} docs processed.\n"
                    )
                    break

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n── Entity Linking Summary ──────────────────────────")
    print(f"  Docs processed:    {len(processed_stems)}")
    print(f"  Entities enriched: {total_entities}")
    print(f"  Entities linked:   {total_linked}")
    if total_entities > 0:
        print(f"  Link rate:         {round(total_linked / total_entities * 100, 1)}%")
    print(f"  Cache:             {cache_path}")
    print(f"  Per-doc output:    {per_doc_out}")
    print(f"  Aggregate:         {aggregate_path}")
    print(f"─────────────────────────────────────────────────────")
    print(f"\nNext: python pipeline/04_graph/extract_relations.py "
          f"--enriched-ner {per_doc_out}")

    cache.close()


if __name__ == "__main__":
    main()
