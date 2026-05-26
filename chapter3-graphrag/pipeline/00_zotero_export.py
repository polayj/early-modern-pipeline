#!/usr/bin/env python3
"""
00_zotero_export.py
Export PDFs from a Zotero group library or collection into ocr_docs/unprocessed/EEBO/.

Reads Zotero's SQLite database to find exactly which items belong to a
named group library or collection, then copies their PDFs preserving
the Author-Year-Title filenames that Zotero already assigned.

IMPORTANT: Close Zotero before running this script (or it will use a
safe read-only copy of the database automatically).

Usage:
    # Step 1 — list all your Zotero collections and groups:
    python pipeline/00_zotero_export.py --list-collections

    # Step 2 — dry run to preview what would be copied:
    python pipeline/00_zotero_export.py --group "CaribbeanGraphRAG" --dry-run

    # Step 3 — actually copy:
    python pipeline/00_zotero_export.py --group "CaribbeanGraphRAG"

    # Export a specific collection instead:
    python pipeline/00_zotero_export.py --collection "EEBO" --dry-run

Options:
    --zotero-dir    Path to Zotero data directory (default: /mnt/h/Zotero)
    --output        Destination folder (default: ocr_docs/unprocessed/EEBO)
    --group         Zotero group library name to export (e.g. CaribbeanGraphRAG)
    --collection    Zotero collection name to export (personal library)
    --list-collections  Print all collections and groups and exit
    --dry-run       Show what would be copied without copying
    --no-rename     Keep Zotero's existing filenames (default behaviour;
                    use --rename to regenerate from metadata instead)
"""

import argparse
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path


def open_db(zotero_dir: Path) -> sqlite3.Connection:
    """
    Open zotero.sqlite in read-only mode.
    Makes a temp copy first so we don't corrupt Zotero's live database.
    """
    db_path = zotero_dir / "zotero.sqlite"
    if not db_path.exists():
        print(f"ERROR: Zotero database not found at {db_path}")
        print("  Check --zotero-dir points to your Zotero data folder.")
        sys.exit(1)

    # Copy to a temp file so we don't lock or corrupt the live DB
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    shutil.copy2(db_path, tmp.name)
    conn = sqlite3.connect(tmp.name)
    conn.row_factory = sqlite3.Row
    return conn


def list_collections(conn: sqlite3.Connection):
    """Print all group libraries and personal collections with item counts."""
    # Group libraries
    groups = conn.execute("""
        SELECT g.name, l.libraryID,
               COUNT(DISTINCT ia.itemID) AS pdf_count
        FROM groups g
        JOIN libraries l ON l.libraryID = g.libraryID
        LEFT JOIN items i ON i.libraryID = l.libraryID
        LEFT JOIN itemAttachments ia ON ia.parentItemID = i.itemID
            AND (ia.contentType = 'application/pdf' OR LOWER(ia.path) LIKE '%.pdf')
        GROUP BY g.groupID
        ORDER BY g.name
    """).fetchall()

    print(f"\n── Group Libraries ──────────────────────────────────")
    print(f"  {'Group Name':<45} {'PDFs':>6}")
    print("  " + "─" * 55)
    for r in groups:
        print(f"  {r['name']:<45} {r['pdf_count']:>6}")
    print(f"\n  Export a group: --group \"<name>\"")

    # Personal collections
    rows = conn.execute("""
        SELECT c.collectionName,
               COUNT(DISTINCT ci.itemID) AS item_count,
               pc.collectionName AS parent_name
        FROM collections c
        LEFT JOIN collectionItems ci ON ci.collectionID = c.collectionID
        LEFT JOIN collections pc ON pc.collectionID = c.parentCollectionID
        WHERE c.libraryID = 1
        GROUP BY c.collectionID
        ORDER BY pc.collectionName NULLS FIRST, c.collectionName
    """).fetchall()

    print(f"\n── Personal Collections ─────────────────────────────")
    print(f"  {'Collection':<45} {'Items':>6}  Parent")
    print("  " + "─" * 65)
    for r in rows:
        parent = f"(in: {r['parent_name']})" if r['parent_name'] else ""
        print(f"  {r['collectionName']:<45} {r['item_count']:>6}  {parent}")
    print(f"\n  Export a collection: --collection \"<name>\"")


