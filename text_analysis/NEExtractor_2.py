import torch
import gc
from flair.data import Sentence
from flair.models import SequenceTagger

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
        """Extract unique entities for each article and store them within the article's dictionary."""
        
        output_list = []
        
        # Process each article individually
        for i, article in enumerate(articles_list):
            entity_dict = {}  # Reset entity dictionary for each article
            
            main_text = article.get("main_text", "")
            sentence = Sentence(main_text)
            
            # Perform entity prediction within a no_grad context
            with torch.no_grad():
                self.tagger.predict(sentence)
            
            # Collect entities from the sentence
            for entity in sentence.get_spans('ner'):
                if entity.text not in entity_dict or entity_dict[entity.text] != entity.tag:
                    entity_dict[entity.text] = entity.tag
            
            # Prepare the central_entities format for the database
            entities = list(entity_dict.keys())
            entity_types = list(entity_dict.values())
            entity_types = [entity_type.lower() for entity_type in entity_types]
            central_entities = [{"type_id": type_id, "title": entity} for entity, type_id in zip(entities, entity_types)]
            
            # Update the article with the central entities
            article.update({"central_entities": central_entities})
            
            # Append the modified article to the output list
            output_list.append(article)
            
            # Explicitly delete objects to free memory
            del sentence, entity_dict, entities, entity_types, central_entities
            
            # Clear GPU memory after processing each article
            torch.cuda.empty_cache()
            
            # Optional: call gc.collect() after every N articles
            if i % 10 == 0:  # Adjust N according to your needs
                gc.collect()
        
        return output_list
