import pickle
from flask import Flask, jsonify, request
import pika
import json
from src.inference.predict import predict_item

# RabbitMQ service name and input queue name
RABBITMQ_HOST = "rabbitmq"
INPUT_QUEUE = "batch_predictions"

MODEL_PATH = "/app/models/model_v1.pkl"

app = Flask(__name__)

# Open & deserialize the model as a dict of the model itself and its FEATURES
with open(MODEL_PATH, 'rb') as f:
    artifact = pickle.load(f)

model = artifact["model"]
FEATURES = artifact["features"]

# Send to queue for batch predictions
def send_to_queue(message: dict):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )
    channel = connection.channel()

    # Durable queue to prevent message deletion if RabbitMQ crashes
    channel.queue_declare(queue=INPUT_QUEUE, durable=True)

    channel.basic_publish(
        exchange="",
        routing_key=INPUT_QUEUE,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            # Write messages to disk - more stable design
            delivery_mode=2
        )
    )

    connection.close()

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

# Predict for a single record - sync
@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()

        if data is None:
            return jsonify({"error": "Request body must be a JSON"}), 400

        result = predict_item(data, model, FEATURES)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Predict for a batch of records - async
@app.route("/predict_batch", methods=["POST"])
def predict_batch():
    try:
        data = request.get_json()

        if data is None:
            return jsonify({"error": "Request body must be a JSON"}), 400

        if not isinstance(data, list):
            return jsonify({"error": "Request body must be a list of JSON objects"}), 400

        message = {
            "items": data
        }

        send_to_queue(message)

        return jsonify({
            "status": "accepted",
            "message": "Batch prediction task sent to queue, see the results in the worker logs",
            "items_count": len(data)
        }), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)