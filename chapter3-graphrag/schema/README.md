# schema/

The Neo4j knowledge-graph schema for the Chapter 3 GraphRAG system.

| File | Contents |
|---|---|
| `schema.cypher` | Constraints + indexes (uniqueness on `:Node.id`, name/label indexes, a full-text index) and the APOC-based `LOAD CSV` procedure |
| `entity-types.md` | Node labels (with counts), the ~1,972 relationship types, all node/edge properties, and CIDOC-CRM alignment |

## The graph

- **218,523 nodes** / **691,577 edges**
- Built by `pipeline/04_graph/build_graph_final.py` and loaded with
  `pipeline/04_graph/load_neo4j.py`
- Exported as `nodes.csv` + `edges.csv`. `edges.csv` is ~112 MB, so the full
  export is **not** in this repo — it ships in the Zenodo **knowledge-graph
  deposit** along with the ChromaDB vector index and the 10-document
  smoke-test subset.

## Loading locally

```bash
# bring up Neo4j (APOC required)
docker compose -f ../docker/unraid/neo4j.compose.yml up -d
# place nodes.csv + edges.csv (from the Zenodo deposit) in the import dir, then:
python ../pipeline/04_graph/load_neo4j.py --wipe
```

License: CC-BY-4.0 (see `../../LICENSE-DATA`).
