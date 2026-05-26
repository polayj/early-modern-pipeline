# Methodology — Cross-Chapter Design Decisions

The "why" behind the choices each chapter doesn't always explain in full. Read this if you want to understand the design rationale of the pipeline as a whole, or if you're adapting the work to another domain.

## Design principles

1. **Humanist judgment at every decision point.** Each chapter's evaluation isn't just "which system is best by F1?" — it's "which system makes the right kind of mistakes for a historian?" That's why metrics like *hallucination rate* (Ch. 1) and *Slot Error Rate with substitutions* (Ch. 2) appear alongside the conventional ones. A system that fabricates plausible text or substitutes "Jamaica" for "Barbados" is more dangerous to a historian than one that simply fails noisily.

2. **Reproducibility over novelty.** Every comparison uses publicly available models (with a few commercial exceptions noted) and publicly available data (Internet Archive sources). The custom contribution — EarlyModernNER — is itself released openly.

3. **Don't redistribute what you don't have the right to.** EEBO scans are held back. The OCR transcriptions derived from them are held back pending librarian review. We share what we are confident we have the right to share.

## Why this pipeline shape (OCR → NER → GraphRAG)

The naïve approach to "ask a question about 20,000 historical documents" is to throw them all into a RAG vector store and let an LLM retrieve relevant chunks. The thesis argues this fails for historical research because:

- **OCR errors compound.** Bad OCR → bad embeddings → bad retrieval → bad answers. Chapter 1 is the foundation, not optional.
- **Entities matter more than topics.** A historian asking about "the ginger trade" needs to find every mention of ginger across the corpus, not the documents that *talk about* ginger. NER (Ch. 2) makes the corpus addressable by entity, not just by topic.
- **Relationships matter more than co-occurrence.** "Which merchants traded ginger between Barbados and Bristol in the 1730s?" requires a graph, not a vector index. Chapter 3 builds the graph.

## Why EarlyModernNER instead of off-the-shelf NER

Chapter 2 tested 15 systems before training a new one. None met the bar because:

- General LLMs (Gemini, Mistral, gemma2) over-generated entities (high recall, low precision) — fine for some uses, fatal for historical research where false-positive entities ripple into the graph.
- Domain-pretrained transformers (MacBERTh, hmBERT) were strong on standardized early modern text but failed on the variable orthography of unedited pamphlet OCR.
- Zero-shot systems (GLiNER variants) were either too narrow (missing commodity entities entirely) or too broad.

The cascading per-entity-type design (commodity, organization, person, toponym adapters separately, then merged) was chosen specifically to let each adapter optimize for *precision over recall in the historian's terms*. Substitutions are penalized harder than misses because a missed entity can be found later by re-reading; a substituted entity invisibly pollutes the graph.

## Why GraphRAG (specifically the Improved Scratchpad variant)

Chapter 3 tested standard RAG, KG+RAG, GraphRAG, Self-RAG, and a custom "Improved Scratchpad" before settling. The shape of the win:

- Standard RAG retrieved a few of the most-similar chunks and answered from those — fine for "what is X?" questions, useless for "find every mention of X across the corpus".
- The Improved Scratchpad uses the knowledge graph to seed retrieval (find documents mentioning the relevant entities), expands to multi-chunk context per document (section-aware chunking), and uses a determinantal point process (DPP) to ensure diversity in what it shows the LLM. The result: ~10 unique documents per query vs. competitors' 4.2 average.

## What this pipeline is *not* good at

- **Handwriting.** Chapter 1's evaluation included some handwritten material; results were noticeably worse. The thesis explicitly excludes the author's own physical archive research at Kew because no OCR system was reliable enough.
- **Tables and structured data.** The table-OCR sub-study in `chapter1-ocr/tables-eval/` shows even the best systems struggle with tabular layouts. The structured customs ledger data in Ch. 3 is hand-extracted, not OCR'd.
- **Long-form summarization.** The GraphRAG system is optimized for *retrieval* and *grounded answers to focused questions*, not for "summarize this period in Caribbean history". For that, read a monograph.

## Reproducibility ceiling

The pipeline is fully reproducible at the *evaluation* level (run our gold standards, get our numbers) but the *training* level reproduction will drift. Specifically:

- Re-training EarlyModernNER with the same code, data, and seed will produce slightly different adapters because of non-determinism in PyTorch CUDA ops.
- The GraphRAG retrieval system uses an LLM in the loop (Qwen3.5-35B-A3B) for entity disambiguation and edge creation. LLM outputs are non-deterministic; the resulting graph will differ slightly each build.

In both cases the *evaluation metrics* should reproduce within reported confidence intervals, but the specific entity IDs, edges, and chunk selections will differ.

## How to adapt this pipeline to another period or language

- **Chapter 1 (OCR)**: re-do the gold standard for your target script/language. The evaluation harness is domain-agnostic. The winning OCR system may differ — vision-language transformers generalize better than traditional OCR to unfamiliar scripts.
- **Chapter 2 (NER)**: re-do the annotations. EarlyModernNER's cascading-adapter architecture transfers to any domain with stable entity types; the YAML configs are easy to modify for new categories.
- **Chapter 3 (GraphRAG)**: the pipeline code is domain-agnostic. The graph schema, prompt templates, and retrieval heuristics will need adaptation. The customs-ledger integration is specific to British Atlantic commerce.

## Acknowledgements specific to methodology

The cascading-adapter design for EarlyModernNER was inspired by discussions on the Qwen3 Discord about per-task LoRA composition. The Improved Scratchpad retrieval architecture extends ideas from the GraphRAG literature (Edge et al. 2024) with section-aware chunking and DPP diversity. See the thesis for the full bibliography.
