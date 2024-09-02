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


# this scraper inherits from BaseScraper
class BayerischerRundfunkScraper(BaseScraper):
    """A scraper for the website"""
    def __init__(self):
        super().__init__()
        self.shadow_host_strategy = WEBSITE_STRATEGIES["bayerischer_rundfunk"]["shadow_dom_host"]
        # access only the identifier in the tuple of the cookie banner button strategy
        self.cookie_banner_button_strategy_css = WEBSITE_STRATEGIES["bayerischer_rundfunk"]["cookie_banner_button"][0][1]
        self.cookie_banner_button_strategy_xpath = WEBSITE_STRATEGIES["bayerischer_rundfunk"]["cookie_banner_button"][1][1]
        self.base_url = BASE_URLS["bayerischer_rundfunk"]
        self.crawler_medium = "bayerischer_rundfunk"
    
    def _get_all_article_urls_on_current_page(self):
        """Get all urls from the current page, and filter for spiegel urls. Inherits from BaseScraper.get_all_urls_on_current_page()"""
        all_urls = super().get_all_urls_on_current_page()
        # Regular expression pattern for article URLs
        # TODO: add this pattern to the config file
        pattern = r'https://www\.br\.de/nachrichten/[a-z\-]+/[a-z0-9\-]+,[A-Za-z0-9]+$'
        # Filter for urls that match the pattern
        # bayerischer rundfunk returns some dictionaries when scraping urls,
        # therefore we filter with isinstance() here
        article_urls = [url for url in all_urls if isinstance(url, str) and re.match(pattern, url)]
        return article_urls
        
        
    def _get_subpage_urls_on_current_page(self):
        all_urls = super().get_all_urls_on_current_page()
        # Regular expression pattern for subpage URLs
        # TODO: add this pattern to the config file
        pattern = r'https://www\.br\.de/nachrichten/[a-z\-]+(,[A-Za-z0-9]+)?$'
        # Filter for links that match the pattern
        subpage_urls = [url for url in all_urls if isinstance(url, str) and re.match(pattern, url)]
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
    
    def click_cookie_button(self):
        # Locate the Shadow Host element in Python
        shadow_host = super().find_element(WEBSITE_STRATEGIES["bayerischer_rundfunk"]["shadow_dom_host"])

        # wait for the cookie banner to appear
        sleep(2)
        
        try:
            self.driver.execute_script("""
                const shadowHost = arguments[0];  // shadowHost in JavaScript is the same as shadow_host in Python
                const cssSelector = arguments[1];  // Get the CSS selector from the arguments
                const xpath = arguments[2];  // Get the XPath from the arguments
                const shadowRoot = shadowHost.shadowRoot;  // Access the Shadow Root
        
                // Try to find the button using CSS selector
                let acceptButton = shadowRoot.querySelector(cssSelector);
        
                // If the button is not found using CSS selector, try using XPath
                if (!acceptButton) {
                    acceptButton = shadowRoot.evaluate(xpath, shadowRoot, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                }
        
                // If the button is found, click it
                if (acceptButton) {
                    acceptButton.click();
                } else {
                    console.error('Accept button not found using both CSS selector and XPath.');
                }
            """, shadow_host, self.cookie_banner_button_strategy_css, self.cookie_banner_button_strategy_xpath)
        except Exception as e:
            print(f"An error occurred. Probably the shadow DOM could not be found. Or the XPATH or CSS selector within it could not be found: {e}")

        # Make sure the JavaScript code is correctly formatted and that the CSS selector is valid
        # CODE WITHOUT STRATEGIES
        #self.driver.execute_script("""
        #    const shadowHost = arguments[0];
        #    const shadowRoot = shadowHost.shadowRoot;
        #    const acceptButton = shadowRoot.querySelector('button.sc-dcJsrY:nth-child(2)');
        #    acceptButton.click();
        #""", shadow_host)
    
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
        
        
        
        

    
    
    
    
    
 