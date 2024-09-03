from config import BASE_URLS
from database_handling.KeycloakLogin import KeycloakLogin
import requests
import json

class DataUploader:
    def __init__(self, auth_token):
        """Initialize the DataDownloader with a database connection."""
        self.base_url = BASE_URLS["m3-api-base"]
        self.headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {auth_token}'
        }

    def _build_query(self, **filters):
        """Utility method to build query string from filters."""
        query = {}
        for key, value in filters.items():
            if value is not None:
                query[key] = value
        return query

    def _return_response(self, response):
        """Utility method to return the response."""
        if response.text:
            try:
                return response.json()
            except json.JSONDecodeError:
                print("Error decoding JSON")
                print(response.text)
                print(response.status_code)
        else:
            print("Empty response received")

    def post_profile(self, data):
        """Uploads profile information."""
        url = f'{self.base_url}api/v1/profile/'
        response = requests.post(url, headers=self.headers, data=json.dumps(data))
        return self._return_response(response)
    
    def post_content(self, data):
        """Uploads content"""
        url = f'{self.base_url}api/v1/content/'
        response = requests.post(url, headers=self.headers, data=json.dumps(data))
        return self._return_response(response)

    def post_use(self, data):
        """Uploads use """
        url = f'{self.base_url}api/v1/use/'
        response = requests.post(url, headers=self.headers, data=json.dumps(data))
        return self._return_response(response)

    def post_encounter(self, data):
        """Uploads encounter"""
        url = f'{self.base_url}api/v1/encounter/'
        response = requests.post(url, headers=self.headers, data=json.dumps(data))
        return self._return_response(response)

    def patch_content(self, data, **params):
        """Patches content with given parameters and data."""
        url = f'{self.base_url}api/v1/content/'
        response = requests.patch(url, headers=self.headers, params=params, data=json.dumps(data))
        return self._return_response(response)
        
    def patch_use(self, data, **params):
        """Patches use with given parameters and data."""
        url = f'{self.base_url}api/v1/use/'
        response = requests.patch(url, headers=self.headers, params=params, data=json.dumps(data))
        return self._return_response(response)

    def patch_encounter(self, data, **params):
        """Patches encounter with given parameters and data."""
        url = f'{self.base_url}api/v1/encounter/'
        response = requests.patch(url, headers=self.headers, params=params, data=json.dumps(data))
        return self._return_response(response)


    
