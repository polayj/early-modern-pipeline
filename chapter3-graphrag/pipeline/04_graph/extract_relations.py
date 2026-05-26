#!/usr/bin/env python3
"""
04_graph/extract_relations.py
Use a local Ollama LLM to extract typed semantic relationships between entity
pairs that co-occur in OCR documents.

Unlike the CO_OCCURS edges in build_graph.py (which only record that two
entities appeared in the same document), this script asks an LLM to read the
passage where two entities appear together and name the actual relationship:
GROWN_IN, SHIPPED_TO, GOVERNED, EMPLOYED_BY, etc.

Output:
    output/relations_output/relations.jsonl
    — one JSON object per extracted relation:
      { doc_id, entity_a, type_a, entity_b, type_b,
        subject, relation, object, confidence, evidence }

Resume-safe: already-processed doc IDs are tracked in
    output/relations_output/processed_docs.txt

Usage:
    # After running pipeline/03_ner/run_ner.py
    python pipeline/04_graph/extract_relations.py

    # Test on first 50 docs:
    python pipeline/04_graph/extract_relations.py --limit 50

    # Use a faster/lighter model:
    python pipeline/04_graph/extract_relations.py --model llama3.2:3b

    # All options:
    python pipeline/04_graph/extract_relations.py \\
        --ner output/ner_output/per_doc \\
        --ocr output/ocr_md \\
        --output output/relations_output \\
        --model qwen2.5:72b \\
        --llm-url http://localhost:8000 \\
        --context-window 500 \\
        --max-pairs 20 \\
        --limit 0
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from tqdm import tqdm

# ── Two-tier CIDOC-CRM relation taxonomy ──────────────────────────────────────
#
# Tier 1: CIDOC-CRM standard properties — LOD-compliant out of the box.
# Tier 2: Domain-specific extensions for Early Modern Caribbean trade history.
#         Flagged cidoc_standard=False for researcher review.
# The LLM is instructed to prefer Tier 1 when applicable, use Tier 2 when
# no standard property fits, and output free-text if neither tier applies.

CIDOC_RELATIONS = {
    "HAS_RESIDENCE":   {"crm_property": "P74",   "crm_uri": "http://www.cidoc-crm.org/cidoc-crm/P74_has_current_or_former_residence", "desc": "a person resides or resided in a place", "cidoc_standard": True},
    "HAS_MEMBER":      {"crm_property": "P107i",  "crm_uri": "http://www.cidoc-crm.org/cidoc-crm/P107i_is_current_or_former_member_of", "desc": "a person belongs to an organization or group", "cidoc_standard": True},
    "HAS_LOCATION":    {"crm_property": "P53",   "crm_uri": "http://www.cidoc-crm.org/cidoc-crm/P53_has_former_or_current_location", "desc": "a thing has its location at a place", "cidoc_standard": True},
    "HAS_TYPE":        {"crm_property": "P2",    "crm_uri": "http://www.cidoc-crm.org/cidoc-crm/P2_has_type", "desc": "an entity is classified as a type", "cidoc_standard": True},
    "FALLS_WITHIN":    {"crm_property": "P89",   "crm_uri": "http://www.cidoc-crm.org/cidoc-crm/P89_falls_within", "desc": "a place is part of or within another place", "cidoc_standard": True},
    "HAS_OWNER":       {"crm_property": "P52",   "crm_uri": "http://www.cidoc-crm.org/cidoc-crm/P52_has_current_owner", "desc": "a thing is owned by a person or organization", "cidoc_standard": True},
    "IDENTIFIED_BY":   {"crm_property": "P1",    "crm_uri": "http://www.cidoc-crm.org/cidoc-crm/P1_is_identified_by", "desc": "an entity is identified by a name or label", "cidoc_standard": True},
}

DOMAIN_RELATIONS = {
    "GROWN_IN":       {"domain": "Trade",     "desc": "a commodity is grown or cultivated in a place", "cidoc_standard": False},
    "PRODUCED_IN":    {"domain": "Trade",     "desc": "a commodity is manufactured or processed in a place", "cidoc_standard": False},
    "EXPORTED_FROM":  {"domain": "Trade",     "desc": "a commodity or goods are sent out from a place", "cidoc_standard": False},
    "IMPORTED_TO":    {"domain": "Trade",     "desc": "a commodity or goods are received at a place", "cidoc_standard": False},
    "SHIPPED_TO":     {"domain": "Trade",     "desc": "goods or a person are transported to a place", "cidoc_standard": False},
    "TRADED_IN":      {"domain": "Trade",     "desc": "trade of a commodity takes place at or in a location", "cidoc_standard": False},
    "TRADED_BY":      {"domain": "Trade",     "desc": "a person or organization buys/sells a commodity", "cidoc_standard": False},
    "TRADED_WITH":    {"domain": "Trade",     "desc": "two places exchanged goods with each other", "cidoc_standard": False},
    "GOVERNED":       {"domain": "Political", "desc": "a person governed, administered, or ruled a place or body", "cidoc_standard": False},
    "BORN_IN":        {"domain": "Life",      "desc": "a person was born in a place", "cidoc_standard": False},
    "DIED_IN":        {"domain": "Life",      "desc": "a person died in a place", "cidoc_standard": False},
    "TRAVELED_TO":    {"domain": "Movement",  "desc": "a person traveled to or visited a place", "cidoc_standard": False},
    "FOUNDED":        {"domain": "Political", "desc": "a person or organization founded or established something", "cidoc_standard": False},
    "EMPLOYED_BY":    {"domain": "Labor",     "desc": "a person works or worked for an organization or person", "cidoc_standard": False},
    "LED":            {"domain": "Political", "desc": "a person led, directed, or commanded an organization", "cidoc_standard": False},
    "PRODUCED":       {"domain": "Trade",     "desc": "a person or organization produced goods or a commodity", "cidoc_standard": False},
    "BASED_IN":       {"domain": "Political", "desc": "an organization is headquartered or located in a place", "cidoc_standard": False},
    "OPERATED_IN":    {"domain": "Trade",     "desc": "an organization worked or traded in a place", "cidoc_standard": False},
    "REGULATED":      {"domain": "Political", "desc": "an organization regulated or controlled a commodity or trade", "cidoc_standard": False},
    "ASSOCIATED_WITH":{"domain": "Social",    "desc": "two persons were associated, partners, or worked together", "cidoc_standard": False},
    "FAMILY_OF":      {"domain": "Social",    "desc": "persons are related by family", "cidoc_standard": False},
    "MARRIED_TO":     {"domain": "Social",    "desc": "persons are married to each other", "cidoc_standard": False},
    "PARTNERED_WITH": {"domain": "Trade",     "desc": "persons or organizations are business partners", "cidoc_standard": False},
    "ENSLAVED_IN":    {"domain": "Labor",     "desc": "a person was enslaved in a place", "cidoc_standard": False},
    "WORKED_IN":      {"domain": "Labor",     "desc": "a person worked in or at a place", "cidoc_standard": False},
    "CONTROLLED_BY":  {"domain": "Political", "desc": "a place or organization is controlled by a person or organization", "cidoc_standard": False},
}

# Combined for validation
ALL_RELATIONS = {**{k: v["desc"] for k, v in CIDOC_RELATIONS.items()},
                 **{k: v["desc"] for k, v in DOMAIN_RELATIONS.items()}}

def get_relation_metadata(relation: str) -> dict:
    """Get metadata for a relation label (tier, CRM property, etc.)."""
    if relation in CIDOC_RELATIONS:
        info = CIDOC_RELATIONS[relation]
        return {
            "relation_tier": "cidoc_standard",
            "crm_property": info["crm_property"],
            "crm_uri": info["crm_uri"],
            "cidoc_standard": True,
        }
    elif relation in DOMAIN_RELATIONS:
        info = DOMAIN_RELATIONS[relation]
        return {
            "relation_tier": "domain",
            "crm_property": None,
            "crm_uri": None,
            "domain": info["domain"],
            "cidoc_standard": False,
        }
    else:
        return {
            "relation_tier": "unclassified",
            "crm_property": None,
            "crm_uri": None,
            "cidoc_standard": False,
        }

SYSTEM_PROMPT = """\
You are a historian analyzing Early Modern British Caribbean documents (1600s–1750s).
Given a passage from a historical document and two named entities, identify the
specific directional relationship the passage expresses between them.
Prefer CIDOC-CRM standard relations when they fit. Use domain-specific relations
when no standard property applies. If neither fits, propose a new relation label.
Respond with ONLY a valid JSON object — no explanation, no markdown, no extra text.
"""

# Build relation list for prompt — CIDOC-CRM first, then domain
RELATION_LIST = "  CIDOC-CRM Standard Relations:\n" + "\n".join(
    f"    {label:<18} — {info['desc']}"
    for label, info in CIDOC_RELATIONS.items()
) + "\n\n  Domain-Specific Relations:\n" + "\n".join(
    f"    {label:<18} — {info['desc']}"
    for label, info in DOMAIN_RELATIONS.items()
)

USER_PROMPT_TEMPLATE = """\
Passage from a historical document:
\"\"\"{evidence}\"\"\"

