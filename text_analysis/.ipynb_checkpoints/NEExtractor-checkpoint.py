import torch
import gc
from flair.data import Sentence
from flair.models import SequenceTagger
from datasets import Dataset

class NEExtractor:
    """A named entity extractor that uses the Flair library to extract named entities from text."""
    
    def __init__(self, model="flair/ner-german-large", max_chunk_size=5000):
        """Initialize the named entity extractor with a specific flair model and chunk size."""
        try:
            self.tagger = SequenceTagger.load(model)
            self.max_chunk_size = max_chunk_size
            print('Tagger instantiated successfully')
        except Exception as e:
            print(f"Failed to load model '{model}'. Error: {e}")
            self.tagger = None  # Ensure tagger is at least defined
    
    def chunk_text(self, text, max_chunk_size):
        """Split the text into smaller chunks of up to max_chunk_size tokens."""
        tokens = text.split()
        if len(tokens) > max_chunk_size:
            chunks = [' '.join(tokens[i:i + max_chunk_size]) for i in range(0, len(tokens), max_chunk_size)]
        else:
            chunks = [text]  # If text is not too long, return it as a single chunk
        return chunks
    
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

            # Chunk the text only if it's too long
            chunks = self.chunk_text(example["main_text"], self.max_chunk_size)

            # Process each chunk individually
            for chunk in chunks:
                sentence = Sentence(chunk)
                
                # Perform entity prediction within a no_grad context
                with torch.no_grad():
                    self.tagger.predict(sentence)
                
                # Collect entities from the sentence
                for entity in sentence.get_spans('ner'):
                    if entity.text not in entity_dict or entity_dict[entity.text] != entity.tag:
                        entity_dict[entity.text] = entity.tag
                
                # Clear the sentence from memory after processing
                del sentence
                gc.collect()
                torch.cuda.empty_cache()

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

        # Final GPU memory cleanup
        del results
        torch.cuda.empty_cache()
        gc.collect()

        return articles_list
