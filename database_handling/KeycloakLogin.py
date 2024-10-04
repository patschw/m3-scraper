import os
import logging
from datetime import datetime, timedelta
from keycloak import KeycloakOpenID
from config import KEYCLOAK_CREDENTIALS_PATH

# Set up logging for the scraper to track events and errors
logger = logging.getLogger(__name__)

class KeycloakLogin:
    def __init__(self):
        logging.debug("Initializing KeycloakLogin class")
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
            logging.info("Loading credentials from file: %s", self.keycloak_credentials)
            try:
                with open(self.keycloak_credentials, "r") as f:
                    credentials = f.read().splitlines()
                self.username, self.password = credentials[0], credentials[1]
                logging.debug("Credentials loaded successfully")
            except FileNotFoundError as e:
                logging.error("Credentials file not found: %s", e)
                raise
            except Exception as e:
                logging.error("Error reading credentials: %s", e)
                raise
        else:
            logging.debug("Credentials already loaded")

    def _initialize_keycloak_openid(self):
        """Initialize the KeycloakOpenID client only when needed."""
        if self.keycloak_openid is None:
            logging.info("Initializing KeycloakOpenID client")
            try:
                self.keycloak_openid = KeycloakOpenID(
                    server_url=self.server_url, 
                    client_id=self.client_id,
                    realm_name=self.realm_name, 
                    verify=True # TODO: Change to true
                )
                logging.debug("KeycloakOpenID client initialized")
            except Exception as e:
                logging.error("Failed to initialize KeycloakOpenID client: %s", e)
                raise
        else:
            logging.debug("KeycloakOpenID client already initialized")

    def get_token(self):
        """Get a valid token, refreshing if necessary."""
        logging.info("Getting token")
        if self.token is None:
            logging.info("Token is None, refreshing token")
            self._refresh_token()
        elif self.token_expiry <= datetime.now():
            logging.info("Token expired, refreshing token")
            self._refresh_token()
        else:
            logging.debug("Token is still valid, no need to refresh")
        return self.token

    def _refresh_token(self):
        """Refresh the token."""
        logging.info("Refreshing token")
        self._initialize_keycloak_openid()
        try:
            token_json = self.keycloak_openid.token(
                username=self.username, 
                password=self.password, 
                scope='openid',
                grant_type='password'
            )
            self.token = token_json['access_token']
            self.token_expiry = datetime.now() + timedelta(seconds=token_json['expires_in'] - 120)
            logging.info("Token refreshed successfully. Token expires at: %s", self.token_expiry)
        except Exception as e:
            logging.error("Failed to refresh token: %s", e)
            raise