def get_group_library_id(conn: sqlite3.Connection, name: str) -> int:
    """Return the libraryID for a named Zotero group library."""
    rows = conn.execute("""
        SELECT g.groupID, g.name, l.libraryID
        FROM groups g
        JOIN libraries l ON l.libraryID = g.libraryID
        WHERE LOWER(g.name) = LOWER(?)
    """, (name,)).fetchall()

    if not rows:
        rows = conn.execute("""
            SELECT g.groupID, g.name, l.libraryID
            FROM groups g
            JOIN libraries l ON l.libraryID = g.libraryID
            WHERE LOWER(g.name) LIKE LOWER(?)
        """, (f"%{name}%",)).fetchall()

    if not rows:
        print(f"ERROR: No group library found matching '{name}'.")
        print("  Run --list-collections to see all groups.")
        sys.exit(1)

    if len(rows) > 1:
        print(f"Multiple groups match '{name}':")
        for r in rows:
            print(f"  - {r['name']} (libraryID={r['libraryID']})")
        sys.exit(1)

    print(f"Group library: '{rows[0]['name']}' (libraryID={rows[0]['libraryID']})")
    return rows[0]["libraryID"]


def get_group_pdf_attachments(conn: sqlite3.Connection, library_id: int) -> list[dict]:
    """Return all PDF attachments for every item in a group library."""
    rows = conn.execute("""
        SELECT
            att_items.key       AS item_key,
            ia.path             AS path,
            ia.contentType      AS content_type,
            (SELECT idv.value FROM itemData id2
             JOIN itemDataValues idv ON idv.valueID = id2.valueID
             JOIN fields f ON f.fieldID = id2.fieldID
             WHERE id2.itemID = ia.parentItemID AND f.fieldName = 'title'
             LIMIT 1)           AS title,
            (SELECT idv.value FROM itemData id2
             JOIN itemDataValues idv ON idv.valueID = id2.valueID
             JOIN fields f ON f.fieldID = id2.fieldID
             WHERE id2.itemID = ia.parentItemID AND f.fieldName = 'date'
             LIMIT 1)           AS date_raw,
            (SELECT lastName FROM creators cr
             JOIN itemCreators ic ON ic.creatorID = cr.creatorID
             WHERE ic.itemID = ia.parentItemID
             ORDER BY ic.orderIndex LIMIT 1) AS author_last,
            (SELECT firstName FROM creators cr
             JOIN itemCreators ic ON ic.creatorID = cr.creatorID
             WHERE ic.itemID = ia.parentItemID
             ORDER BY ic.orderIndex LIMIT 1) AS author_first
        FROM itemAttachments ia
        JOIN items att_items ON att_items.itemID = ia.itemID
        WHERE att_items.libraryID = ?
          AND (ia.contentType = 'application/pdf' OR LOWER(ia.path) LIKE '%.pdf')
          AND att_items.itemID NOT IN (SELECT itemID FROM deletedItems)
    """, (library_id,)).fetchall()

    return [dict(r) for r in rows]


def get_collection_ids(conn: sqlite3.Connection, name: str) -> list[int]:
    """
    Return collectionIDs for the named collection and all its subcollections.
    """
    # Find the root collection (case-insensitive match)
    roots = conn.execute("""
        SELECT collectionID, collectionName
        FROM collections
        WHERE LOWER(collectionName) = LOWER(?)
    """, (name,)).fetchall()

    if not roots:
        # Try partial match
        roots = conn.execute("""
            SELECT collectionID, collectionName
            FROM collections
            WHERE LOWER(collectionName) LIKE LOWER(?)
        """, (f"%{name}%",)).fetchall()

    if not roots:
        print(f"ERROR: No collection found matching '{name}'.")
        print("  Run --list-collections to see all collection names.")
        sys.exit(1)

    if len(roots) > 1:
        print(f"Multiple collections match '{name}':")
        for r in roots:
            print(f"  - {r['collectionName']} (id={r['collectionID']})")
        print("  Use a more specific name.")
        sys.exit(1)

    root_id = roots[0]["collectionID"]
    print(f"Collection: '{roots[0]['collectionName']}' (id={root_id})")

    # Recursively find all subcollection IDs
    all_ids = [root_id]
    queue = [root_id]
    while queue:
        parent_id = queue.pop()
        children = conn.execute("""
            SELECT collectionID FROM collections
            WHERE parentCollectionID = ?
        """, (parent_id,)).fetchall()
        for c in children:
            all_ids.append(c["collectionID"])
            queue.append(c["collectionID"])

    return all_ids


