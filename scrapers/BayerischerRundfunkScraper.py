# Import necessary modules and classes
from config import WEBSITE_STRATEGIES, CREDENTIALS_PATH, LOGIN_URLS, BASE_URLS, PATTERNS
from scrapers.BaseScraper import BaseScraper
from selenium.common.exceptions import StaleElementReferenceException
import logging
import re
from typing import List
from time import sleep

# Set up logging for the scraper
logger = logging.getLogger(__name__)

class BayerischerRundfunkScraper(BaseScraper):
    """A scraper for the Bayerischer Rundfunk website"""

    # Define a constant for the strategy source
    STRATEGY_SOURCE = "bayerischer_rundfunk"

    def __init__(self, headless: bool = True, timeout: int = 10):
        """Initialize the scraper with specific strategies and URLs for Bayerischer Rundfunk
        
        Args:
            headless (bool): Whether to run the browser in headless mode.
            timeout (int): The timeout for browser operations.
        """
        # Call the parent class's initializer
        super().__init__(headless, timeout)
        
        # Load strategies and URLs from the configuration
        self.shadow_host_strategy = WEBSITE_STRATEGIES[self.STRATEGY_SOURCE]["shadow_dom_host"]
        self.cookie_banner_button_strategy_css = WEBSITE_STRATEGIES[self.STRATEGY_SOURCE]["cookie_banner_button"][0][1]
        self.cookie_banner_button_strategy_xpath = WEBSITE_STRATEGIES[self.STRATEGY_SOURCE]["cookie_banner_button"][1][1]
        self.base_url = BASE_URLS[self.STRATEGY_SOURCE]
        self.crawler_medium = self.STRATEGY_SOURCE
        self.article_url_pattern = PATTERNS[self.STRATEGY_SOURCE]['article_url']
        self.subpage_url_pattern = PATTERNS[self.STRATEGY_SOURCE]['subpage_url']

    # def _get_all_article_urls_on_current_page(self) -> List[str]:
    #     """Get all article URLs from the current page
        
    #     Returns:
    #         List[str]: A list of article URLs found on the current page.
    #     """
    #     # Retrieve all URLs from the current page using the base scraper method
    #     all_urls = super().get_all_urls_on_current_page()
        
    #     # Filter URLs that match the article URL pattern
    #     article_urls = [url for url in all_urls if re.match(self.article_url_pattern, url)]
        
    #     # Log the number of article URLs found
    #     logger.info(f"Found {len(article_urls)} article URLs on the current page.")
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
    #     all_article_urls = []
        
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
    #             continue
    #     return all_article_urls

    # def _get_article_urls(self) -> List[str]:
    #     """Get all article URLs from the main page and subpages
        
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
    #     """Scrape articles from the Bayerischer Rundfunk website
        
    #     Args:
    #         keycloak_token: The token used for article verification.
        
    #     Returns:
    #         List[dict]: A list of dictionaries containing article content and metadata.
    #     """
    #     # Get all article URLs to scrape
    #     all_article_urls = self._get_article_urls()
    #     # Verify the articles using the base scraper method
    #     urls_to_scrape = super().reverify_articles(all_article_urls, keycloak_token)
    #     all_articles_content = []

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
    #             logger.info(f"Extracted content from {url}")
    #         except Exception as e:
    #             # Log an error if content extraction fails
    #             logger.error(f"Failed to extract content from {url}: {e}")

    #     # Close the browser after scraping
    #     super().close_browser()
    #     return all_articles_content

    def click_cookie_button(self):
        """Click the cookie consent button if it appears"""
        # Find the shadow host element using the base scraper method
        shadow_host = super().find_element(self.shadow_host_strategy)

        # Wait for the cookie banner to appear
        sleep(2)

        try:
            # Execute JavaScript to click the cookie consent button
            self.driver.execute_script("""
                // Retrieve the shadow host, CSS selector, and XPath from the arguments
                const shadowHost = arguments[0];
                const cssSelector = arguments[1];
                const xpath = arguments[2];
                // Access the shadow root of the shadow host
                const shadowRoot = shadowHost.shadowRoot;

                // Attempt to find the accept button using the CSS selector
                let acceptButton = shadowRoot.querySelector(cssSelector);
                // If the accept button is not found using the CSS selector, try using the XPath
                if (!acceptButton) {
                    acceptButton = shadowRoot.evaluate(xpath, shadowRoot, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                }

                // If the accept button is found, click it
                if (acceptButton) {
                    acceptButton.click();
                } else {
                    // Log an error if the accept button is not found using both the CSS selector and XPath
                    console.error('Accept button not found using both CSS selector and XPath.');
                }
            """, shadow_host, self.cookie_banner_button_strategy_css, self.cookie_banner_button_strategy_xpath)
        except Exception as e:
            # Log an error if clicking the cookie button fails
            logger.error(f"An error occurred while clicking the cookie button: {e}")
        
        
        
        

    
    
    
    
    
 