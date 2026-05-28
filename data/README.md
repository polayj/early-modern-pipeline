# data/ — Large Artifacts Live on Zenodo

This directory is intentionally light. The bulky datasets and model weights
that don't belong in a Git repository are deposited on Zenodo with permanent
DOIs and are listed here.

## Status

**Pre-defense release (v0.9.0)** — all five deposits are published on Zenodo so
examiners can cite the supplementary materials by DOI. After the defense, each
deposit will gain a v1.0.0 "thesis of record" version under the same concept
DOI (which always resolves to the latest version).

## Deposits

### 1. EarlyModernNER — Trained Weights
Concept DOI: [10.5281/zenodo.20420895](https://doi.org/10.5281/zenodo.20420895) ·
v0.9.0 DOI: [10.5281/zenodo.20420896](https://doi.org/10.5281/zenodo.20420896)

Four entity-type-specialized LoRA adapters (COMMODITY, ORGANIZATION, PERSON,
TOPONYM) over the Qwen3-4B-Instruct-2507 base model. Archival mirror of
<https://huggingface.co/jacobpol/earlymodernner-adapters>.

- License: Apache-2.0 (matches Qwen3 base)
- Size: ~2.1 GB (4 × 528 MB adapters + configs)
- Install: see `chapter2-ner/earlymodernner/earlymodernner/adapters/README.md`

### 2. OCR Outputs — Internet Archive Corpus
Concept DOI: [10.5281/zenodo.20420918](https://doi.org/10.5281/zenodo.20420918) ·
v0.9.0 DOI: [10.5281/zenodo.20420919](https://doi.org/10.5281/zenodo.20420919)

Plain-text transcriptions produced by olmOCR-2 over the **Internet Archive**
portion of the corpus — 15,799 documents (selected by positive registry match;
EEBO-derived OCR excluded by construction and verified absent). One `.md` per
source document plus a citation manifest.

- License: CC-BY-4.0
- Size: 1.6 GB compressed (4.7 GB extracted)
- EEBO-derived OCR is **withheld** pending copyright review

### 3. Knowledge Graph + Vector Text/Metadata + Evaluation Outputs
Concept DOI: [10.5281/zenodo.20420920](https://doi.org/10.5281/zenodo.20420920) ·
v0.9.0 DOI: [10.5281/zenodo.20420921](https://doi.org/10.5281/zenodo.20420921)

The Neo4j knowledge graph (**218,523 nodes / 691,577 edges**) used by the
GraphRAG retrieval system, with the chunk text + metadata for the ChromaDB
vector collections (`emgraphrag_v2` 1,787,307 chunks + `entity_evidence`
250,091 records — **embedding vectors not included**, recomputable via
`pipeline/05_embed` + Qwen3-Embedding). Also includes the schema, the
10-document smoke test, and the **full per-system LLM answers** to the 30
eval questions + 5 ginger questions (including the Improved Scratchpad notes).

- License: CC-BY-4.0 (EEBO-derived facts/relations included as extracted facts,
  not page-scan text — see deposit README)
- Size: 2.4 GB compressed
- Use with: `chapter3-graphrag/pipeline/06_query/query.py`

### 4. NER Training Corpus
Concept DOI: [10.5281/zenodo.20420664](https://doi.org/10.5281/zenodo.20420664) ·
v0.9.0 DOI: [10.5281/zenodo.20420665](https://doi.org/10.5281/zenodo.20420665)

The author's annotations + synthetic-augmentation data used to train
EarlyModernNER's per-entity-type adapters. Third-party corpora (Old Bailey
Online, PCEEC2, Royal Society Corpus) are **cited but not redistributed**.

- License: CC-BY-4.0 for the author's annotations and synthetic data
- Size: 1.3 MB (622 files)

### 5. Normalized Customs Ledger Dataset
Concept DOI: [10.5281/zenodo.20420893](https://doi.org/10.5281/zenodo.20420893) ·
v0.9.0 DOI: [10.5281/zenodo.20420894](https://doi.org/10.5281/zenodo.20420894)

A cleaned/joined version of the 57-file `chapter3-graphrag/customs-ledgers/`
Excel data: **43,770 rows** of British Caribbean commodity imports
(1696–1755) in a single tidy CSV, with commodity-name normalization.
Transcribed by the author from **TNA CUST 3** (The National Archives, Kew).

- License: CC-BY-4.0
- Size: ~5 MB CSV (+ JSON form)

## Repository snapshot

The repository itself is also archived on Zenodo via the GitHub → Zenodo
integration. The v0.9.0 repo-level DOI is minted when the `v0.9.0` tag is
processed; it'll be added to this list once available. A v1.0.0 release will
follow post-defense.

## Citing this data

For the thesis bibliography, use each deposit's **concept DOI** (above) —
it auto-resolves to the latest version, so it continues to work after the
post-defense v1.0.0 update. To cite a specific snapshot (e.g. for
reproducibility), use the **v0.9.0 DOI** instead.

> Polay, Jacob. (2026). *early-modern-pipeline*. GitHub.
> https://github.com/polayj/early-modern-pipeline
