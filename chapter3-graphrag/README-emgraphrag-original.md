# emgraphrag

GraphRAG pipeline over the Early Modern Caribbean corpus.

Combines ~18,900+ historical PDFs (archive.org + EEBO), structured commodity
import records (1696–1755), named-entity recognition (EarlyModernNER), and
LightRAG (local Ollama) into a hybrid graph/vector retrieval system.

---

## Corpus

| Source | Contents |
|--------|----------|
| `ocr_docs/unprocessed/archive_org/` | 18,579 PDFs, each in its own subdirectory |
| `ocr_docs/unprocessed/EEBO/` | ~100 Early English Books Online PDFs |
| `import_records/` | 57 xlsx files — British Caribbean commodity imports, 1696–1755 |

---

## Pipeline Overview

```
Step 01 — Parse import records  (WSL2 machine — already done)
Step 02 — OCR PDFs              (school computer, GPU required)
Step 03 — NER over OCR text     (school computer)
Step 04 — Build knowledge graph (school computer)
Step 05 — LightRAG ingest/query (school computer)
```

---

## WSL2 Machine — Already Complete

Step 01 has been run. Outputs are in `output/import_records_parsed/`:
- `all_records.csv` — 43,770 rows
- `all_records.json`
- `import_docs/*.md` — 441 per-location/year markdown documents

Transfer these to the school computer along with the repo (see Transfer section below).

---

## School Computer Setup

**Hardware: Lenovo ThinkStation PGX (30KL0002US)**
- NVIDIA Grace Blackwell GB10 Superchip
- **ARM64 CPU** (20-core Grace, Cortex-X925 + Cortex-A725)
- **Blackwell GPU** with **128GB unified memory** (CPU and GPU share the same pool)
- NVIDIA DGX OS (Ubuntu 22.04-based), CUDA + drivers pre-installed

**Important:** This machine is ARM64/aarch64 — x86 Apptainer containers will not run.
Use native pip installs for all tools.

### Prerequisites

NVIDIA drivers and CUDA are pre-installed on DGX OS. Verify:
```bash
python3 --version    # need 3.10+
nvidia-smi           # should show Blackwell GPU
docker --version
git --version
```

### Get the repo

Option A — USB/network copy:
```bash
rsync -av /path/to/emgraphrag/ ~/emgraphrag/
```

Option B — git clone (if pushed to a remote):
```bash
git clone <your-remote-url> ~/emgraphrag
# Then copy output/import_records_parsed/ separately (it's gitignored)
```

### Python environment

Create a venv and install everything into it. **Always activate the venv before
running any pipeline script.**

```bash
cd ~/emgraphrag
python3 -m venv .venv
source .venv/bin/activate

# Verify you're in the venv (should show ~/emgraphrag/.venv/bin/python)
which python3
```

#### Install base dependencies

```bash
pip install -r requirements.txt
```

#### Install olmOCR (for Step 2 — OCR)

```bash
pip install olmocr
```

If that fails (ARM64 wheel not available), build from source:
```bash
# Install PyTorch with CUDA 12 for Blackwell first
pip install torch torchvision --index-url https://download.pytorch.org/whl/nightly/cu128
git clone https://github.com/allenai/olmocr
pip install -e olmocr/
```

Verify the install:
```bash
python3 -c "import olmocr; print('olmOCR OK')"
nvidia-smi   # confirm GPU is visible
```

#### Install EarlyModernNER (for Step 3 — NER)

```bash
pip install earlymodernner
python3 -c "import earlymodernner; print('EarlyModernNER OK')"
```

#### Activate reminder

Every time you open a new terminal, re-activate before running scripts:
```bash
cd ~/emgraphrag && source .venv/bin/activate
```

---

### Step 2 — OCR

**ARM64 note:** Do not use Apptainer containers — x86 containers will not run on this
machine. `run_ocr.sh` uses native olmOCR directly.

```bash
# Make sure venv is active first
source .venv/bin/activate

bash pipeline/02_ocr/run_ocr.sh
```

#### Environment variables

```bash
# All optional
BATCH_SIZE=100           # PDFs per model invocation (default: 50)
OUTPUT_TAG=run1          # workspace subdirectory label
MODEL=allenai/olmOCR-7B-0825   # override model (if using base container)
```

**Output:** `output/ocr_md/*.md` — ~18,680 files prefixed `archive_org__<id>.md` or `EEBO__<name>.md`

