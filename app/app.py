import pickle
import pandas as pd
from flask import Flask, jsonify, request
import pika
import json

RABBITMQ_HOST = "rabbitmq"
QUEUE_NAME = "batch_predictions"

app = Flask(__name__)

with open('./models/model_v1.pkl', 'rb') as f:
    artifact = pickle.load(f)

model = artifact["model"]
FEATURES = artifact["features"]

def preprocess_input(data: dict) -> pd.DataFrame:
    missing_features = [col for col in FEATURES if col not in data]

    if missing_features:
        raise ValueError(f"Missing features: {missing_features}")

    row = {col: data[col] for col in FEATURES}

    return pd.DataFrame([row])

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
            return jsonify({"error": "Request body must be JSON"}), 400

        X = preprocess_input(data)

        prediction = int(model.predict(X)[0])
        probability = float(model.predict_proba(X)[0, 1])

        return jsonify({
            "prediction": prediction,
            "probability": probability
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)