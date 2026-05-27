// =============================================================================
// emgraphrag — Neo4j schema (constraints + indexes)
//
// The knowledge graph is exported as two CSVs (on Zenodo, knowledge-graph
// deposit):
//   nodes.csv  — columns: id,label,name,wd_label,description,types,
//                coordinates,inception,birth,death,author,year
//   edges.csv  — columns: source,target,type,source_tag,doc_id,crm_property,
//                confidence,year,commodity,total_pounds,weight_tons,
//                hogsheads,year_range
//
// Every node carries the generic :Node label (for MERGE uniqueness) plus a
// dynamic label from its `label` column (Person, Location, Commodity,
// Document, Organization, Year, Entity). Relationship types are dynamic
// (~1,972 distinct types), so loading uses APOC. See load_neo4j.py for the
// full LOAD CSV procedure.
// Requires the APOC plugin.
// =============================================================================

// ── Constraints + indexes (create before loading, for speed) ────────────────
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Node) REQUIRE n.id IS UNIQUE;

CREATE INDEX IF NOT EXISTS FOR (n:Node) ON (n.name);
CREATE INDEX IF NOT EXISTS FOR (n:Node) ON (n.wd_label);
CREATE INDEX IF NOT EXISTS FOR (n:Node) ON (n.label);

CREATE FULLTEXT INDEX node_fulltext IF NOT EXISTS
  FOR (n:Node) ON EACH [n.name, n.wd_label, n.description];

// ── Loading ─────────────────────────────────────────────────────────────────
// Nodes (dynamic label via APOC):
//   LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
//   CALL { WITH row
//     MERGE (n:Node {id: row.id})
//     SET n.name = row.name, n.wd_label = coalesce(row.wd_label,''),
//         n.description = coalesce(row.description,''), n.label = row.label
//     WITH n, row CALL apoc.create.addLabels(n,[row.label]) YIELD node
//     RETURN count(*) AS c
//   } IN TRANSACTIONS OF 5000 ROWS RETURN sum(c);
//
// Edges (dynamic type via APOC):
//   LOAD CSV WITH HEADERS FROM 'file:///edges.csv' AS row
//   CALL { WITH row
//     MATCH (s:Node {id: row.source}) MATCH (t:Node {id: row.target})
//     CALL apoc.create.relationship(s, row.type,
//       {source_tag: row.source_tag, doc_id: coalesce(row.doc_id,''),
//        crm_property: coalesce(row.crm_property,''), ...}, t) YIELD rel
//     RETURN count(*) AS c
//   } IN TRANSACTIONS OF 5000 ROWS RETURN sum(c);
//
// One-command load:  python pipeline/04_graph/load_neo4j.py --wipe
