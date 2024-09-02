from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseScraper:
    """Base class for all scrapers"""
    
    def __init__(self):
        """Initialize the scraper with default attributes"""
        self.driver = None
        self.wait = None
        self.email = None
        self.password = None
        self.url = None
        self.crawler_version = "0.1"
    
    def get_credentials(self, path):
        """Get the credentials from a file"""
        try:
            with open(path, "r") as f:
                credentials = f.read().splitlines()
            return credentials[0], credentials[1]
        except FileNotFoundError as e:
            logger.error(f"Credentials file not found: {e}")
            raise

    def start_browser(self, headless=True):
        """Start the browser and initialize the WebDriver and WebDriverWait instances"""
        if headless:
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

    def navigate_to(self, url):
        """Navigate to a specific URL"""
        try:
            self.url = url
            self.driver.get(self.url)
            logger.info(f"Navigated to {url}")
        except WebDriverException as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            raise

    def get_all_urls_on_current_page(self):
        """Get all URLs from the current page."""
        try:
            # Wait until all anchor elements are present
            self.wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, 'a')))
            # Execute JavaScript to get all href attributes from anchor elements
            urls = self.driver.execute_script('''
                return Array.from(document.querySelectorAll('a'))
                            .map(a => a.href)
                            .filter(href => href);
            ''')
            return [url for url in urls if url is not None]
        except TimeoutException as e:
            logger.error(f"Timeout while getting URLs on current page: {e}")
            return []

    def wait_for_element(self, by, value, timeout=10):
        """Wait for a specific element to be loaded on the page"""
        try:
            element_present = EC.presence_of_element_located((by, value))
            self.wait.until(element_present)
            logger.info(f"Element {value} found")
        except TimeoutException as e:
            logger.error(f"Timeout while waiting for element {value}: {e}")
            raise

    def find_element(self, strategies):
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

    def click_element(self, strategy):
        """Click an element on the page"""
        element = self.find_element(strategy)
        element.click()
        logger.info(f"Clicked element with strategy: {strategy}")

    def input_text(self, element, text):
        """Input text into a field on the page"""
        element.clear()
        element.send_keys(text)
        input_value = element.get_attribute('value')

        if input_value != text:
            logger.error(f"Input text '{text}' was not successfully entered into the field.")
            raise ValueError(f"Input text '{text}' was not successfully entered into the field.")
        logger.info(f"Input text '{text}' successfully entered into the field.")

    def enter_email(self, email, email_strategy=WEBSITE_STRATEGIES["spiegel"]["email_username"]):
        """Enter the email into the email field using the strategies defined in the config"""
        elem_email_username = self.find_element(email_strategy)
        self.input_text(elem_email_username, email)

    def enter_password(self, password, password_strategy=WEBSITE_STRATEGIES["spiegel"]["password"]):
        """Enter the password into the password field using the strategies defined in the config"""
        elem_password = self.find_element(password_strategy)
        self.input_text(elem_password, password)

    def click_submit(self, submit_strategy=WEBSITE_STRATEGIES["spiegel"]["submit"]):
        """Click the submit button using the strategies defined in the config"""
        elem_submit = self.find_element(submit_strategy)
        elem_submit.click()

    def _extract_content(self):
        """Extract the main content from where the driver is currently at using trafilatura."""
        html_content = self.driver.page_source

        # Preprocess HTML content with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        cleaned_html = str(soup)

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
        #config.set("DEFAULT", "EXTRACTION_MIN_LENGTH", "200")
        #config.set("DEFAULT", "EXTRACTION_MAX_LENGTH", "10000")
        #config.set("DEFAULT", "EXTRACTION_KEYWORDS", "news, article, content")
        config.set("DEFAULT", "EXTRACTION_KEYWORDS_THRESHOLD", "0.5")
        config.set("DEFAULT", "EXTRACTION_KEYWORDS_EXCLUDE", "advertisement, promo")
        config.set("DEFAULT", "EXTRACTION_KEYWORDS_EXCLUDE_THRESHOLD", "0.5")
        config.set("DEFAULT", "EXTRACTION_KEYWORDS_EXCLUDE_ELEMENTS", "div.advertisement, aside.sidebar")
        config.set("DEFAULT", "EXTRACTION_KEYWORDS_EXCLUDE_ELEMENTS_THRESHOLD", "0.5")
        config.set("DEFAULT", "EXTRACTION_KEYWORDS_INCLUDE_ELEMENTS", "div.article, section.content")
        config.set("DEFAULT", "EXTRACTION_KEYWORDS_INCLUDE_ELEMENTS_THRESHOLD", "0.5")

        try:
            # Extract main text using trafilatura with the configured settings
            main_text = trafilatura.extract(cleaned_html, config=config)
            if main_text:
                main_text = main_text.replace('\n', ' ')
            else:
                logger.warning("Failed to extract main text")
                main_text = None
        except (ValueError, TypeError) as e:
            logger.error(f"An error occurred during main text extraction: {e}")
            main_text = None

        try:
            # Extract metadata using trafilatura with the configured settings
            extracted_metadata = trafilatura.extract_metadata(cleaned_html, config=config)
        except (ValueError, TypeError) as e:
            logger.error(f"An error occurred during metadata extraction: {e}")
            extracted_metadata = None

        lead_text = ''
        if extracted_metadata:
            lead_text = extracted_metadata.description.replace('\n', ' ') if extracted_metadata.description else ''

        # Create a dictionary with the extracted content and metadata
        content_dict = {
            "url": extracted_metadata.url if extracted_metadata else None,
            "main_text": main_text,
            "lead_text": lead_text,
            "last_online_verification_date": datetime.now().isoformat(),
        }

        return content_dict

    def check_for_paywall(self, paywall_strategy=WEBSITE_STRATEGIES["spiegel"]["paywall"]):
        """Check if the page is paywalled"""
        original_wait = self.wait
        self.wait = WebDriverWait(self.driver, 1)

        try:
            if self.find_element(paywall_strategy):
                return True
        except (NoSuchElementException, TimeoutException):
            return False
        finally:
            self.wait = original_wait

    def save_extracted_data(self):
        """Save the extracted data to a file"""
        filename = "extracted_data.json"
        main_text_to_vectorize, lead_text_to_vectorize, return_url, author, date = self._extract_content()
        main_text_vectorized = self.vectorize_text(main_text_to_vectorize)
        lead_text_vectorized = self.vectorize_text(lead_text_to_vectorize)
        data = {
            "main_text_vector": main_text_vectorized,
            "lead_text_vector": lead_text_vectorized,
            "return_url": return_url,
            "author": author,
            "date": date
        }
        with open(filename, "w") as f:
            json.dump(data, f)
        logger.info(f"Extracted data saved to {filename}")

    def retry_request(self, url, retries=3, delay=5):
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

    def patch_last_online_verification_date(self, auth_token, scraped_urls_already_in_db):
        """Update the last online verification date in a content_dict"""
        data_uploader = DataUploader(auth_token)

        responses = []

        new_last_online_verification_date = datetime.now().isoformat()
        for url in scraped_urls_already_in_db:
            response = data_uploader.patch_content(url=url, data={"last_online_verification_date": new_last_online_verification_date})
            responses.append(response)

        return responses

    def reverify_articles(self, urls, keycloak_token):
        """Reverify articles that are already in the database.
        
        This method takes a list of URLs that the scraper found on the website,
        checks which of these URLs are already in the database, updates the
        last_online_verification_date field for these articles in the database, and returns
        a list of articles that are NOT already in the database.
        """
        # Initialize DataDownloader to interact with the database
        data_downloader = DataDownloader(keycloak_token)

        # Rehydrate articles from the database that match the provided URLs
        articles_in_db = []
        for url in urls:
            status_code = data_downloader.get_content_rehydrate_status_code_only(url=url)
            if status_code == 200:
                articles_in_db.append(url)
                # Update the last_online_verification_date field for these articles
                self.patch_last_online_verification_date(keycloak_token, [url])

        # Return the list of articles that are already in the database
        return articles_in_db
    