Resume-safe: already-processed files are skipped on re-run.

---

### Step 3 — NER

```bash
source .venv/bin/activate
python pipeline/03_ner/run_ner.py

# Test on a small batch first:
python pipeline/03_ner/run_ner.py --limit 100
```

**Output:**
- `output/ner_output/entities.jsonl` — all entities
- `output/ner_output/per_doc/*.jsonl` — per-document files (resume support)

Entity types: `TOPONYM`, `PERSON`, `ORGANIZATION`, `COMMODITY`

---

### Step 4 — Temporal Knowledge Graph (ATOM → Neo4j)

ATOM extracts 5-tuples `(subject, relation, object, t_start, t_end)` with temporal
bounds from each document, then pushes them to Neo4j on your Unraid server.

#### Prerequisites: start services on Unraid

```bash
# On your Unraid server — start Neo4j and ChromaDB
docker compose -f docker/unraid/neo4j.compose.yml up -d
docker compose -f docker/unraid/chromadb.compose.yml up -d
```

Neo4j browser: `http://<unraid-ip>:7474` (login: neo4j / password)

#### Install Ollama and pull models

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable ollama && sudo systemctl start ollama

# Qwen3 MoE — fast sparse inference (~3B active params), high knowledge capacity
ollama pull qwen3:80b-a3b-q8_0   # ~80GB, fits in 128GB unified memory
# Fallback: ollama pull qwen3:30b-a3b
```

#### Generate import record docs (step 4a)

```bash
source .venv/bin/activate
python pipeline/04_graph/import_records_to_docs.py
# → output/lightrag_input/import_docs/*.md  (441 docs)
```

#### Run ATOM extraction (step 4b)

```bash
# Test on 50 docs first
python pipeline/04_graph/run_atom.py --limit 50 \
    --neo4j-uri bolt://<unraid-ip>:7687

# Full run — import records first (~1–2h), then OCR docs (days, resume-safe)
python pipeline/04_graph/run_atom.py \
    --neo4j-uri bolt://<unraid-ip>:7687 \
    --neo4j-password yourpassword

# Connection settings are saved to atom_config.yaml after first run
python pipeline/04_graph/run_atom.py   # subsequent runs use saved config
```

**ATOM** automatically:
- Decomposes each document into atomic facts
- Extracts 5-tuples `(subject, relation, object, t_start, t_end)` with temporal bounds
- Merges entities across documents using semantic similarity (Qwen3-Embedding-8B)
- Writes the temporal knowledge graph to Neo4j

**Throughput:** ~3–5 LLM calls per document with Qwen3:80b-a3b (~10–15s each).
Run import records (441 docs) first to validate, then OCR docs overnight.

---

### Step 5 — Vector Embeddings (Qwen3-Embedding-8B → ChromaDB)

```bash
source .venv/bin/activate

# Test on 50 docs
python pipeline/05_embed/generate_embeddings.py --limit 50 \
    --chroma-host <unraid-ip>

# Full run (resume-safe)
python pipeline/05_embed/generate_embeddings.py \
    --chroma-host <unraid-ip>

# Fallback: local ChromaDB if server not available
python pipeline/05_embed/generate_embeddings.py --chroma-local
```

**Embedding model:** `Qwen/Qwen3-Embedding-8B` — #1 MTEB multilingual, 32k context,
runs on the GB10's GPU via sentence_transformers (~16GB VRAM, fits in 128GB pool).

---

### Step 6 — Query

```bash
source .venv/bin/activate

# Single query (hybrid: graph + vector)
python pipeline/06_query/query.py "What commodities did Jamaica export most in the 1720s?"

# Graph mode (temporal/structural questions — uses Neo4j Cypher)
python pipeline/06_query/query.py --mode graph \
    "Which colonies exported sugar between 1710 and 1730?"

# Vector mode (semantic similarity)
python pipeline/06_query/query.py --mode vector \
    "Tell me about merchant networks in the Caribbean"

# Interactive mode
python pipeline/06_query/query.py

# Example queries
python pipeline/06_query/query.py --examples

# Override connections
python pipeline/06_query/query.py \
    --neo4j-uri bolt://<unraid-ip>:7687 \
    --chroma-host <unraid-ip> \
    "Your question here"
