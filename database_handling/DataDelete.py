from config import BASE_URLS
from database_handling.KeycloakLogin import KeycloakLogin
import requests
import json

class DataDeleter:
    def __init__(self, auth_token):
        """Initialize the DataDelete class with a database connection."""
        self.base_url = BASE_URLS["m3-api-base"]
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {auth_token}'
        }

    def _return_response(self, response):
        """Utility method to return the response."""
        if response:
            try:
                return response.status_code
            except json.JSONDecodeError:
                print("Error decoding JSON")
                return {"error": "JSON decoding error", "response_text": response}
        else:
            print("Empty response received")
            return {"error": "Empty response"}, response

    def _delete_data(self, endpoint, identifier=None):
        """Sends a DELETE request to the specified endpoint with an identifier."""
        url = f'{self.base_url}{endpoint}'
        if identifier:
            url = f'{url}{identifier}'  # Correctly append the identifier to the URL path
        
        try:
            response = requests.delete(url, headers=self.headers)
            response.raise_for_status()  # Raises an HTTPError if the status is 4xx, 5xx
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return {"error": str(e)}, None
        else:
            return self._return_response(response)

    def delete_profile(self, identifier):
        """Deletes profile information."""
        return self._delete_data("api/v1/profile/", identifier)

    def delete_content(self, identifier):
        """Deletes content."""
        return self._delete_data("api/v1/content/", identifier)

    def delete_encounter(self, identifier):
        """Deletes encounters."""
        return self._delete_data("api/v1/encounter/", identifier)

    def delete_use(self, identifier):
        """Deletes use."""
        return self._delete_data("api/v1/use/", identifier)