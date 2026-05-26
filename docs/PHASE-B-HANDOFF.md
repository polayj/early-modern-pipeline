# Phase B Handoff — School Computer

This document is the brief for the Claude session running on the **school computer**, where the full Chapter 3 artifacts live. Phase A built the repo skeleton on a different machine and pushed it to GitHub; Phase B fills in the corpus-scale pieces and prepares the Zenodo deposits.

## Context

Read first:
- `../README.md` — repository overview
- `../chapter3-graphrag/README.md` — current Chapter 3 status (lists what's still missing)
- `../docs/data-provenance.md` — licensing rules to apply consistently

Decisions already made in Phase A (do not re-litigate):
- Repo name: `early-modern-pipeline`
- Code: MIT; data: CC-BY-4.0
- Person-named folders (Andrew, hailey, jessica, etc.): excluded entirely
- EEBO: citations only; OCR outputs of EEBO scans are **withheld** pending librarian review
- Zenodo DOIs minted post-defense; until then use `[DOI pending]` placeholders
- Repo is public from day 1

## What needs to happen

### 1. Clone the repo

```bash
git clone https://github.com/polayj/early-modern-pipeline.git
cd early-modern-pipeline
```

### 2. Find these source paths on the school computer (you'll need to ask the user)

| Artifact | Likely location | Used for |
|---|---|---|
| Full OCR outputs for 20K corpus | `?/emgraphrag/ocr_docs/processed/` | Zenodo deposit + smoke test |
| Neo4j database dump | `?/emgraphrag/output/knowledge_graph/` | Zenodo deposit + schema files |
| ChromaDB index | `?/emgraphrag/output/lightrag_storage/` or similar | Zenodo deposit |
| Full NER outputs | `?/emgraphrag/output/ner_output/` | Zenodo deposit |
| EarlyModernNER trained weights | `?/Qwen35-{Base,DoRA,FFT}/complete/` | Zenodo deposit |
| Evaluation results from blind grading | `?` | Repo (`chapter3-graphrag/results/`) |
| Corpus citation metadata | `?/emgraphrag/ocr_docs/unprocessed/archive_org/*/metadata.json` (Archive.org standard) | Repo (`chapter3-graphrag/corpus-references/`) |

Ask the user for the exact paths before assuming anything.

### 3. Build the Zenodo deposits

Each deposit is a `.zip` ready to upload (do **not** upload yet — DOIs are minted post-defense). Each must contain its own `README.md` and `LICENSE` file.

| Deposit | Contents | License |
|---|---|---|
| `zenodo-earlymodernner-weights.zip` | DoRA + FFT adapters, base model config; instructions to load with the package from `chapter2-ner/earlymodernner/` | Apache-2.0 (matches Qwen3 base) |
| `zenodo-ocr-outputs-20k.zip` | Plain-text OCR transcriptions for **Internet Archive sources only**; per-document JSON metadata; provenance README naming olmOCR-2 as the producing system | CC-BY-4.0 |
| `zenodo-knowledge-graph.zip` | Neo4j dump (`.dump` or Cypher export), ChromaDB index, schema documentation, 10-doc smoke-test subset | CC-BY-4.0 |
| `zenodo-ner-training-corpus.zip` | The training data used to fine-tune EarlyModernNER (your work; cite sources for any imported corpora like PCEEC2, Old Bailey if redistributed) | CC-BY-4.0 (your work); third-party datasets cited but not redistributed unless their license allows |
| `zenodo-customs-ledgers.zip` | Normalized 43K-row trade data (if your transcription); the `.xlsx` files are already in the repo, this deposit adds the cleaned/joined form | CC-BY-4.0 if your work; otherwise cite-and-link only |

### 4. Add to the repo (committed to GitHub)

These pieces go into the repo itself because they're small and essential for reproducibility:

- `chapter3-graphrag/corpus-references/archive-org-items.csv` — full citation manifest (one row per IA item)
- `chapter3-graphrag/corpus-references/eebo-items.csv` — STC/Wing-only manifest for EEBO sources
- `chapter3-graphrag/schema/` — Neo4j schema (Cypher) + entity-type definitions + any migration scripts
- `chapter3-graphrag/queries/` — the exact evaluation queries used in the thesis
- `chapter3-graphrag/results/` — blind-grading results (CSV/JSON), per-system comparison tables
- `chapter3-graphrag/smoke-test/` — 10 representative documents (with OCR text + expected graph fragment) so reviewers can run the pipeline end-to-end without downloading Zenodo
- `chapter3-graphrag/figures/` — Chapter 3 figures (3.1–3.7) as PNG/SVG

### 4a. Grading workflow — important sequencing note

At the time Phase A was committed, the user's Chapter 3 grading was **not yet complete**. The user will hand you a final grading Excel file (likely `chapter3_grading.xlsx` or similar). When that arrives:

1. **Parse the Excel file** — confirm with the user which sheet/columns hold the per-query, per-system scores.
2. **Regenerate every Chapter 3 figure** that depends on grading data — Figures 3.x that show per-system comparison, blind-grading results, tier breakdowns, etc. Save updates to `chapter3-graphrag/figures/`.
3. **Update `chapter3-graphrag/results/`** — write the cleaned grading data as CSV/JSON; preserve the raw Excel alongside for provenance.
4. **Update any numbers in `chapter3-graphrag/README.md`** that reference grading outcomes (e.g., "~10 unique documents per query vs. competitors' 4.2 average" — verify against final grades).
5. **Update the thesis document** itself (`Masters Thesis Draft 3.docx` or whichever is current) with the final grades and figures — confirm with the user before editing the thesis.
6. **Commit in one logical batch** with a message like `chapter 3: add final grading data, regenerate figures, update narrative`.

Do **not** push Chapter 3 grading commits until the user confirms the grades are final and the thesis text has been updated to match.

### 5. Update placeholders

Once Zenodo DOIs are minted (post-defense):
- Top-level `README.md`: replace `[DOI pending]` in the Zenodo deposits table
- `data/README.md`: list each Zenodo deposit with DOI and short description
- `CITATION.cff`: bump version to `1.0.0`, update `date-released`, and add `identifiers:` block with each Zenodo DOI

### 6. Tag the release

```bash
git tag -a v1.0.0 -m "Thesis-of-record release"
git push origin v1.0.0
```

If GitHub-Zenodo integration is enabled on the repo, this will auto-mint a repo-level DOI for the tagged snapshot.

## Validation checklist (run on the school computer before pushing)

```bash
bash scripts/prepare-release.sh
```

The script checks: no secrets, no files >50MB (warn) or >100MB (fail), `.gitignore` covers `.env`, all license files present. It must pass before any push.

Additional manual checks:

- [ ] Every EEBO citation has a clear "OCR text withheld pending review" note nearby
- [ ] Every Internet Archive citation links to the public archive.org URL
- [ ] The smoke-test runs end-to-end on a fresh checkout (verify on a clean Python env)
- [ ] `CITATION.cff` parses (test by clicking "Cite this repository" on GitHub)
- [ ] Zenodo deposit zips each have their own README and LICENSE inside

## Notes for the school-computer session

- This repo's `.gitignore` already excludes weights (`*.safetensors`, `*.pt`, etc.) and database dumps (`*.dump`, `neo4j_data/`). Don't try to commit those — they go to Zenodo deposit zips instead.
- If you find files >50MB that genuinely should be in the repo (e.g., a figure or PDF), confirm with the user before adding.
- The user said "much of what we have from Chapter 3 is on my school computer" — but the **OCR'd docs are 1.3 TB** on the Phase A machine too. Don't accidentally duplicate that bulk into a Zenodo deposit. Confirm what's the canonical version.
- The customs ledger Excel files (`chapter3-graphrag/customs-ledgers/*.xlsx`) are already in the repo from Phase A. The Zenodo customs-ledgers deposit should contain the *normalized/cleaned* version (43K rows in a single tidy CSV), not the raw Excels.
