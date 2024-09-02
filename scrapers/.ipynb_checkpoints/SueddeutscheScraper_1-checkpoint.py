from config import WEBSITE_STRATEGIES
from config import CREDENTIALS_PATH
from config import LOGIN_URLS
from config import BASE_URLS
from scrapers.BaseScraper import BaseScraper
from time import sleep
from sklearn.feature_extraction.text import CountVectorizer
from text_analysis.Vectorizers import Vectorizer
import re
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options



# this scraper inherits from BaseScraper
class SueddeutscheScraper(BaseScraper):
    """A scraper for the sueddeutsche website"""
    
    # Class variable to store the path to the chromedriver executable
    chromedriver_path = None

    def __init__(self):
        super().__init__()
        self.sueddeutsche_email_strategy = WEBSITE_STRATEGIES["sueddeutsche"]["email_username"]
        self.sueddeutsche_password_strategy = WEBSITE_STRATEGIES["sueddeutsche"]["password"]
        self.sueddeutsche_submit_strategy = WEBSITE_STRATEGIES["sueddeutsche"]["submit"]
        #self.sueddeutsche_login_window_iframe_strategy = WEBSITE_STRATEGIES["sueddeutsche"]["login_window_iframe"]
        self.login_url = LOGIN_URLS["sueddeutsche"]
        self.base_url = BASE_URLS["sueddeutsche"]
        self.crawler_medium = "sueddeutsche"


    def start_browser(self):
        """Start the browser and initialize the WebDriver and WebDriverWait instances"""
        # Check if chromedriver_path is already set
        if SueddeutscheScraper.chromedriver_path is None:
            # Download and set the chromedriver path
            SueddeutscheScraper.chromedriver_path = ChromeDriverManager().install()

        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")  # Necessary for running in Docker
        chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems

        # Specify the path to the Chrome binary
        chrome_options.binary_location = "/usr/bin/google-chrome"

        # Optional: Set timeouts and other settings for stability
        chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration (optional, especially useful in headless mode)
        chrome_options.add_argument("--window-size=1920,1080")  # Set a default window size (useful in headless mode)
        chrome_options.add_argument("--dns-prefetch-disable")  # Disable DNS prefetching to potentially resolve DNS issues
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")  # Workaround for some headless issues

        # Initialize the WebDriver instance
        service = Service(SueddeutscheScraper.chromedriver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        # Optional: Set an explicit wait to allow the browser time to stabilize
        self.wait = WebDriverWait(self.driver, 10)
        
        
    # def _is_on_login_page(self):
    #     # checks if the current page is the login page
    #     return self.is_element_visible(self.sueddeutsche_email_strategy)
            

    def login(self):
        """Login to the website using the strategies defined in the config,
        with specific login procedure for sueddeutsche"""
        # Get the credentials from the config file
        email, password = self.get_credentials(CREDENTIALS_PATH)

        # Navigate to the login page, which in the case of sueddeutsche is the same as the base URL
        self.navigate_to(self.login_url)
        
        # The sueeddeutsche login is in an iframe, so we have to switch to it first
        self.target_iframe = self.find_dynamic_iframe()
        # switch the context to the iframe
        self.driver.switch_to.frame(self.target_iframe)
        
        # the email field has to be clicked first, then the email and password can be entered
        self.click_element(self.sueddeutsche_email_strategy)
        self.enter_email(email, self.sueddeutsche_email_strategy)
        self.enter_password(password, self.sueddeutsche_password_strategy)
        self.click_submit(self.sueddeutsche_submit_strategy)
        
        # switch the context back from the iframe to the main page
        self.driver.switch_to.default_content()
        
        sleep(5)
        
    
        
        # # sometimes the login is not successful, so we have to check if we are still on the login page
        # if self._is_on_login_page():
        #     print("Login failed.")
        #     return False
        # else:
        #     print("Login successful.")
        #     return True
        
        # # reattempt login if failed
        
        

        
        
        
    def _get_all_sueddeutsche_article_urls_on_current_page(self):
        """Get all urls from the current page, and filter for sueddeutsche urls. Inherits from BaseScraper.get_all_urls_on_current_page()"""
        all_urls = super().get_all_urls_on_current_page()
        # Regular expression pattern for article URLs
        # TODO: add this pattern to the config file
        # pattern = r'https://www\.sueddeutsche\.de/.+/.+-[a-z0-9\-]+(?<!\d{4})$'
        pattern = r'^https:\/\/www\.sueddeutsche\.de\/(politik|wirtschaft|kultur|panorama|sport|projekte\/artikel|wissen|karriere|auto|stil|leben|deutschland|welt|meinung|digital|gesellschaft|muenchen)\/[\w\-]+(\/[\w\-]+)+\/?(e\d+|lux\.[\w]+)?\/?$'
        
        # Filter for urls that match the pattern
        sueddeutsche_article_urls = [url for url in all_urls if re.match(pattern, url)]
        return sueddeutsche_article_urls
        
    def _get_sueddeutsche_subpage_urls_on_current_page(self):
        all_urls = super().get_all_urls_on_current_page()
        # Regular expression pattern for subpage URLs
        # TODO: add this pattern to the config file
        # pattern = r'^https://www\.sueddeutsche\.de/[a-z]+/$'
        pattern = r'https://www\.sueddeutsche\.de/[a-zA-Z0-9]+(?:/[a-zA-Z0-9_-]+)?$'
        # Filter for links that match the pattern
        subpage_urls = [url for url in all_urls if re.match(pattern, url)]
        return subpage_urls
    


    def _get_all_sueddeutsche_article_urls_on_subpages(self):
        """Get all article urls from the subpages"""
        subpage_urls = self._get_sueddeutsche_subpage_urls_on_current_page()
        all_article_urls = []
        for url in subpage_urls:
            try:
                self.navigate_to(url)
                all_article_urls += self._get_all_sueddeutsche_article_urls_on_current_page()
            except StaleElementReferenceException:
                continue
        return all_article_urls
    
    def _get_sueddeutsche_article_urls(self):
        self.navigate_to(self.base_url)
        startpage_urls = self._get_all_sueddeutsche_article_urls_on_current_page()
        subpage_urls = self._get_all_sueddeutsche_article_urls_on_subpages()
        # Combine the urls from the startpage and the subpages
        all_article_urls = startpage_urls + subpage_urls
        all_article_urls = list(set(all_article_urls))
        return all_article_urls
    
    # TODO leere methode aus base acstract machen
    #def abstract(self):
    # TODO NUR sueddeutsche NENNEN
    def scrape(self):
        # Get all unique article URLs
        all_article_urls = self._get_sueddeutsche_article_urls()

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
    
    
    def find_dynamic_iframe(self):
        try:
            # Try to find the iframe using a generic ID search (e.g., "piano-id-")
            iframes = self.driver.find_elements(By.CSS_SELECTOR, "iframe[id^='piano-id-']")

            # If there's only one, return it
            if len(iframes) == 1:
                return iframes[0]

            # If multiple iframes match, triangulate further using specific attributes
            for iframe in iframes:
                iframe_id = iframe.get_attribute("id")
                
                # Recheck with the full ID
                if iframe_id.startswith("piano-id-"):
                    full_id_selector = f"#{iframe_id}"
                    full_xpath_selector = f"//*[@id='{iframe_id}']"
                    
                    # Verify with CSS selector
                    if self.driver.find_element(By.CSS_SELECTOR, full_id_selector):
                        return iframe
                    
                    # Verify with XPath
                    if self.driver.find_element(By.XPATH, full_xpath_selector):
                        return iframe

            # If none of the above works, raise an error
            raise NoSuchElementException("Could not uniquely identify the iframe.")
        
        except NoSuchElementException as e:
            print(f"Error: {e}")
            return None
    
    # TODO: NEUE .py DATEI DIE DANN DEN OUTPUT VON SCRAPER VERWALTET
    # TODO: return article text
    
    # TODO: finde unterseiten zb /thema/ und scrape auch hier alles urls, auch über regex finden?
    # def_sueddeutsche_snowball(self, urls):
        
        
        
        

    
    
    
    
    
 