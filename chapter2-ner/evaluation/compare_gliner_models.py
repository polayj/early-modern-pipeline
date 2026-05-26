"""
Compare different GLiNER models for zero-shot NER on Caribbean commodity trade documents
Tests 5 models: GLiNER Large v2.1, GLiNER-X Base, NuNER Zero, NuNER v2.0, GLiNER Large v2

Findings:
- Truncation is happening INSIDE GLiNER library (gliner/data_processing/processor.py)
- NOT in our code - we pass full text
- GLiNER models have a max_len of 384 tokens by default
- Text extraction from recipe document is working correctly (2,196 chars)
"""

from gliner import GLiNER
import xml.etree.ElementTree as ET
import json
import time

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

# Define entity labels optimized for Caribbean commodity trade
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

# Models to test
models_to_test = [
    {
        "name": "GLiNER Large v2.1",
        "model_id": "urchade/gliner_large-v2.1",
        "description": "Updated large model (2024)"
    },
    {
        "name": "GLiNER-X Base",
        "model_id": "knowledgator/gliner-x-base",
        "description": "Extended GLiNER base model optimized for diverse domains"
    },
    {
        "name": "NuNER Zero",
        "model_id": "numind/NuNER_Zero",
        "description": "NuMind's zero-shot NER model (original)"
    },
    {
        "name": "NuNER v2.0",
        "model_id": "numind/NuNER-v2.0",
        "description": "NuMind's zero-shot NER model v2.0 (latest)"
    },
    {
        "name": "GLiNER Large v2 (original)",
        "model_id": "urchade/gliner_largev2",
        "description": "Original large model (baseline)"
    }
]

# Test files - use a mix of document types
test_files = [
    {
        "path": "Z:/Corpus/Corpus_Gold/page/Anonymous - 1643 - A briefe relation, abstracted out of severall letters, of a most hellish, cruell, and bloudy plot ag_page_3.xml",
        "type": "political_narrative",
        "manual_entities": 56  # From our manual annotation
    },
    {
        "path": "Z:/Corpus/Corpus_Gold/page/Anonymous - 1690 - The compleat English and French cook describing the best and newest ways of ordering and dressing al_page_122.xml",
        "type": "recipe",
        "expected_commodities": True
    }
]

results = []

print("="*80)
print("GLINER MODEL COMPARISON")
print("="*80)

for model_info in models_to_test:
    print(f"\n{'='*80}")
    print(f"Testing: {model_info['name']}")
    print(f"Model ID: {model_info['model_id']}")
    print(f"Description: {model_info['description']}")
    print(f"{'='*80}")

    try:
        # Load model
        print(f"Loading model...")
        start_load = time.time()
        model = GLiNER.from_pretrained(model_info['model_id'])

        # Increase max_len to handle full documents (default is 384)
        original_max_len = model.config.max_len
        model.config.max_len = 1024  # Increase to 1024 tokens (~4000 characters)

        load_time = time.time() - start_load
        print(f"[OK] Model loaded in {load_time:.2f}s")
        print(f"    Increased max_len from {original_max_len} to {model.config.max_len} tokens")

        model_results = {
            "model_name": model_info['name'],
            "model_id": model_info['model_id'],
            "load_time": load_time,
            "max_len": model.config.max_len,
            "documents": []
        }

        # Test on each document
        for test_file in test_files:
            print(f"\n  Processing: {test_file['type']} document")
            text = extract_text_from_page_xml(test_file['path'])
            print(f"    Text length: {len(text)} characters")
            print(f"    Text preview: {text[:100]}...")

            # Run NER with threshold=0.3 (keeping same as requested)
            start_ner = time.time()
            entities = model.predict_entities(text, entity_labels, threshold=0.3)
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

            # Debug: If we found 0 entities, show warning
            if len(entities) == 0:
                print(f"    [WARNING] No entities found! Text had {len(text)} chars")

            # Show breakdown of entity types found
            if len(entity_by_type) > 0:
                print(f"    Entity types: {', '.join([f'{k}({len(v)})' for k, v in entity_by_type.items()])}")

            # Show some commodity examples if found
            if commodity_count > 0:
                print(f"    Commodity examples: {', '.join(entity_by_type['commodity'][:5])}")

        results.append(model_results)

    except Exception as e:
        print(f"[ERROR] Error loading/testing model: {e}")
        results.append({
            "model_name": model_info['name'],
            "model_id": model_info['model_id'],
            "error": str(e)
        })

# Save detailed results
output_file = "Z:/NER/gliner_model_comparison.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

# Print summary comparison
print(f"\n\n{'='*80}")
print("SUMMARY COMPARISON")
print(f"{'='*80}\n")

print(f"{'Model':<30} {'Doc Type':<20} {'Total':<8} {'Commodities':<12} {'Products':<10}")
print("-" * 80)

for result in results:
    if 'error' in result:
        print(f"{result['model_name']:<30} ERROR: {result['error']}")
    else:
        for doc in result['documents']:
            print(f"{result['model_name']:<30} {doc['type']:<20} {doc['total_entities']:<8} {doc['commodities']:<12} {doc['products']:<10}")

print(f"\n\nDetailed results saved to: {output_file}")

# Show winner for commodity detection
print(f"\n{'='*80}")
print("COMMODITY DETECTION WINNER")
print(f"{'='*80}")

commodity_scores = {}
for result in results:
    if 'documents' in result:
        total_commodities = sum(doc['commodities'] + doc['products'] for doc in result['documents'])
        commodity_scores[result['model_name']] = total_commodities

if commodity_scores:
    winner = max(commodity_scores, key=commodity_scores.get)
    print(f"\n[WINNER] Best for commodities: {winner} ({commodity_scores[winner]} commodity/product entities)")
    print("\nAll models:")
    for model_name, score in sorted(commodity_scores.items(), key=lambda x: x[1], reverse=True):
        print(f"  {model_name}: {score} commodity/product entities")
