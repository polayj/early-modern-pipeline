# Entity Annotation Guidelines
## Detailed Rules for Manual NER

---

## 1. PERSON (PER)

### What to Tag:
- Full names: "Sir Isaac Newton", "George Butcher"
- Partial names with titles: "Mr. William Shakespeare", "Captain Cole"
- Surnames alone when clearly referencing individuals: "Labar"
- Historical figures: "King James I", "Prince Robert"
- Groups of people by role: "Planters", "Inhabitants" (when specific)

### What NOT to Tag:
- Generic references: "people", "men", "women" (unless specific group)
- Possessive adjectives: "French" in "French traders" (tag as MISC instead)

### Examples:
✓ "Sir Isaac Newton published his Philosophiæ"
✓ "Master George Butcher of Christmasse street"
✓ "Thomas Jefferson was the principal author"

---

## 2. LOCATION (LOC)

### What to Tag:
- Countries: "England", "France", "Spain", "Holland"
- Colonies/Regions: "Jamaica", "Barbados", "New-England", "West Indies"
- Cities/Towns: "London", "Bristol", "Philadelphia", "Martinico"
- Geographic features: "Gulf of Florida", "Windward Passage"
- Named plantations or estates (when clearly places)
- "Colonies" when referring to geographic entities

### What NOT to Tag:
- Directional references: "the Northern part" (unless proper name "Northern Colonies")
- Generic: "the City", "the Island" (unless clearly specific place)

### Compound Cases:
- "British Sugar-Colonies" → Tag "British" as MISC, "Sugar" as COMMODITY (if clear), "Colonies" as LOC
- "French Sugar-Colonies" → Similar breakdown

### Examples:
✓ "trade from Jamaica to London"
✓ "the Island of Barbados"
✓ "New-England and other Parts of the Continent"

---

## 3. ORGANIZATION (ORG)

### What to Tag:
- Trading companies: "East-India-Company"
- Government bodies: "Continental Congress", "Parliament", "The Queen"
- Military units: "Prince Robert's Army"
- Formal institutions: "The Church", "Assembly"
- Named ships/vessels (as organizational entities)

### What NOT to Tag:
- Generic references: "the company", "the government" (unless clearly specific)
- Informal groups: "Malignants", "Chavaliers" (use MISC)

### Examples:
✓ "the East-India-Company established trading posts"
✓ "the Continental Congress adopted the Declaration"

---

## 4. COMMODITY (COMMODITY) ⭐ PRIMARY FOCUS

### What to Tag - Agricultural/Raw Trade Goods:

**Major Commodities:**
- Sugar (all forms: "sugar", "sugars")
- Rum
- Molasses/Molosses
- Tobacco
- Cotton
- Indigo
- Coffee
- Cacao/Chocolate

**Spices & Flavorings:**
- Ginger
- Pepper
- Nutmeg
- Mace
- Cinnamon
- Cloves
- Coriander

**Food Commodities:**
- Salt
- Vinegar
- Lemon/Lemons
- Any raw ingredient mentioned in recipes

**Other Trade Goods:**
- Lumber
- Cattle (when traded)
- Provisions (when specific)

### Context Matters:
- "sugar plantations" → "sugar" is COMMODITY
- "sugar bowl" → "sugar" is COMMODITY
- "the sugar trade" → "sugar" is COMMODITY

### Examples:
✓ "twelve hundred pounds of refined sugar"
✓ "great Quantities of Rum"
✓ "Molosses being clear Profit"
✓ "Cotton, Tobacco, and Indigo"
✓ "season them with Salt, Nutmeg, Mace and Pepper"

---

## 5. PRODUCT (PRODUCT)

### What to Tag - Processed/Manufactured Goods:

**Sugar Products:**
- Muscavado (semi-refined sugar)
- Sugar-candy
- Refined sugar
- Clayed sugar
- Sugar royal
- White sugar
- Brown sugar
- Sucre tappe

**Distilled Products:**
- Spirits
- Brandy
- French Brandy
- Inflammable spirit

**Other Processed:**
- Vinous liquors
- Melasses (when referring to product, not raw)

### Distinction from COMMODITY:
- COMMODITY = raw material or basic trade good
- PRODUCT = manufactured/processed version

### Examples:
✓ "Sugar-candy is made from the muscavado"
✓ "refined sugar yield only five hundred"
✓ "inflammable Spirit by distillation"

---

## 6. TRADE_TERM (TRADE)

### What to Tag:

**Economic Terms:**
- Plantations
- Cargoes
- Manufactures
- Exports/Imports
- Navigation
- Duties
- Taxes/Excise
- Trade
- Commerce

