import argparse
import json
from pathlib import Path

# NOTE: the MacBERTh prediction file was NOT archived in this repository.
# Place your copy at the default path below or pass an explicit path.
DEFAULT_INPUT = (Path(__file__).resolve().parents[1] / "results" / "predictions"
                 / "macberth_gold_eval" / "macberth_gold_results_20251210_170140_fixed.json")

parser = argparse.ArgumentParser(description="Count entity types in MacBERTh results")
parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT,
                    help=f"MacBERTh results JSON (default: {DEFAULT_INPUT})")
args = parser.parse_args()

if not args.input.exists():
    raise SystemExit(
        f"ERROR: MacBERTh results file not found: {args.input}\n"
        "This prediction file was not archived in this repository; "
        "place your copy at that path or pass one explicitly."
    )

with open(args.input, 'r', encoding='utf-8') as f:
    data = json.load(f)

total = sum(len(d['entities']) for d in data)
commodity = sum(len([e for e in d['entities'] if e['label']=='COMMODITY']) for d in data)
toponym = sum(len([e for e in d['entities'] if e['label']=='TOPONYM']) for d in data)
person = sum(len([e for e in d['entities'] if e['label']=='PERSON']) for d in data)
org = sum(len([e for e in d['entities'] if e['label']=='ORGANIZATION']) for d in data)

print(f"Total entities: {total}")
print(f"COMMODITY: {commodity}")
print(f"TOPONYM: {toponym}")
print(f"PERSON: {person}")
print(f"ORGANIZATION: {org}")
print()
print(f"PERSON+ORG (not in gold): {person + org} ({(person+org)/total*100:.1f}%)")
