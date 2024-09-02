import torch
import gc
from sentence_transformers import SentenceTransformer
import numpy as np
import nltk
from datasets import Dataset

TRANSFORMER_MODEL_NAMES_DICT = {
    'bert': 'deepset/gbert-base', 
    'roberta': 'T-Systems-onsite/german-roberta-sentence-transformer-v2', 
    'gbert': 'deutsche-telekom/gbert-large-paraphrase-euclidean', 
    'xmlr': 'xlm-roberta-large', 
    'bigbird': 'google/bigbird-roberta-large', 
    'longformer': 'severinsimmler/xlm-roberta-longformer-large-16384'
}

class Vectorizer:
    """A vectorizer that uses various Sentence Transformers models to vectorize text."""
    
    def __init__(self, model_names_dict=TRANSFORMER_MODEL_NAMES_DICT, cache_dir="transformers_cache_dir"):
        self.models = {key: SentenceTransformer(model, cache_folder=cache_dir) for key, model in model_names_dict.items()}
        
    def vectorize(self, articles_list):
        # Convert articles_list to a Dataset
        dataset = Dataset.from_dict({"lead_text": [article.get("lead_text", "") for article in articles_list],
                                     "main_text": [article.get("main_text", "") for article in articles_list]})
        
        # Define a function to apply the vectorization
        def vectorize_example(example):
            for key, model in self.models.items():
                with torch.no_grad():  # Use no_grad to reduce memory usage
                    # Split the texts into sentences
                    lead_sentences = nltk.sent_tokenize(example["lead_text"])
                    main_sentences = nltk.sent_tokenize(example["main_text"])

                    # Generate an embedding for each sentence
                    lead_sentence_embeddings = model.encode(lead_sentences)
                    main_sentence_embeddings = model.encode(main_sentences)

                    # Compute the document embedding as the mean of the sentence embeddings
                    lead_document_embedding = np.mean(lead_sentence_embeddings, axis=0).tolist()
                    main_document_embedding = np.mean(main_sentence_embeddings, axis=0).tolist()

                    # Store the embeddings back into the example dictionary
                    example[f"lead_{key}"] = lead_document_embedding
                    example[f"full_{key}"] = main_document_embedding

                # Explicitly delete the embeddings to free memory
                del lead_sentence_embeddings, main_sentence_embeddings

            return example

        # Apply the vectorization function to the dataset
        vectorized_dataset = dataset.map(vectorize_example, batched=False)

        # Convert the results back to a list of dictionaries
        for i, single_article_dict in enumerate(articles_list):
            for key in TRANSFORMER_MODEL_NAMES_DICT.keys():
                single_article_dict[f"lead_{key}"] = vectorized_dataset[i][f"lead_{key}"]
                single_article_dict[f"full_{key}"] = vectorized_dataset[i][f"full_{key}"]

            # Optionally clear GPU memory and force garbage collection after processing each article
            torch.cuda.empty_cache()
            gc.collect()

        return articles_list
