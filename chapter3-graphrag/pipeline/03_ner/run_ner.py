#!/usr/bin/env python3
"""
03_ner/run_ner.py — EarlyModernNER pipeline runner (debug/diagnostic version)
"""

import argparse
import gc
import json
import os
import sys
import time
from pathlib import Path

import psutil
import torch
from tqdm import tqdm

ENTITY_TYPES = ["TOPONYM", "COMMODITY", "PERSON", "ORGANIZATION"]


_log_file = None

def mem_report(label: str):
    rss = psutil.Process(os.getpid()).memory_info().rss / 1e9
    ca = torch.cuda.memory_allocated() / 1e9 if torch.cuda.is_available() else 0
    cr = torch.cuda.memory_reserved() / 1e9 if torch.cuda.is_available() else 0
    msg = f"  [MEM] {label}: RSS={rss:.1f}GB  CUDA_alloc={ca:.1f}GB  CUDA_reserved={cr:.1f}GB"
    print(msg, flush=True)
    if _log_file:
        _log_file.write(msg + "\n")
        _log_file.flush()


def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            for sep in (". ", "\n\n", "\n"):
                pos = text.rfind(sep, end - 100, end)
                if pos != -1:
                    end = pos + len(sep)
                    break
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def load_base_model(device: str, use_bnb: bool = True):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    from earlymodernner.pipeline import (
        DEFAULT_BASE_MODEL,
        DEFAULT_ADAPTER_NAMES,
        get_adapter_path,
    )

    mem_report("before model load")
    print(f"Loading base model: {DEFAULT_BASE_MODEL}")

    if use_bnb:
        try:
            from transformers import BitsAndBytesConfig
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
            model = AutoModelForCausalLM.from_pretrained(
                DEFAULT_BASE_MODEL,
                quantization_config=bnb_config,
                device_map="auto" if device == "cuda" else device,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )
            mem_gb = model.get_memory_footprint() / 1e9
            if mem_gb > 6:
                raise RuntimeError(f"4-bit model is {mem_gb:.1f}GB")
            print(f"  Base model loaded: {mem_gb:.1f}GB (4-bit)")
        except Exception as e:
            print(f"  4-bit failed ({e}), falling back to bf16...")
            use_bnb = False

    if not use_bnb:
        model = AutoModelForCausalLM.from_pretrained(
            DEFAULT_BASE_MODEL,
            torch_dtype=torch.bfloat16,
            device_map="auto" if device == "cuda" else device,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
        print(f"  Base model loaded: {model.get_memory_footprint()/1e9:.1f}GB (bf16)")

    mem_report("after base model load")

    tokenizer = AutoTokenizer.from_pretrained(DEFAULT_BASE_MODEL, trust_remote_code=True)
    mem_report("after tokenizer load")

    first_type = ENTITY_TYPES[0]
    first_adapter_path = str(get_adapter_path(DEFAULT_ADAPTER_NAMES[first_type]))
    print(f"  Loading adapter: {first_type}")
    model = PeftModel.from_pretrained(model, first_adapter_path, adapter_name=first_type)
    mem_report(f"after {first_type} adapter")

    for entity_type in ENTITY_TYPES[1:]:
        adapter_path = str(get_adapter_path(DEFAULT_ADAPTER_NAMES[entity_type]))
        print(f"  Loading adapter: {entity_type}")
        model.load_adapter(adapter_path, adapter_name=entity_type)
        mem_report(f"after {entity_type} adapter")

    model.eval()
    print(f"  All adapters loaded. Total footprint: {model.get_memory_footprint()/1e9:.1f}GB")
    mem_report("model ready")
    return model, tokenizer


def extract_for_type(text, entity_type, model, tokenizer, chunk_size):
    from earlymodernner.pipeline import build_prompt, extract_json_from_output, normalize_entities

    mem_report(f"{entity_type} — before set_adapter")
    model.set_adapter(entity_type)
    mem_report(f"{entity_type} — after set_adapter")

    chunks = chunk_text(text, chunk_size=chunk_size)
    print(f"  [{entity_type}] {len(chunks)} chunks", flush=True)
    mem_report(f"{entity_type} — after chunking")

    seen = set()
    entities = []

    for i, chunk in enumerate(chunks):
        prompt = build_prompt(chunk, entity_type, tokenizer)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        if i == 0:
            mem_report(f"{entity_type} — before FIRST generate()")

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,
                top_p=None,
                top_k=None,
                temperature=None,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )

        if i == 0:
            mem_report(f"{entity_type} — after FIRST generate()")

        generated = tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )

        del inputs, outputs
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        if i == 0:
            mem_report(f"{entity_type} — after FIRST cleanup")

        # Log every 10 chunks for first 50, then every 100
        if i < 50 and i % 10 == 0:
            mem_report(f"{entity_type} — chunk {i}/{len(chunks)}")
        elif i % 100 == 0:
            mem_report(f"{entity_type} — chunk {i}/{len(chunks)}")

        for e in normalize_entities(extract_json_from_output(generated).get("entities", []), entity_type, chunk):
            key = e["text"].lower().strip()
            if key not in seen:
                seen.add(key)
                entities.append(e)

        del generated
        del chunk

    return entities


