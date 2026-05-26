#!/usr/bin/env python3
"""
05_lightrag/query.py
CLI query interface for the emgraphrag LightRAG knowledge base.

Usage:
    python pipeline/05_lightrag/query.py "What commodities did Jamaica export most in the 1720s?"
    python pipeline/05_lightrag/query.py --mode global "Which Caribbean colonies traded with London?"
    python pipeline/05_lightrag/query.py --mode hybrid --no-citations "Tell me about sugar trade in Barbados"

Query modes:
    local   — entity-focused retrieval (best for specific people, places, commodities)
    global  — broad thematic retrieval (best for cross-corpus questions)
    hybrid  — combines both (default, recommended)
    naive   — simple vector search without graph
"""

import argparse
import sys
from pathlib import Path


def load_config(config_path: Path) -> dict:
    config = {}
    if not config_path.exists():
        print(f"ERROR: Config not found: {config_path}")
        print("  Run pipeline/05_lightrag/setup.py first.")
        sys.exit(1)
    for line in config_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            config[key.strip()] = value.strip()
    return config


def get_lightrag(config: dict):
    try:
        from lightrag import LightRAG
        from lightrag.llm.ollama import ollama_model_complete, ollama_embed
        from lightrag.utils import EmbeddingFunc
    except ImportError:
        print("ERROR: lightrag-hku not installed. Run: pip install lightrag-hku")
        sys.exit(1)

    working_dir = config.get("working_dir", "output/lightrag_storage")
    llm_model = config.get("llm_model", "qwen3.5:35b")
    embed_model = config.get("embedding_model", "nomic-embed-text")
    ollama_url = config.get("ollama_base_url", "http://localhost:11434")
    max_tokens = int(config.get("max_tokens", 32768))
    max_async = int(config.get("max_async", 4))

    rag = LightRAG(
        working_dir=working_dir,
        llm_model_func=lambda prompt, **kw: ollama_model_complete(
            prompt,
            model=llm_model,
            host=ollama_url,
            **kw,
        ),
        embedding_func=EmbeddingFunc(
            embedding_dim=768,
            max_token_size=8192,
            func=lambda texts: ollama_embed(
                texts,
                embed_model=embed_model,
                host=ollama_url,
            ),
        ),
        llm_model_max_token_size=max_tokens,
        max_async=max_async,
    )
    return rag


EXAMPLE_QUERIES = [
    "What commodities did Jamaica export most in the 1720s?",
    "Which Caribbean colonies traded the most sugar with London between 1700 and 1730?",
    "Who were the major merchants or agents mentioned in the trade documents?",
    "How did the volume of cotton exports from Barbados change over time?",
    "What was the role of Antigua in the early 18th century British Atlantic trade?",
    "Which locations exported indigo and in what quantities?",
    "What do the EEBO documents reveal about Caribbean colonial governance?",
]


def main():
    parser = argparse.ArgumentParser(
        description="Query the emgraphrag LightRAG knowledge base.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\nExample queries:\n" + "\n".join(f"  {q}" for q in EXAMPLE_QUERIES[:3]),
    )
    parser.add_argument(
        "question", nargs="?",
        help="Question to ask (omit to enter interactive mode)"
    )
    parser.add_argument(
        "--mode", choices=["local", "global", "hybrid", "naive"],
        default="hybrid",
        help="Retrieval mode (default: hybrid)"
    )
    parser.add_argument(
        "--config", default="lightrag_config.yaml",
        help="Path to lightrag_config.yaml"
    )
    parser.add_argument(
        "--no-citations", action="store_true",
        help="Suppress source citations in output"
    )
    parser.add_argument(
        "--examples", action="store_true",
        help="Print example queries and exit"
    )
    args = parser.parse_args()

    if args.examples:
        print("Example queries for emgraphrag:\n")
        for q in EXAMPLE_QUERIES:
            print(f"  python pipeline/05_lightrag/query.py \"{q}\"")
        print()
        return

    config = load_config(Path(args.config))

    try:
        from lightrag import QueryParam
    except ImportError:
        print("ERROR: lightrag-hku not installed.")
        sys.exit(1)

    print(f"Loading LightRAG (working dir: {config.get('working_dir', 'output/lightrag_storage')})...")
    rag = get_lightrag(config)

    def run_query(question: str, mode: str):
        import asyncio

        print(f"\nQuery [{mode} mode]: {question}")
        print("─" * 60)

        async def _query():
            return await rag.aquery(
                question,
                param=QueryParam(mode=mode),
            )

        try:
            result = asyncio.run(_query())
        except Exception as e:
            print(f"ERROR: Query failed: {e}")
            return

        # result may be a string or a dict
        if isinstance(result, dict):
            answer = result.get("answer") or result.get("response") or str(result)
            sources = result.get("sources") or result.get("context") or []
        else:
            answer = str(result)
            sources = []

        print(answer)

        if not args.no_citations and sources:
            print("\n── Sources ──────────────────────────────────────────")
            if isinstance(sources, list):
                for i, src in enumerate(sources[:10], 1):
                    if isinstance(src, dict):
                        doc_id = src.get("doc_id") or src.get("id") or src.get("source", "")
                        snippet = src.get("content") or src.get("text", "")
                        if snippet:
                            snippet = snippet[:120].replace("\n", " ")
                        print(f"  [{i}] {doc_id}: {snippet}...")
                    else:
                        print(f"  [{i}] {src}")
            else:
                print(str(sources)[:500])

    if args.question:
        run_query(args.question, args.mode)
    else:
        # Interactive mode
        print("\nemgraphrag interactive query")
        print(f"Mode: {args.mode} (change with --mode flag)")
        print("Type 'exit' or Ctrl+C to quit.\n")
        try:
            while True:
                try:
                    question = input("Query> ").strip()
                except EOFError:
                    break
                if not question:
                    continue
                if question.lower() in ("exit", "quit", "q"):
                    break
                run_query(question, args.mode)
                print()
        except KeyboardInterrupt:
            print("\nGoodbye.")


if __name__ == "__main__":
    main()
