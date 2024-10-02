from database_handling.DataDownload import DataDownloader
from database_handling.DataUpload import DataUploader
from database_handling.KeycloakLogin import KeycloakLogin
from scrapers.BayerischerRundfunkScraper import BayerischerRundfunkScraper 

from text_analysis.NEExtractor import NEExtractor
from text_analysis.Summarizer import Summarizer
from text_analysis.TopicExtractor import TopicExtractor
from text_analysis.Vectorizers import Vectorizer

from selenium.webdriver.common.by import By
import transformers
import json
import gc
import torch
import logging

# Configure logging settings to write to both console and a log file
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("process.log"),  # Writes logs to 'process.log'
        logging.StreamHandler()  # Prints logs to the console
    ]
)
logger = logging.getLogger(__name__)

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
        batch = method(batch)

        # Reassign the processed batch back to the main list
        articles[i:i + batch_size] = batch

        logger.info(f"Batch {i // batch_size + 1} of {method_name} completed")
        clear_gpu_memory()  # Clear memory after each batch

    del processor  # Delete the processor instance to free up GPU memory
    clear_gpu_memory()
    logger.info(f"{method_name} processing completed for all articles")

try:
    logger.info("Initializing scraper with headless mode")
    scraper = BayerischerRundfunkScraper(headless=True)

    logger.info("Starting browser and clickling cookie banner.")
    scraper.start_browser()
    # in the other scrapers the navigate_to function is called in the login() function
    # since bayerischer rundfunk does not have a paywall and login, we just navigate to the start page
    scraper.navigate_to("https://www.br.de/nachrichten/")
    scraper.click_cookie_button()

    logger.info("Getting all article URLs from the scraper")
    all_found_urls = scraper.get_article_urls()
    logger.info(f"Found {len(all_found_urls)} article URLs from the scraper")

    # Get the token for the database
    logger.info("Attempting Keycloak login to obtain token")
    keycloak_login = KeycloakLogin()
    token = keycloak_login.get_token()
    logger.info("Successfully retrieved token")

    data_downloader = DataDownloader(token)

    batch_size = 30
    all_urls_already_in_db = []

    logger.info(f"Processing URLs in batches of {batch_size}")

    # Loop through all the URLs in chunks of batch_size
    for i in range(0, len(all_found_urls), batch_size):
        current_batch = all_found_urls[i:i + batch_size]
        logger.info(f"Processing batch {i // batch_size + 1}: URLs {i} to {i + batch_size} out of {len(all_found_urls)}")

        try:
            # Fetch data for the current batch
            response = data_downloader.get_content_rehydrate(url=current_batch)
            logger.info(f"Received response for batch {i // batch_size + 1}")

            # Extract URLs from the 'items' in the response
            batch_urls = [item['url'] for item in response.get('items', [])]
            all_urls_already_in_db.extend(batch_urls)
            logger.info(f"Batch {i // batch_size + 1} processed. URLs in DB: {len(batch_urls)}")

        except Exception as e:
            logger.error(f"Error processing batch {i // batch_size + 1}: {str(e)}", exc_info=True)

    logger.info(f"Total URLs already in the DB: {len(all_urls_already_in_db)}")

    # Refresh the token
    logger.info("Refreshing Keycloak token before data upload")
    token = keycloak_login.get_token()

    data_uploader = DataUploader(token)

    # Patch the last online verification date for the URLs already in the DB
    logger.info("Patching last online verification dates for URLs that are already in the database")
    try:
        responses_for_last_online_verification_date_patch = data_uploader.patch_last_online_verification_date(all_urls_already_in_db)
        logger.info(f"Successfully patched last online verification dates for {len(all_urls_already_in_db)} URLs")
    except Exception as e:
        logger.error(f"Error during patching last online verification dates: {str(e)}", exc_info=True)

    # Refresh the token again if necessary
    logger.info("Refreshing Keycloak token again")
    token = keycloak_login.get_token()

    # Filter URLs for new scraping
    logger.info("Filtering URLs for new scraping")
    articles_list_for_new_scraping = [url for url in all_found_urls if url not in all_urls_already_in_db]
    logger.info(f"Found {len(articles_list_for_new_scraping)} new articles to scrape")

    # Scrape new articles
    logger.info("Starting scraping for new articles")
    try:
        articles = scraper.scrape(articles_list_for_new_scraping)
        logger.info(f"Successfully scraped {len(articles)} new articles")
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}", exc_info=True)

    # Processing articles with NEExtractor
    logger.info("Starting entity extraction...")
    process_articles_in_batches(NEExtractor, 'extract_entities', articles, 100)
    logger.info("Entity extraction completed")

    # Processing articles with TopicExtractor
    logger.info("Starting topic extraction...")
    process_articles_in_batches(TopicExtractor, 'extract_topics', articles, 100)
    logger.info("Topic extraction completed")

    # Processing articles with Vectorizer and handling CUDA OOM errors without stopping the script
    logger.info("Starting vectorization...")
    vectorizer_processor = Vectorizer()
    vectorize_method = getattr(vectorizer_processor, 'vectorize')

    for idx, article in enumerate(articles):
        try:
            logger.info(f"Vectorizing article {idx + 1}/{len(articles)}: {article.get('url', 'N/A')}")
            # Run vectorization for the current article
            articles[idx] = vectorize_method([article])[0]
        except RuntimeError as e:
            if 'CUDA out of memory' in str(e):
                logger.error(f"CUDA OOM error while vectorizing article {idx + 1} with URL: {article.get('url', 'N/A')}")
                clear_gpu_memory()  # Clear GPU memory and log the event
                # Skip to the next article without stopping
            else:
                logger.error(f"Unexpected error while vectorizing article {idx + 1} with URL: {article.get('url', 'N/A')}: {str(e)}")
                clear_gpu_memory()  # Ensure memory is cleared even for non-OOM errors
                # Continue with the next article without raising an error

    # Clean up after vectorization
    del vectorizer_processor
    clear_gpu_memory()
    logger.info("Vectorization completed.")

    # Processing articles with Summarizer
    logger.info("Starting summarization...")
    summarizer_processor = Summarizer()
    summarize_method = getattr(summarizer_processor, 'summarize')

    for idx, article in enumerate(articles):
        try:
            logger.info(f"Summarizing article {idx + 1}/{len(articles)}: {article.get('url', 'N/A')}")
            # Run summarization for the current article
            articles[idx] = summarize_method([article])[0]
        except RuntimeError as e:
            if 'CUDA out of memory' in str(e):
                logger.error(f"CUDA OOM error while summarizing article {idx + 1} with URL: {article.get('url', 'N/A')}")
                clear_gpu_memory()  # Clear GPU memory and log the event
                # Skip to the next article without stopping
            else:
                logger.error(f"Unexpected error while summarizing article {idx + 1} with URL: {article.get('url', 'N/A')}: {str(e)}")
                clear_gpu_memory()  # Ensure memory is cleared even for non-OOM errors
                # Continue with the next article without raising an error

    # Clean up after summarization
    del summarizer_processor
    clear_gpu_memory()
    logger.info("Summarization completed.")

    # Remove main_text and lead_text from articles to save space before uploading
    logger.info("Removing main_text and lead_text from articles to save space")
    for article in articles:
        article.pop('main_text', None)
        article.pop('lead_text', None)
        
    logger.info("Saving articles to drive")
    with open('articles.json', 'w') as f:
        json.dump(articles, f)
    
    logger.info("Refreshing Keycloak token again")
    token = keycloak_login.get_token()
    # Upload each article to the database without batching
    logger.info("Beginning article upload")
    responses = []
    data_uploader = DataUploader(token)
    # TODO: Error chatching, check response code when uploading
    for article in articles:
        try:
            response = data_uploader.post_content(article)
            responses.append(response)
            logger.info(f"Successfully uploaded article: {article.get('url', 'N/A')}")
        except Exception as e:
            logger.error(f"Error uploading article {article.get('url', 'N/A')}: {str(e)}", exc_info=True)
   
    # Save the responses to a JSON file
    with open('responses.json', 'w') as f:
        json.dump(responses, f)
    
    logger.info(f"Article upload completed. Total articles uploaded: {len(responses)}")


except Exception as e:
    logger.critical(f"Critical error in the process: {str(e)}", exc_info=True)

finally:
    # Cleanup and free up resources
    logger.info("Performing garbage collection")
    gc.collect()
    logger.info("Process completed")
