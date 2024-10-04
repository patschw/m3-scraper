import json
import logging
from database_handling.DataUpload import DataUploader

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

        # Initialize DataUploader
        uploader = DataUploader()

        for article in articles:
            response = uploader.post_content(article)  # Implement your upload logic
            logger.info(f"Uploaded article: {article.get('url', 'N/A')}. Response: {response}")

    except Exception as e:
        logger.error(f"Error during upload: {str(e)}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    upload_data()