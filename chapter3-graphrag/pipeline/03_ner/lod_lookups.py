#!/usr/bin/env python3
"""
03_ner/lod_lookups.py
Entity linking via agentic Wikidata MCP tool use.

The LLM (Ollama) is given Wikidata MCP tools and decides how to search for
and verify entity matches. This gives the model full control over:
  - What search queries to run (semantic search via MCP)
  - Whether to inspect entity statements for verification
  - Whether a candidate actually matches the historical entity

All results are cached in a local SQLite database.
"""

import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional


# ── CIDOC-CRM class mapping ──────────────────────────────────────────────────

CIDOC_CRM_CLASSES = {
    "TOPONYM": {
        "class": "E53_Place",
        "uri": "http://www.cidoc-crm.org/cidoc-crm/E53_Place",
    },
    "PERSON": {
        "class": "E21_Person",
        "uri": "http://www.cidoc-crm.org/cidoc-crm/E21_Person",
    },
    "ORGANIZATION": {
        "class": "E74_Group",
        "uri": "http://www.cidoc-crm.org/cidoc-crm/E74_Group",
    },
    "COMMODITY": {
        "class": "E55_Type",
        "uri": "http://www.cidoc-crm.org/cidoc-crm/E55_Type",
    },
}


def get_cidoc_crm(entity_type: str) -> tuple[str, str]:
    """Return (class_name, class_uri) for an entity type."""
    info = CIDOC_CRM_CLASSES.get(entity_type, {})
    return info.get("class", "E1_CRM_Entity"), info.get(
        "uri", "http://www.cidoc-crm.org/cidoc-crm/E1_CRM_Entity"
    )


# ── SQLite cache ─────────────────────────────────────────────────────────────

class LookupCache:
    """SQLite-backed cache for authority lookups."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS lookup_cache (
                normalized_text TEXT,
                entity_type TEXT,
                authority_source TEXT,
                response_json TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (normalized_text, entity_type, authority_source)
            )
        """)
        self.conn.commit()

    def get(self, text: str, entity_type: str, source: str) -> Optional[dict]:
        """Return cached result or None."""
        row = self.conn.execute(
            "SELECT response_json FROM lookup_cache WHERE normalized_text=? AND entity_type=? AND authority_source=?",
            (text.lower(), entity_type, source),
        ).fetchone()
        if row:
            return json.loads(row[0])
        return None

    def put(self, text: str, entity_type: str, source: str, result: dict):
        """Cache a lookup result."""
        self.conn.execute(
            "INSERT OR REPLACE INTO lookup_cache (normalized_text, entity_type, authority_source, response_json) VALUES (?, ?, ?, ?)",
            (text.lower(), entity_type, source, json.dumps(result, ensure_ascii=False)),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()


# ── Rate limiter ──────────────────────────────────────────────────────────────

_last_request_time: dict[str, float] = {}

def _rate_limit(source: str, min_interval: float = 0.5):
    """Ensure at least min_interval seconds between requests to the same source."""
    now = time.time()
    last = _last_request_time.get(source, 0)
    wait = min_interval - (now - last)
    if wait > 0:
        time.sleep(wait)
    _last_request_time[source] = time.time()


# ── Wikidata MCP tool execution ──────────────────────────────────────────────

WIKIDATA_MCP_URL = "https://wd-mcp.wmcloud.org/tool"

def _call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """
    Call a Wikidata MCP tool via its HTTP REST endpoint.
    Returns the response text, or an error message.
    """
    _rate_limit("wikidata_mcp")
    params = urllib.parse.urlencode(arguments)
    url = f"{WIKIDATA_MCP_URL}/{tool_name}?{params}"
    req = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as e:
        return f"ERROR: {e}"


# ── Tool definitions for Ollama ──────────────────────────────────────────────

WIKIDATA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_items",
            "description": (
                "Search Wikidata items (QIDs) using semantic and keyword search. "
                "Find conceptually similar Wikidata items from a natural-language query. "
                "Returns QID, label, and description for each match."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural-language description of the concept to find",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_statements",
            "description": (
                "Return the direct statements (property-value pairs) of a Wikidata entity. "
                "ONLY use this if you need to verify a candidate and cannot decide from the "
                "search results alone. Input is a QID like 'Q42'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Wikidata entity ID (QID), e.g. 'Q42'",
                    },
                },
                "required": ["entity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_result",
            "description": (
                "Submit your final answer. You MUST call this after your first search. "
                "Call with the best QID match, or with empty QID if no good match exists."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "qid": {
                        "type": "string",
                        "description": "The Wikidata QID of the best match (e.g. 'Q3339'), or empty string if no match",
                    },
                    "label": {
                        "type": "string",
                        "description": "The label of the matched entity",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score from 0.0 to 1.0",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Brief explanation of why this is or isn't a match",
                    },
                },
                "required": ["qid", "label", "confidence", "reason"],
            },
        },
    },
]


