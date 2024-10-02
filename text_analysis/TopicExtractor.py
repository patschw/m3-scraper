import torch
from transformers import AutoTokenizer, pipeline
from datasets import Dataset

class TopicExtractor:
    def __init__(self, model_name="MoritzLaurer/bge-m3-zeroshot-v2.0"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        device = 0 if torch.cuda.is_available() else -1  # Use GPU if available
        self.classifier = pipeline("zero-shot-classification", model=model_name, device=device)

    def extract_topics(self, articles_list):
        topics = [
            "Politik",
            "Wirtschaft",
            "Gesellschaft",
            "Kultur",
            "Wissenschaft und Technologie",
            "Umwelt",
            "Gesundheit",
            "Sport",
            "Verkehr und Mobilität",
            "Kriminalität und Recht"
        ]

        hypothesis_template = "In diesem Text der Nachrichtenwebsite spiegel.de geht es um {}" # TODO: spiegel.de austauschen

        # Convert articles_list to a Dataset
        dataset = Dataset.from_dict({"main_text": [article["main_text"] for article in articles_list]})

        # Define a function to apply the classification
        def classify(example):
            with torch.no_grad():
                classification = self.classifier(
                    example["main_text"], topics, hypothesis_template=hypothesis_template, multi_label=False
                )
                return {"topic": classification["labels"][0]}

        # Apply the classification to the entire dataset
        results = dataset.map(classify, batched=False)

        # Update the original articles with the extracted topics
        for i, single_article_dict in enumerate(articles_list):
            single_article_dict["topic"] = {"title": results[i]["topic"]}

        return articles_list
