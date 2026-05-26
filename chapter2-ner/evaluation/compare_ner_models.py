"""
Compare NER models on Early Modern English texts (1600-1800)

This script compares two NER models:
1. dell-research-harvard/historical_newspaper_ner - Fine-tuned on historical newspapers
2. dslim/bert-base-NER - Standard BERT NER model

Usage:
    python compare_ner_models.py
"""

from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import warnings
warnings.filterwarnings('ignore')

def load_models():
    """Load both NER models"""
    print("Loading models... (this may take a minute)\n")

    # Model 1: Historical newspaper NER
    print("1. Loading dell-research-harvard/historical_newspaper_ner...")
    tokenizer1 = AutoTokenizer.from_pretrained("dell-research-harvard/historical_newspaper_ner")
    model1 = AutoModelForTokenClassification.from_pretrained("dell-research-harvard/historical_newspaper_ner")
    ner_pipeline1 = pipeline("ner", model=model1, tokenizer=tokenizer1, aggregation_strategy="simple")

    # Model 2: Standard BERT NER
    print("2. Loading dslim/bert-base-NER...")
    ner_pipeline2 = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")

    print("\nModels loaded successfully!\n")
    return ner_pipeline1, ner_pipeline2


def format_entities(entities):
    """Format entities for display"""
    if not entities:
        return "  No entities found"

    result = []
    for entity in entities:
        result.append(f"  - {entity['word']:<25} [{entity['entity_group']:<5}] (confidence: {entity['score']:.3f})")
    return "\n".join(result)


def compare_on_text(text, ner1, ner2, text_description=""):
    """Compare both models on a given text"""
    print("=" * 80)
    if text_description:
        print(f"TEXT: {text_description}")
    print("=" * 80)
    print(f"\n{text}\n")

    # Run both models
    entities1 = ner1(text)
    entities2 = ner2(text)

    # Display results
    print("\n" + "-" * 80)
    print("MODEL 1: Historical Newspaper NER")
    print("-" * 80)
    print(format_entities(entities1))

    print("\n" + "-" * 80)
    print("MODEL 2: Standard BERT NER")
    print("-" * 80)
    print(format_entities(entities2))
    print("\n")


def main():
    # Load models
    ner1, ner2 = load_models()

    # Sample Early Modern English texts (1600-1800)
    test_texts = [
        {
            "description": "Sample 1: 17th century - Newton's Principia (1687)",
            "text": """In the year 1687, Sir Isaac Newton published his Philosophiæ Naturalis
Principia Mathematica in London, revolutionizing natural philosophy."""
        },
        {
            "description": "Sample 2: 18th century - American Revolution",
            "text": """On July 4, 1776, the Continental Congress adopted the Declaration of Independence
in Philadelphia. Thomas Jefferson was the principal author of this document."""
        },
        {
            "description": "Sample 3: 17th century - Shakespeare reference",
            "text": """Mr. William Shakespeare, the renowned playwright of Stratford-upon-Avon,
presented his works at the Globe Theatre in London during the reign of King James I."""
        },
        {
            "description": "Sample 4: 18th century - Commerce",
            "text": """The East India Company established trading posts in Bombay and Calcutta,
importing spices and textiles to England under the direction of Governor Warren Hastings."""
        }
    ]

    # Run comparisons on sample texts
    print("\n" + "=" * 80)
    print("COMPARING NER MODELS ON EARLY MODERN ENGLISH TEXTS (1600-1800)")
    print("=" * 80 + "\n")

    for test in test_texts:
        compare_on_text(test["text"], ner1, ner2, test["description"])

    # Interactive mode
    print("\n" + "=" * 80)
    print("INTERACTIVE MODE - Test your own text")
    print("=" * 80)
    print("\nYou can now enter your own Early Modern English text to test.")
    print("Type 'quit' or 'exit' to stop.\n")

    while True:
        user_text = input("Enter text to analyze (or 'quit' to exit): ").strip()

        if user_text.lower() in ['quit', 'exit', 'q']:
            print("\nGoodbye!")
            break

        if not user_text:
            continue

        compare_on_text(user_text, ner1, ner2, "Your text")


if __name__ == "__main__":
    main()
