from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from config import WEBSITE_STRATEGIES, CREDENTIALS_PATH
import trafilatura
import json
from datetime import datetime
from text_analysis.NEExtractor import NEExtractor

class BaseScraper:
    """Base class for all scrapers"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.vectorizer = vectorizer
        self.ne_extractor = ne_extractor if ne_extractor is not None else NEExtractor()
        self.crawler_version = "0.1"
    
    def get_credentials(self, path):
        """Get the credentials from a file"""
        with open(path, "r") as f:
            credentials = f.read().splitlines()
        return credentials[0], credentials[1]

    def start_browser(self):
        """Start the browser and initialize the WebDriver and WebDriverWait instances"""
        geckodriver_path = '/usr/local/bin/geckodriver'
        firefox_binary_path = '/usr/bin/firefox'
        
        firefox_options = Options()
        firefox_options.binary_location = firefox_binary_path
        firefox_options.add_argument("--no-sandbox")
        firefox_options.add_argument("--disable-dev-shm-usage")
        firefox_options.add_argument("--headless")
        
        service = Service(geckodriver_path)
        self.driver = webdriver.Firefox(service=service, options=firefox_options)
        self.wait = WebDriverWait(self.driver, 10)
        
    def close_browser(self):
        """Close the browser and end the session"""
        if self.driver:
            self.driver.quit()

    def navigate_to(self, url):
        """Navigate to a specific URL"""
        self.driver.get(url)
    
    def get_all_urls_on_current_page(self):
        """Get all URLs from the current page."""
        self.wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, 'a')))
        urls = self.driver.execute_script('''
            return Array.from(document.querySelectorAll('a')).map(a => a.href).filter(href => href);
        ''')
        return list(set(urls))  # Ensure all URLs are unique

    def wait_for_element(self, by, value, timeout=10):
        """Wait for a specific element to be loaded on the page"""
        element_present = EC.presence_of_element_located((by, value))
        WebDriverWait(self.driver, timeout).until(element_present)

    def find_element(self, strategies):
        """Find an element on the page using the strategies defined in the config"""
        for strategy, locator in strategies:
            try:
                element = self.wait.until(EC.presence_of_element_located((By.__dict__[strategy.replace(' ', '_').upper()], locator)))
                if element:
                    return element
            except (NoSuchElementException, TimeoutException):
                continue
        raise NoSuchElementException("Element not found using any strategy")

    def click_element(self, strategy):
        """Click an element on the page"""
        element = self.find_element(strategy)
        element.click()

    def input_text(self, element, text):
        """Input text into a field on the page"""
        element.clear()
        element.send_keys(text)
        input_value = element.get_attribute('value')
        if input_value != text: 
            raise ValueError(f"Input text '{text}' was not successfully entered into the field.")
        
    def enter_email(self, email, email_strategy):
        """Enter the email into the email field"""
        elem_email_username = self.find_element(email_strategy)
        self.input_text(elem_email_username, email)

    def enter_password(self, password, password_strategy):
        """Enter the password into the password field"""
        elem_password = self.find_element(password_strategy)
        self.input_text(elem_password, password)

    def click_submit(self, submit_strategy):
        """Click the submit button"""
        elem_submit = self.find_element(submit_strategy)
        elem_submit.click()

    def _extract_content(self):
        """Extract the main content from the page using trafilatura."""
        html_content = self.driver.page_source
        
        try:
            main_text = trafilatura.extract(html_content)
            main_text = main_text.replace('\n', ' ') if main_text else None
        except (ValueError, TypeError) as e:
            print(f"Error during main text extraction: {e}")
            main_text = None
    
        try:
            extracted_metadata = trafilatura.extract_metadata(html_content)
            lead_text = extracted_metadata.description.replace('\n', ' ') if extracted_metadata and extracted_metadata.description else ''
        except (ValueError, TypeError, AttributeError) as e:
            print(f"Error during metadata extraction: {e}")
            lead_text = ''
    
        url = extracted_metadata.url if extracted_metadata else None
    
        content_dict = {
            "url": url,
            "main_text": main_text,
            "lead_text": lead_text,
            "last_online_verification_date": datetime.now().isoformat(),
        }
    
        return content_dict

    def check_for_paywall(self, paywall_strategy):
        """Check if the page is paywalled"""
        original_wait = self.wait
        self.wait = WebDriverWait(self.driver, 1)
        
        try:
            return bool(self.find_element(paywall_strategy))
        except (NoSuchElementException, TimeoutException):
            return False 
        finally:
            self.wait = original_wait

    def save_extracted_data(self):
        """Save the extracted data to a file"""
        content_dict = self._extract_content()
        filename = "extracted_data.json"
        data = {
            "main_text_vector": self.vectorize_text(content_dict['main_text'], content_dict['lead_text']),
            "return_url": content_dict["url"],
            "last_online_verification_date": content_dict["last_online_verification_date"],
        }
        with open(filename, "w") as f:
            json.dump(data, f)
