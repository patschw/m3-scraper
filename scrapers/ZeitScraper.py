from config import WEBSITE_STRATEGIES, CREDENTIALS_PATH, LOGIN_URLS, BASE_URLS, PATTERNS
from selenium.common.exceptions import StaleElementReferenceException
from scrapers.BaseScraper import BaseScraper
import logging
import re
from typing import List, Dict, Any
from datetime import datetime
import requests

# Set up logging for the scraper to track events and errors
logger = logging.getLogger(__name__)


class ZeitScraper(BaseScraper):
    """A scraper for the online website of (see name of this class)"""

    # Define constants for strategies and URLs used in the scraping process
    EMAIL_STRATEGY_KEY = "email_username"  # Key for email strategy in the config
    PASSWORD_STRATEGY_KEY = "password"      # Key for password strategy in the config
    SUBMIT_STRATEGY_KEY = "submit"          # Key for submit button strategy in the config
    STRATEGY_SOURCE = "zeit"              # Source identifier for the website

    def __init__(self, headless: bool = True, timeout: int = 10):
        """Initialize the scraper with specific strategies and URLs for Zeit
        
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
        self.subpage_url_pattern = PATTERNS[self.STRATEGY_SOURCE]['subpage_url']  # Regex pattern for subpage URLs
        self.article_url_pattern = PATTERNS[self.STRATEGY_SOURCE]['article_url']  # Regex pattern for article URLs

    def login(self) -> None:
        """Login to the website using the defined strategies
        
        This method navigates to the login page, enters the credentials, and submits the form.
        """
        try:
            # Retrieve email and password credentials from the specified path
            email, password = self.get_credentials(CREDENTIALS_PATH)
            # Navigate to the login URL
            self.navigate_to(self.login_url)
            # Enter the email using the defined strategy
            self.enter_email(email, self.email_strategy)
            # Enter the password using the defined strategy
            self.enter_password(password, self.password_strategy)
            # Click the submit button for the password form
            self.click_submit(self.submit_strategy)
            # Navigate to the base URL after login
            self.navigate_to(self.base_url)
            logger.info("Login successful.")  # Log successful login
        except Exception as e:
            logger.error(f"Login failed: {e}")  # Log any errors during login

    def scrape_archive(self, year_start = 1946, year_end = 1946) -> List[str]:
        """Scrape articles from the archive of the website (if this news outlet has an archive)"""
        
        years = range(year_start, year_end)  # 1945 until today
        issues_weeks = range(1, 9)  # 01 to 09
        issues_weeks = list(map(lambda x: f"{x:02}", issues_weeks)) + [f"{i:02}" for i in range(10, 60)]  # 10 to 60
        
        all_article_urls_archive = []   
        # Iterate over years and issue_weeks and navigate to the issue page
        for year in years:
            #print(year)
            for issue_week in issues_weeks:
                archive_article_url_pattern = f'^https://www\.zeit\.de/{year}/{issue_week}/(?!.*#index)(?!.*index#)(?!index$)[a-z0-9-äöüß]+$'
                #print(archive_article_url_pattern)
                issue_url = f"https://www.zeit.de/{year}/{issue_week}/index"
                try:
                    # Use the updated navigate_to method
                    self.navigate_to(issue_url)
                    
                    # If navigation was skipped due to a 404 status, break the loop
                    if self.url is None:
                        logger.info(f"404 Not Found for URL: {issue_url}. Stopping the loop.")
                        break
                    
                    # Get all article URLs from the current issue page
                    article_urls_tmp = self._get_all_article_urls_on_current_page(archive_article_url_pattern)
                    if article_urls_tmp:
                        for article_url in article_urls_tmp:
                            komplettansicht_url = f"{article_url}/komplettansicht"
                            # Check if the komplettansicht URL exists
                            response = requests.head(komplettansicht_url, allow_redirects=True)
                            if response.status_code != 404:
                                all_article_urls_archive.append(komplettansicht_url)
                            else:
                                all_article_urls_archive.append(article_url)
                        #print(all_article_urls_archive)
                    else:
                        logger.warning(f"No article URLs found on {issue_url}.")
                
                except Exception as e:
                    logger.error(f"Error navigating to {issue_url}: {e}")
                    continue  # Continue to the next issue week even if there's an error

        # Scrape all article URLs
        if all_article_urls_archive:
            all_articles_content_archive = self.scrape(all_article_urls_archive)
        else:
            logger.warning("No article URLs to scrape.")
            all_articles_content_archive = []

        return all_articles_content_archive

            
    # def scrape(self, urls_to_scrape: List[str]) -> List[Dict[str, Any]]:
    #     """Scrape articles from the website
        
    #     Args:
    #         keycloak_token: The token used for article verification.
    #         urls_to_scrape: The list of URLs to scrape.
        
    #     Returns:
    #         List[dict]: A list of dictionaries containing article content and metadata.
    #     """

    #     all_articles_content = []  # Initialize a list to store the content of all articles

    #     # Iterate through each URL to scrape content
    #     for url in urls_to_scrape:
    #         try:
    #             # Navigate to the article URL
    #             self.navigate_to(url)
    #             # Extract content and metadata from the article
    #             article_content_and_metadata = self._extract_content()
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
    #     self.close_browser()
    #     return all_articles_content
        

    
    
    
    
    
 