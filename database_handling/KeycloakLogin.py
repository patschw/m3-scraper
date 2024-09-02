from keycloak import KeycloakOpenID
from config import KEYCLOAK_CREDENTIALS_PATH

class KeycloakLogin:
    def __init__(self):
        self.server_url = "https://login.m3.ifkw.lmu.de/auth/"
        self.realm_name = 'm3-api'
        self.client_id = 'm3-api'
        self.keycloak_credentials = KEYCLOAK_CREDENTIALS_PATH
        self.set_credentials("credentials_keycloak.txt")
        self.token = self.login()['access_token']
        
    def return_token(self):
        """Return the token."""
        return self.token

    def set_credentials(self, credentials_path):
        """Get the credentials from the config file, in case it has to be reset somewhere in the code."""
        with open(credentials_path, "r") as f:
            credentials = f.read().splitlines()
        self.username = credentials[0]
        self.password = credentials[1]    

    def login(self):
        """Login to the keycloak server and get the token. In case login has to happen again somewhere in the code."""
        keycloak_openid = KeycloakOpenID(server_url=self.server_url, 
                                         client_id=self.client_id,
                                         realm_name=self.realm_name, 
                                         verify=True)
        token_json = keycloak_openid.token(username=self.username, 
                                      password=self.password, 
                                      scope='openid',
                                      grant_type='password')
        return token_json


