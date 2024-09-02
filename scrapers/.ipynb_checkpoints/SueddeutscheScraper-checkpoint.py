from config import WEBSITE_STRATEGIES, CREDENTIALS_PATH, LOGIN_URLS, BASE_URLS
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

class SueddeutscheScraper(BaseScraper):
    """A scraper for the Sueddeutsche website"""
    
    chromedriver_path = None

    def __init__(self):
        super().__init__()
        self.email_strategy = WEBSITE_STRATEGIES["sueddeutsche"]["email_username"]
        self.password_strategy = WEBSITE_STRATEGIES["sueddeutsche"]["password"]
        self.submit_strategy = WEBSITE_STRATEGIES["sueddeutsche"]["submit"]
        self.login_url = LOGIN_URLS["sueddeutsche"]
        self.base_url = BASE_URLS["sueddeutsche"]
        self.crawler_medium = "sueddeutsche"

    def start_browser(self):
        """Start the browser and initialize the WebDriver and WebDriverWait instances"""
        if SueddeutscheScraper.chromedriver_path is None:
            SueddeutscheScraper.chromedriver_path = ChromeDriverManager().install()

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.binary_location = "/usr/bin/google-chrome"
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--dns-prefetch-disable")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")

        service = Service(SueddeutscheScraper.chromedriver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

    def login(self):
        """Login to the website using the strategies defined in the config"""
        email, password = self.get_credentials(CREDENTIALS_PATH)
        self.navigate_to(self.login_url)
        self.target_iframe = self.find_dynamic_iframe()
        if self.target_iframe:
            self.driver.switch_to.frame(self.target_iframe)
            self.click_element(self.email_strategy)
            self.enter_email(email, self.email_strategy)
            self.enter_password(password, self.password_strategy)
            self.click_submit(self.submit_strategy)
            self.driver.switch_to.default_content()
            sleep(5)

    def _get_all_article_urls_on_current_page(self):
        """Get all URLs from the current page and filter for URLs"""
        all_urls = super().get_all_urls_on_current_page()
        pattern = r'^https:\/\/www\.sueddeutsche\.de\/(politik|wirtschaft|kultur|panorama|sport|projekte\/artikel|wissen|karriere|auto|stil|leben|deutschland|welt|meinung|digital|gesellschaft|muenchen)\/[\w\-]+(\/[\w\-]+)+\/?(e\d+|lux\.[\w]+)?\/?$'
        return [url for url in all_urls if re.match(pattern, url)]
        
    def _get_subpage_urls_on_current_page(self):
        """Get all subpage URLs from the current page"""
        all_urls = super().get_all_urls_on_current_page()
        pattern = r'https://www\.sueddeutsche\.de/[a-zA-Z0-9]+(?:/[a-zA-Z0-9_-]+)?$'
        return [url for url in all_urls if re.match(pattern, url)]

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
        """Get all unique article URLs from the base URL and its subpages"""
        self.navigate_to(self.base_url)
        startpage_urls = self._get_all_article_urls_on_current_page()
        subpage_urls = self._get_all_article_urls_on_subpages()
        all_article_urls = list(set(startpage_urls + subpage_urls))
        return all_article_urls

    def scrape(self):
        """Scrape all articles and return their content"""
        all_article_urls = self._get_article_urls()
        all_articles_content = []

        for url in all_article_urls:
            self.navigate_to(url)
            article_content_and_metadata = super()._extract_content()
            article_content_and_metadata["medium"] = {"readable_id": self.crawler_medium}
            article_content_and_metadata["crawler_medium"] = self.crawler_medium
            article_content_and_metadata["crawler_version"] = "0.1"
            if article_content_and_metadata not in all_articles_content:
                all_articles_content.append(article_content_and_metadata)
                
        super().close_browser()
        return all_articles_content
    
    def find_dynamic_iframe(self):
        """Find and return the correct iframe for login"""
        try:
            iframes = self.driver.find_elements(By.CSS_SELECTOR, "iframe[id^='piano-id-']")
            if len(iframes) == 1:
                return iframes[0]
            for iframe in iframes:
                iframe_id = iframe.get_attribute("id")
                if iframe_id.startswith("piano-id-"):
                    full_id_selector = f"#{iframe_id}"
                    full_xpath_selector = f"//*[@id='{iframe_id}']"
                    if self.driver.find_element(By.CSS_SELECTOR, full_id_selector):
                        return iframe
                    if self.driver.find_element(By.XPATH, full_xpath_selector):
                        return iframe
            raise NoSuchElementException("Could not uniquely identify the iframe.")
        except NoSuchElementException as e:
            print(f"Error: {e}")
            return None
