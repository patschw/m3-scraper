import torch
import gc
from flair.data import Sentence
from flair.models import SequenceTagger
from datasets import Dataset
import pandas as pd
import rpy2.robjects as robjects
from rpy2.robjects.packages import importr
from rpy2.robjects import pandas2ri

class NEExtractor:
    """A named entity extractor that uses the Flair library to extract named entities from text and newsmap to infer geographical focus."""
    
    def __init__(self, model="flair/ner-german-large", max_chunk_size=5000):
        """Initialize the named entity extractor with a specific flair model and chunk size."""
        try:
            self.tagger = SequenceTagger.load(model)
            self.max_chunk_size = max_chunk_size
            print('Tagger instantiated successfully')
        except Exception as e:
            print(f"Failed to load model '{model}'. Error: {e}")
            self.tagger = None  # Ensure tagger is at least defined
        
        # Initialize R and load necessary packages
        pandas2ri.activate()
        self.r_base = importr('base')
        self.newsmap = importr('newsmap')
        self.quanteda = importr('quanteda')
        
        # Load the pre-trained newsmap model for German
        self.r_model = self.newsmap.readRDS(self.r_base.url("https://github.com/koheiw/newsmap/raw/master/data/model_de.RDS"))

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
        Also infer geographical focus using the newsmap R package.
        
        Parameters:
        articles_list (list): A list of dictionaries containing the articles.
        
        Returns:
        list: The original list of articles with additional 'central_entities' field including the inferred geographical focus.
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

        # Infer geographical focus using newsmap
        articles_list = self._infer_geo_focus(articles_list)

        # Final GPU memory cleanup
        del results
        torch.cuda.empty_cache()
        gc.collect()

        return articles_list

    def _infer_geo_focus(self, articles_list):
        """Infer geographical focus of the articles using the newsmap R package."""
        # Convert articles to a pandas DataFrame
        df = pd.DataFrame(articles_list)
        
        # Convert pandas DataFrame to R dataframe
        r_df = pandas2ri.py2rpy(df)
        
        # Create corpus
        corp = self.quanteda.corpus(r_df, text_field='main_text')
        
        # Tokenize
        toks = self.quanteda.tokens(corp)
        toks = self.quanteda.tokens_remove(toks, self.quanteda.stopwords('german'), valuetype='fixed', padding=True)
        
        # Look up in dictionary
        toks_label = self.quanteda.tokens_lookup(toks, self.newsmap.data_dictionary_newsmap_de, levels=3)
        dfmt_label = self.quanteda.dfm(toks_label)
        
        # Create feature dfm
        dfmt_feat = self.quanteda.dfm(toks, tolower=False)
        dfmt_feat = self.quanteda.dfm_select(dfmt_feat, selection="keep", pattern='^[A-Z][A-Za-z1-2]+', 
                                             valuetype='regex', case_insensitive=False)
        dfmt_feat = self.quanteda.dfm_trim(dfmt_feat, min_termfreq=10)
        
        # Apply the model
        pred = self.newsmap.predict(self.r_model, dfmt_feat)
        
        # Convert R result back to Python
        py_result = pandas2ri.rpy2py(pred)
        
        # Add inferred geographical focus to the original articles as a location named entity
        for i, article in enumerate(articles_list):
            if i < len(py_result):
                geo_focus = py_result[i]
                if geo_focus:  # Check if a geographical focus was inferred
                    article['central_entities'].append({"type_id": "loc", "title": geo_focus})
        
        return articles_list
