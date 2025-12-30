from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

MODEL_NAME = "NlpHUST/ner-vietnamese-electra-base"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME)

ner_pipeline = pipeline(
    "ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple"
)


def ner_extract_locations(text: str):
    results = ner_pipeline(text)
    locations = []

    for ent in results:
        if ent.get("entity_group") in ("LOC", "LOCATION"):
            locations.append(ent["word"].replace("_", " ").strip())

    return locations
