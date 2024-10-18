import json
import os
import logging
import gc
import torch
import threading
from queue import Queue
from kafka_queue.kafka_manager import KafkaQueue  # Import KafkaQueue
import time

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

def process_queue(kafka_queue, processing_queue):
    logger = configure_logging()
    logger.info("Starting queue processing")

    try:
        while True:  # Continuous loop to keep processing messages
            articles = []
            message_limit = 1  # Set a limit for the number of messages to process

            # Use a loop to consume messages from the generator
            for _ in range(message_limit):
                try:
                    message = next(kafka_queue.dequeue())  # Get the next message from the generator
                    if message:
                        articles.append(message)  # Ensure message is added to the list
                        logger.info(f"Received message: {message}")
                    else:
                        logger.info("No more messages to process.")
                        break
                except StopIteration:
                    logger.info("No more messages in the queue.")
                    break

            if articles:
                logger.info(f"Loaded {len(articles)} items from Kafka queue")
                # Add articles to the processing queue
                for article in articles:
                    processing_queue.put(article)
                    print(article)
            else:
                logger.info("No articles to process. Waiting for new messages...")
                time.sleep(5)  # Wait for 5 seconds before checking again

    except Exception as e:
        logger.error(f"Error in process_queue: {str(e)}")
    finally:
        kafka_queue.close()  # Ensure the Kafka consumer is closed

def process_articles(processing_queue):
    logger = configure_logging()
    logger.info("Starting article processing")

    while True:
        articles = processing_queue.get()  # Get an article from the processing queue
        if articles is None:  # Check for termination signal
            break

        # Process the article
        # Uncomment and adjust the following lines as needed
        # processed_article = process_articles_in_batches(NEExtractor, 'extract_entities', articles, 1)
        # processed_article = process_articles_in_batches(Summarizer, 'summarize', articles, 1)
        # processed_article = process_articles_in_batches(TopicExtractor, 'extract_topics', articles, 1)
        # processed_article = process_articles_in_batches(Vectorizer, 'vectorize', articles, 1)

        # Remove unnecessary fields
        articles = [{k: v for k, v in art.items() if k not in ['main_text', 'lead_text']} for art in articles]
        # Produce processed articles back to the processed topic
        kafka_queue.enqueue_processed(articles)
        logger.info(f"Processed articles sent to {kafka_queue.processed_topic}")
        logger.info(f"Processed articles: {articles}")

if __name__ == "__main__":
    kafka_queue = KafkaQueue(topic='raw_articles')
    processing_queue = Queue()  # Create a queue for processing articles

    # Start the processing thread
    processing_thread = threading.Thread(target=process_articles, args=(processing_queue,))
    processing_thread.start()

    # Start the main queue processing
    process_queue(kafka_queue, processing_queue)

    # Signal the processing thread to terminate
    processing_queue.put(None)  # Send termination signal
    processing_thread.join()  # Wait for the processing thread to finish
