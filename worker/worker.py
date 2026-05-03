import json
import pickle
import pika
import time

from src.inference.predict import predict_item

"""
Worker service for RabbitMQ.
Connects to the INPUT_QUEUE and calls callback() for all new items.
Pushes results to RESULT_QUEUE
"""

RABBITMQ_HOST = "rabbitmq"
INPUT_QUEUE = "batch_predictions"
RESULT_QUEUE = "batch_predictions_results"

MODEL_PATH = "/app/models/model_v1.pkl"


with open(MODEL_PATH, "rb") as f:
    artifact = pickle.load(f)

model = artifact["model"]
FEATURES = artifact["features"]

# RabbitMQ takes a longer time to start than the worker.
# Despite depends_on in docker-compose.yml, worker still fails to start the first time
def connect_to_rabbitmq():
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host="rabbitmq")
            )
            print("Connected to RabbitMQ")
            return connection
        except pika.exceptions.AMQPConnectionError:
            print("RabbitMQ is not ready yet, retrying in 5 seconds...")
            time.sleep(5)

# What to do when a message appears in the INPUT_QUEUE
def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        items = message["items"]

        # Predict for all records in the batch
        results = []

        for item in items:
            result = predict_item(item, model, FEATURES)
            results.append(result)

        # JSON-dumps for all results to be published in RESULT_QUEUE
        result_message = json.dumps({
            "status": "processed",
            "items_count": len(items),
            "results": results
        })

        # Publish to RESULT_QUEUE
        ch.basic_publish(
            exchange="",
            routing_key=RESULT_QUEUE,
            body=result_message,
            properties=pika.BasicProperties(
                delivery_mode=2
            )
        )

        # Print result to be seen in "docker compose logs -f worker"
        print(result_message)

        # Confirm the successful message processing
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }))

        # No confirmation of processing, no queueing the message again
        ch.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=False
        )

# Connect to RabbitMQ server, declare queues, loop to listen INPUT_QUEUE
def main():
    connection = connect_to_rabbitmq()

    channel = connection.channel()

    channel.queue_declare(queue=INPUT_QUEUE, durable=True)
    channel.queue_declare(queue=RESULT_QUEUE, durable=True)

    channel.basic_consume(
        queue=INPUT_QUEUE,
        on_message_callback=callback
    )

    print("Worker started...")
    channel.start_consuming()


if __name__ == "__main__":
    main()