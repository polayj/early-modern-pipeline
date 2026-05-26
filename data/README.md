# data/ — Large Artifacts Live on Zenodo

This directory is intentionally light. The bulky datasets and model weights that don't belong in a Git repository are deposited on Zenodo with permanent DOIs and are listed here.

## Status

All deposits are **pending** until the thesis defense. Until then, this list shows what *will* be available; DOIs are placeholders.

## Deposits

### 1. EarlyModernNER — Trained Weights
`[DOI pending]`

DoRA and full-fine-tune adapter weights for the four entity-type-specialized models (Commodity, Organization, Person, Toponym) that constitute EarlyModernNER. Base model is Qwen3-4B-Instruct-2507.

- License: Apache-2.0 (matches Qwen3 base)
- Size: ~20 GB total
- Install: see `chapter2-ner/earlymodernner/earlymodernner/adapters/README.md`

### 2. OCR Outputs — 20K-Document Corpus
`[DOI pending]`

Plain-text transcriptions produced by olmOCR-2 over the Internet Archive portion of the 20,000-document corpus (~18,579 documents). One file per source document plus a JSON manifest with provenance.

- License: CC-BY-4.0
- Size: ~1–5 GB compressed
- EEBO-derived outputs are **not** included pending copyright review

### 3. Knowledge Graph + Vector Index
`[DOI pending]`

The Neo4j knowledge graph (218,000 nodes, 692,000 edges per thesis figures) and the ChromaDB vector index (1.46M–1.78M chunks) used by the GraphRAG retrieval system. Includes loading instructions and the 10-document smoke-test set.

- License: CC-BY-4.0
- Size: TBD; expect several GB
- Use with: `chapter3-graphrag/pipeline/06_query/query.py`

### 4. NER Training Corpus
`[DOI pending]`

The corpus used to train EarlyModernNER's per-entity-type adapters: ~345 manually annotated documents, synthetic-data augmentation, and ~25M tokens drawn from publicly available historical corpora (Old Bailey Online, PCEEC2, Royal Society Corpus).

- License: CC-BY-4.0 for original annotations and synthetic data; third-party corpora cited but redistributed only where their license allows
- Size: TBD
- Use with: `chapter2-ner/training-recipes/train_lora.py`

### 5. Normalized Customs Ledger Dataset
`[DOI pending]`

A cleaned/joined version of the 57-file `chapter3-graphrag/customs-ledgers/` Excel data: ~43,000 rows of British Caribbean commodity imports (1696–1755) in a single tidy CSV, with commodity-name normalization and entity linking to the knowledge graph.

- License: CC-BY-4.0 (pending confirmation of source attribution)
- Size: small (~10 MB)

## How DOIs will be minted

After the thesis defense passes:

1. Each deposit is uploaded to Zenodo (manual; requires login).
2. Zenodo mints a DOI per deposit; each version of a deposit gets its own DOI, with a "concept DOI" linking to the latest.
3. A v1.0.0 GitHub release of this repository triggers Zenodo's GitHub integration, minting a repo-level DOI for the thesis-of-record snapshot.
4. The top-level `README.md` and this file are updated to replace `[DOI pending]` with the actual DOIs.
5. `CITATION.cff` gains an `identifiers:` block listing every DOI.

## Citing this data

Until DOIs are minted, cite the GitHub repository:

> Polay, Jacob. (2026). *early-modern-pipeline*. GitHub. https://github.com/polayj/early-modern-pipeline

Post-defense, cite the appropriate Zenodo DOI for the specific artifact you used.
