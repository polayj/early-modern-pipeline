"""Convert earlymodernner JSONL results to the standard evaluation format.

Input:  earlymodernner/_archive/testresults.jsonl  (JSONL, entities have text/type)
Output: earlymodernner_4cat/results_4cat_single_converted.json  (JSON list, entities have text/label/start/end)
"""

import json
import re
from pathlib import Path

INPUT = Path("/mnt/z/NER/earlymodernner/_archive/testresults.jsonl")
OUTPUT_DIR = Path("/mnt/z/NER/earlymodernner_4cat")
OUTPUT = OUTPUT_DIR / "results_4cat_single_converted.json"


def find_entity_offsets(text: str, entity_text: str, used_positions: set):
    """Find the first unused occurrence of entity_text in text."""
    start = 0
    while True:
        pos = text.find(entity_text, start)
        if pos == -1:
            break
        end = pos + len(entity_text)
        if pos not in used_positions:
            used_positions.add(pos)
            return pos, end
        start = pos + 1

    # Fallback: whitespace-normalised matching
    pattern = re.escape(entity_text)
    pattern = re.sub(r'\\\s+', r'\\s+', pattern)
    for m in re.finditer(pattern, text):
        if m.start() not in used_positions:
            used_positions.add(m.start())
            return m.start(), m.end()

    return None, None


def convert():
    docs = []
    with open(INPUT, 'r', encoding='utf-8') as f:
        for line in f:
            doc = json.loads(line.strip())
            text = doc['text']
            used = set()
            entities = []
            for i, ent in enumerate(doc.get('entities', []), 1):
                start, end = find_entity_offsets(text, ent['text'], used)
                entities.append({
                    'id': f'e{i}',
                    'text': ent['text'],
                    'label': ent['type'],  # type → label
                    'start': start,
                    'end': end,
                })
            # Filter out entities where we couldn't find offsets
            found = [e for e in entities if e['start'] is not None]
            missing = len(entities) - len(found)
            if missing:
                print(f"  [WARN] {doc['doc_id']}: {missing} entities without offsets")
            doc_out = {
                'doc_id': doc['doc_id'],
                'text': text,
                'entities': found,
            }
            docs.append(doc_out)

    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(docs, f, indent=2)

    total = sum(len(d['entities']) for d in docs)
    print(f"\n  Converted {len(docs)} documents, {total} entities")
    print(f"  Saved: {OUTPUT}")


if __name__ == '__main__':
    convert()
