#!/usr/bin/env python3
"""
04_graph/import_records_to_docs.py
Convert import record CSV rows into human-readable markdown documents
suitable for LightRAG ingestion.

This is a complementary/standalone script to 01_parse_import_records.py.
It can re-generate the import_docs from the CSV (without re-parsing xlsx),
and also write a combined version to output/lightrag_input/ alongside
OCR markdown files.

Usage:
    python pipeline/04_graph/import_records_to_docs.py
    python pipeline/04_graph/import_records_to_docs.py \\
        --records output/import_records_parsed/all_records.csv \\
        --output output/lightrag_input/import_docs/
"""

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path


def sanitize_filename(text: str) -> str:
    return re.sub(r"[^\w\-]", "_", text.strip())[:80]


def build_docs(records: list[dict], output_dir: Path) -> int:
    """
    Generate one markdown document per (year_range, from_location) pair.
    Returns count of docs written.
    """
    # Group by (year_range, from_location, to_location)
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        groups[(r["year_range"], r["from_location"])].append(r)

    output_dir.mkdir(parents=True, exist_ok=True)
    written = 0

    for (year_range, from_loc), rows in sorted(groups.items()):
        # Determine destination(s)
        destinations = sorted({r["to_location"] for r in rows if r["to_location"]})
        dest_str = ", ".join(destinations) if destinations else "London"

        safe_yr = sanitize_filename(year_range)
        safe_loc = sanitize_filename(from_loc)
        fname = f"import__{safe_yr}__{safe_loc}.md"
        fpath = output_dir / fname

        # Sort rows by commodity
        rows.sort(key=lambda r: r["commodity_name"])

        # Header
        lines = [
            f"# British Caribbean Import Record: {from_loc}, {year_range}",
            "",
            f"**Period:** {year_range}",
            f"**Exporting colony:** {from_loc}",
            f"**Destination(s):** {dest_str}",
            f"**Source:** British Customs records (1696–1755)",
            "",
            "## Commodity Exports",
            "",
        ]

        # Table header
        lines += [
            "| Commodity | Hogsheads | Tons | Quarters | Pounds (lb) | Total Pounds | Weight Tons | Destination |",
            "|-----------|-----------|------|----------|-------------|--------------|-------------|-------------|",
        ]

        for r in rows:
            lines.append(
                f"| {r['commodity_name']} "
                f"| {r['hh'] or ''} "
                f"| {r['ton'] or ''} "
                f"| {r['quarter'] or ''} "
                f"| {r['lb'] or ''} "
                f"| {r['total_pounds'] or ''} "
                f"| {r['weight_tons'] or ''} "
                f"| {r['to_location'] or ''} |"
            )

        lines += ["", "## Narrative", ""]

        # Group by destination for narrative clarity
        by_dest: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            by_dest[r["to_location"]].append(r)

        for dest, dest_rows in sorted(by_dest.items()):
            notable = [r for r in dest_rows if _is_notable(r)]
            if not notable:
                continue
            lines.append(f"### Exports to {dest}")
            lines.append("")
            for r in notable:
                lines.append(_narrative_sentence(r))
            lines.append("")

        # Aggregate stats
        total_weight = sum(
            float(r["weight_tons"]) for r in rows if r.get("weight_tons")
        )
        total_lbs = sum(
            float(r["total_pounds"]) for r in rows if r.get("total_pounds")
        )
        commodity_count = len({r["commodity_name"] for r in rows})

        lines += [
            "## Summary Statistics",
            "",
            f"- **Total weight exported:** {total_weight:,.2f} weight tons",
            f"- **Total pounds (all commodities):** {total_lbs:,.0f} lb",
            f"- **Number of commodity types:** {commodity_count}",
            f"- **Year range:** {year_range}",
            f"- **Colony:** {from_loc}",
            "",
        ]

        fpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written += 1

    return written


def _is_notable(r: dict) -> bool:
    """Return True if the record has any non-zero quantity."""
    return any(
        r.get(c) and float(r[c]) > 0
        for c in ("total_pounds", "weight_tons", "hh", "ton", "lb")
    )


def _narrative_sentence(r: dict) -> str:
    """Build a single readable sentence for a commodity record."""
    parts = []
    if r.get("hh") and float(r["hh"]) > 0:
        parts.append(f"{int(float(r['hh']))} hogsheads")
    if r.get("ton") and float(r["ton"]) > 0:
        parts.append(f"{float(r['ton']):.1f} tons")
    if r.get("quarter") and float(r["quarter"]) > 0:
        parts.append(f"{int(float(r['quarter']))} quarters")
    if r.get("lb") and float(r["lb"]) > 0:
        parts.append(f"{int(float(r['lb']))} lb")

    qty = ", ".join(parts) if parts else "an unspecified quantity of"
    weight_note = ""
    if r.get("weight_tons") and float(r["weight_tons"]) > 0:
        weight_note = f" (≈ {float(r['weight_tons']):.2f} weight tons)"

    year = r.get("year") or r.get("year_start") or "that year"
    return (
        f"- In {year}, {r['from_location']} exported {qty} of "
        f"**{r['commodity_name']}** to {r['to_location']}{weight_note}."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Convert import records CSV to LightRAG-ready markdown docs."
    )
    parser.add_argument(
        "--records", default="output/import_records_parsed/all_records.csv",
        help="Path to parsed records CSV (from step 01)"
    )
    parser.add_argument(
        "--output", default="output/lightrag_input/import_docs",
        help="Output directory for markdown docs"
    )
    parser.add_argument(
        "--also-copy-ocr", action="store_true",
        help="Also symlink OCR markdown files into output/lightrag_input/"
    )
    parser.add_argument(
        "--ocr-dir", default="output/ocr_md",
        help="OCR markdown directory (used with --also-copy-ocr)"
    )
    args = parser.parse_args()

    records_path = Path(args.records)
    output_dir = Path(args.output)

    if not records_path.exists():
        print(f"ERROR: Records CSV not found: {records_path}")
        print("  Run pipeline/01_parse_import_records.py first.")
        sys.exit(1)

    print(f"Loading records from '{records_path}'...")
    records = []
    with open(records_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if _is_notable(row):
                records.append(row)

    print(f"  {len(records)} non-zero records loaded")

    n = build_docs(records, output_dir)
    print(f"Wrote {n} markdown docs to '{output_dir}'")

    if args.also_copy_ocr:
        ocr_dir = Path(args.ocr_dir)
        if not ocr_dir.exists():
            print(f"WARN: OCR directory not found: {ocr_dir}")
        else:
            lightrag_dir = output_dir.parent
            lightrag_dir.mkdir(parents=True, exist_ok=True)
            ocr_link = lightrag_dir / "ocr_docs"
            if not ocr_link.exists():
                os.symlink(ocr_dir.resolve(), ocr_link)
                print(f"Symlinked OCR docs: {ocr_link} -> {ocr_dir.resolve()}")
            else:
                print(f"OCR symlink already exists: {ocr_link}")

    print("Done.")


if __name__ == "__main__":
    main()
