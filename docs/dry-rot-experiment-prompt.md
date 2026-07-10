# PROMPT — Dry-Rot Seeded-Corpus Experiment (journal article run)

> **How to use this file:** paste it (or point Claude Code at it) on the machine that
> runs the Improved Scratchpad pipeline (the emgraphrag machine with Neo4j, ChromaDB,
> and the local Qwen models). Everything below is addressed to *that* Claude instance.

---

You are Claude Code running on the machine that hosts the emgraphrag retrieval
pipeline built for Chapter 3 of the thesis *Loud Yet Invisible* (Jacob Polay,
University of Saskatchewan). Your job is to set up and execute a new evaluation
experiment whose results will anchor a journal article (target venues: *Digital
Humanities Quarterly* or *Historical Methods*).

## 1. The experiment in one paragraph

We are seeding a small number of new source documents — taken from
https://github.com/jburnford/dry-rot-history, the supervisor's research repository —
into the existing ~19,000-document early modern corpus, and testing whether the
retrieval architectures built for the thesis can find and correctly use them to
answer expert-authored questions. The supervisor holds the answer key. Google's
Gemini previously answered some of these questions incorrectly; those questions are
kept as case studies, but the quantitative core of the experiment is
**architecture-vs-architecture on an identical corpus**, exactly as in the thesis:
every system sees the same seeded corpus, the same model, and the same indexes, so
any difference is attributable to architecture. The seeded documents are a
needle-in-a-haystack target (a handful of documents among ~19,000), which gives us
hard, pre-registered retrieval metrics on top of rubric grading.

## 2. What should already exist on this machine — verify, do not assume

Before doing anything else, locate and verify each of these. If any is missing or
doesn't match, STOP and report to the user rather than improvising.

1. **The emgraphrag repository** (the live version of the snapshot in
   `early-modern-pipeline/chapter3-graphrag/`). Key paths, relative to that repo:
   - `pipeline/03_ner/` — `run_ner.py`, `link_entities.py`, `normalizations.py`, `lod_lookups.py`
   - `pipeline/04_graph/` — `extract_relations.py`, `build_graph.py`
   - `pipeline/05_embed/generate_embeddings.py`
   - `pipeline/06_query/` — query interfaces, including `eval_improved.py` with
     `EVAL_QUESTIONS` / `GINGER_QUESTIONS` and the entry points for all eight systems.
2. **Neo4j**, loaded with the thesis graph: ~218,523 nodes / ~691,577 edges,
   ~19,249 `Document` nodes, chunk-level `MENTIONS` edges, section/chunk hierarchy
   (`FOLLOWED_BY`, section nodes), commodity hierarchy edges
   (`IS_VARIANT_OF`, `DERIVED_FROM`), and the imported customs-ledger rows.
3. **ChromaDB**, with the section-aware chunk index (~1.78M chunks,
   Qwen3-Embedding-0.6B) and the entity-evidence index (~250K snippets,
   Qwen3-Embedding-8B).
4. **The local LLM stack**: Qwen3.5-27B (the thesis benchmark model) and
   Qwen3.6-35B-A3B-FP8 (the extended-context case-study model), however they are
   served here (Ollama or otherwise).
5. **The eight retrieval systems** runnable end-to-end, under the names used in the
   thesis grading key: `rag_only`, `kg_plus_rag`, `true_graphrag`,
   `graphrag_plus_kg`, `graphrag_kg_vector`, `self_rag_rag`, `self_rag_graphrag`,
   `improved_scratchpad`.

Run whatever smoke test exists (see `smoke-test/` in the snapshot repo for the
10-document subset) or a single cheap query through `rag_only` and
`improved_scratchpad` to confirm the stack is alive before committing to long runs.

## 3. Inputs the user must provide — collect these before Phase 1

Ask the user for anything on this list that you cannot find. Do not proceed to
Phase 2 without items 1–3.

1. **The dry-rot source documents.** A local clone of
   `jburnford/dry-rot-history` or an exported folder of the specific files to seed.
   The user and supervisor choose *which* files ("a few" — expect roughly 3–10
   documents). For each seeded document record: filename, title, author, date,
   original archive/URL, format (PDF scan vs. existing transcription), and license.
