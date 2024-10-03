import argparse
import importlib
import logging
import transformers
import json
import gc
import torch

from config import SCRAPER_MAP
from database_handling.DataDownload import DataDownloader
from database_handling.DataUpload import DataUploader
from database_handling.KeycloakLogin import KeycloakLogin
from text_analysis.NEExtractor import NEExtractor
from text_analysis.Summarizer import Summarizer
from text_analysis.TopicExtractor import TopicExtractor
from text_analysis.Vectorizers import Vectorizer

def configure_logging(log_level):
    """Configures logging based on the specified log level."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("process.log"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    return logger

def get_scraper_class(website):
    """Dynamically imports and returns the scraper class based on the website name."""
    if website not in SCRAPER_MAP:
        raise ValueError(f"No scraper available for website: {website}")
    
    module_name, class_name = SCRAPER_MAP[website].rsplit('.', 1)
    module = importlib.import_module(module_name)
    scraper_class = getattr(module, class_name)
    return scraper_class

def clear_gpu_memory():
    """Clears GPU memory and forces garbage collection."""
    torch.cuda.empty_cache()
    gc.collect()
    logger.info("GPU memory cleared and garbage collection performed")

def process_articles_in_batches(text_analysis_class, method_name, articles, batch_size):
    """Process articles in batches using the specified text analysis class and method."""
    processor = text_analysis_class()
    method = getattr(processor, method_name)

    for i in range(0, len(articles), batch_size):
        logger.info(f"Processing batch {i // batch_size + 1} of {method_name} for articles {i} to {i + batch_size}")
        batch = articles[i:i + batch_size]
        
        try:
            batch = method(batch)
        except RuntimeError as e:
            if 'CUDA out of memory' in str(e):
                logger.error(f"CUDA OOM error while processing batch {i // batch_size + 1} during {method_name}")
                clear_gpu_memory()
            else:
                logger.error(f"Unexpected error during {method_name} in batch {i // batch_size + 1}: {str(e)}")
                clear_gpu_memory()

        articles[i:i + batch_size] = batch
        clear_gpu_memory()

    del processor
    clear_gpu_memory()
    logger.info(f"{method_name} processing completed for all articles")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Web scraper for various websites")
    parser.add_argument(
        "-w", "--website", required=True, choices=SCRAPER_MAP.keys(),
        help="The website to scrape (e.g., Spiegel, TOnline)"
    )
    parser.add_argument(
        "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)"
    )
    args = parser.parse_args()

    # Configure logging
    logger = configure_logging(args.log_level)

    try:
        logger.info(f"Initializing scraper for {args.website}")
        
        # Get the scraper class dynamically based on the website argument
        scraper_class = get_scraper_class(args.website)
        scraper = scraper_class(headless=True)
        
        logger.info(f"Starting browser and logging in to scraper for {args.website}")
        scraper.start_browser()
        scraper.login()

        logger.info(f"Getting all article URLs from {args.website} scraper")
        all_found_urls = scraper.get_article_urls()[0:20]
        logger.info(f"Found {len(all_found_urls)} article URLs from {args.website} scraper")

        keycloak_login = KeycloakLogin()
        token = keycloak_login.get_token()

        data_downloader = DataDownloader(token)

        batch_size = 30
        all_urls_already_in_db = []

        for i in range(0, len(all_found_urls), batch_size):
            current_batch = all_found_urls[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1}: URLs {i} to {i + batch_size}")

            try:
                response = data_downloader.get_content_rehydrate(url=current_batch)
                batch_urls = [item['url'] for item in response.get('items', [])]
                all_urls_already_in_db.extend(batch_urls)
                logger.info(f"Batch {i // batch_size + 1} processed.")
            except Exception as e:
                logger.error(f"Error processing batch {i // batch_size + 1}: {str(e)}", exc_info=True)

        logger.info(f"Total URLs already in the DB: {len(all_urls_already_in_db)}")

        token = keycloak_login.get_token()

        data_uploader = DataUploader(token)

        logger.info("Patching last online verification dates for URLs already in DB")
        try:
            data_uploader.patch_last_online_verification_date(all_urls_already_in_db)
            logger.info("Successfully patched last online verification dates")
        except Exception as e:
            logger.error(f"Error during patching last online verification dates: {str(e)}", exc_info=True)

        token = keycloak_login.get_token()

        articles_list_for_new_scraping = [url for url in all_found_urls if url not in all_urls_already_in_db]
        logger.info(f"Found {len(articles_list_for_new_scraping)} new articles to scrape")

        try:
            articles = scraper.scrape(articles_list_for_new_scraping)
            logger.info(f"Successfully scraped {len(articles)} new articles")
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}", exc_info=True)

        process_articles_in_batches(NEExtractor, 'extract_entities', articles, 100)
        process_articles_in_batches(TopicExtractor, 'extract_topics', articles, 100)

        # Catch CUDA OOM errors specifically during vectorization
        process_articles_in_batches(Vectorizer, 'vectorize', articles, 100)

        process_articles_in_batches(Summarizer, 'summarize', articles, 100)

        for article in articles:
            article.pop('main_text', None)
            article.pop('lead_text', None)

        token = keycloak_login.get_token()
        data_uploader = DataUploader(token)
        responses = []
        for article in articles:
            try:
                response = data_uploader.post_content(article)
                responses.append(response)
                logger.info(f"Successfully uploaded article: {article.get('url', 'N/A')}")
            except Exception as e:
                logger.error(f"Error uploading article {article.get('url', 'N/A')}: {str(e)}", exc_info=True)

        with open('responses.json', 'w') as f:
            json.dump(responses, f)

        logger.info("Article upload completed.")

    except Exception as e:
        logger.critical(f"Critical error in the process: {str(e)}", exc_info=True)

    finally:
        gc.collect()
        logger.info("Process completed")