def process_file(md_path, per_doc_dir, chunk_size, model, tokenizer):
    doc_id = md_path.stem
    per_doc_path = per_doc_dir / f"{doc_id}.jsonl"

    if per_doc_path.exists() and per_doc_path.stat().st_size > 0:
        return [
            json.loads(line) for line in per_doc_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    mem_report(f"file '{doc_id}' — before read")
    text = md_path.read_text(encoding="utf-8", errors="replace")
    print(f"  File size: {len(text)} chars ({len(text)/1e6:.1f}MB)", flush=True)
    mem_report(f"file '{doc_id}' — after read")

    if not text.strip():
        per_doc_path.write_text("")
        return []

    raw = []
    for entity_type in ENTITY_TYPES:
        raw.extend(extract_for_type(text, entity_type, model, tokenizer, chunk_size))
        mem_report(f"file '{doc_id}' — after {entity_type} complete")

    claimed = set()
    deduped = []
    for e in raw:
        key = e["text"].lower().strip().replace("-", " ")
        if not any(key == c or key in c for c in claimed):
            deduped.append({
                "doc_id": doc_id,
                "entity_text": e["text"],
                "entity_type": e["type"],
            })
            claimed.add(key)

    with open(per_doc_path, "w", encoding="utf-8") as f:
        for e in deduped:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    del text
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    mem_report(f"file '{doc_id}' — done + cleanup")

    return deduped


def update_counts(entities, type_counts):
    for e in entities:
        etype = e.get("entity_type", "UNKNOWN")
        type_counts[etype] = type_counts.get(etype, 0) + 1
    return len(entities)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="output/ocr_md")
    parser.add_argument("--output", default="output/ner_output")
    parser.add_argument("--chunk-size", type=int, default=2000)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--no-bnb", action="store_true",
                        help="Skip bitsandbytes 4-bit, use bf16 instead")
    parser.add_argument("--log", type=str, default=None,
                        help="Write diagnostic log directly to this file (bypass tee)")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--done-sentinel", default="output/ocr_complete.sentinel")
    parser.add_argument("--poll-interval", type=int, default=30)
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    per_doc_dir = output_dir / "per_doc"
    sentinel = Path(args.done_sentinel)
    aggregate_path = output_dir / "entities.jsonl"

    output_dir.mkdir(parents=True, exist_ok=True)
    per_doc_dir.mkdir(parents=True, exist_ok=True)

    if args.watch and not input_dir.exists():
        print(f"Waiting for '{input_dir}'...")
        while not input_dir.exists():
            time.sleep(args.poll_interval)
    elif not input_dir.exists():
        print(f"ERROR: '{input_dir}' not found.", file=sys.stderr)
        sys.exit(1)

    global _log_file
    if args.log:
        _log_file = open(args.log, "w")
        print(f"Logging to: {args.log}")

    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Device: {args.device}")
    print(f"BnB:    {'disabled' if args.no_bnb else 'enabled'}")
    mem_report("startup")

    model, tokenizer = load_base_model(args.device, use_bnb=not args.no_bnb)

    # ── Warmup: single tiny generate() call to trigger any JIT compilation ──
    print("\n── Warmup: single generate() call to detect JIT overhead ──", flush=True)
    mem_report("before warmup")
    from earlymodernner.pipeline import build_prompt
    _warmup_prompt = build_prompt("Test document.", "TOPONYM", tokenizer)
    _warmup_inputs = tokenizer(_warmup_prompt, return_tensors="pt").to(model.device)
    mem_report("after warmup tokenize")
    model.set_adapter("TOPONYM")
    with torch.no_grad():
        _warmup_out = model.generate(**_warmup_inputs, max_new_tokens=16)
    mem_report("after warmup generate (16 tokens)")
    del _warmup_inputs, _warmup_out, _warmup_prompt
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    mem_report("after warmup cleanup")
    print("── Warmup complete ──\n", flush=True)

    processed_stems = {p.stem for p in per_doc_dir.glob("*.jsonl")}
    type_counts = {}
    total_entities = 0

    if processed_stems:
        print(f"Resuming: {len(processed_stems)} docs done.")

    # Rebuild aggregate
    if processed_stems:
        with open(aggregate_path, "w", encoding="utf-8") as agg:
            for p in per_doc_dir.glob("*.jsonl"):
                for line in p.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        agg.write(line + "\n")
                        try:
                            update_counts([json.loads(line)], type_counts)
                            total_entities += 1
                        except json.JSONDecodeError:
                            pass

    md_files = sorted(f for f in input_dir.glob("*.md") if f.stem not in processed_stems)
    if args.limit > 0:
        md_files = md_files[:args.limit]

    if md_files:
        print(f"\nProcessing {len(md_files)} files...")
        with open(aggregate_path, "a", encoding="utf-8") as agg:
            for md_path in tqdm(md_files, desc="NER"):
                entities = process_file(md_path, per_doc_dir, args.chunk_size, model, tokenizer)
                processed_stems.add(md_path.stem)
                for e in entities:
                    agg.write(json.dumps(e, ensure_ascii=False) + "\n")
                total_entities += update_counts(entities, type_counts)
                agg.flush()
    else:
        print("No new files to process.")

    if args.watch:
        print(f"\nWatch mode: polling every {args.poll_interval}s...")
        with open(aggregate_path, "a", encoding="utf-8") as agg:
            while True:
                time.sleep(args.poll_interval)
                new_files = sorted(f for f in input_dir.glob("*.md") if f.stem not in processed_stems)
                if new_files:
                    for md_path in new_files:
                        entities = process_file(md_path, per_doc_dir, args.chunk_size, model, tokenizer)
                        processed_stems.add(md_path.stem)
                        for e in entities:
                            agg.write(json.dumps(e, ensure_ascii=False) + "\n")
                        total_entities += update_counts(entities, type_counts)
                        print(f"  [{len(processed_stems)}] {md_path.stem} ({len(entities)} entities)")
                    agg.flush()
                if sentinel.exists() and not new_files:
                    print("Sentinel found, queue empty — done.")
                    break

    Path("output/ner_complete.sentinel").write_text(
        f"NER complete. {len(processed_stems)} docs, {total_entities} entities.\n"
    )

    print(f"\n── NER Summary ──────────────────────────────────────")
    print(f"  Docs processed: {len(processed_stems)}")
    print(f"  Total entities: {total_entities}")
    for etype in ENTITY_TYPES:
        if etype in type_counts:
            print(f"    {etype}: {type_counts[etype]}")
    print(f"  Aggregate: {aggregate_path}")
    print("─────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
