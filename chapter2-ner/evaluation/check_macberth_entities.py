import json

with open(r"Z:\NER\macberth_gold_eval\macberth_gold_results_20251210_170140_fixed.json", 'r', encoding='utf-8') as f:
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
