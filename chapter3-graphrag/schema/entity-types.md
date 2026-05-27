# Knowledge-graph schema — node labels, edge types, properties

The graph holds **218,523 nodes** and **691,577 edges**, built from
EarlyModernNER output over the OCR'd corpus plus the customs import-ledger
records, with entity linking to Wikidata and CIDOC-CRM property alignment.

## Node labels

Every node also carries the generic `:Node` label. The type-specific label
comes from the `label` column of `nodes.csv`.

| Label | Count | Notes |
|---|---:|---|
| `Person` | 129,221 | NER type PERSON |
| `Location` | 40,194 | NER type TOPONYM (place/toponym) |
| `Commodity` | 19,776 | NER type COMMODITY; commodity hierarchy via `IS_VARIANT_OF` |
| `Document` | 19,249 | Source documents (one per OCR'd item that entered the graph) |
| `Organization` | 7,615 | NER type ORGANIZATION |
| `Entity` | 2,367 | Generic / not-yet-typed entities |
| `Year` | 57 | Temporal anchors for time-scoped relations |

> The NER stage emits four entity types — **PERSON, TOPONYM, ORGANIZATION,
> COMMODITY**. In the graph these map to `Person`, `Location`, `Organization`,
> and `Commodity` respectively (`TOPONYM → Location`).

### Node properties (`nodes.csv` columns)

`id`, `label`, `name`, `wd_label` (Wikidata label if linked), `description`,
`types`, `coordinates`, `inception`, `birth`, `death`, `author`, `year`.

## Relationship types

There are **~1,972 distinct relationship types** — a mix of (a) open,
LLM-extracted semantic relations, (b) CIDOC-CRM properties, and (c) structural
relations. Most-frequent types:

| Type | Count | Kind |
|---|---:|---|
| `MENTIONS` | 449,412 | structural (document/chunk → entity) |
| `ASSOCIATED_WITH` | 66,508 | semantic |
| `P2_has_type` | 29,463 | CIDOC-CRM |
| `FALLS_WITHIN` | 12,252 | structural / temporal |
| `P89_falls_within` | 8,932 | CIDOC-CRM |
| `CORRESPONDED_WITH` | 8,257 | semantic |
| `EXPORTED` / `EXPORTED_IN` | 7,916 / 7,916 | semantic (trade) |
| `PARTNERED_WITH` | 7,332 | semantic |
| `TRAVELED_TO` | 7,223 | semantic |
| `IMPORTED_TO` | 6,847 | semantic (trade) |

Other notable types: `IS_VARIANT_OF` (commodity hierarchy traversal),
`HAS_RESIDENCE`, `EMPLOYED_BY`, `GOVERNED`, `TRADED_WITH`, `PRODUCED_IN`.

### Relationship properties (`edges.csv` columns)

`source`, `target`, `type`, `source_tag` (provenance: NER / customs / wikidata),
`doc_id` (originating document), `crm_property` (CIDOC-CRM alignment, where
applicable), `confidence`, `year`, `commodity`, `total_pounds`, `weight_tons`,
`hogsheads`, `year_range`.

## CIDOC-CRM alignment

Relations carry a `crm_property` where they map onto CIDOC-CRM (e.g.
`P2_has_type`, `P89_falls_within`), supporting downstream conversion to RDF /
LINCS-compatible output. The trade quantities (`total_pounds`, `weight_tons`,
`hogsheads`) come from the TNA CUST 3 customs ledgers.
