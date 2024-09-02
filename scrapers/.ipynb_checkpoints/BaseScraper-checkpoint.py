from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from database_handling.DataDownload import DataDownloader
from config import WEBSITE_STRATEGIES, CREDENTIALS_PATH
import trafilatura
import json
from sklearn.feature_extraction.text import CountVectorizer
from datetime import datetime

class BaseScraper:
    """Base class for all scrapers"""
    def __init__(self):
        self.driver = None
        self.wait = None  # Define the wait attribute here
        self.email = None
        self.password = None
        self.url = None
        # create a ne_extractor instance if not provided

        self.crawler_version = "0.1"
    
    def get_credentials(self, path):
        """Get the credentials from a file"""
        # line 1: email
        # line 2: password
        with open(path, "r") as f:
            credentials = f.read().splitlines()
        return credentials[0], credentials[1]

    def start_browser(self):
        """Start the browser and initialize the WebDriver and WebDriverWait instances"""

        geckodriver_path = '/usr/local/bin/geckodriver'
        # Path to the Firefox executable
        firefox_binary_path = '/usr/bin/firefox'
        
        # Set up Firefox options
        firefox_options = Options()
        firefox_options.binary_location = firefox_binary_path
        firefox_options.add_argument("--no-sandbox")
        firefox_options.add_argument("--disable-dev-shm-usage")
        firefox_options.add_argument("--headless")  # Run in headless mode
        firefox_options.add_argument('--window-size=1920,1080')
        firefox_options.add_argument("--dns-prefetch-disable")
        firefox_options.add_argument("--disable-features=VizDisplayCompositor")

        # Debugging information
        #print("GeckoDriver path:", geckodriver_path)
        #print("Firefox binary path:", firefox_binary_path)

        # Initialize the WebDriver instance
        service = Service(geckodriver_path)
        self.driver = webdriver.Firefox(service=service, options=firefox_options)
        # Initialize the WebDriverWait instance
        self.wait = WebDriverWait(self.driver, 3)

    # write a method that reverifies articles that are already in db
    # it takes the list of URLS that the scraper found on the webiste
    # and returns (as a in between step) a list of articles that are already in the DB
    # and updates last_verification in the database
        
    def close_browser(self):
        """Close the browser and end the session"""
        # Close the browser and end the session
        if self.driver:
            self.driver.quit()

    def navigate_to(self, url):
        """Navigate to a specific path relative to the base URL"""
        # Navigate to a specific path relative to the base URL
        self.url = url
        self.driver.get(self.url)
    
    def get_all_urls_on_current_page(self):
        """Get all URLs from the current page."""
        # TODO: Improve this method and all that build on it using trafilatura: https://trafilatura.readthedocs.io/en/latest/crawls.html
        # Wait for all <a> tags to be loaded
        WebDriverWait(self.driver, 10).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'a')))

        # # Find all <a> tags
        # a_tags = self.driver.find_elements(By.TAG_NAME, 'a')
        
        # # Get the href attribute of each <a> tag
        # urls = [a.get_attribute('href') for a in a_tags]
        
        # Javascript to get all URLs on the page, quickest way to get all URLs
        urls = self.driver.execute_script('''
            return Array.from(document.querySelectorAll('a'))
                        .map(a => a.href)
                        .filter(href => href);
        ''')

        # Filter out any None values and return the links
        return [url for url in urls if url is not None]

    
    # hier eine methode einbauen, die für einen news media base url (zb spiegel.de) alle URLS der DB über den rehydrate endpoint zieht
    
    
    def wait_for_element(self, by, value, timeout=10):
        """Wait for a specific element to be loaded on the page"""
        # Wait for a specific element to be loaded on the page
        element_present = EC.presence_of_element_located((by, value))
        WebDriverWait(self.driver, timeout).until(element_present)

    def find_element(self, strategies):
        """Find an element on the page using the strategies defined in the config"""
        found_element = None
        last_exception = None

        for strategy, locator in strategies:
            try:
                # Try to find the element using the specified strategy
                element = self.wait.until(EC.presence_of_element_located((By.__dict__[strategy.replace(' ', '_').upper()], locator)))
                if element:
                    found_element = element
                    break  # If the element is found, break out of the loop
            except (NoSuchElementException, TimeoutException) as e:
                last_exception = e
                continue  # If not found, continue to the next strategy

        if found_element:
            return found_element
        elif last_exception:
            raise last_exception
        else:
            raise NoSuchElementException("Element not found using any strategy")

    def click_element(self, strategy):
        """Click an element on the page"""
        # Click an element on the page
        element = self.find_element(strategy)
        element.click()

    def input_text(self, element, text):
        """Input text into a field on the page"""
        # Clear the input field before typing
        element.clear()
        # Input text into a field on the page
        element.send_keys(text)
        # Get the value of the input field
        input_value = element.get_attribute('value')

        # Check if the input was successful
        if input_value != text: 
            raise ValueError(f"Input text '{text}' was not successfully entered into the field.")
        
    def enter_email(self, email, email_strategy = WEBSITE_STRATEGIES["spiegel"]["email_username"]):
        """Enter the email into the email field using the strategies defined in the config"""
        # Find the email field using the strategies defined in the config
        elem_email_username = self.find_element(email_strategy)
        # Input the email into the email field
        self.input_text(elem_email_username, email)

    def enter_password(self, password, password_strategy = WEBSITE_STRATEGIES["spiegel"]["password"]):
        """Enter the password into the password field using the strategies defined in the config"""
        # Find the password field using the strategies defined in the config
        elem_password = self.find_element(password_strategy)
        # Input the password into the password field
        self.input_text(elem_password, password)

    def click_submit(self, submit_strategy = WEBSITE_STRATEGIES["spiegel"]["submit"]):
        """Click the submit button using the strategies defined in the config"""
        # click the submit button
        elem_submit = self.find_element(submit_strategy)
        elem_submit.click()

    def _extract_content(self):
        """Extract the main content from where the driver is currently at using trafilatura.
        Returns a content_dict is already structured in the way the database expects it to be."""
        # Extract the main content using trafilatura
        # TODO: use beatifulsoup to preprocess the html content before passing it to trafilatura
        # # Parse the HTML with BeautifulSoup 
        # soup = BeautifulSoup(html_content, 'html.parser')
        html_content = self.driver.page_source
        
        # Catch error if trafilatura fails to extract the main text
        try:
            main_text = trafilatura.extract(html_content)
            if main_text is not None:
                main_text = main_text.replace('\n', ' ')
            else:
                print("Failed to extract main text")
                main_text = None
        except (ValueError, TypeError) as e:
            print(f"An error occurred during main text extraction: {e}")
            main_text = None
    
        # Extract metadata
        try:
            extracted_metadata = trafilatura.extract_metadata(html_content)
        except (ValueError, TypeError) as e:
            print(f"An error occurred during metadata extraction: {e}")
            extracted_metadata = None
    
        # Check if extracted_metadata is None
        try:
            if extracted_metadata is None:
                print("Failed to extract metadata")
                lead_text = ''  # Set lead_text to an empty string or handle it appropriately
            else:
                if extracted_metadata.description is not None:
                    lead_text = extracted_metadata.description.replace('\n', ' ')
                else:
                    lead_text = ''
        except AttributeError as e:
            print(f"An error occurred during lead text extraction: {e}")
            lead_text = ''
    
        # Check if the URL matches the extracted URL
        url = extracted_metadata.url if extracted_metadata else None
        author = extracted_metadata.author if extracted_metadata else None
        date = extracted_metadata.date if extracted_metadata else None
    
        # Create a dictionary with the extracted content and metadata
        content_dict = {
            "url": url,
            "main_text": main_text,
            "lead_text": lead_text,
            "last_online_verification_date": datetime.now().isoformat(),
        }
    
        return content_dict

    def check_for_paywall(self, paywall_strategy = WEBSITE_STRATEGIES["spiegel"]["paywall"]):
        """Check if the page is paywalled"""
        original_wait = self.wait  # Save the original wait
        self.wait = WebDriverWait(self.driver, 1)  # Set a shorter wait
        
        # Check if the page is paywalled using the strategies defined in the config
        try:
            if self.find_element(paywall_strategy):
                return True
        except (NoSuchElementException, TimeoutException):
            return False 
        finally:
            self.wait = original_wait  # Reset the wait


    def save_extracted_data(self):
        """Save the extracted data to a file"""
        filename = "extracted_data.json"
        main_text_to_vectorize, lead_text_to_vectorize, return_url, author, date = self.extract_content()
        main_text_vectorized = self.vectorize_text(main_text_to_vectorize)
        lead_text_vectorized = self.vectorize_text(lead_text_to_vectorize)
        data = {
            "main_text_vector": main_text_vectorized,
            "lead_text_vector": lead_text_vectorized,
            "return_url": return_url,
            "author": author,
            "date": date
        }
        with open(filename, "w") as f:
            json.dump(data, f)


    def close_browser(self):
        """Close the browser and end the session"""
        # Close the browser and end the session
        if self.driver:
            self.driver.quit()