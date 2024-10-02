from config import BASE_URLS
from database_handling.DataUpload import DataUploader
from database_handling.DataDownload import DataDownloader
from datetime import datetime

# TODO: Neuen Namen für die Klasse finden
class DataHandler:
    def __init__(self):
        pass
        
        
    def find_scraped_articles_already_in_db(self, scraped_articles, articles_already_in_db):
        # The database content is returned as a dictionary of dictionaries where the first key is "iteams"
        # The scrper content is returned as a list of dictionaries
        # The different formats make sense since we can only upload to the DB one article at a time and therefore need a list of dicts
        # The download can be done in bulk and therefore a dict of dicts is more efficient

        # DB format
        db_format_urls_list = [item['url'] for item in articles_already_in_db]

        # Scraper format
        scraper_format_urls_list = [item['url'] for item in scraped_articles]
        
        # Find matching URLs, those scraped URLs that are already in the database
        scraped_urls_already_in_db = set(db_format_urls_list).intersection(scraper_format_urls_list)

        return scraped_urls_already_in_db
    
    def find_scraped_articles_not_already_in_db(self, scraped_articles, articles_already_in_db):
        # Get the URLs that are already in the database
        scraped_urls_already_in_db = self.find_scraped_articles_already_in_db(scraped_articles, articles_already_in_db)
    
        # Scraper format
        scraper_format_urls_list = [item['url'] for item in scraped_articles]
    
        # Find URLs that are in the scraped articles but not in the database
        scraped_urls_not_in_db = list(set(scraper_format_urls_list) - scraped_urls_already_in_db)
    
        return scraped_urls_not_in_db
        
    
    def patch_last_online_verification_date(self, auth_token, scraped_urls_already_in_db):
        """Update the last online verification date in a content_dict"""
        data_uploader = DataUploader(auth_token)
        
        responses = []
    
        new_last_online_verification_date = datetime.now().isoformat()
        for url in scraped_urls_already_in_db:
            response = data_uploader.patch_content(url=url, data={"last_online_verification_date": new_last_online_verification_date})
            responses.append(response)
        
        return responses