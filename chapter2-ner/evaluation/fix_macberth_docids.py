"""
Fix doc_ids in MacBERTh results by removing .xml extension
"""
import json

# Load MacBERTh results
input_file = r"Z:\NER\macberth_gold_eval\macberth_gold_results_20251210_170140.json"
output_file = r"Z:\NER\macberth_gold_eval\macberth_gold_results_20251210_170140_fixed.json"

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
