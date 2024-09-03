from keycloak import KeycloakOpenID
from config import KEYCLOAK_CREDENTIALS_PATH
import os
from datetime import datetime, timedelta

class KeycloakLogin:
    def __init__(self):
        self.server_url = "https://login.m3.ifkw.lmu.de/auth/"
        self.realm_name = 'm3-api'
        self.client_id = 'm3-api'
        self.keycloak_credentials = KEYCLOAK_CREDENTIALS_PATH
        self.username, self.password = self._get_credentials()
        self.token = None
        self.token_expiry = None
        self.keycloak_openid = KeycloakOpenID(server_url=self.server_url, 
                                              client_id=self.client_id,
                                              realm_name=self.realm_name, 
                                              verify=True)
    
    def _get_credentials(self):
        """Get the credentials from the config file."""
        with open(self.keycloak_credentials, "r") as f:
            credentials = f.read().splitlines()
        return credentials[0], credentials[1]

    def get_token(self):
        """Get a valid token, refreshing if necessary."""
        if self.token is None or self.token_expiry <= datetime.now():
            self._refresh_token()
        return self.token

    def _refresh_token(self):
        """Refresh the token."""
        token_json = self.keycloak_openid.token(username=self.username, 
                                                password=self.password, 
                                                scope='openid',
                                                grant_type='password')
        self.token = token_json['access_token']
        self.token_expiry = datetime.now() + timedelta(seconds=token_json['expires_in'] - 60)  # Refresh 1 minute before expiry


