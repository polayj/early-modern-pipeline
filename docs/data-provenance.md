# Data Provenance

Per-source attribution, licensing, and redistribution status for every dataset, model, and corpus referenced in this repository.

## Source corpora

| Source | Used in | Items | License / Status | Redistributed here? |
|---|---|---|---|---|
| Internet Archive | Ch. 1 (gold standard), Ch. 3 (main corpus) | 18,579 PDFs | Items are public-domain digitizations of 1614–1810 printed works. archive.org Terms of Use permit research and noncommercial use of metadata and content. | Citations + URLs only. OCR transcriptions deposited on Zenodo. Original PDFs not redistributed (archive.org hosts them). |
| Early English Books Online (EEBO/ProQuest) | Ch. 1 (subset), Ch. 3 (~100 PDFs) | ~100 PDFs | Proprietary, ProQuest licensed | **Not redistributed.** Citations by STC/Wing number only. OCR outputs of EEBO scans withheld pending librarian review. |
| EEBO-TCP (Text Creation Partnership) | Comparator only | n/a in this release | Phase I public domain (released 2015), Phase II public domain (released 2020) | Not currently included. If used in v2, would be redistributable. |
| British Customs Import Ledgers (1696–1755) | Ch. 3 (`chapter3-graphrag/customs-ledgers/`) | 57 .xlsx files, ~43,000 rows | TBC — to be confirmed with the user whether these are the author's transcription or sourced from an existing dataset | Excel files included; normalized form to be deposited on Zenodo |

## External datasets cited but not redistributed

These are referenced as comparators or as upstream training material. Their original licenses apply; consult each source for terms.

| Dataset | Used for | Source / License |
|---|---|---|
| PCEEC2 (Penn Corpus of Early English Correspondence v2) | NER training (Ch. 2) | <https://github.com/beatrice57/pceec2> — see repo for license |
| Old Bailey Online | NER training (Ch. 2) | <https://www.oldbaileyonline.org> — CC-BY-NC-SA |
| Royal Society Corpus | NER training (Ch. 2) | <https://fedora.clarin-d.uni-saarland.de/rsc/> — CC-BY |

## External models

| Model | Used in | License | Source |
|---|---|---|---|
| Qwen3-4B-Instruct-2507 | EarlyModernNER base (Ch. 2) | Apache-2.0 | <https://huggingface.co/Qwen/Qwen3-4B> |
| Qwen3.5-35B-A3B | Graph disambiguation (Ch. 3) | Apache-2.0 | <https://huggingface.co/Qwen/Qwen3.5-35B-A3B> |
| Qwen3-Embedding-0.6B | Vector embeddings (Ch. 3) | Apache-2.0 | <https://huggingface.co/Qwen> |
| gemma-2-9b | NER comparator (Ch. 2) | Gemma license | <https://huggingface.co/google/gemma-2-9b> |
| Mistral-7B-Instruct-v0.3 | NER comparator (Ch. 2) | Apache-2.0 | <https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3> |
| MacBERTh | NER comparator (Ch. 2) | See model card | HuggingFace |
| hmBERT | NER comparator (Ch. 2) | See model card | HuggingFace |

## OCR systems benchmarked (Ch. 1)

Each system was used per its own license terms. We do not redistribute their code or weights; we redistribute only their outputs on our gold-standard corpus.

| System | License | Source |
|---|---|---|
| Tesseract (v5, Legacy) | Apache-2.0 | <https://github.com/tesseract-ocr/tessdoc> |
| Kraken | Apache-2.0 | <https://github.com/mittagessen/kraken> |
| EasyOCR | Apache-2.0 | <https://github.com/JaidedAI/EasyOCR> |
| Transkribus | Commercial (READ-COOP) | <https://transkribus.eu> — used via paid institutional access |
| olmOCR-1 / olmOCR-2 | Apache-2.0 | <https://github.com/allenai/olmocr> |
| DeepSeek-OCR | MIT | <https://github.com/deepseek-ai> |
| Chandra (v1, v2) | Apache-2.0 | <https://github.com/datalab-to/chandra> |
| MinerU 2.6.2 | AGPL-3.0 | <https://github.com/opendatalab/MinerU> |
| LightOn | Commercial | Used via API |
| Gemini 2.5 Pro | Commercial (Google) | Used via API |

## Original work in this repository (CC-BY-4.0)

- `chapter1-ocr/gold-standard/transcriptions/` — 100 hand-transcribed pages
- `chapter1-ocr/gold-standard/page-xml/` — geometric ground truth
- `chapter2-ner/gold-standard/annotations/` and `reviewed/` — 100 hand-annotated documents
- `chapter2-ner/earlymodernner/` — original Python package
- `chapter3-graphrag/pipeline/` — pipeline code authored by Jacob Polay (snapshot from emgraphrag repo)
- All `results/` directories — original evaluation outputs
- All `figures/` directories — original figures

## Questions or corrections

If you believe any item here is mislabeled or improperly attributed, please open a GitHub issue. The author will respond.
