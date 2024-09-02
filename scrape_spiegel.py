import json

from database_handling.DataDownload import DataDownloader
from database_handling.DataHandleAndOtherHelpers import DataHandler
from database_handling.DataUpload import DataUploader
from database_handling.KeycloakLogin import KeycloakLogin
from scrapers.SpiegelScraper import SpiegelScraper
from text_analysis.NEExtractor import NEExtractor
from text_analysis.Summarizer import Summarizer
from text_analysis.TopicExtractor import TopicExtractor
from text_analysis.Vectorizers import Vectorizer

# scrape the spiegel
spiegel_scraper = SpiegelScraper()
spiegel_scraper.start_browser()
spiegel_scraper.login()
this_runs_articles = spiegel_scraper.scrape_spiegel()


# get the token for the database
keycloak_login = KeycloakLogin()
token = keycloak_login.return_token()

# get all spiegel urls that are already in the database
data_downloader = DataDownloader(token)
spiegel_articles_in_db = data_downloader.get_content(url="https://www.spiegel.de/") # TODO: Durch config ersetzen

# print(spiegel_articles_in_db)


# instantiate all data anylysis classes
# summarizer = Summarizer()
entity_extractor = NEExtractor()
topic_extractor = TopicExtractor()
vectorizer = Vectorizer()


# instantiate the data handler
data_handler = DataHandler()

# for the articles that are already in the database, only update the last_verification_date
articles_for_last_verifcation_date_update = data_handler.find_scraped_articles_already_in_db(this_runs_articles, spiegel_articles_in_db)
# safe the responses to the last verification date update
responses_to_last_verifcation_date_update = data_handler.patch_last_online_verification_date(token, articles_for_last_verifcation_date_update)
# get the articles that are not yet in the database
spiegel_articles_not_yet_in_db = data_handler.find_scraped_articles_not_already_in_db(this_runs_articles, spiegel_articles_in_db)
spiegel_articles_not_yet_in_db_list_of_dicts = [article for article in this_runs_articles if article['url'] in spiegel_articles_not_yet_in_db]

# Define the number of articles to process and upload per iteration
articles_per_iteration = 30

# Calculate the number of iterations
iterations = len(spiegel_articles_not_yet_in_db_list_of_dicts) // articles_per_iteration + (len(spiegel_articles_not_yet_in_db_list_of_dicts) % articles_per_iteration > 0)

responses = []

for i in range(iterations):
    print("Processing articles", i*articles_per_iteration, "to", (i+1)*articles_per_iteration, "from", len(spiegel_articles_not_yet_in_db_list_of_dicts))
    # Get the articles for this iteration
    articles = spiegel_articles_not_yet_in_db_list_of_dicts[i*articles_per_iteration:(i+1)*articles_per_iteration]

    print("Running text processing on articles", i*articles_per_iteration, "to", (i+1)*articles_per_iteration, "from", len(spiegel_articles_not_yet_in_db_list_of_dicts))
    # Add the summaries, named entities, topics, and vectors to the articles dict
    # articles = summarizer.summarize(articles)
    articles = entity_extractor.extract_entities(articles)
    articles = topic_extractor.extract_topics(articles)
    articles = vectorizer.vectorize(articles)

    # Remove main_text and lead_text from articles
    for article in articles:
        article.pop('main_text', None)
        article.pop('lead_text', None)

    print("Uploading articles", i*articles_per_iteration, "to", (i+1)*articles_per_iteration, "from", len(spiegel_articles_not_yet_in_db_list_of_dicts))
    # Ensure that the token is still valid every n iterations
    # TODO: Tell Mario chuncking was done because I get a new token every 30 uploads to make sure the token is always valid
    # if we do that every 1 upload that takes much longer since it takes ~20 seconds to get a net token/ensure the token is valid
    keycloak_login = KeycloakLogin()
    token = keycloak_login.return_token()

    # Loop over articles and put every article into the database
    data_uploader = DataUploader(token)

    for article in articles:
        response = data_uploader.post_content(article)
        responses.append(response)

    print("Processed and uploaded articles", i*articles_per_iteration, "to", (i+1)*articles_per_iteration, "from", len(spiegel_articles_not_yet_in_db_list_of_dicts))

    
# save the responses to a json file
with open('responses.json', 'w') as f:
    json.dump(responses, f)