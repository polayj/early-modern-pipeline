#!/usr/bin/env python3
"""
03_ner/normalizations.py
Spelling normalization dicts for entity linking.

IMPORTANT: These normalize spelling variants ONLY — they never collapse distinct
historical categories. "Brown sugar" and "white sugar" remain separate because
they were genuinely different commodities in the Early Modern Caribbean trade.
"""

# ── Toponym spelling normalization ────────────────────────────────────────────
# Maps OCR/import-record spelling variants to modern standard spellings.
# The standard form is what gets looked up in GeoNames/Wikidata.
TOPONYM_NORMALIZATIONS: dict[str, str] = {
    # Import record variants
    "mountserat": "Montserrat",
    "stkitts": "Saint Kitts",
    "st kitts": "Saint Kitts",
    "st. kitts": "Saint Kitts",
    "generalwi": "West Indies",
    "westindiesgeneral": "West Indies",
    "newengland": "New England",
    "new england": "New England",
    # Common OCR spelling variants from 17th-18th century docs
    "barbadoes": "Barbados",
    "barbada": "Barbados",
    "barbudo": "Barbuda",
    "jamaico": "Jamaica",
    "summerset": "Somerset",
    "somersett": "Somerset",
    "bristoll": "Bristol",
    "londone": "London",
    "hispaniola": "Hispaniola",
    "st. christophers": "Saint Kitts",
    "saint christophers": "Saint Kitts",
    "st christophers": "Saint Kitts",
    "st. christopher": "Saint Kitts",
    "saint christopher": "Saint Kitts",
    "nevis island": "Nevis",
    "isle of nevis": "Nevis",
    "tobagoe": "Tobago",
    "tobago": "Tobago",
    "trinidad": "Trinidad",
    "trinidado": "Trinidad",
    "bermudas": "Bermuda",
    "bermudoes": "Bermuda",
    "carolina": "Province of Carolina",
    "virgina": "Virginia",
    "virginia": "Virginia",
    "guiana": "Guiana",
    "guyana": "Guiana",
    "surinam": "Suriname",
    "suriname": "Suriname",
    "martinico": "Martinique",
    "martinique": "Martinique",
    "guadalupe": "Guadeloupe",
    "guadaloupe": "Guadeloupe",
    "guadeloupe": "Guadeloupe",
    "curacao": "Curacao",
    "st. domingue": "Saint-Domingue",
    "saint domingue": "Saint-Domingue",
    "porto rico": "Puerto Rico",
    "puerto rico": "Puerto Rico",
    "havanna": "Havana",
    "havana": "Havana",
    "carthagena": "Cartagena",
}

