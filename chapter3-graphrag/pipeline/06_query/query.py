#!/usr/bin/env python3
"""
06_query/query.py
Query the emgraphrag knowledge base using Neo4j (temporal graph) +
ChromaDB (vector search), combined via LangChain.

Query modes:
  hybrid (default) — graph traversal + vector similarity, combined
  graph             — Neo4j Cypher only (structured temporal questions)
  vector            — ChromaDB only (semantic similarity)

Usage:
    # Single query (hybrid mode)
    python pipeline/06_query/query.py "What commodities did Jamaica export in the 1720s?"

    # Graph mode (temporal/structural questions)
    python pipeline/06_query/query.py --mode graph \\
        "Which colonies exported sugar between 1710 and 1730?"

    # Vector mode (semantic questions)
    python pipeline/06_query/query.py --mode vector \\
        "Tell me about merchant networks in the Caribbean"

    # Interactive mode
    python pipeline/06_query/query.py

    # Show example queries
    python pipeline/06_query/query.py --examples

    # Override connections
    python pipeline/06_query/query.py \\
        --neo4j-uri bolt://192.168.1.100:7687 \\
        --chroma-host 192.168.1.100 \\
        "Your question here"
"""

import argparse
import os
import sys
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH  = PROJECT_ROOT / "atom_config.yaml"

DEFAULTS = {
    "neo4j_uri":      "bolt://localhost:7687",
    "neo4j_user":     "neo4j",
    "neo4j_password": "password",
    "ollama_url":     os.environ.get("OLLAMA_URL",
                          f"http://{os.environ['OLLAMA_HOST']}" if "OLLAMA_HOST" in os.environ
                          else "http://localhost:11434"),
    "model":          "qwen3.5:35b",
    "embed_model":    "Qwen/Qwen3-Embedding-8B",
    "chroma_host":    "localhost",
    "chroma_port":    8000,
    "collection":     "emgraphrag",
    "top_k":          5,
}

EXAMPLE_QUERIES = [
    "What commodities did Jamaica export most between 1710 and 1730?",
    "Which Caribbean colonies traded the most sugar with London?",
    "How did indigo exports from Antigua change over the period 1696–1755?",
    "Who were the merchants or agents mentioned in documents about Barbados trade?",
    "What was the relationship between rum production and sugar exports?",
    "Which colonies exported the most cotton, and during which decades?",
    "What do the documents reveal about enslaved people in the Caribbean trade networks?",
    "How did the War of the Spanish Succession affect Caribbean commodity exports?",
    "What organizations or trading companies are mentioned in documents about Jamaica?",
    "Compare the export volumes of different colonies in the 1720s.",
]


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            import yaml
            loaded = yaml.safe_load(CONFIG_PATH.read_text()) or {}
            # Only pull relevant keys
            for k in DEFAULTS:
                if k in loaded:
                    cfg[k] = loaded[k]
        except Exception:
            pass
    return cfg


# ── Graph query (Neo4j + Cypher) ──────────────────────────────────────────────

def query_graph(question: str, cfg: dict) -> str:
    try:
        from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
        from langchain_ollama import ChatOllama
    except ImportError as e:
        return f"[Graph query unavailable: {e}]"

    try:
        graph = Neo4jGraph(
            url=cfg["neo4j_uri"],
            username=cfg["neo4j_user"],
            password=cfg["neo4j_password"],
        )
        llm = ChatOllama(
            model=cfg["model"],
            base_url=cfg["ollama_url"],
            temperature=0,
        )
        chain = GraphCypherQAChain.from_llm(
            llm=llm,
            graph=graph,
            verbose=False,
            return_intermediate_steps=False,
        )
        result = chain.invoke({"query": question})
        return result.get("result", str(result))
    except Exception as e:
        return f"[Graph query error: {e}]"


# ── Vector query (ChromaDB) ───────────────────────────────────────────────────

def query_vector(question: str, cfg: dict, top_k: int = 5) -> list[dict]:
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        print(f"[Vector query unavailable: {e}]")
        return []

    try:
        client = chromadb.HttpClient(host=cfg["chroma_host"], port=cfg["chroma_port"])
        client.heartbeat()
    except Exception:
        try:
            local_dir = PROJECT_ROOT / "output/chromadb"
            client = chromadb.PersistentClient(path=str(local_dir))
        except Exception as e:
            print(f"[ChromaDB unavailable: {e}]")
            return []

    try:
        collection = client.get_collection(cfg["collection"])
        model = SentenceTransformer(cfg["embed_model"], trust_remote_code=True)
        # Use query prompt for better retrieval quality
        query_embedding = model.encode(
            [question],
            prompt_name="query",
            normalize_embeddings=True,
        ).tolist()
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append({
                "text":     doc,
                "doc_id":   meta.get("doc_id", ""),
                "source":   meta.get("source", ""),
                "score":    round(1 - dist, 3),
            })
        return chunks
    except Exception as e:
        print(f"[Vector query error: {e}]")
        return []


