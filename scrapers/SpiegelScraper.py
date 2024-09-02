from config import WEBSITE_STRATEGIES
from config import CREDENTIALS_PATH
from config import LOGIN_URLS
from config import BASE_URLS
from selenium.common.exceptions import StaleElementReferenceException
from scrapers.BaseScraper import BaseScraper
import logging
import re

logger = logging.getLogger(__name__)

# TODO: Im Headless mode kommt der Scraper über den login zwar an die Spiegel+ Artikel. Vor dem main text steht dann aber immer das hier: "Dieser Artikel gehört zum Angebot von SPIEGEL+. Sie können ihn auch ohne Abonnement lesen, weil er Ihnen geschenkt wurde"
# Das sollten wir noch wegmachen.

import logging

logger = logging.getLogger(__name__)

class SpiegelScraper(BaseScraper):
    """A scraper for the Spiegel website"""

    def __init__(self):
        """Initialize the scraper with specific strategies and URLs for Spiegel"""
        super().__init__()
        self.email_strategy = WEBSITE_STRATEGIES["spiegel"]["email_username"]
        self.password_strategy = WEBSITE_STRATEGIES["spiegel"]["password"]
        self.submit_strategy = WEBSITE_STRATEGIES["spiegel"]["submit"]
        self.submit_after_login_strategy = WEBSITE_STRATEGIES["spiegel"]["submit_after_login"]
        self.login_url = LOGIN_URLS["spiegel"]
        self.base_url = BASE_URLS["spiegel"]
        self.crawler_medium = "spiegel"

    def login(self):
        """Login to the Spiegel website using the defined strategies"""
        email, password = self.get_credentials(CREDENTIALS_PATH)
        self.navigate_to(self.login_url)
        self.enter_email(email, self.email_strategy)
        self.click_submit(self.submit_strategy)
        self.enter_password(password, self.password_strategy)
        self.click_submit(self.submit_strategy)
        self.navigate_to(self.base_url)
        self.click_submit(self.submit_after_login_strategy)

    def _get_all_article_urls_on_current_page(self):
        """Get all article URLs from the current page"""
        all_urls = super().get_all_urls_on_current_page()
        pattern = r'https://www\.spiegel\.de/.+/.+-[a-z0-9\-]+(?<!\d{4})$'
        article_urls = [url for url in all_urls if re.match(pattern, url)]
        return article_urls

    def _get_subpage_urls_on_current_page(self):
        """Get all subpage URLs from the current page"""
        all_urls = super().get_all_urls_on_current_page()
        pattern = r'^https://www\.spiegel\.de/[a-z]+/$'
        subpage_urls = [url for url in all_urls if re.match(pattern, url)]
        return subpage_urls

    def _get_all_article_urls_on_subpages(self):
        """Get all article URLs from the subpages"""
        subpage_urls = self._get_subpage_urls_on_current_page()
        all_article_urls = []
        for url in subpage_urls:
            try:
                self.navigate_to(url)
                all_article_urls += self._get_all_article_urls_on_current_page()
            except StaleElementReferenceException:
                continue
        return all_article_urls

    def _get_article_urls(self):
        """Get all article URLs from the main page and subpages"""
        self.navigate_to(self.base_url)
        startpage_urls = self._get_all_article_urls_on_current_page()
        subpage_urls = self._get_all_article_urls_on_subpages()
        all_article_urls = list(set(startpage_urls + subpage_urls))
        return all_article_urls

    def scrape(self, keycloak_token):
        """Scrape articles from the Spiegel website"""
        all_article_urls = self._get_article_urls()
        urls_to_scrape = super().reverify_articles(all_article_urls, keycloak_token)
        all_articles_content = []

        for url in urls_to_scrape:
            try:
                self.navigate_to(url)
                article_content_and_metadata = super()._extract_content()
                article_content_and_metadata["medium"] = {"readable_id": self.crawler_medium}
                article_content_and_metadata["crawler_medium"] = self.crawler_medium
                article_content_and_metadata["crawler_version"] = "0.1"
                all_articles_content.append(article_content_and_metadata)
                logger.info(f"Extracted content from {url}")
            except Exception as e:
                logger.error(f"Failed to extract content from {url}: {e}")

        super().close_browser()
        return all_articles_content
        
        
        
        

    
    
    
    
    
 