# ── Agentic entity resolution ───────────────────────────────────────────────

MAX_TOOL_ROUNDS = 4  # search → (optional verify) → submit (+ 1 nudge if text response)


def lookup_entity(
    normalized_text: str,
    entity_type: str,
    cache: LookupCache,
    geonames_username: str = "",
    llm_url: str = "http://localhost:8000",
    llm_model: str = "",
    context_passage: str = "",
) -> dict:
    """
    Look up an entity using agentic Wikidata MCP tool calling.

    The LLM searches Wikidata, evaluates results, and submits its decision.
    No entities are excluded — everything gets searched.

    Returns a dict with:
        authority_uri, authority_label, authority_source, confidence, linked
    """
    # Check cache first
    cached = cache.get(normalized_text, entity_type, "resolved")
    if cached is not None:
        return cached

    if not llm_model or not llm_url:
        result = _no_model_result()
        cache.put(normalized_text, entity_type, "resolved", result)
        return result

    system_msg = (
        "You are a historical entity linking specialist for Early Modern British Caribbean "
        "documents (1500s–1800s). You have Wikidata tools.\n\n"
        "WORKFLOW: Call search_items ONCE, then IMMEDIATELY call submit_result with your answer. "
        "Do NOT call search_items more than once. Do NOT call search_properties.\n\n"
        "After seeing search results:\n"
        "- If a result clearly matches → submit_result with its QID and high confidence\n"
        "- If you need to verify one candidate → call get_statements on that QID, then submit_result\n"
        "- If no results match → submit_result with empty QID and confidence 0.0\n\n"
        "Entity type guidance:\n"
        "- TOPONYM: pick the geographic place relevant to Caribbean/Atlantic/European history\n"
        "- PERSON: prefer entries from the 1500-1800 period\n"
        "- ORGANIZATION: historical companies, guilds, colonial bodies\n"
        "- COMMODITY: the material/substance/trade good itself, not a brand"
    )

    context_str = ""
    if context_passage:
        context_str = f"\nDocument context: \"{context_passage[:300]}\""

    user_msg = (
        f"Link this entity to Wikidata:\n"
        f"  Text: \"{normalized_text}\"\n"
        f"  Type: {entity_type}"
        f"{context_str}\n\n"
        f"Call search_items, then submit_result."
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    # Agent loop
    for round_num in range(MAX_TOOL_ROUNDS):
        response = _llm_chat(llm_url, llm_model, messages, WIKIDATA_TOOLS)
        if response is None:
            print(f"    [{normalized_text}] round {round_num+1}: Ollama returned None", flush=True)
            break

        msg = response.get("message", {})
        messages.append(msg)

        tool_calls = msg.get("tool_calls", [])
        if not tool_calls:
            content = msg.get("content", "")
            print(f"    [{normalized_text}] round {round_num+1}: text response (no tool call)", flush=True)
            result = _try_parse_text_result(content)
            if result:
                linked_str = f"→ {result['authority_uri']}" if result["linked"] else "→ unlinked"
                print(f"    [{normalized_text}] DONE: {linked_str}", flush=True)
                cache.put(normalized_text, entity_type, "resolved", result)
                return result
            # Nudge the model to use submit_result instead of text
            messages.append({
                "role": "user",
                "content": "You must call the submit_result tool with your answer. Do not respond with text.",
            })
            continue

        for tc in tool_calls:
            fn_name = tc.get("function", {}).get("name", "")
            fn_args = tc.get("function", {}).get("arguments", {})

            if fn_name == "submit_result":
                result = _process_submit(fn_args)
                linked_str = f"→ {result['authority_label']} ({result['authority_uri']})" if result["linked"] else "→ unlinked"
                reason = fn_args.get("reason", "")
                print(f"    [{normalized_text}] DONE: {linked_str} [{reason}]", flush=True)
                cache.put(normalized_text, entity_type, "resolved", result)
                return result

            # Execute the MCP tool
            print(f"    [{normalized_text}] round {round_num+1}: {fn_name}({fn_args})", flush=True)
            tool_result = _call_mcp_tool(fn_name, fn_args)

            messages.append({
                "role": "tool",
                "content": tool_result[:3000],
            })

    # Fell through without a submit — mark as unlinked
    print(f"    [{normalized_text}] DONE: → unlinked [max rounds reached]", flush=True)
    result = _no_model_result()
    cache.put(normalized_text, entity_type, "resolved", result)
    return result


def _process_submit(args: dict) -> dict:
    """Convert a submit_result tool call into our standard result dict."""
    qid = (args.get("qid") or "").strip()
    label = (args.get("label") or "").strip()
    confidence = float(args.get("confidence", 0.0))

    if qid and confidence > 0.0:
        return {
            "authority_uri": f"http://www.wikidata.org/entity/{qid}",
            "authority_label": label,
            "authority_source": "wikidata",
            "confidence": min(confidence, 1.0),
            "linked": True,
        }
    else:
        return {
            "authority_uri": None,
            "authority_label": None,
            "authority_source": None,
            "confidence": 0.0,
            "linked": False,
        }


def _no_model_result() -> dict:
    return {
        "authority_uri": None,
        "authority_label": None,
        "authority_source": None,
        "confidence": 0.0,
        "linked": False,
    }


def _try_parse_text_result(content: str) -> Optional[dict]:
    """Try to parse a result from model text output (JSON or natural language)."""
    # Try JSON first
    try:
        obj = json.loads(content)
        if "qid" in obj:
            return _process_submit(obj)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try to extract QID from natural language like "The best match is Q145 (United Kingdom)"
    m = re.search(r'\b(Q\d+)\b', content)
    if m:
        qid = m.group(1)
        # Try to extract a label near the QID
        label_match = re.search(r'Q\d+[:\s\-—]+([A-Z][^.,\n]{2,40})', content)
        label = label_match.group(1).strip() if label_match else ""
        return _process_submit({"qid": qid, "label": label, "confidence": 0.7, "reason": "extracted from text"})

    return None


def _llm_chat(
    api_url: str,
    model: str,
    messages: list[dict],
    tools: list[dict],
) -> Optional[dict]:
    """
    Send a chat request with tool definitions.
    Uses OpenAI-compatible API format (works with vLLM, Ollama, etc.).
    """
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "tools": tools,
        "temperature": 0.0,
        "max_tokens": 512,
    }).encode("utf-8")

    url = f"{api_url.rstrip('/')}/v1/chat/completions"

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        # OpenAI format: choices[0].message
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})

        # Normalize tool_calls format
        tool_calls = msg.get("tool_calls", [])
        normalized_calls = []
        for tc in tool_calls:
            fn = tc.get("function", {})
            args = fn.get("arguments", "")
            # vLLM returns arguments as a JSON string; parse it
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except (json.JSONDecodeError, ValueError):
                    args = {}
            normalized_calls.append({
                "function": {
                    "name": fn.get("name", ""),
                    "arguments": args,
                },
            })

        return {
            "message": {
                "role": msg.get("role", "assistant"),
                "content": msg.get("content", ""),
                "tool_calls": normalized_calls if normalized_calls else [],
            }
        }
    except Exception as e:
        print(f"  WARN: LLM chat failed: {e}", file=sys.stderr)
        return None
