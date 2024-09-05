from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException, StaleElementReferenceException
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from database_handling.DataDownload import DataDownloader
from database_handling.DataUpload import DataUploader
from database_handling.DataHandleAndOtherHelpers import DataHandler
from config import WEBSITE_STRATEGIES, CREDENTIALS_PATH
import trafilatura
import json
from sklearn.feature_extraction.text import CountVectorizer
from datetime import datetime
from bs4 import BeautifulSoup
import time
import requests
from requests.exceptions import RequestException
import logging
from trafilatura.settings import use_config
import os
from typing import List, Tuple, Optional, Dict, Any
from abc import ABC, abstractmethod
import re
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseScraper:
    """Base class for all scrapers"""

    def __init__(self, headless: bool = True, timeout: int = 10):
        """Initialize the scraper with default attributes"""
        self.driver: Optional[webdriver.Firefox] = None
        self.wait: Optional[WebDriverWait] = None
        self.email: Optional[str] = None
        self.password: Optional[str] = None
        self.url: Optional[str] = None
        self.crawler_version: str = "0.1"
        self.headless: bool = headless
        self.timeout: int = timeout
        self.article_url_pattern = r'PLACEHOLDER_FOR_ARTICLE_URL_PATTERN'
        self.subpage_url_pattern = r'PLACEHOLDER_FOR_SUBPAGE_URL_PATTERN'
    
    def get_credentials(self, path: str) -> Tuple[str, str]:
        """Get the credentials from a file"""
        try:
            with open(path, "r") as f:
                credentials = f.read().splitlines()
            return credentials[0], credentials[1]
        except FileNotFoundError as e:
            logger.error(f"Credentials file not found: {e}")
            raise

    def start_browser(self):
        """Start the browser and initialize the WebDriver and WebDriverWait instances"""
        if self.headless:
            geckodriver_path = '/usr/local/bin/geckodriver'
            firefox_binary_path = '/usr/bin/firefox'

            firefox_options = Options()
            firefox_options.binary_location = firefox_binary_path
            firefox_options.add_argument("--no-sandbox")
            firefox_options.add_argument("--disable-dev-shm-usage")
            firefox_options.add_argument('--window-size=1920,1080')
            firefox_options.add_argument("--dns-prefetch-disable")
            firefox_options.add_argument("--disable-features=VizDisplayCompositor")
            firefox_options.add_argument("--headless")
            try:
                service = Service(geckodriver_path)
                self.driver = webdriver.Firefox(service=service, options=firefox_options)
                self.wait = WebDriverWait(self.driver, 3)
                logger.info("Browser started successfully")
            except WebDriverException as e:
                logger.error(f"Failed to start browser: {e}")
                raise
        else:
            self.driver = webdriver.Firefox()
            # Initialize the WebDriverWait instance here
            self.wait = WebDriverWait(self.driver, 3)

    def close_browser(self):
        """Close the browser and end the session"""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed successfully")

    def navigate_to(self, url: str):
        """Navigate to a specific URL and check for HTTP status."""
        try:
            # Check the HTTP status code before navigating
            response = requests.head(url, allow_redirects=True)
            if response.status_code == 404:
                logger.warning(f"404 Not Found for URL: {url}. Skipping navigation.")
                return  # Skip navigation if the page is not found

            # If the status code is OK, proceed to navigate
            self.url = url
            self.driver.get(self.url)
            logger.info(f"Navigated to {url}")
        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")

    def _get_all_urls_on_current_page(self) -> List[str]:
        """Get all URLs from the current page."""
        try:
            # Wait for the body element to be present, which indicates the page has loaded
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            
            # Use JavaScript to get all URLs
            urls = self.driver.execute_script('''
                return Array.from(document.links).map(a => a.href).filter(Boolean);
            ''')
            
            return urls
        except TimeoutException as e:
            logger.error(f"Timeout while getting URLs on current page: {e}")
            return []

    def wait_for_element(self, by: By, value: str, timeout: int = 10):
        """Wait for a specific element to be loaded on the page"""
        try:
            element_present = EC.presence_of_element_located((by, value))
            self.wait.until(element_present)
            logger.info(f"Element {value} found")
        except TimeoutException as e:
            logger.error(f"Timeout while waiting for element {value}: {e}")
            raise

    def find_element(self, strategies: List[Tuple[str, str]]) -> webdriver.Firefox.find_element:
        """Find an element on the page using the strategies defined in the config"""
        found_element = None
        last_exception = None

        for strategy, locator in strategies:
            try:
                # Use the strategy to locate the element
                element = self.wait.until(EC.presence_of_element_located((By.__dict__[strategy.replace(' ', '_').upper()], locator)))
                if element:
                    found_element = element
                    break
            except (NoSuchElementException, TimeoutException) as e:
                last_exception = e
                continue

        if found_element:
            return found_element
        elif last_exception:
            logger.error(f"Element not found using any strategy: {last_exception}")
            raise last_exception
        else:
            raise NoSuchElementException("Element not found using any strategy")

    def click_element(self, strategy: List[Tuple[str, str]]):
        """Click an element on the page"""
        element = self.find_element(strategy)
        element.click()
        logger.info(f"Clicked element with strategy: {strategy}")

    def input_text(self, element: webdriver.Firefox.find_element, text: str):
        """Input text into a field on the page"""
        element.clear()
        element.send_keys(text)
        input_value = element.get_attribute('value')

        if input_value != text:
            logger.error(f"Input text was not successfully entered into the field.")
            raise ValueError(f"Input text was not successfully entered into the field.")
        logger.info(f"Input text successfully entered into the field.")

    def enter_email(self, email: str, email_strategy: List[Tuple[str, str]] = WEBSITE_STRATEGIES["spiegel"]["email_username"]):
        """Enter the email into the email field using the strategies defined in the config"""
        elem_email_username = self.find_element(email_strategy)
        self.input_text(elem_email_username, email)

    def enter_password(self, password: str, password_strategy: List[Tuple[str, str]] = WEBSITE_STRATEGIES["spiegel"]["password"]):
        """Enter the password into the password field using the strategies defined in the config"""
        elem_password = self.find_element(password_strategy)
        self.input_text(elem_password, password)

    def click_submit(self, submit_strategy: List[Tuple[str, str]] = WEBSITE_STRATEGIES["spiegel"]["submit"]):
        """Click the submit button using the strategies defined in the config"""
        elem_submit = self.find_element(submit_strategy)
        elem_submit.click()

    def _get_page_source(self) -> str:
        """Get the page source using JavaScript for better performance."""
        try:
            # Execute JavaScript to get the outer HTML of the entire document
            html_content = self.driver.execute_script("return document.documentElement.outerHTML;")
            return html_content
        except Exception as e:
            logger.error(f"Error getting page source using JavaScript: {e}")
            # Fallback to the default method if JavaScript execution fails
            return self.driver.page_source

    def _extract_content(self) -> Dict[str, Optional[str]]:
        """Extract the main content from where the driver is currently at using trafilatura."""
        html_content = self._get_page_source()

        # Preprocess HTML content with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        # self._remove_duplicate_sections(soup)
        cleaned_html = str(soup)
        # write html_content to a file
        # with open("html_content.html", "w") as f:
        #     f.write(html_content)
        # # write soup to a file
        # with open("soup.html", "w") as f:
        #     f.write(str(soup))
        # # write cleaned_html to a file
        # with open("cleaned_html.html", "w") as f:
        #     f.write(cleaned_html)

        # Initialize and configure trafilatura settings
        config = use_config()
        config.set("DEFAULT", "EXTRACTION", "true")
        config.set("DEFAULT", "STRICT", "true")
        config.set("DEFAULT", "ADVANCED_FILTER", "true")
        config.set("DEFAULT", "ADBLOCK_FILTERING", "true")
        config.set("DEFAULT", "NO_FOOTER", "true")
        config.set("DEFAULT", "EXCLUDE_ELEMENTS", "div.advertisement, aside.sidebar")
        config.set("DEFAULT", "BLACKLIST_ELEMENTS", "div.cookie-consent, div.pop-up")
        config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
        config.set("DEFAULT", "EXTRACTION_KEYWORDS_THRESHOLD", "0.5")
        config.set("DEFAULT", "EXTRACTION_KEYWORDS_EXCLUDE", "advertisement, promo")
        config.set("DEFAULT", "EXTRACTION_KEYWORDS_EXCLUDE_THRESHOLD", "0.5")
        config.set("DEFAULT", "EXTRACTION_KEYWORDS_EXCLUDE_ELEMENTS", "div.advertisement, aside.sidebar")
        config.set("DEFAULT", "EXTRACTION_KEYWORDS_EXCLUDE_ELEMENTS_THRESHOLD", "0.5")
        config.set("DEFAULT", "EXTRACTION_KEYWORDS_INCLUDE_ELEMENTS", "div.article, section.content")
        config.set("DEFAULT", "EXTRACTION_KEYWORDS_INCLUDE_ELEMENTS_THRESHOLD", "0.5")
        config.set("DEFAULT", "DEDUPLICATE", "true")
        config.set("DEFAULT", "FAVOR_PRECISION", "true")

        try:
            # Extract main text using trafilatura with the configured settings
            main_text = trafilatura.extract(cleaned_html, config=config)
            main_text = main_text.replace('\n', ' ') if main_text else None
        except (ValueError, TypeError) as e:
            logger.error(f"An error occurred during main text extraction: {e}")
            main_text = None

        try:
            # Extract metadata using trafilatura with the configured settings
            extracted_metadata = trafilatura.extract_metadata(cleaned_html)
            lead_text = extracted_metadata.description.replace('\n', ' ') if extracted_metadata and extracted_metadata.description else ''
            url = self.driver.current_url
            extracted_url = extracted_metadata.url if extracted_metadata else None
            if url != extracted_url:
                logger.warning(f"URL mismatch: Driver URL '{url}' differs from extracted URL '{extracted_url}'")
        except (ValueError, TypeError) as e:
            logger.error(f"An error occurred during metadata extraction: {e}")
            lead_text = ''
            url = None

        # Create a dictionary with the extracted content and metadata
        content_dict = {
            "url": url,
            "main_text": main_text,
            "lead_text": lead_text,
            "last_online_verification_date": datetime.now().isoformat(),
        }

        return content_dict
    
    # def _remove_duplicate_sections(self, soup):
    #     """Some news websites use scrolling elements where text only scrolls into view. This leads to duplicate sections in the HTML content.
    #     This function removes duplicate sections from the HTML content.
    #     """
    #     # Create a dictionary to store hashes of content
    #     content_hashes = {}
        
    #     # Find all div elements (adjust selector as needed)
    #     for div in soup.find_all('div', class_='slide-container'):
    #         # Generate a hash of the div's content
    #         content_hash = hashlib.md5(div.encode_contents().strip()).hexdigest()
            
    #         # If we've seen this content before, remove the element
    #         if content_hash in content_hashes:
    #             div.decompose()
    #         else:
    #             content_hashes[content_hash] = True

    def check_for_paywall(self) -> bool:
        """Check if the page is paywalled using JavaScript."""
        try:
            return self.driver.execute_script('''
                return Boolean(document.querySelector('.paywall, .paid-content, #paywall-container'));
            ''')
        except Exception as e:
            logger.error(f"Error checking for paywall using JavaScript: {e}")
            return False

    def save_extracted_data(self) -> None:
        """Save the extracted data to a file"""
        filename = "extracted_data.json"
        content_dict = self._extract_content()
        with open(filename, "w") as f:
            json.dump(content_dict, f)
        logger.info(f"Extracted data saved to {filename}")

    def retry_request(self, url: str, retries: int = 3, delay: int = 5) -> requests.Response:
        """Retry logic for network requests"""
        for attempt in range(retries):
            try:
                response = requests.get(url)
                response.raise_for_status()
                return response
            except RequestException as e:
                logger.error(f"Request failed: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
        raise RequestException(f"Failed to fetch {url} after {retries} attempts")

    def patch_last_online_verification_date(self, data_uploader: DataUploader, urls: List[str]) -> List[requests.Response]:
        """Update the last online verification date for multiple URLs"""
        start_time = datetime.now()
        logger.info(f"Starting patch_last_online_verification_date for {len(urls)} URLs at {start_time.isoformat()}")
        new_last_online_verification_date = datetime.now().isoformat()
        data = {"last_online_verification_date": new_last_online_verification_date}

        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(data_uploader.patch_content, url=url, data=data) for url in urls]
            responses = [future.result() for future in as_completed(futures)]

        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"patch_last_online_verification_date completed at {end_time.isoformat()}")
        logger.info(f"Total duration: {duration.total_seconds():.3f} seconds for {len(urls)} URLs")
        logger.info(f"Average time per URL: {(duration.total_seconds() / len(urls)):.3f} seconds")

        return responses

    def reverify_articles(self, urls: List[str], keycloak_token: str) -> List[str]:
        """Reverify articles and update last_online_verification_date for those in the database"""
        start_time = datetime.now()
        logger.info(f"Starting reverify_articles for {len(urls)} URLs at {start_time.isoformat()}")
        data_downloader = DataDownloader(keycloak_token)
        data_uploader = DataUploader(keycloak_token)
        articles_in_db = []
        articles_not_in_db = []

        def process_url(url):
            url_start_time = datetime.now()
            status_code = data_downloader.get_content_rehydrate_status_code_only(url=url)
            if status_code == 200:
                logger.info(f"Article found in the database: {url}. Status code: {status_code}")
                articles_in_db.append(url)
            else:
                logger.info(f"Article not found in the database: {url}. Status code: {status_code}")
                articles_not_in_db.append(url)
            url_end_time = datetime.now()
            logger.debug(f"Processed URL {url} in {(url_end_time - url_start_time).total_seconds():.3f} seconds")

        with ThreadPoolExecutor(max_workers=30) as executor:
            list(executor.map(process_url, urls))

        if articles_in_db:
            patch_start_time = datetime.now()
            self.patch_last_online_verification_date(data_uploader, articles_in_db)
            patch_end_time = datetime.now()
            logger.info(f"Updated last_online_verification_date for {len(articles_in_db)} articles in the database")
            logger.info(f"Patch operation took {(patch_end_time - patch_start_time).total_seconds():.3f} seconds")

        end_time = datetime.now()
        total_duration = end_time - start_time
        logger.info(f"reverify_articles completed at {end_time.isoformat()}")
        logger.info(f"Total duration: {total_duration.total_seconds():.3f} seconds for {len(urls)} URLs")
        logger.info(f"Average time per URL: {(total_duration.total_seconds() / len(urls)):.3f} seconds")

        return articles_not_in_db

    # def reverify_articles(self, urls: List[str], keycloak_token: str) -> List[str]:
    #     """Reverify articles that are already in the database.
        
    #     This method takes a list of URLs that the scraper found on the website,
    #     checks which of these URLs are already in the database, updates the
    #     last_online_verification_date field for these articles in the database, and returns
    #     a list of articles that are NOT already in the database.
    #     """
    #     data_downloader = DataDownloader(keycloak_token)
    #     data_uploader = DataUploader(keycloak_token)
    #     articles_in_db = []
    #     articles_not_in_db = []

    #     def process_url(url):
    #         status_code = data_downloader.get_content_rehydrate_status_code_only(url=url)
    #         if status_code == 200:
    #             articles_in_db.append(url)
    #             self.patch_last_online_verification_date(data_uploader, [url])
    #             logger.info(f"Article reverified and updated last_online_verification_date: {url}")
    #         else:
    #             articles_not_in_db.append(url)

    #     with ThreadPoolExecutor(max_workers=10) as executor:  # Adjust max_workers as needed
    #         list(executor.map(process_url, urls))

    #     return articles_not_in_db
    
    def _get_all_article_urls_on_current_page(self) -> List[str]:
        """Get all article URLs from the current page

        Returns:
            List[str]: A list of article URLs found on the current page.
        """
        try:
            article_urls = self.driver.execute_script(f'''
                const pattern = new RegExp('{self.article_url_pattern}');
                return Array.from(document.links)
                    .map(a => a.href)
                    .filter(url => pattern.test(url));
            ''')
            logger.info(f"Found {len(article_urls)} article URLs on the current page: {self.driver.current_url}")
            return article_urls
        except Exception as e:
            logger.error(f"Error getting article URLs using JavaScript: {e}")
            return []

    def _get_subpage_urls_on_current_page(self) -> List[str]:
        """Get all unique subpage URLs from the current page using JavaScript."""
        try:
            subpage_urls = self.driver.execute_script(f'''
                const pattern = new RegExp('{self.subpage_url_pattern}');
                return [...new Set(Array.from(document.links)
                    .map(a => a.href)
                    .filter(url => pattern.test(url)))];
            ''')
            return subpage_urls
        except Exception as e:
            logger.error(f"Error getting subpage URLs using JavaScript: {e}")
            return []

    def _get_all_article_urls_on_subpages(self) -> List[str]:
        """Get all article URLs from the subpages
        
        Returns:
            List[str]: A list of all article URLs found on subpages.
        """
        # Get all subpage URLs from the current page
        subpage_urls = self._get_subpage_urls_on_current_page()
        all_article_urls = []  # Initialize a list to store all article URLs
        
        # Iterate through each subpage URL
        for url in subpage_urls:
            try:
                # Navigate to the subpage
                self.navigate_to(url)
                # Collect article URLs from the subpage
                all_article_urls += self._get_all_article_urls_on_current_page()
            except StaleElementReferenceException:
                # Log a warning if a stale element reference exception occurs
                logger.warning(f"StaleElementReferenceException occurred while navigating to {url}")
                continue  # Skip to the next URL if an exception occurs
        return all_article_urls
        
    def get_article_urls(self) -> List[str]:
        """Get all unique article URLs from the main page and subpages

        Returns:
            List[str]: A list of all unique article URLs.
        """
        # Navigate to the base URL of the scraper
        self.navigate_to(self.base_url)
        # Get article URLs from the main page
        article_urls_from_startpage = self._get_all_article_urls_on_current_page()
        # Get article URLs from subpages
        article_urls_from_subpages = self._get_all_article_urls_on_subpages()
        # Combine and deduplicate the URLs using a set
        all_article_urls = list(dict.fromkeys(article_urls_from_startpage + article_urls_from_subpages))
        return all_article_urls

    # def _extract_content(self) -> Dict[str, Optional[str]]:
    #     """Extract the main content from the current page using trafilatura."""
    #     html_content = self._get_page_source()

    #     # Preprocess HTML content with BeautifulSoup
    #     soup = BeautifulSoup(html_content, 'html.parser')
    #     cleaned_html = str(soup)

    #     # Initialize and configure trafilatura settings
    #     config = use_config()
    #     config.set("DEFAULT", "EXTRACTION", "true")
    #     config.set("DEFAULT", "STRICT", "true")
    #     config.set("DEFAULT", "ADVANCED_FILTER", "true")
    #     config.set("DEFAULT", "ADBLOCK_FILTERING", "true")
    #     config.set("DEFAULT", "NO_FOOTER", "true")
    #     config.set("DEFAULT", "EXCLUDE_ELEMENTS", "div.advertisement, aside.sidebar")
    #     config.set("DEFAULT", "BLACKLIST_ELEMENTS", "div.cookie-consent, div.pop-up")
    #     config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
    #     config.set("DEFAULT", "EXTRACTION_KEYWORDS_THRESHOLD", "0.5")
    #     config.set("DEFAULT", "EXTRACTION_KEYWORDS_EXCLUDE", "advertisement, promo")
    #     config.set("DEFAULT", "EXTRACTION_KEYWORDS_EXCLUDE_THRESHOLD", "0.5")
    #     config.set("DEFAULT", "EXTRACTION_KEYWORDS_EXCLUDE_ELEMENTS", "div.advertisement, aside.sidebar")
    #     config.set("DEFAULT", "EXTRACTION_KEYWORDS_EXCLUDE_ELEMENTS_THRESHOLD", "0.5")
    #     config.set("DEFAULT", "EXTRACTION_KEYWORDS_INCLUDE_ELEMENTS", "div.article, section.content")
    #     config.set("DEFAULT", "EXTRACTION_KEYWORDS_INCLUDE_ELEMENTS_THRESHOLD", "0.5")

    #     try:
    #         # Extract main text using trafilatura with the configured settings
    #         main_text = trafilatura.extract(cleaned_html, config=config)
    #         main_text = main_text.replace('\n', ' ') if main_text else None
    #     except (ValueError, TypeError) as e:
    #         logger.error(f"An error occurred during main text extraction: {e}")
    #         main_text = None

    #     try:
    #         # Extract metadata using trafilatura with the configured settings
    #         extracted_metadata = trafilatura.extract_metadata(cleaned_html)
    #         lead_text = extracted_metadata.description.replace('\n', ' ') if extracted_metadata and extracted_metadata.description else ''
    #         url = self.driver.current_url
    #         extracted_url = extracted_metadata.url if extracted_metadata else None
    #         if url != extracted_url:
    #             logger.warning(f"URL mismatch: Driver URL '{url}' differs from extracted URL '{extracted_url}'")
    #     except (ValueError, TypeError) as e:
    #         logger.error(f"An error occurred during metadata extraction: {e}")
    #         lead_text = ''
    #         url = None

    #     # Create a dictionary with the extracted content and metadata
    #     content_dict = {
    #         "url": url,
    #         "main_text": main_text,
    #         "lead_text": lead_text,
    #         "last_online_verification_date": datetime.now().isoformat(),
    #     }

    #     return content_dict
    
    def scrape(self, urls_to_scrape: List[str]) -> List[Dict[str, Any]]:
        """Scrape articles from the Spiegel website
        
        Args:
            keycloak_token: The token used for article verification.
            urls_to_scrape: The list of URLs to scrape.
        
        Returns:
            List[dict]: A list of dictionaries containing article content and metadata.
        """

        all_articles_content = []  # Initialize a list to store the content of all articles

        # Iterate through each URL to scrape content
        for url in urls_to_scrape:
            try:
                # Navigate to the article URL
                self.navigate_to(url)
                # Extract content and metadata from the article
                article_content_and_metadata = self._extract_content()
                # Add additional metadata
                article_content_and_metadata["medium"] = {"readable_id": self.crawler_medium}
                article_content_and_metadata["crawler_medium"] = self.crawler_medium
                article_content_and_metadata["crawler_version"] = "0.1"
                # Append the content to the results list
                all_articles_content.append(article_content_and_metadata)
                logger.info(f"Extracted content from {url}")  # Log successful extraction
            except Exception as e:
                # Log an error if content extraction fails
                logger.error(f"Failed to extract content from {url}: {e}")

        # Close the browser after scraping
        self.close_browser()
        return all_articles_content
    