# ── Synthesis (combine graph + vector results) ────────────────────────────────

def synthesize(question: str, graph_answer: str,
               vector_chunks: list[dict], cfg: dict) -> str:
    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage, SystemMessage
    except ImportError as e:
        # Fallback: just concatenate
        parts = []
        if graph_answer:
            parts.append(f"Graph: {graph_answer}")
        if vector_chunks:
            parts.append("Documents:\n" + "\n\n".join(c["text"] for c in vector_chunks))
        return "\n\n".join(parts) if parts else "No results found."

    llm = ChatOllama(
        model=cfg["model"],
        base_url=cfg["ollama_url"],
        temperature=0.1,
    )

    context_parts = []
    if graph_answer and not graph_answer.startswith("["):
        context_parts.append(f"## Knowledge Graph Answer\n{graph_answer}")

    if vector_chunks:
        doc_texts = []
        for i, chunk in enumerate(vector_chunks, 1):
            doc_texts.append(
                f"[{i}] (doc: {chunk['doc_id']}, relevance: {chunk['score']})\n"
                f"{chunk['text']}"
            )
        context_parts.append("## Relevant Document Passages\n" + "\n\n".join(doc_texts))

    if not context_parts:
        return "I could not find relevant information in the knowledge base."

    context = "\n\n".join(context_parts)
    messages = [
        SystemMessage(content=(
            "You are a historian specialising in early modern British Caribbean trade "
            "(1696–1755). Answer the user's question using ONLY the provided context. "
            "Be precise about dates and quantities. Cite document IDs where relevant."
        )),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {question}"),
    ]

    response = llm.invoke(messages)
    return response.content


# ── Main query function ───────────────────────────────────────────────────────

def answer(question: str, mode: str, cfg: dict) -> str:
    print(f"\nMode: {mode} | Model: {cfg['model']}")
    print("-" * 60)

    graph_answer  = ""
    vector_chunks = []

    if mode in ("graph", "hybrid"):
        print("Querying knowledge graph (Neo4j)...")
        graph_answer = query_graph(question, cfg)

    if mode in ("vector", "hybrid"):
        print(f"Searching document embeddings (ChromaDB, top {cfg['top_k']})...")
        vector_chunks = query_vector(question, cfg, top_k=cfg["top_k"])
        print(f"  Found {len(vector_chunks)} relevant passages")

    if mode == "graph":
        return graph_answer
    if mode == "vector" and vector_chunks:
        return synthesize(question, "", vector_chunks, cfg)

    print("Synthesising answer...")
    return synthesize(question, graph_answer, vector_chunks, cfg)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    cfg = load_config()

    parser = argparse.ArgumentParser(
        description="Query the emgraphrag knowledge base"
    )
    parser.add_argument("question", nargs="?", default=None,
                        help="Question to ask (omit for interactive mode)")
    parser.add_argument("--mode",           default="hybrid",
                        choices=["hybrid", "graph", "vector"])
    parser.add_argument("--neo4j-uri",      default=cfg["neo4j_uri"])
    parser.add_argument("--neo4j-user",     default=cfg["neo4j_user"])
    parser.add_argument("--neo4j-password", default=cfg["neo4j_password"])
    parser.add_argument("--ollama-url",     default=cfg["ollama_url"])
    parser.add_argument("--model",          default=cfg["model"])
    parser.add_argument("--embed-model",    default=cfg["embed_model"])
    parser.add_argument("--chroma-host",    default=cfg["chroma_host"])
    parser.add_argument("--chroma-port",    type=int, default=cfg["chroma_port"])
    parser.add_argument("--collection",     default=cfg["collection"])
    parser.add_argument("--top-k",          type=int, default=cfg["top_k"])
    parser.add_argument("--examples",       action="store_true",
                        help="Print example queries and exit")
    args = parser.parse_args()

    if args.examples:
        print("Example queries:")
        for q in EXAMPLE_QUERIES:
            print(f"  {q}")
        return

    cfg.update({
        "neo4j_uri":      args.neo4j_uri,
        "neo4j_user":     args.neo4j_user,
        "neo4j_password": args.neo4j_password,
        "ollama_url":     args.ollama_url,
        "model":          args.model,
        "embed_model":    args.embed_model,
        "chroma_host":    args.chroma_host,
        "chroma_port":    args.chroma_port,
        "collection":     args.collection,
        "top_k":          args.top_k,
    })

    if args.question:
        result = answer(args.question, args.mode, cfg)
        print("\n" + "=" * 60)
        print(result)
        return

    # Interactive mode
    print("emgraphrag query interface (Ctrl-C or 'quit' to exit)")
    print(f"Mode: {args.mode} | Type '--examples' to see sample queries")
    print()
    while True:
        try:
            question = input("Question: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            break
        if question == "--examples":
            for q in EXAMPLE_QUERIES:
                print(f"  {q}")
            continue
        result = answer(question, args.mode, cfg)
        print("\n" + result + "\n")


if __name__ == "__main__":
    main()