# ── Commodity spelling normalization ──────────────────────────────────────────
# Fixes spelling variants only — does NOT merge distinct commodity types.
# "Brown Sugar" and "White Sugar" remain separate entries.
COMMODITY_NORMALIZATIONS: dict[str, str] = {
    # Cochineal variants
    "cocheneal": "Cochineal",
    "cockeneal": "Cochineal",
    # Cocoa variants (keep subtypes separate)
    "cocoa nutts": "Cocoa Nuts",
    "cocoa past": "Cocoa Paste",
    "cocoa paster": "Cocoa Paste",
    "cocoa vaste? waste? (60)": "Cocoa Waste",
    "cocoa past paste? (62)": "Cocoa Paste",
    "cocoa past? last?": "Cocoa Paste",
    "chocolate cast/past/last": "Chocolate Paste",
    "chocolate past": "Chocolate Paste",
    # Cortex variants
    "cortex elatheria": "Cortex Elutheria",
    "cortex eletharia": "Cortex Elutheria",
    "cortex eletheria": "Cortex Elutheria",
    # Elephant teeth
    "elephants teeth": "Elephant Teeth",
    "elephant teeth": "Elephant Teeth",
    # Fustick/Fustic (same wood, different spellings)
    "fustick wood": "Fustic Wood",
    "wood, fustick": "Fustic Wood",
    "wood, fustick wood": "Fustic Wood",
    "wood, wood, fustick": "Fustic Wood",
    # Gum variants
    "gum arabeck": "Gum Arabic",
    "gum arabick": "Gum Arabic",
    "gum guiaci": "Gum Guaiacum",
    "gum guiacum": "Gum Guaiacum",
    # Guinea grains
    "guiney grains": "Guinea Grains",
    # Hops
    "hopps": "Hops",
    # Jalap
    "jallop?": "Jalap",
    "jollop": "Jalap",
    # Lignum Vitae
    "lingum vitae": "Lignum Vitae",
    # Muscovado
    "muscavado sugar": "Muscovado Sugar",
    # Orchil/Archil variants
    "orchal": "Orchil",
    "orchall?": "Orchil",
    "orchelia": "Orchil",
    "archelia": "Orchil",
    # Sarsaparilla
    "sarsparila": "Sarsaparilla",
    "sasparilla": "Sarsaparilla",
    # Tamarinds
    "tamerinds": "Tamarinds",
    # Tortoise shell
    "tortoise shells": "Tortoise Shell",
    "tortoise shell": "Tortoise Shell",
    # Bay berries
    "bay berries": "Bayberries",
    # Beeswax
    "bees wax": "Beeswax",
    # Snuff
    "shruff": "Snuff",
    "shruff? snuff?": "Snuff",
    "snuff?": "Snuff",
    # Vinellas (Vanilla)
    "vinellas": "Vanilla",
    # Succade variants
    "succand": "Succade",
    "succands": "Succade",
    "succads": "Succade",
    # Barbados Tar/Turpentine
    "barbados tarr": "Barbados Tar",
    "barbados turp": "Barbados Turpentine",
    "barbados t…": "Barbados Tar",
    # Bermuda plait
    "bermudos plat": "Bermuda Plait",
    "plat bermudos": "Bermuda Plait",
    # Currants
    "corrants? currants?": "Currants",
    # Cocus wood
    "wppd, cocus": "Cocuswood",
    "wood, cocus": "Cocuswood",
    # Soft raisins
    "soft raisans": "Soft Raisins",
    # Smalts
    "slude": "Slude",
    "slude?": "Slude",
    # Misc wood normalization (keep type distinctions)
    "wood, boxwood": "Boxwood",
    "wood, braziletto": "Braziletto Wood",
    "wood, cam": "Camwood",
    "wood, camwood": "Camwood",
    "wood, cedar": "Cedarwood",
    "wood, cocoa": "Cocoa Wood",
    "wood, crocus": "Crocuswood",
    "wood, ebony": "Ebony",
    "wood, iron": "Ironwood",
    "wood, logwood": "Logwood",
    "wood, mahogany": "Mahogany",
    "wood, marble": "Marblewood",
    "wood, nicaragua": "Nicaragua Wood",
    "wood, pidgeonwood": "Pigeonwood",
    "wood, redwood": "Redwood",
    "wood, rosewood": "Rosewood",
    "wood, sweetwood": "Sweetwood",
    # Train oil
    "train oyl": "Train Oil",
    "oyl turpyn": "Oil of Turpentine",
    # Madera wine
    "madera wine": "Madeira Wine",
    # Saltpetre
    "salt petre": "Saltpetre",
    # Hypococania (likely Ipecacuanha)
    "hypococania": "Ipecacuanha",
    # Sea horse teeth
    "sea horse teeth?": "Walrus Teeth",
}

# ── Person title normalization ────────────────────────────────────────────────
# Standardizes title prefixes for better matching. The name itself is preserved.
PERSON_TITLE_MAP: dict[str, str] = {
    "mr.": "Mr",
    "mr ": "Mr",
    "master ": "Mr",
    "mrs.": "Mrs",
    "mrs ": "Mrs",
    "capt.": "Captain",
    "capt ": "Captain",
    "col.": "Colonel",
    "col ": "Colonel",
    "gen.": "General",
    "gen ": "General",
    "dr.": "Dr",
    "dr ": "Dr",
    "sir ": "Sir",
    "lord ": "Lord",
    "gov.": "Governor",
    "gov ": "Governor",
}


def normalize_entity(text: str, entity_type: str) -> str:
    """
    Normalize an entity's text for authority lookup.
    Returns the normalized form, or the original if no normalization applies.
    """
    lower = text.strip().lower()

    if entity_type == "TOPONYM":
        return TOPONYM_NORMALIZATIONS.get(lower, text.strip())

    if entity_type == "COMMODITY":
        return COMMODITY_NORMALIZATIONS.get(lower, text.strip())

    if entity_type == "PERSON":
        # Normalize title prefix but keep the name
        for old_title, new_title in PERSON_TITLE_MAP.items():
            if lower.startswith(old_title):
                rest = text.strip()[len(old_title):].strip()
                return f"{new_title} {rest}"
        return text.strip()

    return text.strip()
