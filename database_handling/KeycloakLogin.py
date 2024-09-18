import requests
import socket
import time
from datetime import datetime, timedelta
import logging
from keycloak import KeycloakOpenID

logger = logging.getLogger(__name__)

class KeycloakLogin:
    def __init__(self):
        self.server_hostname = "login.m3.ifkw.lmu.de"
        self.realm_name = 'm3-api'
        self.client_id = 'm3-api'
        self.username = None
        self.password = None
        self.keycloak_credentials_path = "credentials_keycloak.txt"
        self._load_credentials()
        self.token = None
        self.token_expiry = None
        self.server_ip = socket.gethostbyname(self.server_hostname)
        logger.debug(f"Resolved Keycloak server IP: {self.server_ip}")

    def _load_credentials(self):
        logger.debug("Loading credentials")
        start_time = time.time()
        if not self.username or not self.password:
            with open(self.keycloak_credentials_path, "r") as f:
                credentials = f.read().splitlines()
            self.username, self.password = credentials[0], credentials[1]
        logger.debug(f"Credential loading took {time.time() - start_time:.2f} seconds")

    def _initialize_keycloak_openid(self):
        logger.debug("Initializing KeycloakOpenID client")
        start_time = time.time()
        if self.keycloak_openid is None:
            self.keycloak_openid = KeycloakOpenID(
                server_url=self.server_url, 
                client_id=self.client_id,
                realm_name=self.realm_name, 
                verify=True
            )
        logger.debug(f"KeycloakOpenID initialization took {time.time() - start_time:.2f} seconds")


    def _refresh_ip(self):
        try:
            new_ip = socket.gethostbyname(self.server_hostname)
            if new_ip != self.server_ip:
                logger.info(f"Keycloak server IP changed from {self.server_ip} to {new_ip}")
                self.server_ip = new_ip
        except socket.gaierror as e:
            logger.error(f"Failed to refresh IP address: {str(e)}")

    def get_token(self):
        logger.debug("Getting token")
        start_time = time.time()
        if self.token is None or self.token_expiry <= datetime.now():
            self._refresh_token()
        logger.debug(f"Token retrieval took {time.time() - start_time:.2f} seconds")
        return self.token

    def _refresh_token(self):
        logger.debug("Refreshing token")
        start_time = time.time()

        headers = {'Host': self.server_hostname}
        data = {
            'grant_type': 'password',
            'client_id': self.client_id,
            'username': self.username,
            'password': self.password
        }
        token_url = f"https://{self.server_ip}/auth/realms/{self.realm_name}/protocol/openid-connect/token"

        try:
            response = requests.post(token_url, headers=headers, data=data, verify=False)
            response.raise_for_status()
            token_json = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during token request: {str(e)}")
            raise

        logger.debug(f"Token request took {time.time() - start_time:.2f} seconds")
        self.token = token_json['access_token']
        self.token_expiry = datetime.now() + timedelta(seconds=token_json['expires_in'] - 120)
        logger.debug(f"Token refresh took {time.time() - start_time:.2f} seconds")
