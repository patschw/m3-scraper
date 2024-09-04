from config import WEBSITE_STRATEGIES, CREDENTIALS_PATH, LOGIN_URLS, BASE_URLS, PATTERNS
from scrapers.BaseScraper import BaseScraper
from time import sleep
import re
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import logging
from typing import List

# Set up logging for the scraper to track events and errors
logger = logging.getLogger(__name__)

class SueddeutscheScraper(BaseScraper):
    """A scraper for the Sueddeutsche website"""
    
    # Define constants for strategies and URLs used in the scraping process
    EMAIL_STRATEGY_KEY = "email_username"  # Key for email strategy in the config
    PASSWORD_STRATEGY_KEY = "password"      # Key for password strategy in the config
    SUBMIT_STRATEGY_KEY = "submit"          # Key for submit button strategy in the config
    STRATEGY_SOURCE = "sueddeutsche"        # Source identifier for the website

    # Class variable to store the path of the ChromeDriver
    chromedriver_path = None

    def __init__(self, headless: bool = True, timeout: int = 10):
        """Initialize the scraper with specific strategies and URLs for Sueddeutsche
        
        Args:
            headless (bool): Whether to run the browser in headless mode (without a GUI).
            timeout (int): The timeout duration for browser operations.
        """
        # Call the parent class's initializer to set up the base scraper
        super().__init__(headless, timeout)
        
        # Load strategies and URLs from the configuration
        self.email_strategy = WEBSITE_STRATEGIES[self.STRATEGY_SOURCE][self.EMAIL_STRATEGY_KEY]
        self.password_strategy = WEBSITE_STRATEGIES[self.STRATEGY_SOURCE][self.PASSWORD_STRATEGY_KEY]
        self.submit_strategy = WEBSITE_STRATEGIES[self.STRATEGY_SOURCE][self.SUBMIT_STRATEGY_KEY]
        self.login_url = LOGIN_URLS[self.STRATEGY_SOURCE]  # URL for the login page
        self.base_url = BASE_URLS[self.STRATEGY_SOURCE]    # Base URL for the website
        self.crawler_medium = self.STRATEGY_SOURCE          # Identifier for the crawler medium
        self.article_url_pattern = PATTERNS[self.STRATEGY_SOURCE]['article_url']  # Regex pattern for article URLs
        self.subpage_url_pattern = PATTERNS[self.STRATEGY_SOURCE]['subpage_url']  # Regex pattern for subpage URLs

    def start_browser(self):
        """Start the browser and initialize the WebDriver and WebDriverWait instances"""
        # Check if the ChromeDriver path is already set; if not, install it
        # firefox has weird ad blockers that makes it impossible to scrape suddeutsche
        # therefore we use chrome
        if SueddeutscheScraper.chromedriver_path is None:
            SueddeutscheScraper.chromedriver_path = ChromeDriverManager().install()
        
        # Set up Chrome options for headless browsing
        if self.headless:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Run in headless mode
            chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
            chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
            chrome_options.binary_location = "/usr/bin/google-chrome"  # Path to Chrome binary
            chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
            chrome_options.add_argument("--window-size=1920,1080")  # Set window size
            chrome_options.add_argument("--dns-prefetch-disable")  # Disable DNS prefetching
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")  # Disable certain features

            # Create a service object for the ChromeDriver
            service = Service(SueddeutscheScraper.chromedriver_path)
            # Initialize the WebDriver with the specified options
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 3)  # Set up WebDriverWait
        else:
            # If not headless, initialize the WebDriver normally
            self.driver = webdriver.Chrome(executable_path=SueddeutscheScraper.chromedriver_path)
            self.wait = WebDriverWait(self.driver, 3)  # Set up WebDriverWait

    def login(self) -> None:
        """Login to the website using the strategies defined in the config"""
        sleep(3)
        try:
            # Retrieve credentials from the specified path
            email, password = self.get_credentials(CREDENTIALS_PATH)
            # Navigate to the login URL
            self.navigate_to(self.login_url)
            # Find and switch to the target iframe for login
            self.target_iframe = self.find_dynamic_iframe()
            if self.target_iframe:
                self.driver.switch_to.frame(self.target_iframe)  # Switch to the iframe
                self.click_element(self.email_strategy)  # Click on the email input field
                self.enter_email(email, self.email_strategy)  # Enter the email
                self.enter_password(password, self.password_strategy)  # Enter the password
                self.click_submit(self.submit_strategy)  # Click the submit button
                self.driver.switch_to.default_content()  # Switch back to the default content
                sleep(5)  # Wait for the login process to complete
            logger.info("Login successful.")  # Log successful login
        except Exception as e:
            logger.error(f"Login failed: {e}")  # Log any errors during login

    # def _get_all_article_urls_on_current_page(self) -> List[str]:
    #     """Get all URLs from the current page and filter for URLs using the config pattern
        
    #     Returns:
    #         List[str]: A list of article URLs found on the current page.
    #     """
    #     # Retrieve all URLs from the current page using the base scraper method
    #     all_urls = super()._get_all_urls_on_current_page()
    #     # Filter URLs that match the article URL pattern
    #     article_urls = [url for url in all_urls if re.match(self.article_url_pattern, url)]
    #     logger.info(f"Found {len(article_urls)} article URLs on the current page.")  # Log the count of found URLs
    #     return article_urls

    # def _get_subpage_urls_on_current_page(self) -> List[str]:
    #     """Get all subpage URLs from the current page using the config pattern
        
    #     Returns:
    #         List[str]: A list of subpage URLs found on the current page.
    #     """
    #     # Retrieve all URLs from the current page
    #     all_urls = super()._get_all_urls_on_current_page()
    #     # Filter URLs that match the subpage URL pattern
    #     subpage_urls = [url for url in all_urls if re.match(self.subpage_url_pattern, url)]
    #     return subpage_urls

    # def _get_all_article_urls_on_subpages(self) -> List[str]:
    #     """Get all article URLs from the subpages
        
    #     Returns:
    #         List[str]: A list of all article URLs found on subpages.
    #     """
    #     # Get all subpage URLs from the current page
    #     subpage_urls = self._get_subpage_urls_on_current_page()
    #     all_article_urls = []  # Initialize a list to store all article URLs
        
    #     # Iterate through each subpage URL
    #     for url in subpage_urls:
    #         try:
    #             # Navigate to the subpage
    #             self.navigate_to(url)
    #             # Collect article URLs from the subpage
    #             all_article_urls += self._get_all_article_urls_on_current_page()
    #         except StaleElementReferenceException:
    #             # Log a warning if a stale element reference exception occurs
    #             logger.warning(f"StaleElementReferenceException occurred while navigating to {url}")
    #             continue  # Skip to the next URL if an exception occurs
    #     return all_article_urls

    # def _get_article_urls(self) -> List[str]:
    #     """Get all unique article URLs from the base URL and its subpages
        
    #     Returns:
    #         List[str]: A list of all unique article URLs.
    #     """
    #     # Navigate to the base URL of the scraper
    #     self.navigate_to(self.base_url)
    #     # Get article URLs from the main page
    #     startpage_urls = self._get_all_article_urls_on_current_page()
    #     # Get article URLs from subpages
    #     subpage_urls = self._get_all_article_urls_on_subpages()
    #     # Combine and deduplicate the URLs
    #     all_article_urls = list(set(startpage_urls + subpage_urls))
    #     return all_article_urls

    # def scrape(self, keycloak_token):
    #     """Scrape all articles and return their content
        
    #     Args:
    #         keycloak_token: The token used for article verification.
        
    #     Returns:
    #         List[dict]: A list of dictionaries containing article content and metadata.
    #     """
    #     # Get all article URLs to scrape
    #     all_article_urls = self._get_article_urls()
    #     # Verify the articles using the base scraper method
    #     urls_to_scrape = super().reverify_articles(all_article_urls, keycloak_token)
    #     all_articles_content = []  # Initialize a list to store the content of all articles

    #     # Iterate through each URL to scrape content
    #     for url in urls_to_scrape:
    #         try:
    #             # Navigate to the article URL
    #             self.navigate_to(url)
    #             # Extract content and metadata from the article
    #             article_content_and_metadata = super()._extract_content()
    #             # Add additional metadata
    #             article_content_and_metadata["medium"] = {"readable_id": self.crawler_medium}
    #             article_content_and_metadata["crawler_medium"] = self.crawler_medium
    #             article_content_and_metadata["crawler_version"] = "0.1"
    #             # Append the content to the results list
    #             all_articles_content.append(article_content_and_metadata)
    #             logger.info(f"Extracted content from {url}")  # Log successful extraction
    #         except Exception as e:
    #             # Log an error if content extraction fails
    #             logger.error(f"Failed to extract content from {url}: {e}")

    #     # Close the browser after scraping
    #     super().close_browser()
    #     return all_articles_content

    def find_dynamic_iframe(self):
        """Find and return the correct iframe for login
        
        Returns:
            WebElement: The iframe element if found, otherwise None.
        """
        try:
            # Find all iframes that match the specified CSS selector
            iframes = self.driver.find_elements(By.CSS_SELECTOR, "iframe[id^='piano-id-']")
            # If only one iframe is found, return it
            if len(iframes) == 1:
                return iframes[0]
            # Iterate through the found iframes to find the correct one
            for iframe in iframes:
                iframe_id = iframe.get_attribute("id")  # Get the ID of the iframe
                if iframe_id.startswith("piano-id-"):  # Check if the ID matches the expected pattern
                    full_id_selector = f"#{iframe_id}"  # Create a full CSS selector
                    full_xpath_selector = f"//*[@id='{iframe_id}']"  # Create a full XPath selector
                    # Check if the iframe can be found using the CSS selector
                    if self.driver.find_element(By.CSS_SELECTOR, full_id_selector):
                        return iframe  # Return the found iframe
                    # Check if the iframe can be found using the XPath
                    if self.driver.find_element(By.XPATH, full_xpath_selector):
                        return iframe  # Return the found iframe
            # Raise an exception if no unique iframe is found
            raise NoSuchElementException("Could not uniquely identify the iframe.")
        except NoSuchElementException as e:
            # Log an error if the iframe cannot be found
            print(f"Error: {e}")
            return None  # Return None if an error occurs
