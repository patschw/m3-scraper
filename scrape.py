import json
import os
import logging
import argparse
from tqdm import tqdm
from database_handling.DataDownload import DataDownloader
from database_handling.DataUpload import DataUploader
from database_handling.KeycloakLogin import KeycloakLogin
from config import SCRAPER_MAP
import importlib
from kafka_queue.kafka_manager import KafkaQueue  # Import the KafkaQueue class

def configure_logging(log_level):
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("scraper.log"),
            logging.StreamHandler()
        ]
    )

def get_scraper_class(website):
    """Dynamically imports and returns the scraper class based on the website name."""
    try:
        if website not in SCRAPER_MAP:
            raise ValueError(f"No scraper available for website: {website}")
        
        module_name, class_name = SCRAPER_MAP[website].rsplit('.', 1)
        module = importlib.import_module(module_name)
        scraper_class = getattr(module, class_name)
        logging.info(f"Successfully loaded scraper class for {website}")
        return scraper_class
    except Exception as e:
        logging.error(f"Error loading scraper class for {website}: {e}")
        raise

def check_and_download(website):
    try:
        # logging.info(f"Starting URL gathering for {website}")
        
        # # Initialize scraper
        # scraper_class = get_scraper_class(website)
        # scraper = scraper_class(headless=True)
        # scraper.start_browser()
        # scraper.login()
        # logging.info("Browser started and logged in")

        # # Scrape URLs
        # all_found_urls = scraper.get_article_urls()[0:20]
        # logging.info(f"Found {len(all_found_urls)} URLs")

        # Check which URLs are already in the database
        # logging.info("Checking for existing URLs in the database")
        # keycloak_login = KeycloakLogin()
        # token = keycloak_login.get_token()
        # data_downloader = DataDownloader(token)
        
        # batch_size = 30
        # all_urls_already_in_db = []
        # for i in tqdm(range(0, len(all_found_urls), batch_size), desc="Checking URL batches"):
        #     current_batch = all_found_urls[i:i + batch_size]
        #     try:
        #         response = data_downloader.get_content_rehydrate(url=current_batch)
        #         batch_urls = [item['url'] for item in response.get('items', [])]
        #         all_urls_already_in_db.extend(batch_urls)
        #     except Exception as e:
        #         logging.error(f"Error checking batch {i // batch_size + 1}: {e}")

        # logging.info(f"Found {len(all_urls_already_in_db)} existing URLs in the database")

        # token = keycloak_login.get_token()
        # data_uploader = DataUploader(token)

        # logging.info("Patching last online verification dates for URLs already in DB")
        
        # if all_urls_already_in_db:
        #     try:
        #         data_uploader.patch_last_online_verification_date(all_urls_already_in_db)
        #         logging.info("Successfully patched last online verification dates")
        #     except Exception as e:
        #         logging.error(f"Error during patching last online verification dates: {str(e)}", exc_info=True)
        # else:
        #     logging.info("No URLs to patch for last online verification dates")

        # articles_list_for_new_scraping = [url for url in all_found_urls if url not in all_urls_already_in_db]
        

        # Filter new URLs
        # new_urls = [url for url in all_found_urls if url not in all_urls_already_in_db]
        # logging.info(f"Found {len(new_urls)} new URLs to scrape")

        # Initialize Kafka queue
        kafka_queue = KafkaQueue()

        # Download content for new URLs
        # new_content = []
        try:
            # Scrape content for new URLs
            # new_content = scraper.scrape(new_urls)

            #logging.debug(f"Scraped content for {len(new_urls)} URLs")

            # Prepare test data
            new_content = [
                {'main_text': 'Test article 1', 'lead_text': 'Lead text for article 1', 'url': 'http://testurl1.com'},
                {'main_text': 'Test article 2', 'lead_text': 'Lead text for article 2', 'url': 'http://testurl2.com'},
                {'main_text': 'Test article 3', 'lead_text': 'Lead text for article 3', 'url': 'http://testurl3.com'}
            ]

            # Send the entire batch of scraped articles to Kafka
            kafka_queue.enqueue(new_content)  # Send the entire list of articles to Kafka
            logging.info(f"New content sent to Kafka: {len(new_content)} articles")

        except Exception as e:
            logging.error(f"Error scraping new URLs: {e}")

    except Exception as e:
        logging.error(f"Error in check_and_download: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape articles from a specified website.")
    parser.add_argument("-w", "--website", required=True, help="The website to scrape.")
    parser.add_argument("-l", "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level (default: INFO)")
    args = parser.parse_args()

    configure_logging(args.log_level)
    try:
        check_and_download(args.website)
    except Exception as e:
        logging.critical(f"Critical error in main: {e}")
