# corpus-references/

Citation manifest for the documents used in Chapter 3's GraphRAG system. The
source PDFs are **not** redistributed here — this directory provides the
citations so any item can be retrieved from its original host.

## Files

| File | Rows | Contents |
|---|---|---|
| `archive-org-items.csv` | 20,333 | Internet Archive download registry: `identifier, title, creator, publication_year, publication_place, publisher, archive_url`. |
| `eebo-items.csv` | 1,338 | The EEBO documents OCR'd into the pipeline: `author, year, title, source, ocr_status`. Citation only — OCR withheld. |

## What the numbers reconcile to

From the OCR job manifest (`pdf_list.txt`), the pipeline OCR'd **19,112**
documents:

- **17,774** Internet Archive documents
- **1,338** EEBO documents

A further ~2,559 Internet Archive items were downloaded (20,333 total in
`archive-org-items.csv`) but not carried into the final pipeline. The graph
holds **19,249 `Document` nodes** (≈ the 19,112 OCR'd).

> The thesis text's "18,579 IA + ~100 EEBO" predates this reconciliation; the
> verifiable EEBO count is **1,338**, not ~100.

## Copyright stance

- **Internet Archive items**: public-domain digitizations (1614–1810). Full
  citation + `archive_url`; OCR text deposited on Zenodo (Internet Archive
  sources only). Original PDFs hosted by archive.org.
- **EEBO items**: page scans are proprietary (ProQuest). **OCR text derived
  from EEBO scans is withheld** pending copyright review with the university
  librarian. `eebo-items.csv` gives author/title/year (the filename-derived
  citation; some titles are truncated, and STC/Wing numbers are not present in
  the source metadata — readers with institutional EEBO access can locate the
  originals by author/title/year).
- **EEBO-derived graph triples**: entities and relations extracted from EEBO
  OCR *are* present in the knowledge graph (and its Zenodo deposit), on the
  basis that extracted facts/relations are not the copyrighted page-scan text.
  This is noted in the deposit provenance and is subject to the same librarian
  review.

The OCR Zenodo deposit is built **withholding-by-construction**: it ships only
transcriptions whose document positively matches the Internet Archive registry,
so no EEBO-derived OCR text can leak into it.

See `../customs-ledgers/` and `../../docs/data-provenance.md` for the customs
import-ledger provenance (transcribed from TNA CUST 3).
