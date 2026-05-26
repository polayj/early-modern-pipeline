#!/usr/bin/env python3
"""
04_graph/build_graph.py
Build a knowledge graph (nodes/edges CSVs) from NER output + import records.

Node types:
    Document     — OCR'd document (title, year, author, source collection)
    Person       — PERSON entity from NER
    Location     — TOPONYM entity from NER + import record locations
    Organization — ORGANIZATION entity from NER
    Commodity    — COMMODITY entity from NER + import record commodities
    Year         — calendar year

Edge types:
    MENTIONS     — Document → Entity  (document contains this entity)
    DATED        — Document → Year
    AUTHORED_BY  — Document → Person  (from document metadata, not NER)
    CO_OCCURS    — Entity ↔ Entity    (appear together in the same document;
                                       weighted by number of shared documents)
    EXPORTS      — Location → Commodity  (from structured import records)
    IMPORTED_TO  — Commodity → Location  (from structured import records)
    EXPORTED_IN  — Location → Year       (from structured import records)

CO_OCCURS edges are the key relationship layer: if Sugar and Jamaica both appear
in the same document, they get a CO_OCCURS edge. The more documents two entities
share, the higher the weight — making high-weight edges the strongest associations
in the corpus.

Outputs:
    output/knowledge_graph/nodes.csv
    output/knowledge_graph/edges.csv

Usage:
    python pipeline/04_graph/build_graph.py
    python pipeline/04_graph/build_graph.py \\
        --ner output/ner_output \\
        --records output/import_records_parsed/all_records.csv \\
        --ocr-docs ocr_docs/unprocessed \\
        --output output/knowledge_graph/
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


# ── Helpers ───────────────────────────────────────────────────────────────────

def sanitize_id(text: str) -> str:
    return re.sub(r"[^\w\-]", "_", text.strip().lower())[:120]


def normalize_name(text: str) -> str:
    """Lowercase and strip for deduplication comparisons."""
    return text.strip().lower()


# ── Metadata extraction ───────────────────────────────────────────────────────

def load_archive_org_metadata(ocr_docs_dir: Path) -> dict[str, dict]:
    """
    Load title/author/year from archive_org _metadata.json files.
    Returns dict keyed by sanitized doc_id (matching NER doc_id stem).
    """
    meta = {}
    archive_dir = ocr_docs_dir / "archive_org"
    if not archive_dir.exists():
        return meta

    for subdir in archive_dir.iterdir():
        if not subdir.is_dir():
            continue
        doc_title = subdir.name
        meta_file = subdir / f"{doc_title}_metadata.json"
        if not meta_file.exists():
            # Try any *_metadata.json in the folder
            candidates = list(subdir.glob("*_metadata.json"))
            if not candidates:
                continue
            meta_file = candidates[0]

        try:
            data = json.loads(meta_file.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue

        safe_id = re.sub(r"[^\w\-.]", "_", doc_title)
        doc_id = f"archive_org__{safe_id}"

        # Archive.org metadata fields vary; try common keys
        title = (
            data.get("title") or
            data.get("Title") or
            doc_title
        )
        if isinstance(title, list):
            title = title[0]

        creator = (
            data.get("creator") or
            data.get("Creator") or
            data.get("author") or
            data.get("Author") or
            ""
        )
        if isinstance(creator, list):
            creator = creator[0]

        date = (
            data.get("date") or
            data.get("Date") or
            data.get("year") or
            ""
        )
        if isinstance(date, list):
            date = date[0]
        year = _extract_year(str(date))

        meta[doc_id] = {
            "title": str(title).strip()[:200],
            "author": str(creator).strip()[:200],
            "year": year,
        }

    return meta


def load_eebo_metadata(ocr_docs_dir: Path) -> dict[str, dict]:
    """
    Extract title/author/year from EEBO filenames:
    'Author - Year - Title.pdf' → parsed directly.
    """
    meta = {}
    eebo_dir = ocr_docs_dir / "EEBO"
    if not eebo_dir.exists():
        return meta

    for pdf in eebo_dir.glob("*.pdf"):
        stem = pdf.stem
        safe_base = re.sub(r"[^\w\-.]", "_", stem)
        doc_id = f"EEBO__{safe_base}"

        # Parse 'Author - Year - Title' pattern
        parts = stem.split(" - ", 2)
        if len(parts) == 3:
            author, year_str, title = parts
            year = _extract_year(year_str)
        elif len(parts) == 2:
            author, title = parts
            year = _extract_year(stem)
        else:
            author, title, year = "", stem, _extract_year(stem)

        meta[doc_id] = {
            "title": title.strip()[:200],
            "author": author.strip()[:200],
            "year": year,
        }

    return meta


def _extract_year(text: str) -> str:
    m = re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", str(text))
    return m.group(1) if m else ""


# ── NER loading ───────────────────────────────────────────────────────────────

def load_ner_per_doc(ner_dir: Path) -> dict[str, list[dict]]:
    """
    Load per-doc NER JSONL files.
    Returns dict: doc_id → list of entity dicts.
    """
    per_doc_dir = ner_dir / "per_doc"
    doc_entities: dict[str, list[dict]] = {}

    if not per_doc_dir.exists():
        # Fall back to aggregate file
        agg = ner_dir / "entities.jsonl"
        if agg.exists():
            for line in agg.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                    doc_id = e.get("doc_id", "")
                    if doc_id:
                        doc_entities.setdefault(doc_id, []).append(e)
                except json.JSONDecodeError:
                    pass
        return doc_entities

    for jsonl_file in per_doc_dir.glob("*.jsonl"):
        doc_id = jsonl_file.stem
        entities = []
        for line in jsonl_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    entities.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        if entities:
            doc_entities[doc_id] = entities

    return doc_entities


# ── Import records ────────────────────────────────────────────────────────────

def load_import_records(csv_path: Path) -> list[dict]:
    records = []
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if any(row.get(c) for c in ("total_pounds", "weight_tons", "hh", "ton", "lb")):
                records.append(row)
    return records


# ── Main graph builder ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Build knowledge graph nodes/edges from NER output + import records."
    )
    parser.add_argument("--ner", default="output/ner_output")
    parser.add_argument("--records", default="output/import_records_parsed/all_records.csv")
    parser.add_argument("--ocr-docs", default="ocr_docs/unprocessed",
                        help="Path to ocr_docs/unprocessed/ (for metadata JSON files)")
    parser.add_argument("--output", default="output/knowledge_graph/")
    parser.add_argument("--max-evidence-docs", type=int, default=5,
                        help="Max document IDs to store per CO_OCCURS edge (default: 5)")
    parser.add_argument("--relations", default="output/relations_output/relations.jsonl",
                        help="Typed relations JSONL from extract_relations.py "
                             "(optional; used in addition to CO_OCCURS)")
    args = parser.parse_args()

    ner_dir = Path(args.ner)
    records_path = Path(args.records)
    ocr_docs_dir = Path(args.ocr_docs)
    output_dir = Path(args.output)
    relations_path = Path(args.relations)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Node registry ──────────────────────────────────────────────────────────
    # node_id → {id, label, name, ...props}
    nodes: dict[str, dict] = {}

    def add_node(node_id: str, label: str, name: str, **props) -> str:
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, "label": label, "name": name, **props}
        return node_id

    # ── Edge registry ──────────────────────────────────────────────────────────
    # For CO_OCCURS, aggregate weight across docs rather than one edge per doc
    edges: list[dict] = []

    # co_occurs_map: (node_id_a, node_id_b) → {weight, doc_ids, entity_types}
    co_occurs_map: dict[tuple, dict] = {}

    def add_edge(source: str, target: str, rel_type: str, **props):
        edges.append({"source": source, "target": target, "type": rel_type, **props})

    def add_co_occurs(id_a: str, id_b: str, entity_types: str, doc_id: str):
        key = (min(id_a, id_b), max(id_a, id_b))  # canonical order
        if key not in co_occurs_map:
            co_occurs_map[key] = {"weight": 0, "doc_ids": [], "entity_types": entity_types}
        co_occurs_map[key]["weight"] += 1
        if len(co_occurs_map[key]["doc_ids"]) < args.max_evidence_docs:
            co_occurs_map[key]["doc_ids"].append(doc_id)

    # ── Load document metadata ─────────────────────────────────────────────────
    print("Loading document metadata...")
    doc_meta: dict[str, dict] = {}
    if ocr_docs_dir.exists():
        doc_meta.update(load_archive_org_metadata(ocr_docs_dir))
        doc_meta.update(load_eebo_metadata(ocr_docs_dir))
    print(f"  Metadata loaded for {len(doc_meta)} documents")

    # ── Process import records ─────────────────────────────────────────────────
    if records_path.exists():
        print(f"Loading import records from '{records_path}'...")
        records = load_import_records(records_path)
        print(f"  {len(records)} non-zero records")

        year_location_seen: set[tuple] = set()

        for rec in records:
            commodity = rec["commodity_name"].strip()
            from_loc  = rec["from_location"].strip()
            to_loc    = rec["to_location"].strip()
            year      = rec.get("year") or rec.get("year_start") or ""
            year_range = rec.get("year_range", "")

            c_id  = "commodity__" + sanitize_id(commodity)
            fl_id = "location__"  + sanitize_id(from_loc)
            tl_id = "location__"  + sanitize_id(to_loc)

            add_node(c_id,  "Commodity", commodity)
            add_node(fl_id, "Location",  from_loc)
            add_node(tl_id, "Location",  to_loc)

            add_edge(fl_id, c_id, "EXPORTS",
                     year=year, year_range=year_range,
                     total_pounds=rec.get("total_pounds", ""),
                     weight_tons=rec.get("weight_tons", ""),
                     hogsheads=rec.get("hh", ""),
                     to_location=to_loc)

            add_edge(c_id, tl_id, "IMPORTED_TO",
                     year=year, year_range=year_range,
                     from_location=from_loc)

            # Direct Location→Location trade edge
            add_edge(fl_id, tl_id, "TRADED_WITH",
                     year=year, commodity=commodity)

            if year:
                yr_id = "year__" + sanitize_id(year)
                add_node(yr_id, "Year", year, year=year)
                key = (from_loc, year)
                if key not in year_location_seen:
                    year_location_seen.add(key)
                    add_edge(fl_id, yr_id, "EXPORTED_IN")

            # CO_OCCURS between commodity and both locations (from structured data)
            add_co_occurs(c_id, fl_id, "COMMODITY_LOCATION", f"import__{year_range}")
            add_co_occurs(c_id, tl_id, "COMMODITY_LOCATION", f"import__{year_range}")

    else:
        print(f"WARN: Import records not found at '{records_path}' — skipping.")

    # ── Process NER output ─────────────────────────────────────────────────────
    if ner_dir.exists():
        print(f"\nLoading NER entities from '{ner_dir}'...")
        doc_entities = load_ner_per_doc(ner_dir)
        print(f"  {len(doc_entities)} documents with entities")

        for doc_id, entities in doc_entities.items():
            # ── Document node ──────────────────────────────────────────────────
            meta = doc_meta.get(doc_id, {})
            title  = meta.get("title", doc_id)
            author = meta.get("author", "")
            year   = meta.get("year", "")
            source = "archive_org" if doc_id.startswith("archive_org") else "EEBO"

            doc_node_id = "doc__" + sanitize_id(doc_id)
            add_node(doc_node_id, "Document", title,
                     doc_id=doc_id,
                     title=title,
                     author=author,
                     year=year,
                     source_collection=source)

            # DATED edge
            if year:
                yr_id = "year__" + sanitize_id(year)
                add_node(yr_id, "Year", year, year=year)
                add_edge(doc_node_id, yr_id, "DATED")

            # AUTHORED_BY edge (from metadata, not NER)
            if author:
                author_id = "person__" + sanitize_id(author)
                add_node(author_id, "Person", author,
                         source="document_metadata")
                add_edge(doc_node_id, author_id, "AUTHORED_BY")

            # ── Entity nodes + MENTIONS edges ──────────────────────────────────
            entity_node_ids: list[tuple[str, str]] = []  # (node_id, entity_type)

            for e in entities:
                etype = e.get("entity_type", "").upper()
                etext = e.get("entity_text", "").strip()
                if not etext or not etype:
                    continue

                if etype == "PERSON":
                    label, prefix = "Person",       "person__"
                elif etype == "TOPONYM":
                    label, prefix = "Location",     "location__"
                elif etype == "ORGANIZATION":
                    label, prefix = "Organization", "org__"
                elif etype == "COMMODITY":
                    label, prefix = "Commodity",    "commodity__"
                else:
                    label, prefix = "Entity",       "entity__"

                entity_id = prefix + sanitize_id(etext)
                add_node(entity_id, label, etext)
                add_edge(doc_node_id, entity_id, "MENTIONS")
                entity_node_ids.append((entity_id, etype))

            # ── CO_OCCURS edges between all entity pairs in this document ───────
            # Every pair of entities that appear in the same document gets an edge.
            # Weight accumulates across documents — high weight = strong association.
            for i in range(len(entity_node_ids)):
                for j in range(i + 1, len(entity_node_ids)):
                    id_a, type_a = entity_node_ids[i]
                    id_b, type_b = entity_node_ids[j]
                    # Label the edge with the entity type pair (sorted alphabetically)
                    type_pair = "_".join(sorted([type_a, type_b]))
                    add_co_occurs(id_a, id_b, type_pair, doc_id)

    else:
        print(f"WARN: NER directory not found at '{ner_dir}' — skipping NER entities.")
        print("  Run pipeline/03_ner/run_ner.py first.")

    # ── Load typed relations from extract_relations.py (if available) ──────────
    typed_relation_count = 0
    if relations_path.exists():
        print(f"\nLoading typed relations from '{relations_path}'...")
        with open(relations_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rel = json.loads(line)
                except json.JSONDecodeError:
                    continue

                subject_text = rel.get("subject", "").strip()
                object_text  = rel.get("object",  "").strip()
                relation     = rel.get("relation", "").strip().upper()
                confidence   = rel.get("confidence", "low")
                evidence     = rel.get("evidence", "")[:300]

                if not subject_text or not object_text or not relation:
                    continue

                # Resolve node IDs for subject and object using type hints
                # entity_a/entity_b carry the original NER types
                def _entity_id(text: str, etype: str) -> str:
                    etype = etype.upper()
                    if etype == "PERSON":
                        return "person__" + sanitize_id(text)
                    elif etype == "TOPONYM":
                        return "location__" + sanitize_id(text)
                    elif etype == "ORGANIZATION":
                        return "org__" + sanitize_id(text)
                    elif etype == "COMMODITY":
                        return "commodity__" + sanitize_id(text)
                    return "entity__" + sanitize_id(text)

                type_a = rel.get("type_a", "")
                type_b = rel.get("type_b", "")
                entity_a = rel.get("entity_a", subject_text)
                entity_b = rel.get("entity_b", object_text)

                # Determine which entity is subject and which is object
                if subject_text.lower() == entity_a.lower():
                    subj_id = _entity_id(entity_a, type_a)
                    obj_id  = _entity_id(entity_b, type_b)
                else:
                    subj_id = _entity_id(entity_b, type_b)
                    obj_id  = _entity_id(entity_a, type_a)

                # Only add the edge if both nodes already exist (from NER pass)
                if subj_id in nodes and obj_id in nodes:
                    add_edge(
                        subj_id, obj_id, relation,
                        confidence=confidence,
                        evidence=evidence,
                        doc_id=rel.get("doc_id", ""),
                    )
                    typed_relation_count += 1

        print(f"  {typed_relation_count} typed relation edges added.")
    else:
        print(f"\nNo typed relations file found at '{relations_path}'.")
        print("  Run pipeline/04_graph/extract_relations.py to add semantic edges.")

    # ── Materialise CO_OCCURS edges ────────────────────────────────────────────
    for (id_a, id_b), data in co_occurs_map.items():
        edges.append({
            "source": id_a,
            "target": id_b,
            "type": "CO_OCCURS",
            "weight": data["weight"],
            "entity_types": data["entity_types"],
            "evidence_docs": "|".join(data["doc_ids"]),
        })

    # ── Write nodes.csv ────────────────────────────────────────────────────────
    all_prop_keys: set[str] = set()
    for n in nodes.values():
        all_prop_keys.update(n.keys())
    node_fields = ["id", "label", "name"] + sorted(
        k for k in all_prop_keys if k not in ("id", "label", "name")
    )

    nodes_path = output_dir / "nodes.csv"
    with open(nodes_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=node_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(nodes.values())

    # ── Write edges.csv ────────────────────────────────────────────────────────
    all_edge_keys: set[str] = set()
    for e in edges:
        all_edge_keys.update(e.keys())
    edge_fields = ["source", "target", "type"] + sorted(
        k for k in all_edge_keys if k not in ("source", "target", "type")
    )

    edges_path = output_dir / "edges.csv"
    with open(edges_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=edge_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(edges)

    # ── Summary ────────────────────────────────────────────────────────────────
    label_counts: dict[str, int] = defaultdict(int)
    for n in nodes.values():
        label_counts[n["label"]] += 1
    type_counts: dict[str, int] = defaultdict(int)
    for e in edges:
        type_counts[e["type"]] += 1

    print(f"\n── Graph Summary ────────────────────────────────────")
    print(f"  Nodes: {len(nodes)}")
    for label, count in sorted(label_counts.items()):
        print(f"    {label:<20} {count:>6}")
    print(f"  Edges: {len(edges)}")
    for etype, count in sorted(type_counts.items()):
        print(f"    {etype:<25} {count:>6}")

    if typed_relation_count:
        print(f"\n  Typed semantic relations: {typed_relation_count}")

    # Top CO_OCCURS pairs by weight
    top_co = sorted(co_occurs_map.items(), key=lambda x: x[1]["weight"], reverse=True)[:10]
    if top_co:
        print(f"\n  Top entity associations (by co-occurrence weight):")
        for (id_a, id_b), data in top_co:
            name_a = nodes.get(id_a, {}).get("name", id_a)
            name_b = nodes.get(id_b, {}).get("name", id_b)
            print(f"    {name_a[:30]:<30} ↔  {name_b[:30]:<30}  weight={data['weight']}")

    print(f"\n  Nodes CSV: {nodes_path}")
    print(f"  Edges CSV: {edges_path}")
    print(f"─────────────────────────────────────────────────────")
    print(f"\nNext: python pipeline/05_lightrag/ingest.py")


if __name__ == "__main__":
    main()