2. **Question Set A (neutral benchmark).** Questions authored by the supervisor
   *before any system is run*, NOT selected on the basis of any model's prior
   success or failure. These carry the quantitative claims. Aim for 10–15 questions,
   tier-labelled with the thesis's five tiers (Factual / Temporal / Relational /
   Analytical / Interpretive) where applicable.
3. **Question Set B (Gemini-failure case studies).** The questions Gemini answered
   incorrectly, verbatim as they were put to Gemini. These are analyzed as case
   studies only — never pooled with Set A in any aggregate statistic, because they
   were adversarially selected against a baseline.
4. **The expert answer key** — ideally NOT given to you at all until grading time.
   If the user hands it to you early, store it in `answer-key/` and never open it
   during Phases 1–4 (see Hard Rules).
5. **Gemini provenance for Set B**: exact model/version, date asked, full prompt
   and response transcripts (screenshots or exports). If the user doesn't have
   transcripts, note that the article will need the questions re-asked to Gemini
   with everything archived — produce `gemini-protocol.md` (Phase 5) to script that.

Store all of this under a new directory in the emgraphrag repo, e.g.
`experiments/dryrot-2026/` — everything the experiment produces lives there:

```
experiments/dryrot-2026/
├── inputs/
│   ├── seed-documents/          # the raw dry-rot files
│   ├── seed-manifest.json       # one entry per seeded doc (see §7)
│   ├── questions-setA.json      # same schema as queries/eval-questions.json
│   ├── questions-setB.json
│   └── gemini-transcripts/
├── answer-key/                  # SEALED — do not read until Phase 6
├── runs/
│   ├── pre-seed/                # Phase 1 outputs
│   └── post-seed/               # Phase 4 outputs
├── metrics/                     # Phase 5 outputs
├── grading/                     # blind packet + sealed mapping key
├── run-manifest.json            # versions, configs, hashes, timings
└── gemini-protocol.md
```

## 4. Hard rules (read twice)

1. **Never let the answer key near a model.** No answer-key text may appear in any
   prompt to any retrieval system, at any phase. The key exists only for human
   grading. If you need to sanity-check an answer mid-run, don't — that's Phase 6.
2. **Snapshot before you mutate.** Before ingesting anything, take a restorable
   backup of Neo4j (`neo4j-admin database dump` or the docker-volume equivalent)
   and of the ChromaDB collections. Record backup paths + checksums in
   `run-manifest.json`. The thesis graph is a citable artifact (Zenodo
   10.5281/zenodo.20420920) — it must be recoverable exactly.
3. **Tag everything you add.** Every node, edge, and chunk created from a seeded
   document gets a property `seed_batch: "dryrot-2026"` (and chunks get equivalent
   metadata in ChromaDB). This makes the seeding reversible and makes seeded-source
   recall (§8) mechanically checkable.
4. **Same configs pre and post.** Phases 1 and 4 must use byte-identical system
   configurations: same models, same quantizations, same temperatures/seeds, same
   top-k, DPP settings, context windows, prompts. Diff the configs and store both.
5. **Benchmark config = thesis config.** For the cross-system comparison, run all
   eight systems in the configurations used for the thesis 30-question benchmark
   (Qwen3.5-27B, the standard context window). The extended configuration
   (Qwen3.6-35B-A3B-FP8, 262K context, 35 DPP chunks, turn-the-page=4) may be run
   *additionally* for Improved Scratchpad only, reported as a separately labelled
   variant (`improved_scratchpad_extended`) — never silently substituted.
6. **Archive raw outputs immediately.** Every system answer, every retrieved chunk
   list, every Cypher query the agent writes, every verifier flag — written to
   `runs/` as JSON before any post-processing. No cherry-picking: every run that
   starts gets archived, including failures and crashes (log them as such).
7. **No live-web or parametric leakage checks skipped.** Part of the experiment's
   value is the pre-seed control; do not "fix" a pre-seed failure by tweaking
   anything before the post-seed run.
