# config.py:
from selenium.webdriver.common.by import By

# Define the strategy lists for different websites
WEBSITE_STRATEGIES = {
    'spiegel': {
        'email_username': [
            (By.ID, "username"),
            (By.NAME, "loginform:username"),
            (By.CSS_SELECTOR, "#username"),
            (By.XPATH, """//*[@id="username"]"""),
        ],
        'password': [
            (By.ID, "password"),
            (By.NAME, "loginform:password"),
            (By.CSS_SELECTOR, "#password"),
            (By.XPATH, """//*[@id="password"]"""),
        ],
        'submit': [
            (By.ID, "submit"),
            (By.NAME, "loginform:submit"),
            (By.CSS_SELECTOR, "#submit"),
            (By.XPATH, """//*[@id="submit"]"""),
        ],
        'submit_after_login': [
            (By.CSS_SELECTOR, "a.sm\:hidden:nth-child(2) > span:nth-child(1)"),
            (By.XPATH, "/html/body/header/div/div/div[1]/div/div/div/a[2]/span")
        ],
        'paywall': [
        (By.ID, "fieldset-monatsabo"),
        (By.NAME, "subscription"),
        (By.CSS_SELECTOR, "#fieldset-monatsabo"),
        (By.XPATH, """//*[@id="fieldset-monatsabo"]"""),
        ]
    },
    'zeit': {
        'email_username': [
            (By.ID, "login_email"),
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "#login_email"),
            (By.XPATH, """//*[@id="login_email"]"""),
        ],
        'password': [
            (By.ID, "login_pass"),
            (By.NAME, "pass"),
            (By.CSS_SELECTOR, "#login_pass"),
            (By.XPATH, """//*[@id="login_pass"]"""),
        ],
        'submit': [
            (By.CSS_SELECTOR, ".submit-button"),
            (By.XPATH, """/html/body/main/div/div/div/div/form/div[4]/input"""),
        ],
        'paywall': [
        (By.ID, "paywall"),
        (By.CSS_SELECTOR, "#paywall"),
        (By.XPATH, """//*[@id="paywall"]"""),
        ]
    },
    'sueddeutsche': {
        'email_username': [
            (By.ID, "login"),
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "#login"),
            (By.XPATH, """//*[@id="login"]"""),
        ],
        'password': [
            (By.ID, "current-password"),
            (By.NAME, "current-password"),
            (By.CSS_SELECTOR, "#current-password"),
            (By.XPATH, """//*[@id="current-password"]"""),
        ],
        'submit': [
            (By.ID, "authentication-button"),
            (By.CSS_SELECTOR, ".cta-button"),
            (By.XPATH, """/html/body/app-main/app-widget/screen-layout/main/current-screen/div/screen-login/div/form/div/button[1]"""),
        ],
        'login_window_iframe': [
            (By.CSS_SELECTOR, "#notice > div.message-component.message-row.cmp-contract-layer-body > div.message-component.message-column.cmp-contract-layer-with-subscription > div.message-component.message-row.cmp-contract-layer-login-row > button.message-component.message-button.no-children.focusable.cmp-contract-layer-login-button.link-button.sp_choice_type_5"),
            (By.XPATH, """//*[@id="notice"]/div[3]/div[2]/div[2]/button[2]"""),
            ],
        'paywall': [
        (By.ID, "paywall"),
        (By.CSS_SELECTOR, "#paywall"),
        (By.XPATH, """//*[@id="paywall"]"""),
        ]
    },
    'bayerischer_rundfunk': {
        'shadow_dom_host': [
        (By.ID, "usercentrics-root"),
        (By.CSS_SELECTOR, "#usercentrics-root"),
        (By.XPATH, """//*[@id="usercentrics-root"]"""),
        ],
        'cookie_banner_button': [
        (By.CSS_SELECTOR, "button.sc-dcJsrY:nth-child(2)"),
        (By.XPATH, "/div/div/div[2]/div/div[2]/div/div[2]/div/div/div/button[2]"),
        ]
    },

}

# Regex patterns for article and subpage URLs
PATTERNS = {
    'spiegel': {
        'article_url': r'https://www\.spiegel\.de/.+/.+-[a-z0-9\-]+(?<!\d{4})$',
        'subpage_url': r'^https://www\.spiegel\.de/[a-z]+/$'
    }, 
    'sueddeutsche': {
        'article_url': r'^https:\/\/www\.sueddeutsche\.de\/(politik|wirtschaft|kultur|panorama|sport|projekte\/artikel|wissen|karriere|auto|stil|leben|deutschland|welt|meinung|digital|gesellschaft|muenchen)\/[\w\-]+(\/[\w\-]+)+\/?(e\d+|lux\.[\w]+)?\/?$',
        'subpage_url': r'^https://www\.sueddeutsche\.de/[a-zA-Z0-9]+(?:/[a-zA-Z0-9_-]+)?$'
    },
    'zeit': {
        'article_url': r'https://www\.zeit\.de/.+/.+-[a-z0-9\-]+(?<!\d{4})$',
        'subpage_url': r'^https://www\.zeit\.de/[a-z]+/$'
    },
    'bayerischer_rundfunk': {
        'article_url': r'https://www\.br\.de/.+/.+-[a-z0-9\-]+(?<!\d{4})$',
        'subpage_url': r'^https://www\.br\.de/[a-z]+/$'
    }
}


# You can also add other configuration settings here
CREDENTIALS_PATH = "credentials.txt"

# Path to the file containing the credentials for the keycloak login
KEYCLOAK_CREDENTIALS_PATH = "credentials_keycloak.txt"


# URLs for login pages
LOGIN_URLS = {"spiegel": "https://gruppenkonto.spiegel.de/anmelden.html",
              "zeit": "https://meine.zeit.de/anmelden",
              "sueddeutsche": "https://www.sueddeutsche.de/?piano-screen=login"}


# Base URLs for the different websites
# RULE: THE URL HERE ENDS WITH A SLASH, THE REMAINDER PART OF THE URL IN THE CODE DOES NOT START WITH A SLASH
BASE_URLS = {"m3-api-base": "https://api.m3.ifkw.lmu.de/",
            "spiegel": "https://www.spiegel.de/", 
            "zeit": "https://www.zeit.de/", 
            "sueddeutsche": "https://www.sueddeutsche.de/",
            "bayerischer_rundfunk": "https://www.br.de/nachrichten/"}

# transformer models used for vectorisation
TRANSFORMER_MODEL_NAMES_DICT = {'bert': 'deepset/gbert-large', 
                                'roberta': 'T-Systems-onsite/german-roberta-sentence-transformer-v2', 
                                'gbert': 'deutsche-telekom/gbert-large-paraphrase-euclidean', 
                                'xmlr': 'xlm-roberta-large', 
                                'bigbird': 'google/bigbird-roberta-large', 
                                'longformer': 'severinsimmler/xlm-roberta-longformer-large-16384'}