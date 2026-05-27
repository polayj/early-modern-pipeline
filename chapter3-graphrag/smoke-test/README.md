# smoke-test/ — 10-document end-to-end subset

Ten representative **Internet Archive** (public-domain) documents from the
corpus, packaged so a reviewer can exercise the NER → knowledge-graph pipeline
on a fresh checkout **without** downloading the full Zenodo deposits.

All ten are confirmed Internet Archive items (their `archive.org` identifiers
are in `manifest.csv`); **no EEBO material is included**.

## Layout

```
smoke-test/
├── manifest.csv            # the 10 documents with full citations + archive.org URLs
└── documents/
    ├── <hex>.ocr.md          # olmOCR-2 transcription (input to NER)
    ├── <hex>.entities.jsonl  # EarlyModernNER output (doc_id, entity_text, entity_type)
    └── <hex>.graph.json      # expected knowledge-graph fragment for that document
```

`<hex>` is the document's 8-character id; `manifest.csv` maps it to the
archive.org identifier, title, year, creator, and URL.

## The graph fragment (`*.graph.json`)

Each fragment is the slice of the full knowledge graph attributable to that one
document (`edges` where `doc_id` matches, plus the `nodes` they connect):

```json
{
  "doc_id": "<hex>_<title>",
  "document_node": "doc__<hex>_<title>",
  "archive_org_identifier": "...",
  "n_edges_total": 100,
  "edges": [{"source": "...", "type": "EXPORTED", "target": "...", "crm_property": "...", "source_tag": "ocr_llm"}],
  "nodes": [{"id": "wd:Q...", "label": "Commodity", "name": "...", "wd_label": "..."}]
}
```

> Fragments are capped at 100 edges per document to keep this directory small;
> the complete graph (218,523 nodes / 691,577 edges) is in the Zenodo
> knowledge-graph deposit.

## Documents

| hex | archive.org id | short title |
|---|---|---|
| 2209b096 | `americangeography00mors` | The American geography (Morse) |
| 2617efac | `morewondersofinv1700cale` | More wonders of the invisible world (Calef) |
| e7d32ccb | `fullrelationofan00bourrich` | A full relation of another voyage into the West Indies |
| 282ee81a | `votesproceedings1751newj` | Votes and proceedings of the General Assembly (NJ, 1751) |
| 4238a32b | `naturalhistoryof00chamuoft` | The natural history of coffee, thee, chocolate |
| 618a65cc | `actslawsmajrhode00allerich` | Acts and laws of His Majesty's colony of Rhode Island |
| e4e2b27c | `dissertatiodege00meri` | Dissertatio de generatione et metamorphosibus (Merian) |
| e316591e | `essaysonvenereal00blai` | Essays on the venereal disease (Blair) |
| c8d71255 | `abridgementofmin12grea` | Abridgement of the minutes of the evidence (slave trade) |
| c29b3a4a | `votesproceedings1754newj` | Votes and proceedings of the General Assembly (NJ, 1754) |

## Running it

```bash
# re-run NER on a document and compare to the committed entities
python ../pipeline/03_ner/run_ner.py --input documents/2209b096.ocr.md

# or load the expected fragments into Neo4j and query them
```

See `manifest.csv` for full citations. Original PDFs are at
`https://archive.org/details/<archive_org_identifier>`.

License: CC-BY-4.0 (see `../../LICENSE-DATA`). OCR transcriptions produced by
olmOCR-2; entity annotations by EarlyModernNER.
