# kafka_test.py
import logging
from kafka_queue.kafka_manager import KafkaQueue

# Configure logging
logging.basicConfig(level=logging.INFO)

def main():
    # Create an instance of KafkaQueue
    kafka_queue = KafkaQueue(topic='test-topic')

    # Sending messages to the 'article_queue'
    messages_to_send = [
        {"title": "Article 1", "content": "Content of article 1"},
        {"title": "Article 2", "content": "Content of article 2"},
        {"title": "Article 3", "content": "Content of article 3"},
    ]

    for message in messages_to_send:
        kafka_queue.enqueue(message)

    # Receiving messages from the 'article_queue'
    logging.info("Receiving messages from the test topic:")
    for message in kafka_queue.dequeue():  # This will now consume from 'test-topic'
        logging.info(f"Received message: {message}")

    # Optionally, send processed messages to the 'processed_article_queue'
    for message in messages_to_send:
        kafka_queue.enqueue_processed(message)

    # Receiving processed messages
    logging.info("Receiving messages from the processed_article_queue:")
    for message in kafka_queue.dequeue_processed():
        logging.info(f"Received processed message: {message}")

    # Close the KafkaQueue instance
    kafka_queue.close()

if __name__ == "__main__":
    main()