```

**Query modes:**

| Mode | What it uses | Best for |
|------|-------------|----------|
| `hybrid` (default) | Neo4j graph + ChromaDB vectors | General questions |
| `graph` | Neo4j Cypher queries only | Temporal/structural questions |
| `vector` | ChromaDB semantic search only | Narrative/thematic questions |

---

## Running on Nibi (Alliance HPC)

Use Nibi when the school computer is unavailable. Nibi has H100 GPUs (x86_64)
and 48-hour SLURM job limits. Steps 4–5 (relation extraction + LightRAG) still
run on the school computer once available.

**Nibi facts:** SSH alias `nibi`, user `jacobpol`, account `def-jic823`.
No concurrent processes — each SLURM job runs one task at a time.

### Throughput estimate

H100 processes ~20–30 sec/PDF → ~125–150 hours for 18k PDFs.
One 48h job handles ~6,000–8,000 PDFs → 3 job rounds needed.

### Workflow

```
WSL2                          Nibi login node              Nibi compute nodes
─────                         ────────────────             ──────────────────
copy_to_nibi.sh ──rsync──→   pipeline/ + import records
                               ↓
                              (copy PDFs manually — see below)
                               ↓
                              setup_nibi_env.sh   (one-time: venv + model download)
                               ↓
                              submit_pipeline.sh  (submits OCR→NER→OCR→NER→OCR→NER)
                                                             ↓
                                                    [48h OCR job × 3 rounds]
                                                    [24h NER job × 3 rounds]
                               ↓
                              rsync results back to WSL2
                               ↓ (transfer output/ to school computer)
                              Steps 4–5 on school computer
```

### Step-by-step

**1. Copy scripts and small data to Nibi (from WSL2):**
```bash
bash pipeline/nibi/copy_to_nibi.sh
```
This rsyncs `pipeline/`, `requirements.txt`, `CLAUDE.md`, and
`output/import_records_parsed/` (~50 MB) to Nibi automatically.

**2. Copy the PDF corpus (large — run in screen/tmux):**
```bash
screen -S rsync_pdfs
rsync -av --progress --partial \
    /mnt/z/emgraphrag/ocr_docs/unprocessed/ \
    nibi:~/projects/def-jic823/Jacob-Projects/emgraphrag/ocr_docs/unprocessed/
# Ctrl-A D to detach; screen -r rsync_pdfs to reattach
```
Alternative: use Globus for Alliance-to-Alliance transfers.

**3. Set up the Python environment (once, on the Nibi login node):**
```bash
ssh nibi
cd ~/projects/def-jic823/Jacob-Projects/emgraphrag
bash pipeline/nibi/setup_nibi_env.sh
```
This creates the venv (using the Alliance wheelhouse for PyTorch), installs
olmOCR and EarlyModernNER, and pre-downloads the olmOCR model into
`.cache/huggingface/` (~15 GB, internet access on login node).

**4. Submit the job chain (on the Nibi login node):**
```bash
cd ~/projects/def-jic823/Jacob-Projects/emgraphrag
bash pipeline/nibi/submit_pipeline.sh
```
This submits 3 rounds of OCR → NER as a SLURM dependency chain:
`ocr1 → ner1 → ocr2 → ner2 → ocr3 → ner3`

All jobs are resume-safe — already-processed files are skipped if a job is
restarted.

**5. Monitor jobs:**
```bash
squeue -u jacobpol
tail -f emgraphrag_ocr_<JOBID>.out
tail -f emgraphrag_ner_<JOBID>.out
```

**6. Download results (from WSL2 after all jobs complete):**
```bash
rsync -av --progress \
    nibi:~/projects/def-jic823/Jacob-Projects/emgraphrag/output/ocr_md/ \
    output/ocr_md/
rsync -av --progress \
    nibi:~/projects/def-jic823/Jacob-Projects/emgraphrag/output/ner_output/ \
    output/ner_output/
```

**7. Continue with Steps 4–5 on the school computer** (graph + LightRAG).

### Nibi scripts

| Script | Purpose |
|--------|---------|
| `pipeline/nibi/setup_nibi_env.sh` | One-time venv + model download (login node) |
| `pipeline/nibi/process_ocr.sh` | OCR worker (called by SLURM job) |
| `pipeline/nibi/submit_ocr.slurm` | 48h OCR SLURM job |
| `pipeline/nibi/submit_ner.slurm` | 24h NER SLURM job |
| `pipeline/nibi/submit_pipeline.sh` | Submit full 6-job chain at once |
| `pipeline/nibi/copy_to_nibi.sh` | Rsync scripts + small data from WSL2 |

---

## Transferring Files Between Machines

The `output/` directory is gitignored. You need to transfer it manually.

From WSL2 to school computer (via USB drive or network):
```bash
# Copy the whole repo + output together
rsync -av --progress /mnt/z/emgraphrag/ user@school-ip:~/emgraphrag/

