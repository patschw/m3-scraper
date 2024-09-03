from config import WEBSITE_STRATEGIES, CREDENTIALS_PATH, LOGIN_URLS, BASE_URLS, PATTERNS
from selenium.common.exceptions import StaleElementReferenceException
from scrapers.BaseScraper import BaseScraper
import logging
import re
from typing import List

# Set up logging for the scraper to track events and errors
logger = logging.getLogger(__name__)

# TODO: In headless mode, the scraper can access Spiegel+ articles after login.
# However, a message appears before the main text: "Dieser Artikel gehört zum Angebot von SPIEGEL+.
# Sie können ihn auch ohne Abonnement lesen, weil er Ihnen geschenkt wurde."
# This message should be removed.

class SpiegelScraper(BaseScraper):
    """A scraper for the Spiegel website"""

    # Define constants for strategies and URLs used in the scraping process
    EMAIL_STRATEGY_KEY = "email_username"  # Key for email strategy in the config
    PASSWORD_STRATEGY_KEY = "password"      # Key for password strategy in the config
    SUBMIT_STRATEGY_KEY = "submit"          # Key for submit button strategy in the config
    SUBMIT_AFTER_LOGIN_STRATEGY_KEY = "submit_after_login"  # Key for submit button after login
    STRATEGY_SOURCE = "spiegel"              # Source identifier for the website

    def __init__(self, headless: bool = True, timeout: int = 10):
        """Initialize the scraper with specific strategies and URLs for Spiegel
        
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
        self.submit_after_login_strategy = WEBSITE_STRATEGIES[self.STRATEGY_SOURCE][self.SUBMIT_AFTER_LOGIN_STRATEGY_KEY]
        self.login_url = LOGIN_URLS[self.STRATEGY_SOURCE]  # URL for the login page
        self.base_url = BASE_URLS[self.STRATEGY_SOURCE]    # Base URL for the website
        self.crawler_medium = self.STRATEGY_SOURCE          # Identifier for the crawler medium
        self.subpage_url_pattern = PATTERNS[self.STRATEGY_SOURCE]['subpage_url']  # Regex pattern for subpage URLs
        self.article_url_pattern = PATTERNS[self.STRATEGY_SOURCE]['article_url']  # Regex pattern for article URLs

    def login(self) -> None:
        """Login to the Spiegel website using the defined strategies
        
        This method navigates to the login page, enters the credentials, and submits the form.
        """
        try:
            # Retrieve email and password credentials from the specified path
            email, password = self.get_credentials(CREDENTIALS_PATH)
            # Navigate to the login URL
            self.navigate_to(self.login_url)
            # Enter the email using the defined strategy
            self.enter_email(email, self.email_strategy)
            # Click the submit button for the email form
            self.click_submit(self.submit_strategy)
            # Enter the password using the defined strategy
            self.enter_password(password, self.password_strategy)
            # Click the submit button for the password form
            self.click_submit(self.submit_strategy)
            # Navigate to the base URL after login
            self.navigate_to(self.base_url)
            # Click the submit button after login to finalize the process, spiegel needs one more submit click
            self.click_submit(self.submit_after_login_strategy)
            logger.info("Login successful.")  # Log successful login
        except Exception as e:
            logger.error(f"Login failed: {e}")  # Log any errors during login

    # def _get_all_article_urls_on_current_page(self) -> List[str]:
    #     """Get all article URLs from the current page
        
    #     Returns:
    #         List[str]: A list of article URLs found on the current page.
    #     """
    #     # Retrieve all URLs from the current page using the base scraper method
    #     all_urls = super().get_all_urls_on_current_page()
    #     # Filter URLs that match the article URL pattern
    #     article_urls = [url for url in all_urls if re.match(self.article_url_pattern, url)]
    #     logger.info(f"Found {len(article_urls)} article URLs on the current page.")  # Log the count of found URLs
    #     return article_urls

    # def _get_subpage_urls_on_current_page(self) -> List[str]:
    #     """Get all subpage URLs from the current page
        
    #     Returns:
    #         List[str]: A list of subpage URLs found on the current page.
    #     """
    #     # Retrieve all URLs from the current page
    #     all_urls = super().get_all_urls_on_current_page()
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
    #     """Get all unique article URLs from the main page and subpages
        
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
    #     """Scrape articles from the Spiegel website
        
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
        
        
        
        

    
    
    
    
    
 