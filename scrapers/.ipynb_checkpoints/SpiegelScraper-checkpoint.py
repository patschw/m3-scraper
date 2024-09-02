from config import WEBSITE_STRATEGIES
from config import CREDENTIALS_PATH
from config import LOGIN_URLS
from config import BASE_URLS
from scrapers.BaseScraper import BaseScraper
from time import sleep
from sklearn.feature_extraction.text import CountVectorizer
from text_analysis.Vectorizers import Vectorizer
import re
from selenium.common.exceptions import StaleElementReferenceException


# TODO: Im Headless mode kommt der Scraper über den login zwar an die Spiegel+ Artikel. Vor dem main text steht dann aber immer das hier: "Dieser Artikel gehört zum Angebot von SPIEGEL+. Sie können ihn auch ohne Abonnement lesen, weil er Ihnen geschenkt wurde"
# Das sollten wir noch wegmachen.

# this scraper inherits from BaseScraper
class SpiegelScraper(BaseScraper):
    """A scraper for the website"""
    def __init__(self):
        super().__init__()
        self.email_strategy = WEBSITE_STRATEGIES["spiegel"]["email_username"]
        self.password_strategy = WEBSITE_STRATEGIES["spiegel"]["password"]
        self.submit_strategy = WEBSITE_STRATEGIES["spiegel"]["submit"]
        self.submit_after_login_strategy = WEBSITE_STRATEGIES["spiegel"]["submit_after_login"]
        self.login_url = LOGIN_URLS["spiegel"]
        self.base_url = BASE_URLS["spiegel"]
        self.crawler_medium = "spiegel"

    def login(self):
        """Login to the website using the strategies defined in the config,
        with specific login procedure for the scraper's scraped website"""
        # Get the credentials from the config file
        email, password = self.get_credentials(CREDENTIALS_PATH)

        # Navigate to the login page
        self.navigate_to(self.login_url)

        # Enter the email and password
        self.enter_email(email, self.email_strategy)
        # Spiegel shows the email field first, then you have to click submit to enter the password
        self.click_submit(self.submit_strategy)
        self.enter_password(password, self.password_strategy)
        self.click_submit(self.submit_strategy)

        # spiegel has a special login procedure. For some reason, after logging in and 
        # navigating to the article, the page is not fully loaded, and still not in
        # spiegel plus "mode". Therefore, we have to click again the "Anmelden" button on the 
        # top of the page. Note that no new login is required, it just has to be clicked again.
        # Also note that this is not the same as the "Anmelden" button on the login page.
        # It has no name or id, therefore the only two strategies that work are the CSS selector
        # and the XPATH.
        # One also has to navigate to an article or the base URL for the button to appear.
        self.navigate_to(self.base_url)
        self.click_submit(self.submit_after_login_strategy)
    
    def _get_all_article_urls_on_current_page(self):
        """Get all urls from the current page, and filter for spiegel urls. Inherits from BaseScraper.get_all_urls_on_current_page()"""
        all_urls = super().get_all_urls_on_current_page()
        # Regular expression pattern for article URLs
        # TODO: add this pattern to the config file
        pattern = r'https://www\.spiegel\.de/.+/.+-[a-z0-9\-]+(?<!\d{4})$'
        # Filter for urls that match the pattern
        article_urls = [url for url in all_urls if re.match(pattern, url)]
        return article_urls
        
    def _get_subpage_urls_on_current_page(self):
        all_urls = super().get_all_urls_on_current_page()
        # Regular expression pattern for subpage URLs
        # TODO: add this pattern to the config file
        pattern = r'^https://www\.spiegel\.de/[a-z]+/$'
        # Filter for links that match the pattern
        subpage_urls = [url for url in all_urls if re.match(pattern, url)]
        return subpage_urls
    


    def _get_all_article_urls_on_subpages(self):
        """Get all article urls from the subpages"""
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
        self.navigate_to(self.base_url)
        startpage_urls = self._get_all_article_urls_on_current_page()
        subpage_urls = self._get_all_article_urls_on_subpages()
        # Combine the urls from the startpage and the subpages
        all_article_urls = startpage_urls + subpage_urls
        all_article_urls = list(set(all_article_urls))
        return all_article_urls
    
    # TODO leere methode aus base acstract machen
    #def abstract(self):
    # TODO NUR SPIEGEL NENNEN
    def scrape(self):
        # Get all unique article URLs
        all_article_urls = self._get_article_urls()

        all_articles_content = []

        # Iterate over the list of URLs
        for url in all_article_urls:
            # try:
                # Extract the content from each URL
            self.navigate_to(url)
            article_content_and_metadata = super()._extract_content()
            article_content_and_metadata["medium"] = {"readable_id": self.crawler_medium}
            # TODO: add the crawler version somewhere else, not when scraping
            article_content_and_metadata["crawler_medium"] = self.crawler_medium
            article_content_and_metadata["crawler_version"] = "0.1"
            all_articles_content.append(article_content_and_metadata)
            # print(f"Extracted content from {url}")
            # except Exception as e:
            #     print(f"Failed to extract content from {url}: {e}")
        super().close_browser()
        return all_articles_content
    
    # TODO: NEUE .py DATEI DIE DANN DEN OUTPUT VON SCRAPER VERWALTET
    # TODO: return article text
    
    # TODO: finde unterseiten zb /thema/ und scrape auch hier alles urls, auch über regex finden?
    # def_spiegel_snowball(self, urls):
        
        
        
        

    
    
    
    
    
 