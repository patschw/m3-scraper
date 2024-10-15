from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException, StaleElementReferenceException
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

from database_handling.DataDownload import DataDownloader
from database_handling.DataUpload import DataUploader
from database_handling.DataHandleAndOtherHelpers import DataHandler
from config import WEBSITE_STRATEGIES, CREDENTIALS_PATH
import trafilatura
import json
from sklearn.feature_extraction.text import CountVectorizer
from pathlib import Path
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
import tempfile

# Configure logging
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
        try:
            logger.info("Starting browser")
            
            firefox_options = Options()
            
            # Set Firefox binary path explicitly if needed
            firefox_binary_path = "/usr/bin/firefox"  # Adjust this path if necessary
            if os.path.exists(firefox_binary_path):
                firefox_options.binary_location = firefox_binary_path
            else:
                logger.warning(f"Firefox binary not found at {firefox_binary_path}. Using default.")
            
            # Set Firefox preferences
            firefox_options.set_preference("browser.download.folderList", 2)
            firefox_options.set_preference("browser.download.manager.showWhenStarting", False)
            firefox_options.set_preference("browser.download.dir", os.path.join(os.getcwd(), "downloads"))
            firefox_options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf,application/x-pdf")
            
            # Add Firefox arguments
            firefox_options.add_argument("--start-maximized")
            firefox_options.add_argument("--disable-infobars")
            firefox_options.add_argument("--disable-extensions")
            firefox_options.add_argument("--no-sandbox")
            firefox_options.add_argument("--disable-dev-shm-usage")
            firefox_options.add_argument('--window-size=1920,1080')
            firefox_options.add_argument("--dns-prefetch-disable")
            firefox_options.add_argument("--disable-features=VizDisplayCompositor")
            
            if self.headless:
                firefox_options.add_argument("--headless")
            
            # Create a temporary profile directory
            temp_profile_dir = tempfile.mkdtemp()
            firefox_options.set_preference("profile", temp_profile_dir)
            
            # Create the WebDriver instance using GeckoDriverManager
            service = FirefoxService(GeckoDriverManager().install())
            
            self.driver = webdriver.Firefox(
                service=service,
                options=firefox_options
            )
            
            self.wait = WebDriverWait(self.driver, self.timeout)
            
            logger.debug("Browser started successfully")
            
            # Set timeout for finding elements
            self.driver.implicitly_wait(self.timeout)
            
            # Maximize browser window
            self.driver.maximize_window()
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise

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
    
    def _get_all_article_urls_on_current_page(self, pattern: str = None) -> List[str]:
        """Get all article URLs from the current page

        Args:
            pattern (str): Optional regex pattern to filter article URLs. Defaults to self.article_url_pattern if not provided.
            (Background: Some website use different URL patterns (for instance for real online articles and for archive articles)).
            subpage_url_pattern (str): Optional regex pattern to filter subpage URLs. Defaults to self.subpage_url_pattern if not provided.
            
        Returns:
            List[str]: A list of article URLs found on the current page.
        """
        pattern = pattern or self.article_url_pattern
        #logger.info("Waiting for content to load")
        #time.sleep(2)
        self.driver.save_screenshot("screenshot.png")

        try:
            article_urls = self.driver.execute_script(f'''
                const pattern = new RegExp('{pattern}');
                return [...new Set(Array.from(document.links)
                    .map(a => a.href)
                    .filter(url => pattern.test(url)))];
            ''')
            logger.info(f"Found {len(article_urls)} unique article URLs on the current page: {self.driver.current_url}")
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
                all_article_urls += self._get_all_article_urls_on_current_page(self.article_url_pattern)
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
        article_urls_from_startpage = self._get_all_article_urls_on_current_page(self.article_url_pattern)
        # Get article URLs from subpages
        article_urls_from_subpages = self._get_all_article_urls_on_subpages()
        # Combine and deduplicate the URLs using a set
        all_article_urls = list(dict.fromkeys(article_urls_from_startpage + article_urls_from_subpages))
        return all_article_urls

    def scrape(self, urls_to_scrape: List[str]) -> List[Dict[str, Any]]:
        """Scrape articles from the Spiegel website
        
        Args:
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