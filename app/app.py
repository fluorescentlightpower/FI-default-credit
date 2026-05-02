import pickle
from flask import Flask, jsonify, request
import pika
import json
from src.inference.predict import predict_item

RABBITMQ_HOST = "rabbitmq"
QUEUE_NAME = "batch_predictions"

app = Flask(__name__)

with open('../models/model_v1.pkl', 'rb') as f:
    artifact = pickle.load(f)

model = artifact["model"]
FEATURES = artifact["features"]

def send_to_queue(message: dict):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )
    channel = connection.channel()

    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    channel.basic_publish(
        exchange="",
        routing_key=QUEUE_NAME,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2
        )
    )

    connection.close()

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)