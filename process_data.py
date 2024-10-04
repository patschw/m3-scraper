import json
import os
import logging
import gc
import torch
from tqdm import tqdm

# from text_analysis.NEExtractor import NEExtractor
# from text_analysis.Summarizer import Summarizer
# from text_analysis.TopicExtractor import TopicExtractor
# from text_analysis.Vectorizers import Vectorizer

def configure_logging(log_level="INFO"):
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("process_queue.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def clear_gpu_memory():
    """Clears GPU memory and forces garbage collection."""
    torch.cuda.empty_cache()
    gc.collect()
    logging.info("GPU memory cleared and garbage collection performed")

def process_articles_in_batches(text_analysis_class, method_name, articles, batch_size):
    """Process articles in batches using the specified text analysis class and method."""
    processor = text_analysis_class()
    method = getattr(processor, method_name)

    for i in range(0, len(articles), batch_size):
        logging.info(f"Processing batch {i // batch_size + 1} of {method_name} for articles {i} to {i + batch_size}")
        batch = articles[i:i + batch_size]
        
        try:
            batch = method(batch)
        except RuntimeError as e:
            if 'CUDA out of memory' in str(e):
                logging.error(f"CUDA OOM error while processing batch {i // batch_size + 1} during {method_name}")
                clear_gpu_memory()
            else:
                logging.error(f"Unexpected error during {method_name} in batch {i // batch_size + 1}: {str(e)}")
                clear_gpu_memory()

        articles[i:i + batch_size] = batch
        clear_gpu_memory()

    del processor
    clear_gpu_memory()
    logging.info(f"{method_name} processing completed for all articles")

def process_queue():
    logger = configure_logging()
    logger.info("Starting queue processing")

    try:
        # Read content from the queue file
        queue_file_path = 'queue/content.json'
        with open(queue_file_path, 'r') as f:
            articles = json.load(f)
        
        logger.info(f"Loaded {len(articles)} items from queue")

        # Process articles
        # process_articles_in_batches(NEExtractor, 'extract_entities', articles, 100)
        # process_articles_in_batches(TopicExtractor, 'extract_topics', articles, 100)
        # process_articles_in_batches(Vectorizer, 'vectorize', articles, 100)
        # process_articles_in_batches(Summarizer, 'summarize', articles, 100)

        # Remove unnecessary fields
        for article in articles:
            article.pop('main_text', None)
            article.pop('lead_text', None)

        # Write processed articles back to the queue folder
        processed_file_path = 'queue/processed_content.json'
        with open(processed_file_path, 'w') as f:
            json.dump(articles, f)
        logger.info(f"Processed content written to {processed_file_path}")

    except Exception as e:
        logger.error(f"Error in process_queue: {str(e)}")

if __name__ == "__main__":
    process_queue()