def get_pdf_attachments(conn: sqlite3.Connection, collection_ids: list[int]) -> list[dict]:
    """
    Return a list of dicts with all PDF attachments for items in the given collections.
    Each dict: {item_key, filename, title, author, year, content_type}
    """
    placeholders = ",".join("?" * len(collection_ids))

    rows = conn.execute(f"""
        SELECT
            att_items.key       AS item_key,
            ia.path             AS path,
            ia.contentType      AS content_type,
            -- Title from parent item
            (SELECT idv.value FROM itemData id2
             JOIN itemDataValues idv ON idv.valueID = id2.valueID
             JOIN fields f ON f.fieldID = id2.fieldID
             WHERE id2.itemID = ia.parentItemID AND f.fieldName = 'title'
             LIMIT 1)           AS title,
            -- Year from parent item (date field)
            (SELECT idv.value FROM itemData id2
             JOIN itemDataValues idv ON idv.valueID = id2.valueID
             JOIN fields f ON f.fieldID = id2.fieldID
             WHERE id2.itemID = ia.parentItemID AND f.fieldName = 'date'
             LIMIT 1)           AS date_raw,
            -- First author (creator) of parent item
            (SELECT lastName FROM creators cr
             JOIN itemCreators ic ON ic.creatorID = cr.creatorID
             WHERE ic.itemID = ia.parentItemID
             ORDER BY ic.orderIndex
             LIMIT 1)           AS author_last,
            (SELECT firstName FROM creators cr
             JOIN itemCreators ic ON ic.creatorID = cr.creatorID
             WHERE ic.itemID = ia.parentItemID
             ORDER BY ic.orderIndex
             LIMIT 1)           AS author_first
        FROM collectionItems ci
        JOIN itemAttachments ia ON ia.parentItemID = ci.itemID
        JOIN items att_items ON att_items.itemID = ia.itemID
        WHERE ci.collectionID IN ({placeholders})
          AND (ia.contentType = 'application/pdf' OR LOWER(ia.path) LIKE '%.pdf')
          AND att_items.itemID NOT IN (SELECT itemID FROM deletedItems)
    """, collection_ids).fetchall()

    return [dict(r) for r in rows]


def extract_year(date_raw: str | None) -> str:
    """Extract 4-digit year from a Zotero date string."""
    if not date_raw:
        return "unknown"
    m = re.search(r"\b(\d{4})\b", str(date_raw))
    return m.group(1) if m else "unknown"


def make_filename(row: dict, original_filename: str) -> str:
    """
    Build a clean 'Author - Year - Title.pdf' filename.
    Falls back to the original filename if metadata is missing.
    """
    author = row.get("author_last") or ""
    if not author and row.get("author_first"):
        author = row["author_first"]
    if not author:
        author = "Unknown"

    year = extract_year(row.get("date_raw"))
    title = (row.get("title") or "").strip()

    if not title:
        # Fall back to original filename (strip extension)
        title = Path(original_filename).stem

    # Sanitize: remove chars that are bad in filenames
    def clean(s: str) -> str:
        return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', s).strip()[:120]

    author = clean(author)
    title = clean(title)

    return f"{author} - {year} - {title}.pdf"


