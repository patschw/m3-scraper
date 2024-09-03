from keycloak import KeycloakOpenID
from config import KEYCLOAK_CREDENTIALS_PATH
import os
from datetime import datetime, timedelta
import logging

class KeycloakLogin:
    def __init__(self):
        self.server_url = "https://login.m3.ifkw.lmu.de/auth/"
        self.realm_name = 'm3-api'
        self.client_id = 'm3-api'
        self.keycloak_credentials = KEYCLOAK_CREDENTIALS_PATH
        self.username = None
        self.password = None
        self._load_credentials()
        self.token = None
        self.token_expiry = None
        self.keycloak_openid = None

    def _load_credentials(self):
        """Load credentials once and store them."""
        if not self.username or not self.password:
            with open(self.keycloak_credentials, "r") as f:
                credentials = f.read().splitlines()
            self.username, self.password = credentials[0], credentials[1]

    def _initialize_keycloak_openid(self):
        """Initialize the KeycloakOpenID client only when needed."""
        if self.keycloak_openid is None:
            self.keycloak_openid = KeycloakOpenID(
                server_url=self.server_url, 
                client_id=self.client_id,
                realm_name=self.realm_name, 
                verify=True
            )

    def get_token(self):
        """Get a valid token, refreshing if necessary."""
        if self.token is None or self.token_expiry <= datetime.now():
            self._refresh_token()
        return self.token

    def _refresh_token(self):
        """Refresh the token."""
        self._initialize_keycloak_openid()
        token_json = self.keycloak_openid.token(
            username=self.username, 
            password=self.password, 
            scope='openid',
            grant_type='password'
        )
        self.token = token_json['access_token']
        self.token_expiry = datetime.now() + timedelta(seconds=token_json['expires_in'] - 120)  # Refresh 2 minutes before expiry
