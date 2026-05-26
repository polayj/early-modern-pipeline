# Caribbean Commodity Trade NER Project
## Manual Annotation by Claude (Domain Expert)

**Start Date:** November 5, 2025
**Corpus:** 100 Early Modern English documents (1614-1807)
**Source:** Z:/Corpus/Corpus_Gold/page/*.xml (PAGE XML format from Transkribus)
**Domain:** Caribbean commodity trade, colonial economics, recipes, manufacturing

---

## Project Goal

Create high-quality "gold standard" Named Entity Recognition annotations for comparison with:
1. Traditional BERT NER models (already completed)
2. Zero-shot NER (GLiNER)
3. LLM-based NER (this annotation)

This will be used in an academic paper demonstrating different NER approaches for Early Modern English historical documents.

---

## Processing Schedule

**10 documents per day × 10 days = 100 documents**

- **Batch 01:** Documents 1-10
- **Batch 02:** Documents 11-20
- **Batch 03:** Documents 21-30
- **Batch 04:** Documents 31-40
- **Batch 05:** Documents 41-50
- **Batch 06:** Documents 51-60
- **Batch 07:** Documents 61-70
- **Batch 08:** Documents 71-80
- **Batch 09:** Documents 81-90
- **Batch 10:** Documents 91-100

---

## Entity Types to Annotate

### 1. **PERSON** (PER)
Individual names, titles
- Examples: Sir Isaac Newton, Mr. William Shakespeare, Captain Cole, George Butcher

### 2. **LOCATION** (LOC)
Places, colonies, regions, countries
- Examples: Jamaica, London, New-England, Martinico, British Sugar-Colonies, West Indies, Barbados

### 3. **ORGANIZATION** (ORG)
Companies, institutions, governmental bodies
- Examples: East-India-Company, Continental Congress, The Queen, Parliament

### 4. **COMMODITY** (COMMODITY) ⭐ KEY ENTITY
Trade goods, raw materials, agricultural products
- Examples: sugar, rum, tobacco, cotton, molasses, indigo, coffee, cacao, ginger, pepper, spices

### 5. **PRODUCT** (PRODUCT)
Manufactured/processed goods derived from commodities
- Examples: muscavado, sugar-candy, refined sugar, spirits, brandy, clayed sugar, sugar royal

### 6. **TRADE_TERM** (TRADE)
Economic/commercial terminology specific to colonial trade
- Examples: plantations, cargoes, duties, manufactures, exports, navigation, hogsheads

### 7. **DATE** (DATE)
Temporal references
- Examples: 1687, July 4 1776, Tuesday night, the last yeere

### 8. **CURRENCY** (CURRENCY)
Money, prices, financial amounts
- Examples: pounds, shillings, pence, Four and a half per Cent, twelve hundred pounds

### 9. **QUANTITY** (QUANTITY)
Measurements, weights, amounts
- Examples: twelve hundred pounds, five hundred and forty-six, a good handful, a quarter of a pound

### 10. **EVENT** (EVENT)
Historical events, wars, significant occurrences
- Examples: American Revolution, War with France, Massacre of France, earthquake in Jamaica

### 11. **MISCELLANEOUS** (MISC)
Other significant entities not fitting above categories
- Nationalities: French, British, Dutch, Spanish
- Ships, vessels
- Other notable items

---

## Document Types in Corpus

1. **Trade Policy Documents** - Economic arguments, legislation
2. **Recipe/Cookbook Pages** - Food preparation, ingredients
3. **Technical Manufacturing** - Sugar refining, distillation processes
4. **Economic Commentary** - Prices, market analysis
5. **Legal/Administrative** - Laws, regulations, duties
6. **Historical Narratives** - Events, descriptions
7. **Scientific/Natural History** - Botanical descriptions

---

## Special Considerations for Early Modern English

### Language Features:
- Archaic spellings: "rowl" (roll), "souce" (souse), "gar-nishing" (garnishing)
- Long s: ſ (may appear in OCR)
- Inconsistent capitalization
- Period-specific terminology

### OCR Issues:
- Potential errors from scanning old documents
- Broken words, misreads
- Use context to infer correct entity despite OCR errors

### Compound Terms:
- "French Sugar-Colonies" - tag as multiple entities if appropriate
- "East-India-Company" - single organization
- "sugar-candy" - single product
- "Horse-raddish" - commodity/ingredient

---

## Annotation Principles

1. **Context is Key:** Use your understanding of 17th-18th century Caribbean trade
2. **Be Inclusive:** When uncertain, tag rather than miss (we want comprehensive coverage)
3. **Preserve Original Text:** Tag exactly as it appears, including OCR errors
4. **Overlapping Entities:** Allow (e.g., "British Sugar-Colonies" = LOC + COMMODITY)
5. **Compound Entities:** Tag the full phrase, note components

---

## Output Format

JSON file for each document:
```json
{
  "filename": "document_name",
  "text": "full extracted text",
  "entities": [
    {
      "text": "sugar",
      "entity_type": "COMMODITY",
      "start": 100,
      "end": 105,
      "context": "surrounding text for verification",
      "confidence": "high/medium/low"
    }
  ],
  "entity_count": 25,
  "document_type": "trade_policy",
  "notes": "any observations"
}
```

---

## Daily Workflow

### When Starting Each Day:

1. Read this file (PROJECT_CONTEXT.md)
2. Read ENTITY_GUIDELINES.md for detailed rules
3. Check PROGRESS.json to see which batch to process
4. Process 10 documents:
   - Extract text from XML
   - Identify all entities
   - Create comprehensive annotations
   - Save to appropriate batch folder
5. Update PROGRESS.json

### Quality Checks:

- Ensure commodities are thoroughly tagged (this is what BERT missed!)
- Check for trade-specific terminology
- Capture quantities, currencies, dates mentioned
- Note any interesting patterns or challenges

---

## Success Metrics

**Goal:** Annotate significantly more entities than BERT models

- BERT Model 1: 1,186 entities total (11.86 per doc)
- BERT Model 2: 1,305 entities total (13.05 per doc)
- **Target:** 2,000+ entities (20+ per doc) with better domain coverage

**Key Improvement Areas:**
- Commodities: 0-1% → 15-20% of entities
- Trade terms: <5% → 10-15% of entities
- Quantities/Currencies: 0% → 5-10% of entities

---

## Reminder About Document Ordering

Documents are alphabetically ordered by filename in:
Z:/Corpus/Corpus_Gold/page/

List generated by: `ls Z:/Corpus/Corpus_Gold/page/*.xml | sort`

First 10 documents (Batch 01):
1. Anonymous - 1643 - A briefe relation... (plot against Bristol)
2. Anonymous - 1660 - By the merchants owners of ships...
3. Anonymous - 1675 - Every woman her own midwife...
4. Anonymous - 1675 - The Accomplish'd lady's delight...
5. Anonymous - 1675 - The gentlewomans cabinet unlocked...
6. Anonymous - 1676 - Wonderful news from Bristol...
7. Anonymous - 1677 - The Case of His Majesties Plantations...
8. Anonymous - 1680 - The Interest of the three kingdoms...
9. Anonymous - 1682 - A letter from Jamaica...
10. Anonymous - 1690 - The compleat English and French cook...

---

## Notes for Future Sessions

When you return each day, simply say:
**"Continue with today's NER batch"**

Claude will:
1. Read this context
2. Check progress
3. Process next 10 documents
4. Update status
5. Report completion

---

**Remember:** Your domain expertise in Early Modern Caribbean trade history is the key advantage over automated systems. Use your contextual understanding to provide rich, accurate annotations that capture the economic and historical significance of these documents.
