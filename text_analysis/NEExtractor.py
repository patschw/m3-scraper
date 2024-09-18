import torch
import gc
from flair.data import Sentence
from flair.models import SequenceTagger
from datasets import Dataset
import logging
import subprocess
import os

class NEExtractor:
    """A named entity extractor that uses the Flair library to extract named entities from text and newsmap to infer geographical focus."""
    
    def __init__(self, model="flair/ner-german-large", max_chunk_size=5000):
        """Initialize the named entity extractor with a specific flair model and chunk size."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing NEExtractor with model: %s", model)
        try:
            self.tagger = SequenceTagger.load(model)
            self.max_chunk_size = max_chunk_size
            self.logger.info('Tagger instantiated successfully')
        except Exception as e:
            self.logger.error("Failed to load model '%s'. Error: %s", model, e)
            self.tagger = None  # Ensure tagger is at least defined

    def chunk_text(self, text, max_chunk_size):
        """Split the text into smaller chunks of up to max_chunk_size tokens."""
        tokens = text.split()
        if len(tokens) > max_chunk_size:
            self.logger.debug("Chunking text of %d tokens into smaller pieces", len(tokens))
            chunks = [' '.join(tokens[i:i + max_chunk_size]) for i in range(0, len(tokens), max_chunk_size)]
        else:
            chunks = [text]  # If text is not too long, return it as a single chunk
        return chunks
    
    def extract_entities(self, articles_list):
        """
        Extract unique entities for each entry in the articles list and add them to the dataset.
        Also infer geographical focus using the newsmap R package.
        """
        self.logger.info("Starting entity extraction for %d articles", len(articles_list))
        
        # Convert articles_list to a Hugging Face Dataset
        dataset = Dataset.from_dict({"main_text": [article["main_text"] for article in articles_list]})

        # Define a function to extract entities
        def extract(example):
            entity_dict = {}

            # Chunk the text only if it's too long
            chunks = self.chunk_text(example["main_text"], self.max_chunk_size)

            # Process each chunk individually
            for i, chunk in enumerate(chunks):
                self.logger.debug("Processing chunk %d of %d", i+1, len(chunks))
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
            
            self.logger.debug("Extracted %d unique entities", len(central_entities))
            return {"central_entities": central_entities}

        # Apply the extraction to the entire dataset
        self.logger.info("Applying entity extraction to all articles")
        results = dataset.map(extract, batched=False)

        # Update the original articles with the extracted entities
        for i, single_article_dict in enumerate(articles_list):
            single_article_dict["central_entities"] = results[i]["central_entities"]

        # Infer geographical focus using newsmap
        self.logger.info("Inferring geographical focus")
        articles_list = self._infer_geo_focus(articles_list)

        # Final GPU memory cleanup
        del results
        torch.cuda.empty_cache()
        gc.collect()

        self.logger.info("Entity extraction and geographical focus inference complete")
        return articles_list


    def _infer_geo_focus(self, articles_list):
        """Infer geographical focus of the articles using the newsmap R package."""
        self.logger.info("Starting geographical focus inference for %d articles", len(articles_list))
        # delete the files if they exist
        if os.path.exists('main_texts_for_geo_focus_inference.txt'):
            os.remove('main_texts_for_geo_focus_inference.txt')
        if os.path.exists('geo_inference_country_names.txt'):
            os.remove('geo_inference_country_names.txt')

        try:
            # Write main_text to file
            input_file_path = 'main_texts_for_geo_focus_inference.txt'
            with open(input_file_path, 'w', encoding='utf-8') as f:
                for article in articles_list:
                    f.write(article['main_text'] + '\n')
            
            self.logger.debug("Wrote main texts to file: %s", input_file_path)

            # Call R script
            r_script_path = os.path.join('text_analysis', 'infer_geo_focus.R')
            self.logger.debug("Calling R script: %s", r_script_path)
            subprocess.run(['Rscript', r_script_path], check=True)
            
            # Read the output file
            output_file_path = 'geo_inference_country_names.txt'
            with open(output_file_path, 'r', encoding='utf-8') as f:
                country_names = f.read().strip().split('\n')
            
            # Add inferred geographical focus to the original articles
            for i, (article, country) in enumerate(zip(articles_list, country_names)):
                if country and country != 'NA':
                    article['central_entities'].append({"title": country, "type_id": "loc"})
                    self.logger.debug("Added geographical focus '%s' to article %d", country, i)
                else:
                    self.logger.debug("No geographical focus inferred for article %d", i)
            
            self.logger.info("Geographical focus inference completed successfully")
        except Exception as e:
            self.logger.error("Error in geographical focus inference: %s", str(e))
        
        return articles_list