8. **Determinism where possible.** Fix random seeds where the pipeline exposes
   them; record them where it doesn't. Record wall-clock time and LLM-call count
   per query per system (the article reuses the thesis's cost-vs-quality analysis).

## 5. Phase 0 — Environment verification and cost estimate

1. Verify everything in §2; write versions (model files/hashes, Neo4j & Chroma
   versions, GPU, driver) into `run-manifest.json`.
2. Estimate total runtime before launching: with N = |Set A| + |Set B| questions,
   the full design is 8 systems × N questions × 2 (pre/post), plus the extended
   Scratchpad variant × N × 2. Improved Scratchpad averaged ~593 s/query in the
   thesis; the other seven averaged far less. Compute the estimate, report it to
   the user, and get an explicit go-ahead if the total exceeds ~24 h of wall-clock.
   If it does, the agreed fallback is: all 8 systems on Set A; only
   `improved_scratchpad`, `self_rag_rag` (best thesis runner-up), and `rag_only`
   (floor baseline) on Set B and on the extended variant.

## 6. Phase 1 — Pre-seed control runs

Run every question in Set A and Set B through every in-scope system against the
**unmodified** corpus. Archive to `runs/pre-seed/<system>/<question-id>.json` with:
the answer text, retrieved chunk IDs + document IDs, any Cypher issued, verifier
output, latency, LLM-call count.

Purpose: (a) establish that the answers are not already derivable from the base
corpus or the model's parametric knowledge; (b) capture abstention behaviour —
whether each system says "the sources don't establish this" versus confabulating.
Abstention-vs-confabulation pre-seeding is itself a headline result: tag each
pre-seed answer later (Phase 6, by the human graders) as
*abstained / hedged / confabulated / actually-answered*.

## 7. Phase 2 — Ingest the seeded documents through the full pipeline

Process the dry-rot documents through the same stages as the original corpus — no
shortcuts, because the pipeline itself is part of the article's story:

1. **OCR** (only if a document is a page-scan PDF): olmOCR-2, same settings as the
   corpus. If a document is already a clean transcription, skip OCR but record that
   in the manifest (`"ocr": "not-needed"`), since it means that document bypassed
   one pipeline stage.
2. **NER**: `pipeline/03_ner/run_ner.py` with EarlyModernNER, then
   `link_entities.py` / `normalizations.py`. **Flag, don't fix:** if the dry-rot
   material is later than the training distribution (e.g., 19th-century naval
   timber literature) and NER quality looks degraded, record examples in the
   manifest — that's a finding about out-of-domain generalization, not a bug to
   patch mid-experiment.
3. **Graph**: `pipeline/04_graph/extract_relations.py` → `build_graph.py`, into the
   live Neo4j, with `seed_batch: "dryrot-2026"` on every created node and edge.
   Wire the new documents into the same Document→Section→Chunk hierarchy with
   `FOLLOWED_BY` edges, chunk-level `MENTIONS`, and entity-evidence snippets, so
   they are first-class citizens of graph-directed retrieval.
4. **Embeddings**: section-aware chunking + `pipeline/05_embed/generate_embeddings.py`
   into the existing ChromaDB collections (both the chunk index and the
   entity-evidence index), with `seed_batch` metadata on every vector.
5. **Entity disambiguation**: run the same LLM disambiguation step used for corpus
   construction so dry-rot entities merge with existing nodes where appropriate
   (e.g., shared places, institutions, people). Record all merges in the manifest.
6. **Deduplication check**: confirm none of the seeded documents near-duplicates an
   existing corpus document (the corpus dedup step would otherwise silently drop
   or shadow a needle).

Write `inputs/seed-manifest.json`, one entry per document:

```json
{
  "seed_id": "dryrot-001",
  "source_file": "…",
  "title": "…", "author": "…", "date": "…",
  "origin_url": "…", "license": "…",
  "ocr": "olmocr-2 | not-needed",
  "document_node_id": "…",
  "n_sections": 0, "n_chunks": 0,
  "n_entities": 0, "entity_merges": ["…"],
  "chunk_ids": ["…"],
  "notes": "NER quality observations, anomalies"
}
```

Sanity check before Phase 4: for each seeded document, confirm (a) its chunks are
retrievable from ChromaDB by an obvious verbatim query, and (b) its `MENTIONS`
edges resolve in Neo4j. If a needle isn't findable by construction, the experiment
can't measure anything.

**If any Set A/B question is quantitative** and the supervisor's repo contains
tabular data (the analogue of the customs ledgers), ingest it via the same route as
`import_records_to_docs.py` and tag it. If a quantitative question has *no*
corresponding structured data anywhere, tell the user before running it — the
thesis showed the Cypher-agent path is what answers those, and without a table the
question tests abstention, not recovery. That's fine, but it should be a design
decision, not a surprise.

## 8. Phase 4 — Post-seed runs

(Phase 3 is the ingest verification above.) Re-run exactly what Phase 1 ran — same
questions, same systems, same configs — against the seeded corpus. Archive to
`runs/post-seed/` in the identical format. Then compute, mechanically, per system ×
question, into `metrics/`:

- **Seeded-source recall**: did the retrieved set include ≥1 chunk with
  `seed_batch = "dryrot-2026"`? (Binary, plus the count.)
- **Seeded-source citation**: does the final answer cite/name a seeded document?
- **Quote fidelity**: for each direct quote attributed to a seeded document, does
  the quoted string actually appear in that document's chunks? (String match with
  light normalization; report per-system rates.)
