"""
Fix doc_ids in MacBERTh results by removing .xml extension
"""
import argparse
import json
from pathlib import Path

# NOTE: the raw MacBERTh prediction file was NOT archived in this repository.
# Place your copy at the default path below or pass explicit paths.
_MACBERTH_DIR = (Path(__file__).resolve().parents[1] / "results" / "predictions"
                 / "macberth_gold_eval")
DEFAULT_INPUT = _MACBERTH_DIR / "macberth_gold_results_20251210_170140.json"
DEFAULT_OUTPUT = _MACBERTH_DIR / "macberth_gold_results_20251210_170140_fixed.json"

parser = argparse.ArgumentParser(description="Strip .xml from doc_ids in MacBERTh results")
parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT,
                    help=f"Raw MacBERTh results JSON (default: {DEFAULT_INPUT})")
parser.add_argument("output", nargs="?", type=Path, default=None,
                    help="Output path (default: <input stem>_fixed.json alongside input)")
args = parser.parse_args()

input_file = args.input
output_file = args.output if args.output else input_file.with_name(input_file.stem + "_fixed.json")

if not input_file.exists():
    raise SystemExit(
        f"ERROR: MacBERTh results file not found: {input_file}\n"
        "This prediction file was not archived in this repository; "
        "place your copy at that path or pass one explicitly."
    )

with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Remove .xml extension from all doc_ids
for doc in data:
    if doc['doc_id'].endswith('.xml'):
        doc['doc_id'] = doc['doc_id'][:-4]

# Save fixed version
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Fixed {len(data)} documents")
print(f"Saved to: {output_file}")
