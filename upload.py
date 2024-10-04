import json
import logging
from database_handling.DataUpload import DataUploader
from database_handling.KeycloakLogin import KeycloakLogin
# configure logging
def configure_logging(log_level):
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("uploader.log"),
            logging.StreamHandler()
        ]
    )

def upload_data():
    logger = logging.getLogger(__name__)
    logger.info("Starting data upload")

    try:
        # Read processed data from the queue file
        processed_file_path = 'queue/processed_content.json'
        with open(processed_file_path, 'r') as f:
            articles = json.load(f)

        logger.info(f"Loaded {len(articles)} processed items for upload")

        responses = []
        # initialize keycloak login
        keycloak_login = KeycloakLogin()
        token = keycloak_login.get_token()
        # Initialize DataUploader
        data_uploader = DataUploader(token)

        for article in articles:
            try:
                response = data_uploader.post_content(article)
                responses.append(response)
                logger.info(f"Successfully uploaded article: {article.get('url', 'N/A')}")
            except Exception as e:
                logger.error(f"Error uploading article {article.get('url', 'N/A')}: {str(e)}", exc_info=True)

        with open('responses.json', 'w') as f:
            json.dump(responses, f)

        logger.info("Article upload completed.")

    except Exception as e:
        logger.error(f"Error during upload: {str(e)}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    upload_data()