- **Pre/post delta**: paired comparison of the same question pre- and post-seeding.
- **Cost**: latency and LLM calls per query (reuse the thesis's cost-vs-quality
  framing).

These metrics require no human judgment and should be fully reproducible from the
archived `runs/` JSON by a single script — write that script (`metrics/compute.py`)
rather than computing numbers ad hoc, and commit it.

## 9. Phase 5 — Blind grading packet + Gemini protocol

1. Build the grading packet for the human graders (the supervisor, and a second
   grader if available):
   - For **each question independently**, assign fresh random letters to the
     systems' post-seed answers (use a seeded RNG, seed recorded in the manifest).
     This fixes the thesis's known blinding bug — the mapping must NOT be constant
     across questions.
   - Strip anything that identifies a system (headers, telltale formatting like
     scratchpad-note structure should be normalized to plain prose paragraphs as
     far as possible without altering content; if full anonymization is impossible,
     note it honestly in the manifest).
   - Include pre-seed answers as additional letter-labelled entries mixed in, so
     graders also produce the abstained/confabulated tagging of §6 blind.
   - Rubric: the thesis's five criteria (Groundedness, Completeness, Accuracy,
     Synthesis, Usefulness), 1–5 each, defined verbatim from the thesis, PLUS the
     answer key in hand for Accuracy. Export as .docx or .md per question +
     an .xlsx/.csv grading sheet.
   - Write the letter→system mapping to `grading/mapping-key.json` and do not
     surface it in any user-facing summary until grading is returned.
2. Write `gemini-protocol.md`: the exact procedure for the fair frontier baseline —
   which Gemini model/version, the verbatim questions (Set A and Set B), two
   conditions (closed-book, and with the seeded source documents attached/uploaded),
   instruction to archive full transcripts + date + version string into
   `inputs/gemini-transcripts/`. Note in the protocol that closed-book Gemini vs.
   corpus-equipped local systems is a *framing* comparison, not a controlled one,
   and must be reported as such.

## 10. Phase 6 — After grades come back (later session)

Ingest the returned grading sheet, join with `grading/mapping-key.json`, and
produce: per-system means (Set A only), per-tier and per-criterion breakdowns,
pairwise win rates, seeded-recall × grade cross-tabs, pre/post deltas, and the
cost-vs-quality plot — mirroring the thesis's `results/` tables so the article can
present continuous methodology. Set B is written up as narrative case studies with
the Gemini transcripts alongside.

## 11. Deliverables checklist (what "done" looks like for this machine)

- [ ] `run-manifest.json` — every version, hash, config, seed, backup path, timing
- [ ] Neo4j + Chroma backups taken and checksummed (pre-seeding state)
- [ ] `inputs/` complete: seed docs, seed manifest, both question files, Gemini transcripts (if available)
- [ ] `runs/pre-seed/` — full archive, all systems × all questions
- [ ] Seeded ingest complete, tagged, and verified retrievable
- [ ] `runs/post-seed/` — full archive, identical configs
- [ ] `metrics/compute.py` + its CSV outputs
- [ ] `grading/` — blind packet (per-question shuffling) + sealed mapping key
- [ ] `gemini-protocol.md`
- [ ] Everything committed to the emgraphrag repo (or this experiments dir) with clear messages

Work through the phases in order. Report progress at each phase boundary with what
was produced and where it lives. If anything in the pipeline behaves differently
from how this document describes it (script names moved, configs renamed), trust
the machine over the document, fix the reference, and note the discrepancy in
`run-manifest.json`.