**Commercial Units:**
- Hogsheads
- Barrels
- Tons (when trade unit)

**Business Concepts:**
- Monopoly
- Market
- Consumption
- Profit
- Advantage
- Stock

**Only tag when used in commercial/trade context**

### Examples:
✓ "the Sugar-Colonies and their Plantations"
✓ "Cargoes sold there"
✓ "Duties of Four and a half per Cent"
✓ "the African Trade"

---

## 7. DATE (DATE)

### What to Tag:
- Specific years: "1687", "1776"
- Full dates: "July 4, 1776", "June the 7th. 1692"
- Relative dates: "Tuesday night", "the last yeere"
- Periods: "from 1681, to 1737"
- Temporal phrases: "in the year 1848"

### Examples:
✓ "In the year 1687, Sir Isaac Newton"
✓ "from 1681, to 1737, inclusive"
✓ "on July 4, 1776"

---

## 8. CURRENCY (CURRENCY)

### What to Tag:
- British currency: "pounds", "shillings", "pence"
- Amounts: "twelve hundred pounds", "Five Shillings"
- Percentages when monetary: "Four and a half per Cent"
- Currency symbols with amounts

### Context:
- "pound of sugar" → QUANTITY, not CURRENCY
- "hundred pounds" (money) → CURRENCY
- "pound of French-barley" → QUANTITY

### Examples:
✓ "twelve hundred pounds of refined sugar yield"
✓ "Duty of Four and a half per Cent"
✓ "Five Shillings per Cent"

---

## 9. QUANTITY (QUANTITY)

### What to Tag:
- Weights: "twelve hundred pounds", "a quarter of a pound"
- Volumes: "a quart of White wine", "a good handful"
- Counts: "five hundred and forty-six", "Nine Thousand"
- Measurements: "upwards of Nine Thousand well-disciplin'd Men"

### Include:
- Numbers with units
- Descriptive amounts: "a good handful", "some slices"

### Examples:
✓ "twelve hundred pounds of refined sugar"
✓ "five hundred and forty-six of sugar royal"
✓ "a quarter of a pound of French-barley"
✓ "a good handful of Sweet Herbs"

---

## 10. EVENT (EVENT)

### What to Tag:
- Wars: "War with France", "American Revolution"
- Battles: "Massacre of France"
- Natural disasters: "earthquake in Jamaica"
- Historical occurrences: "Declaration of Independence"
- Plots/conspiracies: "the late barbarous and bloody plot"

### Examples:
✓ "in Case of a War with France"
✓ "the late earthquake in Jamaica, June the 7th. 1692"
✓ "a most hellish, cruell, and bloudy plot"

---

## 11. MISCELLANEOUS (MISC)

### What to Tag:
- Nationalities as adjectives: "French", "British", "Dutch", "Spanish"
- Ethnic groups: "Negro", "Indian"
- Languages: "French language"
- Ship names
- Book/document titles
- Other named entities not fitting categories above

### Examples:
✓ "The French prepare, in imitation"
✓ "British Manufactures"
✓ "Dutch traders"

---

## Special Annotation Rules

### Overlapping Entities:
When a phrase contains multiple entity types, tag each:
- "British Sugar-Colonies" → [British: MISC] [Sugar: COMMODITY] [Colonies: LOC]
- "French-barley" → [French: MISC] [barley: COMMODITY]

### Confidence Levels:
Mark confidence for each entity:
- **high:** Clearly identifiable, no ambiguity
- **medium:** Likely correct but some uncertainty
- **low:** Educated guess based on context

### OCR Errors:
Tag as written, note correction in context field:
- "Park" (should be "Pork") → Tag as written, note: "likely 'Pork' (meat)"

### Historical Spelling:
Tag exactly as appears:
- "Molosses" (not modern "Molasses")
- "souce" (not "souse")

---

## Priority Entities

Given BERT's failures, **prioritize thorough tagging of:**

1. **COMMODITY** - This is what BERT completely missed
2. **PRODUCT** - Also missed
3. **TRADE_TERM** - Mostly missed
4. **QUANTITY/CURRENCY** - Never attempted

Then tag the standard entities (PER, LOC, ORG, MISC) for completeness.

---

## Context Field

Always include surrounding text (±20 chars) in the context field to verify:
```json
{
  "text": "sugar",
  "context": "...hundred pounds of refined sugar yield only five..."
}
```

This helps verify annotations and understand entity usage.

---

## Document Notes

At the end of each document annotation, include:
- Document type (trade_policy, recipe, technical, etc.)
- Overall observations
- Notable patterns
- Challenges encountered
- Estimated confidence in annotations

This metadata helps evaluate annotation quality and understand document characteristics.
