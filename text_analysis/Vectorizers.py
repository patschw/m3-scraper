import torch
import gc
from sentence_transformers import SentenceTransformer
import numpy as np
import nltk
from datasets import Dataset
from config import TRANSFORMER_MODEL_NAMES_DICT_VECTORIZATION

# TRANSFORMER_MODEL_NAMES_DICT_VECTORIZATION = {
#     'bert': 'deepset/gbert-base', 
#     'roberta': 'T-Systems-onsite/german-roberta-sentence-transformer-v2', 
#     'gbert': 'deutsche-telekom/gbert-large-paraphrase-euclidean', 
#     'xmlr': 'xlm-roberta-large', 
#     'bigbird': 'google/bigbird-roberta-large', 
#     'longformer': 'severinsimmler/xlm-roberta-longformer-large-16384'
# }

class Vectorizer:
    """A vectorizer that uses various Sentence Transformers models to vectorize text."""
    
    def __init__(self, model_names_dict=TRANSFORMER_MODEL_NAMES_DICT_VECTORIZATION, cache_dir="transformers_cache_dir"):
        self.models = {key: SentenceTransformer(model, cache_folder=cache_dir) for key, model in model_names_dict.items()}
        
    def vectorize(self, articles_list):
        # Convert articles_list to a Dataset
        dataset = Dataset.from_dict({
            "lead_text": [article.get("lead_text", "") for article in articles_list],
            "main_text": [article.get("main_text", "") for article in articles_list]
        })
        
        # Define a function to apply the vectorization
        def vectorize_example(example):
            for key, model in self.models.items():
                with torch.no_grad():  # Use no_grad to reduce memory usage
                    lead_sentences = nltk.sent_tokenize(example["lead_text"]) if example["lead_text"] else []
                    main_sentences = nltk.sent_tokenize(example["main_text"]) if example["main_text"] else []

                    # Generate an embedding for each sentence
                    if lead_sentences:
                        lead_sentence_embeddings = model.encode(lead_sentences)
                        lead_document_embedding = np.mean(lead_sentence_embeddings, axis=0).tolist()
                    else:
                        lead_sentence_embeddings = [] # Return empty list if no lead sentences
                        lead_document_embedding = []  # Return empty list if no lead sentences

                    if main_sentences:
                        main_sentence_embeddings = model.encode(main_sentences)
                        main_document_embedding = np.mean(main_sentence_embeddings, axis=0).tolist()
                    else:
                        main_document_embedding = [] # Return empty list if no main sentences
                        main_document_embedding = []  # Return empty list if no main sentences

                    # Store the embeddings back into the example dictionary
                    example[f"lead_{key}"] = lead_document_embedding
                    example[f"full_{key}"] = main_document_embedding

                # Explicitly delete the embeddings to free memory
                del lead_sentence_embeddings, main_sentence_embeddings, lead_document_embedding, main_document_embedding

            return example

        # Apply the vectorization function to the dataset
        vectorized_dataset = dataset.map(vectorize_example, batched=False)

        # Convert the results back to a list of dictionaries
        for i, single_article_dict in enumerate(articles_list):
            for key in TRANSFORMER_MODEL_NAMES_DICT_VECTORIZATION.keys():
                single_article_dict[f"lead_{key}"] = vectorized_dataset[i][f"lead_{key}"]
                single_article_dict[f"full_{key}"] = vectorized_dataset[i][f"full_{key}"]

            # Optionally clear GPU memory and force garbage collection after processing each article
            torch.cuda.empty_cache()
            gc.collect()

        return articles_list