# Or just copy the pre-parsed import records (step 01 output, ~50MB)
rsync -av /mnt/z/emgraphrag/output/import_records_parsed/ user@school-ip:~/emgraphrag/output/import_records_parsed/
```

After OCR/NER are done on the school computer, copy results back:
```bash
rsync -av user@school-ip:~/emgraphrag/output/ocr_md/ /mnt/z/emgraphrag/output/ocr_md/
rsync -av user@school-ip:~/emgraphrag/output/ner_output/ /mnt/z/emgraphrag/output/ner_output/
```

---

## Repository Structure

```
emgraphrag/
├── import_records/                  # 57 xlsx files (untouched)
├── ocr_docs/                        # PDF corpus (untouched)
├── pipeline/
│   ├── 01_parse_import_records.py   # xlsx → CSV + JSON + markdown docs
│   ├── 02_ocr/
│   │   └── run_ocr.sh               # olmOCR batch processing (school computer)
│   ├── nibi/                        # Alliance HPC scripts
│   │   ├── setup_nibi_env.sh        # one-time venv + model download
│   │   ├── process_ocr.sh           # OCR worker (called by SLURM)
│   │   ├── submit_ocr.slurm         # 48h OCR SLURM job
│   │   ├── submit_ner.slurm         # 24h NER SLURM job
│   │   ├── submit_pipeline.sh       # submit full OCR→NER chain
│   │   └── copy_to_nibi.sh          # rsync scripts to Nibi (run from WSL2)
│   ├── 03_ner/
│   │   └── run_ner.py               # EarlyModernNER over OCR markdown
│   ├── 04_graph/
│   │   ├── extract_relations.py     # LLM relation extraction (GROWN_IN, SHIPPED_TO, …)
│   │   ├── build_graph.py           # NER + import records + relations → nodes/edges CSV
│   │   └── import_records_to_docs.py # CSV → richer markdown for LightRAG
│   ├── 05_embed/
│   │   └── generate_embeddings.py  # Qwen3-Embedding-8B → ChromaDB
│   ├── 06_query/
│   │   └── query.py                # hybrid Neo4j + ChromaDB query interface
│   └── 05_lightrag/                # superseded — kept for reference
│       ├── setup.py
│       ├── ingest.py
│       └── query.py
├── docker/
│   └── unraid/
│       ├── neo4j.compose.yml       # Neo4j Community on Unraid
│       └── chromadb.compose.yml    # ChromaDB server on Unraid
├── output/                          # gitignored — generated data
│   ├── import_records_parsed/       # step 01 (done on WSL2)
│   ├── ocr_md/                      # step 02 outputs
│   ├── ner_output/                  # step 03 outputs
│   ├── knowledge_graph/             # step 04 outputs
│   ├── lightrag_input/              # combined docs for LightRAG ingestion
│   └── lightrag_storage/            # LightRAG graph + vector index
├── CLAUDE.md                        # context file for Claude Code on school computer
├── lightrag_config.yaml             # generated by setup.py (gitignored)
├── requirements.txt
└── .gitignore
```

---

## Import Records Data

- **57 xlsx files**, covering years 1696–1755
- **43,770 total records** (including zero-value rows)
- **11,686 non-zero records**
- **204 unique commodities** (Brown Sugar, Tobacco, Cotton, Indigo, Rum, etc.)
- **15 unique colony locations** (Antigua, Barbados, Jamaica, Nevis, etc.)
- **441 markdown documents** generated for LightRAG ingestion

Column schema: `year_range, year, commodity_name, from_location, to_location, ton, hh, quarter, lb, total_pounds, weight_tons`

---

## Notes

- `output/` is gitignored — all generated data stays local; transfer manually
- All pipeline steps are resume-safe (re-running skips already-processed files)
- LightRAG uses `hybrid` mode by default (graph traversal + vector similarity)
- `qwen2.5:72b` needs ~48GB — fits fully in the GB10's 128GB unified memory pool
- `nomic-embed-text` is the required embedding model (small, fast)
- EarlyModernNER is optimised for early modern English spelling variants
- `pipeline/02_ocr/run_ocr.sh` uses Apptainer by default; adapt for native olmOCR install
