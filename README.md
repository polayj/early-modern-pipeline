# early-modern-pipeline

Code, datasets, and evaluation results accompanying the Master's thesis
**["Loud Yet Invisible: A Humanist-Designed Pipeline for Unlocking the Early Modern Archive"](#citation)** by Jacob Polay (University of Saskatchewan, 2026).

This repository replaces what would have been a printed appendix. It contains the OCR gold standard, the EarlyModernNER model and its training data, the GraphRAG retrieval pipeline, and reproducible evaluation harnesses for all three chapters.

> **Status**: Pre-defense release (v0.1.0). The full Chapter 3 artifacts (Neo4j graph, ChromaDB index, 20K-corpus OCR outputs, model weights) are being assembled on a separate machine in Phase B and will be deposited on Zenodo after the thesis defense. DOI links below currently read `[DOI pending]` and will be filled in then.

---

## Repository map

```
early-modern-pipeline/
├── README.md                 (you are here)
├── LICENSE                   MIT (code)
├── LICENSE-DATA              CC-BY-4.0 (data and annotations)
├── CITATION.cff              Academic citation metadata
├── docs/
│   ├── reproduction-guide.md     End-to-end pipeline walkthrough
│   ├── methodology.md            Cross-chapter design decisions
│   ├── data-provenance.md        Every corpus, its source, its license
│   └── PHASE-B-HANDOFF.md        Instructions for the school-computer build
├── chapter1-ocr/             100-page gold standard + 13 systems benchmarked
├── chapter2-ner/             EarlyModernNER + 100-doc annotated gold standard
├── chapter3-graphrag/        Snapshot of github.com/polayj/emgraphrag
├── data/                     Pointer to Zenodo deposits (large artifacts)
└── scripts/
    └── prepare-release.sh    Pre-push validation (secrets, file sizes, licenses)
```

## The pipeline at a glance

```
                                 ┌────────────────────────┐
[Internet Archive + EEBO PDFs] ─►│ Ch.1: OCR              │─►[transcribed text]
                                 │ olmOCR-2 winner        │
                                 └────────────────────────┘
                                              │
                                              ▼
                                 ┌────────────────────────┐
                                 │ Ch.2: NER              │─►[entity-tagged text]
                                 │ EarlyModernNER F1=.823 │
                                 └────────────────────────┘
                                              │
                                              ▼
                                 ┌────────────────────────┐
                                 │ Ch.3: GraphRAG         │─►[grounded answers
                                 │ Neo4j + Chroma         │   to historical Qs]
                                 │ Improved Scratchpad    │
                                 └────────────────────────┘
```

Each chapter is independently runnable from its own README.

## Zenodo deposits

Large artifacts that don't belong in a Git repository are deposited on Zenodo with permanent DOIs. Each has its own README and license.

| Deposit | Contents | DOI |
|---|---|---|
| EarlyModernNER weights | DoRA + full-fine-tune adapters | `[DOI pending]` |
| OCR outputs (20K corpus) | Plain-text transcriptions, Internet Archive sources | `[DOI pending]` |
| Knowledge graph dump | Neo4j export + ChromaDB index | `[DOI pending]` |
| NER training corpus | Annotated training data (your work) | `[DOI pending]` |
| Customs ledger dataset | 43K-row trade data, normalized | `[DOI pending]` |

The repository itself will be released on Zenodo as a versioned snapshot (GitHub → Zenodo integration), yielding a repo-level DOI for v1.0.0 post-defense.

## Provenance and licensing — at a glance

| Artifact type | License | Notes |
|---|---|---|
| Original code (this repo) | MIT | See `LICENSE` |
| Original transcriptions, annotations, results | CC-BY-4.0 | See `LICENSE-DATA` |
| Internet Archive page scans | Not redistributed | Cited; users can fetch from archive.org |
| EEBO page scans | Not redistributed (proprietary) | Cited by STC/Wing number |
| EEBO-derived OCR outputs | **Withheld pending librarian review** | See `chapter3-graphrag/README.md` |
| External corpora (PCEEC2, Old Bailey, Royal Society Corpus, MacBERTh, etc.) | Their original licenses | Cited in `docs/data-provenance.md` |

## Reproducing a single chapter

Each chapter is self-contained — see the chapter READMEs:

- `chapter1-ocr/README.md` — re-run OCR evaluation against the gold standard
- `chapter2-ner/README.md` — re-run NER comparison; train EarlyModernNER
- `chapter3-graphrag/README.md` — end-to-end GraphRAG (requires Phase B Zenodo deposits)

## Citation

If you use this code, datasets, or evaluation methodology, please cite:

> Polay, Jacob. (2026). *Loud Yet Invisible: A Humanist-Designed Pipeline for Unlocking the Early Modern Archive*. Master's thesis, University of Saskatchewan.

GitHub provides a "Cite this repository" button (top right) that exports the entry from `CITATION.cff` to BibTeX, CSL-JSON, RIS, and other formats.

## Acknowledgements

Built as the thesis appendix at the suggestion of my supervisor. Thanks to the EarlyModernNER and emgraphrag development discussions; to the Internet Archive and EEBO/ProQuest for hosting the source documents; to the maintainers of olmOCR, Tesseract, Kraken, MinerU, Chandra, DeepSeek-OCR, Gemini, Transkribus, EasyOCR, and LightOn for their OCR systems; and to the Qwen3 team for the base model used in EarlyModernNER.

## Contact

Issues, corrections, or questions: open a GitHub issue or email <polayjacob@gmail.com>.
