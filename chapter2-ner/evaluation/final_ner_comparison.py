"""
Final NER Model Comparison for Caribbean Commodity Trade Documents
Compares: GLiNER v2.1, GLiNER-X, NuNER Zero, and spaCy (transformer)
"""

from gliner import GLiNER
import spacy
import xml.etree.ElementTree as ET
import json
import time

spacy.prefer_gpu()
def extract_text_from_page_xml(filepath):
    """Extract text from PAGE XML format"""
    tree = ET.parse(filepath)
    root = tree.getroot()
    ns = {'page': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'}

    text_lines = []
    for text_line in root.findall('.//page:TextLine', ns):
        unicode_elem = text_line.find('.//page:Unicode', ns)
        if unicode_elem is not None and unicode_elem.text:
            text_lines.append(unicode_elem.text.strip())

    return ' '.join(text_lines)

# Entity labels for GLiNER models (zero-shot)
entity_labels = [
    "person",           # Individual names, titles
    "location",         # Places, colonies, regions, countries
    "organization",     # Companies, institutions, governmental bodies
    "commodity",        # Trade goods, raw materials (sugar, rum, tobacco, etc.)
    "product",          # Manufactured/processed goods (muscavado, refined sugar, etc.)
    "trade term",       # Economic/commercial terminology
    "date",             # Temporal references
    "currency",         # Money, prices, financial amounts
    "quantity",         # Measurements, weights, amounts
    "event",            # Historical events, wars
    "nationality"       # French, British, Dutch, Spanish, etc.
]

# spaCy entity mapping to our schema
SPACY_ENTITY_MAP = {
    'PERSON': 'person',
    'PER': 'person',
    'ORG': 'organization',
    'GPE': 'location',        # Geopolitical entity
    'LOC': 'location',
    'FAC': 'location',        # Facility
    'DATE': 'date',
    'TIME': 'date',
    'MONEY': 'currency',
    'PERCENT': 'currency',
    'QUANTITY': 'quantity',
    'CARDINAL': 'quantity',
    'ORDINAL': 'quantity',
    'EVENT': 'event',
    'PRODUCT': 'product',
    'NORP': 'nationality',    # Nationalities or religious/political groups
}

# Models to test
models_config = [
    {
        "type": "gliner",
        "name": "GLiNER Large v2.1",
        "model_id": "urchade/gliner_large-v2.1",
        "description": "Updated large GLiNER model (2024)"
    },
    {
        "type": "gliner",
        "name": "GLiNER-X Base",
        "model_id": "knowledgator/gliner-x-base",
        "description": "Extended GLiNER base model optimized for diverse domains"
    },
    {
        "type": "gliner",
        "name": "NuNER Zero",
        "model_id": "numind/NuNER_Zero",
        "description": "NuMind's zero-shot NER model"
    },
    {
        "type": "spacy",
        "name": "spaCy Transformer",
        "model_id": "en_core_web_trf",
        "description": "spaCy transformer-based NER (RoBERTa)"
    }
]

# Test files
test_files = [
    {
        "path": "Z:/Corpus/Corpus_Gold/page/Anonymous - 1643 - A briefe relation, abstracted out of severall letters, of a most hellish, cruell, and bloudy plot ag_page_3.xml",
        "type": "political_narrative",
        "manual_entities": 56
    },
    {
        "path": "Z:/Corpus/Corpus_Gold/page/Anonymous - 1690 - The compleat English and French cook describing the best and newest ways of ordering and dressing al_page_122.xml",
        "type": "recipe",
        "expected_commodities": True
    }
]

results = []

print("="*80)
print("FINAL NER MODEL COMPARISON")
print("="*80)

for model_config in models_config:
    print(f"\n{'='*80}")
    print(f"Testing: {model_config['name']}")
    print(f"Type: {model_config['type'].upper()}")
    print(f"Model ID: {model_config['model_id']}")
    print(f"{'='*80}")

    try:
        # Load model based on type
        print(f"Loading model...")
        start_load = time.time()

        if model_config['type'] == 'gliner':
            model = GLiNER.from_pretrained(model_config['model_id'])
            # Increase max_len from 384 to 1024
            original_max_len = model.config.max_len
            model.config.max_len = 1024
            print(f"[OK] GLiNER model loaded in {time.time() - start_load:.2f}s")
            print(f"    Increased max_len from {original_max_len} to {model.config.max_len} tokens")
        else:  # spacy
            model = spacy.load(model_config['model_id'])
            print(f"[OK] spaCy model loaded in {time.time() - start_load:.2f}s")

        model_results = {
            "model_name": model_config['name'],
            "model_type": model_config['type'],
            "model_id": model_config['model_id'],
            "load_time": time.time() - start_load,
            "documents": []
        }

        # Test on each document
        for test_file in test_files:
            print(f"\n  Processing: {test_file['type']} document")
            text = extract_text_from_page_xml(test_file['path'])
            print(f"    Text length: {len(text)} characters")

            # Run NER based on model type
            start_ner = time.time()

            if model_config['type'] == 'gliner':
                entities_raw = model.predict_entities(text, entity_labels, threshold=0.3)
                # Convert to standard format
                entities = [{
                    'text': e['text'],
                    'label': e['label'],
                    'start': e['start'],
                    'end': e['end']
                } for e in entities_raw]
            else:  # spacy
                doc = model(text)
                # Convert spaCy entities to our format
                entities = []
                for ent in doc.ents:
                    mapped_label = SPACY_ENTITY_MAP.get(ent.label_, 'misc')
                    entities.append({
                        'text': ent.text,
                        'label': mapped_label,
                        'start': ent.start_char,
                        'end': ent.end_char,
                        'original_label': ent.label_
                    })

            ner_time = time.time() - start_ner

            # Group by type
            entity_by_type = {}
            for entity in entities:
                entity_type = entity['label']
                if entity_type not in entity_by_type:
                    entity_by_type[entity_type] = []
                entity_by_type[entity_type].append(entity['text'])

            # Count commodities specifically
            commodity_count = len(entity_by_type.get('commodity', []))
            product_count = len(entity_by_type.get('product', []))

            doc_result = {
                "file": test_file['path'].split('/')[-1],
                "type": test_file['type'],
                "total_entities": len(entities),
                "commodities": commodity_count,
                "products": product_count,
                "entity_breakdown": {k: len(v) for k, v in entity_by_type.items()},
                "ner_time": ner_time
            }

            model_results['documents'].append(doc_result)

            print(f"    Entities found: {len(entities)}")
            print(f"    Commodities: {commodity_count}, Products: {product_count}")
            print(f"    Processing time: {ner_time:.2f}s")

            # Show entity type breakdown
            if len(entity_by_type) > 0:
                print(f"    Entity types: {', '.join([f'{k}({len(v)})' for k, v in sorted(entity_by_type.items())])}")
            else:
                print(f"    [WARNING] No entities found!")

            # Show commodity examples if found
            if commodity_count > 0:
                print(f"    Commodity examples: {', '.join(entity_by_type['commodity'][:5])}")

        results.append(model_results)

    except Exception as e:
        print(f"[ERROR] Error loading/testing model: {e}")
        import traceback
        traceback.print_exc()
        results.append({
            "model_name": model_config['name'],
            "model_type": model_config['type'],
            "model_id": model_config['model_id'],
            "error": str(e)
        })

# Save results
output_file = "Z:/NER/final_ner_comparison.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

# Print summary
print(f"\n\n{'='*80}")
print("SUMMARY COMPARISON")
print(f"{'='*80}\n")

print(f"{'Model':<25} {'Type':<10} {'Doc Type':<20} {'Total':<8} {'Comm':<6} {'Prod':<6}")
print("-" * 85)

for result in results:
    if 'error' in result:
        print(f"{result['model_name']:<25} ERROR: {result['error']}")
    else:
        for doc in result['documents']:
            model_type = result['model_type'].upper()
            print(f"{result['model_name']:<25} {model_type:<10} {doc['type']:<20} {doc['total_entities']:<8} {doc['commodities']:<6} {doc['products']:<6}")

# Show winner
print(f"\n\n{'='*80}")
print("OVERALL WINNER (Most entities detected)")
print(f"{'='*80}")

total_entities_by_model = {}
for result in results:
    if 'documents' in result:
        total = sum(doc['total_entities'] for doc in result['documents'])
        total_entities_by_model[result['model_name']] = total

if total_entities_by_model:
    winner = max(total_entities_by_model, key=total_entities_by_model.get)
    print(f"\n[WINNER] {winner}: {total_entities_by_model[winner]} total entities")
    print("\nAll models ranked:")
    for model_name, count in sorted(total_entities_by_model.items(), key=lambda x: x[1], reverse=True):
        print(f"  {model_name}: {count} entities")

print(f"\n\nDetailed results saved to: {output_file}")
