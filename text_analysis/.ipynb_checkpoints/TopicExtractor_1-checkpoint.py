from transformers import AutoTokenizer, pipeline

class TopicExtractor:
    def __init__(self, model_name="MoritzLaurer/bge-m3-zeroshot-v2.0"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.classifier = pipeline("zero-shot-classification", model=model_name)

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
        hypothesis_template = "In diesem Text der Nachrichtenwebsite spiegel.de geht es um {}"

        output_list = articles_list
        
        for single_article_dict in output_list:
            text = single_article_dict['main_text']  # assuming 'text' key contains the article text
            classification = self.classifier(text, topics, hypothesis_template=hypothesis_template, multi_label=False)
            highest_score_label = classification['labels'][0]
            topic_dict = {
                "title": highest_score_label # this is being slugged to readable_id in the database
            }
            single_article_dict.update({"topic": topic_dict})

        return output_list