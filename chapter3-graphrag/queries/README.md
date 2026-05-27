# queries/

The exact evaluation queries used in the Chapter 3 GraphRAG evaluation.

| File | Contents |
|---|---|
| `eval-questions.json` | The 30-question benchmark across five tiers (T1 Factual → T5 Interpretive) |
| `ginger-questions.json` | The 5-question "ginger" commodity case study |

These are extracted verbatim from `pipeline/06_query/eval_improved.py`
(`EVAL_QUESTIONS` and `GINGER_QUESTIONS`). Each of the eight systems was run
over the 30-question set; answers were then blind-graded — see `../results/`
for the scores and `../results/README.md` for the grading design.

To re-run the benchmark against a loaded graph + vector index:

```bash
python ../pipeline/06_query/eval_improved.py                 # 30-question set
python ../pipeline/06_query/eval_improved.py --questions ginger
```

License: CC-BY-4.0 (see `../../LICENSE-DATA`).
