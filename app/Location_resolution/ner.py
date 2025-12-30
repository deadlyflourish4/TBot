from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline


class NERService:
    def __init__(self):
        self.model_name = "Davlan/xlm-roberta-base-ner-hrl"
        print(f"🚀 Loading NER model: {self.model_name}")

        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModelForTokenClassification.from_pretrained(self.model_name)

        self.pipeline = pipeline(
            "ner",
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy="simple",
        )

        print("✅ NERService ready")

    def extract_locations(self, text: str):
        results = self.pipeline(text)
        locs = []

        for ent in results:
            if ent.get("entity_group") in ("LOC", "ORG"):
                locs.append(ent["word"].replace("_", " ").strip())

        return locs
