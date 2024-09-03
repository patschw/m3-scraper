from config import BASE_URLS
from database_handling.KeycloakLogin import KeycloakLogin
import requests
import json
import logging


#TODO: Status code ausgeben, damit im final laufenden scraper script gechecked werden kann, ob der download erfolgreich war

logger = logging.getLogger(__name__)

class DataDownloader:
    def __init__(self, auth_token):
        """Initialize the DataDownloader with a database connection."""
        self.base_url = BASE_URLS["m3-api-base"]
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {auth_token}'
        }
                

    def _build_query(self, **params):
        """Utility method to build query string from filters."""
        # This method converts filter arguments into a dictionary that `requests` can use.
        query = {}
        for key, value in params.items():
            if value is not None:  # This ensures only provided filters are included
                query[key] = value
        return query
    
    def _return_response(self, response):
        """Utility method to return the response."""
        # Check if the response is not empty
        if response.text:
            # Try to parse the response as JSON
            try:
                return response.json()
            # Handle JSON decoding errors
            except json.JSONDecodeError:
                print("Error decoding JSON")
                print(response.text)
                print(response.status_code)
        else:
            print("Empty response received")
            
    def _get_data(self, endpoint, **params):
        """Sends a GET request to the specified endpoint with optional parameters."""
        url = f'{self.base_url}{endpoint}'
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()  # Raises a HTTPError if the status is 4xx, 5xx
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return None
        else:
            return self._return_response(response)

    def _get_data_status_code_only(self, endpoint, **params):
        """Sends a GET request to the specified endpoint and returns only the status code."""
        url = f'{self.base_url}{endpoint}'
        try:
            response = requests.get(url, headers=self.headers, params=params, stream=False, timeout=1)
            return response.status_code
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred while checking {url}: {e}")
            return None

    def get_profile(self):
        """Fetches profile information."""
        return self._get_data("api/v1/profile/")

    def get_profile_token(self):
        """Fetches a token for the profile."""
        return self._get_data("api/v1/profile/token/")
    
    def get_content(self, **params):
        """Fetches content with optional filters."""
        return self._get_data("api/v1/content/", **params)
    
    def get_only_urls(self, **params):
        """Fetches URLs with optional filters."""
        full_result_dictionary = self.get_content(**params)
        url_list = [item['url'] for item in full_result_dictionary['items']]
        return url_list

    def get_encounter(self, **params):
        """Fetches encounters with optional filters."""
        return self._get_data("api/v1/encounter/", **params)
        
    def get_use(self, **params):
        """Fetches uses with optional filters."""
        return self._get_data("api/v1/use/", **params)
    
    def get_content_rehydrate(self, **params):
        """Gets content rehydrate with optional filters."""
        return self._get_data("api/v1/content/rehydrate/", **params)

    def get_content_rehydrate_status_code_only(self, **params):
        """
        Sends a GET request to the content rehydrate API with optional filters and returns only the status code.
    
        Parameters:
        - **params: Optional query parameters to be included in the request.
    
        Returns:
        - The status code of the response (e.g., 200, 404, 500).
        """
        status_code = self._get_data_status_code_only("api/v1/content/rehydrate/", **params)
        return status_code

        # Note: This method doesn't only produce a 200 status code. It can return various status codes
        # depending on the server's response. For example:
        # - 200: Successful request
        # - 400: Bad request
        # - 401: Unauthorized
        # - 404: Not found
        # - 500: Internal server error
        # The actual status code returned depends on the server's response to the request.

    def get_content_entity(self):
        """Gets content entity."""
        return self._get_data("api/v1/content/entity/")

    def get_content_entitytype(self):
        """Gets content entitytype."""
        return self._get_data("api/v1/content/entitytype/")

    def get_content_medium(self):
        """Gets content medium."""
        return self._get_data("api/v1/content/medium/")

    def get_content_topic(self):
        """Gets content topic."""
        return self._get_data("api/v1/content/topic/")

    def get_use_channel(self):
        """Gets use channel."""
        return self._get_data("api/v1/use/channel/")

    def get_use_device(self):
        """Gets use device."""
        return self._get_data("api/v1/use/device/")

    def get_use_survey(self):
        """Gets use survey."""
        return self._get_data("api/v1/use/survey/")
    
    def get_data(self, endpoint, **params):
        """Fetches data from a specified endpoint with optional filters.
        A more general method that can be used to fetch data from any endpoint.
        The other endpoint-specific methods are kept for convenience."""
        return self._get_data(f"api/v1/{endpoint}/", **params)

