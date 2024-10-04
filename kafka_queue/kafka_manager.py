from kafka import KafkaProducer, KafkaConsumer
import json
import logging

class KafkaQueue:
    def __init__(self, topic='article_queue', processed_topic='processed_article_queue', bootstrap_servers='localhost:9092'):
        self.topic = topic
        self.processed_topic = processed_topic
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        self.consumer = KafkaConsumer(
            self.topic,
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='article_group'
        )
        self.processed_consumer = KafkaConsumer(
            self.processed_topic,
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='processed_article_group'
        )

    def enqueue(self, message):
        self.producer.send(self.topic, message)
        self.producer.flush()
        logging.info(f"Enqueued message: {message}")

    def dequeue(self):
        for message in self.consumer:
            logging.info(f"Dequeued message: {message.value}")
            yield message.value

    def enqueue_processed(self, message):
        self.producer.send(self.processed_topic, message)
        self.producer.flush()
        logging.info(f"Enqueued processed message: {message}")

    def dequeue_processed(self):
        for message in self.processed_consumer:
            logging.info(f"Dequeued processed message: {message.value}")
            yield message.value

    def close(self):
        self.producer.close()
        self.consumer.close()
        self.processed_consumer.close()
