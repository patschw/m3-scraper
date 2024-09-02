from sentence_transformers import SentenceTransformer
import numpy as np
import nltk

TRANSFORMER_MODEL_NAMES_DICT = {'bert': 'deepset/gbert-base', 
                                'roberta': 'T-Systems-onsite/german-roberta-sentence-transformer-v2', 
                                'gbert': 'deutsche-telekom/gbert-large-paraphrase-euclidean', 
                                'xmlr': 'xlm-roberta-large', 
                                'bigbird': 'google/bigbird-roberta-large', 
                                'longformer': 'severinsimmler/xlm-roberta-longformer-large-16384'
                                }


# TODO: use torch no grad

class Vectorizer:
    """A vectorizer that uses various Sentence Transformers models to vectorize text."""
    def __init__(self, model_names_dict=TRANSFORMER_MODEL_NAMES_DICT, cache_dir="transformers_cache_dir"):
        self.models = {key: SentenceTransformer(model, cache_folder=cache_dir) for key, model in model_names_dict.items()}
        
    def vectorize(self, articles_list):
        # Loop over all articles
        for single_article_dict in articles_list:
            # Get the lead text and main text
            lead_text = single_article_dict.get("lead_text", "")
            main_text = single_article_dict.get("main_text", "")

            # Split the texts into sentences
            lead_sentences = nltk.sent_tokenize(lead_text)
            main_sentences = nltk.sent_tokenize(main_text)

            # Loop over all models
            for key, model in self.models.items():
                # Generate an embedding for each sentence
                lead_sentence_embeddings = model.encode(lead_sentences)
                main_sentence_embeddings = model.encode(main_sentences)

                # Compute the document embedding as the mean of the sentence embeddings
                lead_document_embedding = np.mean(lead_sentence_embeddings, axis=0).tolist()
                main_document_embedding = np.mean(main_sentence_embeddings, axis=0).tolist()

                # Store the embeddings in the article dictionary
                single_article_dict[f"lead_{key}"] = lead_document_embedding
                single_article_dict[f"full_{key}"] = main_document_embedding

        return articles_list