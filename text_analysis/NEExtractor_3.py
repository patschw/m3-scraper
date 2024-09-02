import torch
import gc
from flair.data import Sentence
from flair.models import SequenceTagger
from datasets import Dataset

class NEExtractor:
    """A named entity extractor that uses the Flair library to extract named entities from text."""
    
    def __init__(self, model="flair/ner-german-large"):
        """Initialize the named entity extractor with a specific flair model."""
        try:
            self.tagger = SequenceTagger.load(model)
            print('Tagger instantiated successfully')
        except Exception as e:
            print(f"Failed to load model '{model}'. Error: {e}")
            self.tagger = None  # Ensure tagger is at least defined
    
    def extract_entities(self, articles_list):
        """
        Extract unique entities for each entry in the articles list and add them to the dataset.
        
        Parameters:
        articles_list (list): A list of dictionaries containing the articles.
        
        Returns:
        list: The original list of articles with an additional 'central_entities' field containing extracted entities.
        """
        
        # Convert articles_list to a Hugging Face Dataset
        dataset = Dataset.from_dict({"main_text": [article["main_text"] for article in articles_list]})

        # Define a function to extract entities
        def extract(example):
            entity_dict = {}
            sentence = Sentence(example["main_text"])
            
            # Perform entity prediction within a no_grad context
            with torch.no_grad():
                self.tagger.predict(sentence)
            
            # Collect entities from the sentence
            for entity in sentence.get_spans('ner'):
                if entity.text not in entity_dict or entity_dict[entity.text] != entity.tag:
                    entity_dict[entity.text] = entity.tag
            
            # Prepare the central_entities format
            entities = list(entity_dict.keys())
            entity_types = list(entity_dict.values())
            entity_types = [entity_type.lower() for entity_type in entity_types]
            central_entities = [{"type_id": type_id, "title": entity} for entity, type_id in zip(entities, entity_types)]
            
            return {"central_entities": central_entities}

        # Apply the extraction to the entire dataset
        results = dataset.map(extract, batched=False)

        # Update the original articles with the extracted entities
        for i, single_article_dict in enumerate(articles_list):
            single_article_dict["central_entities"] = results[i]["central_entities"]

        # Clear GPU memory after processing
        torch.cuda.empty_cache()
        gc.collect()

        return articles_list