Entity A: "{entity_a}" (type: {type_a})
Entity B: "{entity_b}" (type: {type_b})

What specific relationship does this passage express between these entities?

Valid relationship types (prefer CIDOC-CRM Standard when applicable):
{relation_list}

If no specific directional relationship is clearly stated, use: NONE
If a clear relationship exists but none of the above labels fit, propose a short
UPPER_SNAKE_CASE label (it will be flagged for researcher review).

Rules:
- Choose the SINGLE most precise matching relation.
- "subject" and "object" must be the exact entity names shown above.
- The subject performs or holds the relationship; the object receives it
  (e.g. Sugar GROWN_IN Jamaica → subject=Sugar, relation=GROWN_IN, object=Jamaica).
- confidence: "high" = clearly stated, "medium" = implied, "low" = uncertain.

Respond with ONLY this JSON (no other text):
{{"subject": "<entity name>", "relation": "<RELATION_TYPE or NONE>", "object": "<entity name>", "confidence": "high|medium|low"}}
"""


# ── Ollama API ────────────────────────────────────────────────────────────────

def call_llm(
    system: str,
    user: str,
    model: str,
    llm_url: str,
    timeout: int = 90,
) -> str:
    """
    Call an OpenAI-compatible /v1/chat/completions endpoint with JSON mode.
    Works with vLLM, Ollama (/v1/ endpoint), etc.
    Returns the assistant message content, or "" on error.
    """
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "temperature": 0.0,
        "max_tokens": 120,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{llm_url.rstrip('/')}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except urllib.error.URLError as e:
        print(f"\nERROR: Cannot reach LLM at {llm_url}: {e}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"\nWARN: LLM call failed: {e}", file=sys.stderr)
        return ""


def parse_llm_response(response: str, entity_a: str, entity_b: str) -> dict | None:
    """
    Parse and validate the LLM JSON response.
    Returns dict with subject/relation/object/confidence, or None if invalid.
    """
    if not response:
        return None
    try:
        obj = json.loads(response)
    except json.JSONDecodeError:
        # Try to extract JSON from the response (sometimes wrapped in text)
        m = re.search(r'\{[^{}]+\}', response, re.DOTALL)
        if not m:
            return None
        try:
            obj = json.loads(m.group())
        except json.JSONDecodeError:
            return None

    relation = str(obj.get("relation", "")).strip().upper()
    subject  = str(obj.get("subject",  "")).strip()
    object_  = str(obj.get("object",   "")).strip()
    confidence = str(obj.get("confidence", "low")).strip().lower()

    if relation in ("NONE", "", "NULL", "N/A"):
        return None

    # Accept both known and unclassified relations (unclassified get flagged for review)
    # Only reject truly empty/null relations

    # Validate subject/object are recognizable entity names
    valid_names = {entity_a.lower(), entity_b.lower()}
    if subject.lower() not in valid_names or object_.lower() not in valid_names:
        # Try case-insensitive match
        for name in (entity_a, entity_b):
            if name.lower() == subject.lower():
                subject = name
            if name.lower() == object_.lower():
                object_ = name
        if subject.lower() not in valid_names or object_.lower() not in valid_names:
            return None

    if confidence not in ("high", "medium", "low"):
        confidence = "low"

    return {
        "subject":    subject,
        "relation":   relation,
        "object":     object_,
        "confidence": confidence,
    }


# ── Entity pair extraction ────────────────────────────────────────────────────

def find_close_pairs(
    text: str,
    entities: list[dict],
    window_chars: int = 500,
    max_pairs: int = 20,
) -> list[dict]:
    """
    Find entity pairs whose mentions appear within window_chars of each other
    in the OCR text.

    Returns up to max_pairs items, sorted by proximity (closest first):
        {entity_a, type_a, entity_b, type_b, evidence, distance}

    Only the closest co-occurrence of each pair is returned.
    """
    # Build position index: entity_text → (positions list, entity_type, authority_uri)
    pos_index: dict[str, tuple[list, str, str | None]] = {}
    for e in entities:
        name = e.get("entity_text", "").strip()
        etype = e.get("entity_type", "UNKNOWN")
        if not name:
            continue
        pattern = re.compile(re.escape(name), re.IGNORECASE)
        positions = [(m.start(), m.end()) for m in pattern.finditer(text)]
        if positions:
            pos_index[name] = (positions, etype, e.get("authority_uri"))

    names = list(pos_index.keys())
    candidates: list[dict] = []
    seen: set[tuple] = set()

    for i, name_a in enumerate(names):
        for name_b in names[i + 1:]:
            pair_key = tuple(sorted([name_a.lower(), name_b.lower()]))
            if pair_key in seen:
                continue
            seen.add(pair_key)

            positions_a, type_a, uri_a = pos_index[name_a]
            positions_b, type_b, uri_b = pos_index[name_b]

            # Find the closest occurrence of this pair
            best_dist = float("inf")
            best_lo = best_hi = 0

            for sa, ea in positions_a:
                for sb, eb in positions_b:
                    # Gap between the two spans (0 if overlapping/adjacent)
                    dist = max(0, max(sa, sb) - min(ea, eb))
                    if dist < window_chars and dist < best_dist:
                        best_dist = dist
                        best_lo = min(sa, sb)
                        best_hi = max(ea, eb)

            if best_dist < window_chars:
                ctx_start = max(0, best_lo - 200)
                ctx_end   = min(len(text), best_hi + 200)
                # Trim to sentence boundaries if possible
                excerpt = text[ctx_start:ctx_end]
                candidates.append({
                    "entity_a": name_a,
                    "type_a":   type_a,
                    "entity_b": name_b,
                    "type_b":   type_b,
                    "evidence": excerpt.strip(),
                    "distance": int(best_dist),
                    "subject_uri": uri_a,
                    "object_uri":  uri_b,
                })

    # Sort by proximity; return top max_pairs
    candidates.sort(key=lambda x: x["distance"])
    return candidates[:max_pairs]


# ── Per-document processing ───────────────────────────────────────────────────

def process_document(
    doc_id: str,
    ner_dir: Path,
    ocr_dir: Path,
    model: str,
    llm_url: str,
    window_chars: int,
    max_pairs: int,
    relation_list: str,
) -> list[dict]:
    """
    Extract typed relations for one document.
    Returns list of relation dicts ready for JSONL output.
    """
    # Load NER entities
    per_doc_path = ner_dir / f"{doc_id}.jsonl"
    if not per_doc_path.exists():
        return []

    entities = []
    for line in per_doc_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entities.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    if len(entities) < 2:
        return []

    # Load OCR text
    md_path = ocr_dir / f"{doc_id}.md"
    if not md_path.exists():
        return []

    text = md_path.read_text(encoding="utf-8", errors="replace")
    if len(text) < 50:
        return []

    # Find close entity pairs
    pairs = find_close_pairs(text, entities, window_chars=window_chars, max_pairs=max_pairs)
    if not pairs:
        return []

    results: list[dict] = []

    for pair in pairs:
        user_prompt = USER_PROMPT_TEMPLATE.format(
            evidence=pair["evidence"][:800],   # cap evidence length
            entity_a=pair["entity_a"],
            type_a=pair["type_a"],
            entity_b=pair["entity_b"],
            type_b=pair["type_b"],
            relation_list=relation_list,
        )

        raw = call_llm(SYSTEM_PROMPT, user_prompt, model, llm_url)
        parsed = parse_llm_response(raw, pair["entity_a"], pair["entity_b"])

        if parsed:
            rel_meta = get_relation_metadata(parsed["relation"])
            result_entry = {
                "doc_id":         doc_id,
                "entity_a":       pair["entity_a"],
                "type_a":         pair["type_a"],
                "entity_b":       pair["entity_b"],
                "type_b":         pair["type_b"],
                "subject":        parsed["subject"],
                "relation":       parsed["relation"],
                "object":         parsed["object"],
                "confidence":     parsed["confidence"],
                "evidence":       pair["evidence"][:400],
                "relation_tier":  rel_meta["relation_tier"],
                "crm_property":   rel_meta.get("crm_property"),
                "crm_uri":        rel_meta.get("crm_uri"),
                "cidoc_standard": rel_meta["cidoc_standard"],
            }
            # Map authority URIs to correct subject/object based on LLM's assignment
            if parsed["subject"].lower() == pair["entity_a"].lower():
                result_entry["subject_uri"] = pair.get("subject_uri")
                result_entry["object_uri"] = pair.get("object_uri")
            else:
                result_entry["subject_uri"] = pair.get("object_uri")
                result_entry["object_uri"] = pair.get("subject_uri")
            results.append(result_entry)

    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extract typed entity relations using a local Ollama LLM."
    )
    parser.add_argument("--ner", default="output/ner_output/per_doc",
                        help="Directory of per-doc NER JSONL files (default: output/ner_output/per_doc)")
    parser.add_argument("--enriched-ner", default="",
                        help="Directory of enriched (entity-linked) per-doc JSONL files. "
                             "If provided, uses these instead of --ner and includes authority URIs in output.")
    parser.add_argument("--ocr", default="output/ocr_md",
                        help="Directory of OCR markdown files (default: output/ocr_md)")
    parser.add_argument("--output", default="output/relations_output",
                        help="Output directory (default: output/relations_output)")
    parser.add_argument("--model", default="",
                        help="Model name (default: read from lightrag_config.yaml, "
                             "fallback Qwen/Qwen3.5-35B-A3B)")
    parser.add_argument("--llm-url",
                        default=os.environ.get("LLM_URL",
                            os.environ.get("OLLAMA_URL",
                                f"http://{os.environ['OLLAMA_HOST']}" if "OLLAMA_HOST" in os.environ
                                else "http://localhost:8000")),
                        help="LLM API base URL — OpenAI-compatible (vLLM, Ollama, etc). "
                             "Default: $LLM_URL or localhost:8000")
    parser.add_argument("--context-window", type=int, default=500,
                        help="Max character gap between entity mentions to consider a pair "
                             "(default: 500)")
    parser.add_argument("--max-pairs", type=int, default=20,
                        help="Max entity pairs to process per document (default: 20)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Process only first N docs (0 = all, default: 0)")
    parser.add_argument("--timeout", type=int, default=90,
                        help="Seconds to wait for each Ollama response (default: 90)")
    parser.add_argument("--watch", action="store_true",
                        help="Watch mode: poll for new NER/entity-linking files as they appear")
    parser.add_argument("--done-sentinel", default="output/entity_linking_complete.sentinel",
                        help="Sentinel file indicating upstream step is done "
                             "(default: output/entity_linking_complete.sentinel)")
    parser.add_argument("--poll-interval", type=int, default=30,
                        help="Seconds between polls in watch mode (default: 30)")
    args = parser.parse_args()

    ner_dir    = Path(args.enriched_ner) if args.enriched_ner else Path(args.ner)
    ocr_dir    = Path(args.ocr)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.enriched_ner:
        print(f"Using enriched (entity-linked) NER from: {ner_dir}")
        print(f"  Authority URIs will be included in relation output.")

    # ── Resolve model name ──────────────────────────────────────────────────
    model = args.model
    if not model:
        config_path = Path("lightrag_config.yaml")
        if config_path.exists():
            for line in config_path.read_text().splitlines():
                if "llm_model" in line and ":" in line:
                    model = line.split(":", 1)[1].strip().strip('"').strip("'")
                    break
    if not model:
        model = "Qwen/Qwen3.5-35B-A3B"
    sentinel = Path(args.done_sentinel)

    print(f"Model:         {model}")
    print(f"LLM URL:       {args.llm_url}")
    print(f"NER dir:       {ner_dir}")
    print(f"OCR dir:       {ocr_dir}")
    print(f"Output dir:    {output_dir}")
    print(f"Context window:{args.context_window} chars")
    print(f"Max pairs/doc: {args.max_pairs}")
    if args.watch:
        print(f"Watch mode:    ON (poll every {args.poll_interval}s)")
        print(f"  Sentinel:    '{sentinel}'")

    # ── Pre-flight: check LLM is reachable ──────────────────────────────────
    print("\nChecking LLM connection...")
    try:
        req = urllib.request.Request(
            f"{args.llm_url.rstrip('/')}/v1/models",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            available = [m.get("id", "") for m in data.get("data", [])]
            if available:
                print(f"  OK — available models: {available}")
            else:
                print(f"  OK — LLM reachable (model list empty, will try '{model}')")
    except Exception as e:
        print(f"  ERROR: Cannot reach LLM at {args.llm_url}: {e}")
        print("  Make sure vLLM is running: vllm serve <model>")
        sys.exit(1)

    # ── Load already-processed docs (resume safety) ─────────────────────────
    processed_path = output_dir / "processed_docs.txt"
    processed_docs: set[str] = set()
    if processed_path.exists():
        for line in processed_path.read_text().splitlines():
            line = line.strip()
            if line:
                processed_docs.add(line)
    if processed_docs:
        print(f"\nResuming: {len(processed_docs)} docs already processed.")

    # ── Find all NER per-doc files ──────────────────────────────────────────
    if args.watch and not ner_dir.exists():
        print(f"\nWatch mode: waiting for '{ner_dir}' to appear...")
        while not ner_dir.exists():
            time.sleep(args.poll_interval)
        print(f"  '{ner_dir}' found — starting.")
    elif not ner_dir.exists():
        print(f"\nERROR: NER directory '{ner_dir}' not found.", file=sys.stderr)
        print("  Run pipeline/03_ner/run_ner.py first, or use --watch to wait.", file=sys.stderr)
        sys.exit(1)

    all_docs = sorted(
        p.stem for p in ner_dir.glob("*.jsonl")
        if p.stem not in processed_docs
    )

    if args.limit > 0:
        all_docs = all_docs[:args.limit]

    print(f"\n{len(all_docs)} documents to process")
    if not all_docs and not args.watch:
        print("Nothing to do.")
        return

    # ── Process documents ────────────────────────────────────────────────────
    relations_path = output_dir / "relations.jsonl"
    unclassified_path = output_dir / "unclassified_relations.jsonl"
    total_relations = 0
    total_unclassified = 0
    relation_counts: dict[str, int] = {}
    tier_counts: dict[str, int] = {"cidoc_standard": 0, "domain": 0, "unclassified": 0}

    relation_list_str = RELATION_LIST  # pre-rendered for prompt

    with (
        open(relations_path, "a", encoding="utf-8") as rel_f,
        open(unclassified_path, "a", encoding="utf-8") as uncl_f,
        open(processed_path, "a", encoding="utf-8") as proc_f,
    ):
        for doc_id in tqdm(all_docs, desc="Extracting relations"):
            relations = process_document(
                doc_id=doc_id,
                ner_dir=ner_dir,
                ocr_dir=ocr_dir,
                model=model,
                llm_url=args.llm_url,
                window_chars=args.context_window,
                max_pairs=args.max_pairs,
                relation_list=relation_list_str,
            )

            for r in relations:
                tier = r.get("relation_tier", "unclassified")
                tier_counts[tier] = tier_counts.get(tier, 0) + 1

                if tier == "unclassified":
                    uncl_f.write(json.dumps(r, ensure_ascii=False) + "\n")
                    total_unclassified += 1
                else:
                    rel_f.write(json.dumps(r, ensure_ascii=False) + "\n")

                relation_counts[r["relation"]] = relation_counts.get(r["relation"], 0) + 1
                total_relations += 1

            if relations_path.stat().st_size > 0:
                rel_f.flush()
            uncl_f.flush()

            processed_docs.add(doc_id)
            proc_f.write(doc_id + "\n")

        # ── Watch mode: keep polling ──────────────────────────────────────
        if args.watch:
            print(f"\nWatch mode: polling every {args.poll_interval}s for new files...")
            print("  (Press Ctrl+C to stop manually)\n")

            while True:
                time.sleep(args.poll_interval)

                new_docs = sorted(
                    p.stem for p in ner_dir.glob("*.jsonl")
                    if p.stem not in processed_docs
                )

                if new_docs:
                    print(f"  {len(new_docs)} new file(s) found — processing...")
                    for doc_id in new_docs:
                        relations = process_document(
                            doc_id=doc_id,
                            ner_dir=ner_dir,
                            ocr_dir=ocr_dir,
                            model=model,
                            llm_url=args.llm_url,
                            window_chars=args.context_window,
                            max_pairs=args.max_pairs,
                            relation_list=relation_list_str,
                        )

                        for r in relations:
                            tier = r.get("relation_tier", "unclassified")
                            tier_counts[tier] = tier_counts.get(tier, 0) + 1
                            if tier == "unclassified":
                                uncl_f.write(json.dumps(r, ensure_ascii=False) + "\n")
                                total_unclassified += 1
                            else:
                                rel_f.write(json.dumps(r, ensure_ascii=False) + "\n")
                            relation_counts[r["relation"]] = relation_counts.get(r["relation"], 0) + 1
                            total_relations += 1

                        processed_docs.add(doc_id)
                        proc_f.write(doc_id + "\n")
                        print(f"    [{len(processed_docs)}] {doc_id} "
                              f"({len(relations)} relations)")
                    rel_f.flush()
                    uncl_f.flush()
                    proc_f.flush()

                if sentinel.exists() and not new_docs:
                    print("\nUpstream sentinel found and queue empty — relation extraction complete.")
                    Path("output/relations_complete.sentinel").write_text(
                        f"Relation extraction complete. {len(processed_docs)} docs processed.\n"
                    )
                    break

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n── Relation Extraction Summary ──────────────────────")
    print(f"  Docs processed:  {len(processed_docs)}")
    print(f"  Relations found: {total_relations}")
    print(f"  By tier:")
    for tier, count in sorted(tier_counts.items()):
        print(f"    {tier:<20} {count:>5}")
    if relation_counts:
        print(f"  By type:")
        for rel, count in sorted(relation_counts.items(), key=lambda x: -x[1]):
            meta = get_relation_metadata(rel)
            tag = "CRM" if meta["cidoc_standard"] else ("DOM" if meta["relation_tier"] == "domain" else "NEW")
            print(f"    [{tag}] {rel:<20} {count:>5}")
    print(f"  Output:          {relations_path}")
    if total_unclassified:
        print(f"  Unclassified:    {unclassified_path} ({total_unclassified} entries)")
        print(f"    Review these and add approved labels to DOMAIN_RELATIONS in this script.")
    print(f"─────────────────────────────────────────────────────")
    print(f"\nNext: python pipeline/04_graph/build_graph.py")
    print(f"  (will pick up {relations_path} automatically)")


if __name__ == "__main__":
    main()
