#!/usr/bin/env python3
"""
04_graph/load_neo4j.py
Load the knowledge-graph CSVs (nodes.csv + edges.csv) into Neo4j.

Reconstructed from the LOAD CSV procedure documented in schema/schema.cypher
(the original load_neo4j.py was not archived with the repo). It reproduces the
documented behaviour:

  - every node gets the generic :Node label (MERGE uniqueness on n.id) plus a
    dynamic label from its `label` column (Person, Location, Commodity, ...)
  - relationship types are dynamic (~1,972 distinct types), created via APOC
  - constraints + indexes from schema/schema.cypher are applied before loading

Requires:
  - a running Neo4j with the APOC plugin (see docker/unraid/neo4j.compose.yml)
  - nodes.csv and edges.csv placed in Neo4j's *import* directory
    (the compose file mounts /mnt/user/appdata/neo4j/import)

Usage:
    # Fresh load, wiping any existing graph first:
    python pipeline/04_graph/load_neo4j.py --wipe

    # Custom connection / file names:
    python pipeline/04_graph/load_neo4j.py \\
        --neo4j-uri bolt://192.168.1.100:7687 \\
        --neo4j-user neo4j --neo4j-password yourpassword \\
        --nodes-csv nodes.csv --edges-csv edges.csv
"""

import argparse
import os
import sys
import time

# ── Schema (mirrors schema/schema.cypher) ────────────────────────────────────

SCHEMA_STATEMENTS = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Node) REQUIRE n.id IS UNIQUE",
    "CREATE INDEX IF NOT EXISTS FOR (n:Node) ON (n.name)",
    "CREATE INDEX IF NOT EXISTS FOR (n:Node) ON (n.wd_label)",
    "CREATE INDEX IF NOT EXISTS FOR (n:Node) ON (n.label)",
    """CREATE FULLTEXT INDEX node_fulltext IF NOT EXISTS
       FOR (n:Node) ON EACH [n.name, n.wd_label, n.description]""",
]

WIPE_STATEMENT = """
CALL { MATCH (n) DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS
"""

LOAD_NODES = """
LOAD CSV WITH HEADERS FROM $url AS row
CALL {
  WITH row
  MERGE (n:Node {id: row.id})
  SET n.name        = row.name,
      n.label       = row.label,
      n.wd_label    = coalesce(row.wd_label, ''),
      n.description = coalesce(row.description, ''),
      n.types       = coalesce(row.types, ''),
      n.coordinates = coalesce(row.coordinates, ''),
      n.inception   = coalesce(row.inception, ''),
      n.birth       = coalesce(row.birth, ''),
      n.death       = coalesce(row.death, ''),
      n.author      = coalesce(row.author, ''),
      n.year        = coalesce(row.year, '')
  WITH n, row
  CALL apoc.create.addLabels(n, [row.label]) YIELD node
  RETURN count(*) AS c
} IN TRANSACTIONS OF 5000 ROWS
RETURN sum(c) AS total
"""

LOAD_EDGES = """
LOAD CSV WITH HEADERS FROM $url AS row
CALL {
  WITH row
  MATCH (s:Node {id: row.source})
  MATCH (t:Node {id: row.target})
  CALL apoc.create.relationship(s, row.type, {
    source_tag:   coalesce(row.source_tag, ''),
    doc_id:       coalesce(row.doc_id, ''),
    crm_property: coalesce(row.crm_property, ''),
    confidence:   coalesce(row.confidence, ''),
    year:         coalesce(row.year, ''),
    commodity:    coalesce(row.commodity, ''),
    total_pounds: coalesce(row.total_pounds, ''),
    weight_tons:  coalesce(row.weight_tons, ''),
    hogsheads:    coalesce(row.hogsheads, ''),
    year_range:   coalesce(row.year_range, '')
  }, t) YIELD rel
  RETURN count(*) AS c
} IN TRANSACTIONS OF 5000 ROWS
RETURN sum(c) AS total
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load nodes.csv + edges.csv into Neo4j (APOC required)."
    )
    parser.add_argument("--neo4j-uri",
                        default=os.environ.get("NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--neo4j-user",
                        default=os.environ.get("NEO4J_USER", "neo4j"))
    parser.add_argument("--neo4j-password",
                        default=os.environ.get("NEO4J_PASSWORD", "password"))
    parser.add_argument("--nodes-csv", default="nodes.csv",
                        help="File name inside Neo4j's import dir, or a full "
                             "file:///... / http(s)://... URL (default: nodes.csv)")
    parser.add_argument("--edges-csv", default="edges.csv",
                        help="File name inside Neo4j's import dir, or a full "
                             "URL (default: edges.csv)")
    parser.add_argument("--wipe", action="store_true",
                        help="Delete the existing graph before loading")
    args = parser.parse_args()

    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("ERROR: neo4j driver not installed. Run: pip install neo4j")
        sys.exit(1)

    def to_url(name: str) -> str:
        if "://" in name:
            return name
        return f"file:///{name}"

    nodes_url = to_url(args.nodes_csv)
    edges_url = to_url(args.edges_csv)

    print(f"Neo4j:  {args.neo4j_uri}")
    print(f"Nodes:  {nodes_url}")
    print(f"Edges:  {edges_url}")

    driver = GraphDatabase.driver(
        args.neo4j_uri, auth=(args.neo4j_user, args.neo4j_password)
    )
    driver.verify_connectivity()

    # CALL {...} IN TRANSACTIONS needs auto-commit transactions → session.run
    with driver.session() as session:
        apoc_ok = session.run(
            "RETURN apoc.version() AS v"
        ).single()
        print(f"APOC:   {apoc_ok['v']}")

        if args.wipe:
            print("\nWiping existing graph...")
            session.run(WIPE_STATEMENT).consume()

        print("Applying constraints + indexes...")
        for stmt in SCHEMA_STATEMENTS:
            session.run(stmt).consume()

        print("\nLoading nodes (this takes a few minutes)...")
        t0 = time.time()
        total_nodes = session.run(LOAD_NODES, url=nodes_url).single()["total"]
        print(f"  {total_nodes:,} nodes loaded in {time.time() - t0:.0f}s")

        print("Loading edges (this is the slow part)...")
        t0 = time.time()
        total_edges = session.run(LOAD_EDGES, url=edges_url).single()["total"]
        print(f"  {total_edges:,} edges loaded in {time.time() - t0:.0f}s")

        n = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        r = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]

    driver.close()

    print(f"\nGraph now contains {n:,} nodes and {r:,} relationships.")
    print("Expected for the thesis graph: 218,523 nodes / 691,577 edges.")


if __name__ == "__main__":
    main()