def resolve_path(zotero_dir: Path, item_key: str, path_field: str) -> Path | None:
    """
    Resolve a Zotero attachment path to an actual filesystem path.
    - Stored files: path = "storage:filename.pdf" → <zotero_dir>/storage/<key>/filename.pdf
    - Linked files: path = absolute path or relative
    """
    if path_field and path_field.startswith("storage:"):
        filename = path_field[len("storage:"):]
        return zotero_dir / "storage" / item_key / filename
    elif path_field:
        # Linked file — may be absolute path or attachments-relative
        p = Path(path_field)
        if p.exists():
            return p
        # Try relative to zotero_dir
        candidate = zotero_dir / path_field
        if candidate.exists():
            return candidate
    # Fall back: search the storage subfolder for any PDF
    storage_dir = zotero_dir / "storage" / item_key
    if storage_dir.exists():
        pdfs = list(storage_dir.glob("*.pdf")) + list(storage_dir.glob("*.PDF"))
        if pdfs:
            return pdfs[0]
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Export PDFs from a Zotero group/collection to ocr_docs/unprocessed/EEBO/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--zotero-dir", default="/mnt/h/Zotero",
                        help="Zotero data directory (default: /mnt/h/Zotero)")
    parser.add_argument("--output", default="ocr_docs/unprocessed/EEBO",
                        help="Output directory (default: ocr_docs/unprocessed/EEBO)")
    parser.add_argument("--group", default=None,
                        help="Zotero group library name to export (e.g. CaribbeanGraphRAG)")
    parser.add_argument("--collection", default=None,
                        help="Zotero personal collection name to export")
    parser.add_argument("--list-collections", action="store_true",
                        help="List all groups and collections and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview what would be copied without copying")
    parser.add_argument("--rename", action="store_true",
                        help="Regenerate filenames from metadata (default: keep Zotero's filenames)")
    args = parser.parse_args()

    zotero_dir = Path(args.zotero_dir)
    output_dir = Path(args.output)

    if not zotero_dir.exists():
        print(f"ERROR: Zotero directory not found: {zotero_dir}")
        sys.exit(1)

    print(f"Zotero data dir: {zotero_dir}")
    print("Opening database (read-only copy)...")
    conn = open_db(zotero_dir)

    if args.list_collections:
        list_collections(conn)
        return

    if not args.group and not args.collection:
        print("ERROR: Specify --group <name> or --collection <name>")
        print("  Example: python pipeline/00_zotero_export.py --group CaribbeanGraphRAG --dry-run")
        print("  Run --list-collections to see available options.")
        sys.exit(1)

    # Get attachments from group library or named collection
    if args.group:
        library_id = get_group_library_id(conn, args.group)
        attachments = get_group_pdf_attachments(conn, library_id)
    else:
        collection_ids = get_collection_ids(conn, args.collection)
        print(f"  (includes {len(collection_ids)} subcollection(s))")
        attachments = get_pdf_attachments(conn, collection_ids)

    print(f"  PDF attachments found: {len(attachments)}")

    if not attachments:
        print("No PDFs found.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Build set of filenames already in the output directory (for duplicate detection)
    existing_names = {f.name for f in output_dir.glob("*.pdf")}
    existing_names.update(f.name for f in output_dir.glob("*.PDF"))
    print(f"  Already in output dir: {len(existing_names)} files (will be skipped)")

    if args.dry_run:
        print(f"\n── DRY RUN — first 20 files that would be copied ──────")

    copied = 0
    skipped_existing = 0
    skipped_duplicate = 0
    missing = 0
    renamed = 0

    for row in attachments:
        item_key = row["item_key"]
        path_field = row.get("path") or ""

        src = resolve_path(zotero_dir, item_key, path_field)

        if src is None or not src.exists():
            if missing < 5:
                print(f"  MISSING: key={item_key}  path={path_field}")
            missing += 1
            continue

        original_name = src.name

        # Determine destination filename
        if args.rename:
            dest_name = make_filename(row, original_name)
            if dest_name != original_name:
                renamed += 1
        else:
            # Keep Zotero's existing filename (already Author - Year - Title.pdf)
            dest_name = original_name

        # Skip if this filename already exists in the output dir
        if dest_name in existing_names:
            skipped_duplicate += 1
            continue

        dest = output_dir / dest_name

        if dest.exists():
            skipped_existing += 1
            continue

        if args.dry_run:
            if copied < 20:
                print(f"  {original_name[:90]}")
                if args.rename and dest_name != original_name:
                    print(f"    → {dest_name}")
            copied += 1
            continue

        shutil.copy2(src, dest)
        existing_names.add(dest_name)  # prevent dupes within this run
        copied += 1

    # Summary
    total_skipped = skipped_existing + skipped_duplicate
    print(f"\n── Summary ──────────────────────────────────────────")
    if args.dry_run:
        print(f"  Would copy:    {copied}")
        print(f"  Already exist: {total_skipped} (skipped — already in EEBO folder)")
        print(f"  Missing files: {missing}")
        if args.rename:
            print(f"  Would rename:  {renamed}")
        print(f"\n  Re-run without --dry-run to copy.")
    else:
        print(f"  Copied:        {copied}")
        print(f"  Already exist: {total_skipped} (skipped)")
        print(f"  Missing files: {missing} (not in Zotero storage)")
        if args.rename:
            print(f"  Renamed:       {renamed}")
        print(f"  Output dir:    {output_dir}")
    print("─────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
