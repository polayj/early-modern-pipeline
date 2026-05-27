# Chapter 3 Figures

The figures reproduced in Chapter 3 of *Loud Yet Invisible*. Each is the
final rendered version used in the thesis. Figures 3.1–3.5 are architecture
diagrams of the retrieval systems; Figures 3.6–3.11 are generated from the
blind-grading and retrieval-diversity data in `../results/`.

| Figure | File | Description |
|---|---|---|
| 3.1 | `figure-3.1-plain-rag.png` | Plain RAG (vector retrieval only) |
| 3.2 | `figure-3.2-kg-rag.png` | Knowledge-graph-augmented RAG |
| 3.3 | `figure-3.3-true-graphrag.png` | True GraphRAG (graph traversal + vector) |
| 3.4 | `figure-3.4-document-tree.png` | Document-tree / hierarchical chunk structure |
| 3.5 | `figure-3.5-improved-system.png` | Improved Scratchpad retrieval (final architecture) |
| 3.6 | `figure-3.6-grading-overall.png` | Blind grading — overall mean score per system |
| 3.7 | `figure-3.7-grading-per-tier.png` | Blind grading — mean score per question tier (T1–T5) |
| 3.8 | `figure-3.8-grading-per-criterion.png` | Blind grading — mean score per criterion |
| 3.9 | `figure-3.9-pairwise-winrate.png` | Pairwise win-rate between systems |
| 3.10 | `figure-3.10-retrieval-diversity.png` | Retrieval diversity (unique documents/chunks per system) |
| 3.11 | `figure-3.11-cost-vs-quality.png` | Cost vs. answer quality |

Figures 3.6–3.11 can be regenerated from the data in `../results/` with the
plotting scripts in the upstream pipeline repository
(`pipeline/06_query/visualize_preliminary.py` and `visualize_extras.py`).

License: CC-BY-4.0 (see `../../LICENSE-DATA`).
