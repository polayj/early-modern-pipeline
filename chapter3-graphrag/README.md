# Chapter 3 — From NER to GraphRAG

Materials accompanying Chapter 3 of *Loud Yet Invisible: A Humanist-Designed Pipeline for Unlocking the Early Modern Archive*. This chapter takes the output of Chapter 1's OCR and Chapter 2's NER and builds a hybrid knowledge-graph + vector retrieval system over the full 20,000-document corpus.

The pipeline code in this directory is a **snapshot** of the actively maintained repository at <https://github.com/polayj/emgraphrag>. For the latest development version, see that repo; for the version-of-record for the thesis, use this snapshot.

## Phase A + B — complete

This directory was assembled in two phases, both now complete:

| Phase | What it added |
|---|---|
| **A** | Pipeline code, customs ledgers, docker configs, READMEs |
| **B** | Final figures (3.1–3.11), blind-grading results, the Internet Archive citation manifest (20,333 items), Neo4j schema docs, the evaluation queries, and the 10-document smoke test. Large artifacts (Neo4j graph, ChromaDB index, OCR outputs, model weights) — plus the full per-system LLM answers — are deposited on Zenodo. |

The EEBO STC/Wing citation manifest (`corpus-references/eebo-items.csv`) is the
one piece still pending a consolidated source list; EEBO-derived OCR remains
withheld regardless. See `../docs/PHASE-B-HANDOFF.md` for the original build brief.

## What's in here

```
chapter3-graphrag/
├── README.md                          # (this file)
├── README-emgraphrag-original.md      # The original emgraphrag README, preserved verbatim
├── requirements.txt
├── pipeline/                          # The full pipeline, numbered 00 → 06
│   ├── 00_zotero_export.py
│   ├── 01_parse_import_records.py
│   ├── 02_ocr/                        # OCR-stage submission scripts
│   ├── 03_ner/                        # NER + entity linking + LOD lookups
│   ├── 04_graph/                      # Graph construction
│   ├── 05_embed/                      # Vector embeddings
│   ├── 05_lightrag/                   # LightRAG ingest + query
│   ├── 06_query/                      # Query interfaces
│   ├── nibi/                          # SLURM scripts for the U of S 'nibi' cluster
│   └── run_pipeline.sh
├── docker/
│   └── unraid/                        # ChromaDB + Neo4j compose files
├── customs-ledgers/                   # 57 .xlsx files: British Caribbean commodity imports, 1696-1755
├── corpus-references/                 # IA citation manifest (20,333 items); EEBO manifest pending
├── schema/                            # Neo4j schema (Cypher) + entity-type definitions
├── queries/                           # Evaluation queries (30 + 5 ginger)
├── results/                           # Blind-grading results + per-system comparison tables
├── smoke-test/                        # 10-document end-to-end subset
└── figures/                           # Chapter 3 figures (3.1–3.11)
```

## The corpus

Documents OCR'd and fed into the pipeline (per the OCR job manifest):

| Source | Count |
|---|---|
| Internet Archive (OCR'd) | 17,774 |
| Early English Books Online (EEBO; OCR withheld) | 1,338 |
| British customs import ledgers (xlsx) | 57 files / 43,770 rows |

Total documents OCR'd: **19,112** (≈ 19,249 `Document` nodes in the graph).
Knowledge graph: **218,523 nodes / 691,577 edges**. (A further ~2,559 Internet
Archive items were downloaded but not carried into the final pipeline; the full
download registry of 20,333 items is in `corpus-references/archive-org-items.csv`.)

**The PDFs themselves are not redistributed.** `corpus-references/archive-org-items.csv`
lists the Internet Archive items; `corpus-references/eebo-items.csv` lists the
1,338 EEBO documents (citation only — their OCR is withheld pending review).

### Licensing notes

- **Internet Archive items**: digitized public-domain works (1614–1810). Source URLs in `corpus-references/`. OCR outputs derived from these sources will be released as a Zenodo deposit.
- **EEBO items**: page scans are proprietary (ProQuest). **OCR outputs derived from EEBO scans are withheld from this release pending copyright review with the university librarian.** Citations to EEBO sources include the STC/Wing number; readers with institutional EEBO access can consult the originals.
- **Customs ledgers (`customs-ledgers/`)**: see top-level `docs/data-provenance.md` for transcription/source attribution.

## The pipeline at a glance

```
Step 00 — Zotero export                  (optional metadata seeding)
Step 01 — Parse import records           (already done; this machine)
Step 02 — OCR PDFs                       (Phase B; GPU on school computer)
Step 03 — NER over OCR text              (Phase B; uses EarlyModernNER from Chapter 2)
Step 04 — Build knowledge graph          (Phase B)
   ├── extract_relations.py
   ├── build_graph.py                    → Neo4j (218K nodes, 692K edges per thesis)
   └── import_records_to_docs.py
Step 05 — Vector embeddings              (Phase B)
   └── generate_embeddings.py            → ChromaDB index
Step 05b — LightRAG ingest               (Phase B; alternative retrieval path)
Step 06 — Query                          (Phase B)
   └── Improved Scratchpad retrieval
```

## Running the pipeline (after Phase B Zenodo downloads)

```bash
pip install -r requirements.txt

# Bring up Neo4j + ChromaDB locally
docker compose -f docker/unraid/neo4j.compose.yml up -d
docker compose -f docker/unraid/chromadb.compose.yml up -d

# Run end-to-end (requires GPU, OCR'd documents, and configured Ollama/LLM)
bash pipeline/run_pipeline.sh
```

A 10-document smoke-test subset will be added in Phase B so reviewers can verify the pipeline runs without downloading the full Zenodo deposit.

## Live development

This snapshot represents the state of the pipeline at thesis submission. Ongoing development happens at **<https://github.com/polayj/emgraphrag>**.

## Citation

See top-level `CITATION.cff`.
