import pandas as pd


def preprocess_item(item: dict, features: list) -> pd.DataFrame:
    missing_features = [col for col in features if col not in item]

    if missing_features:
        raise ValueError(f"Missing features: {missing_features}")

    row = {col: item[col] for col in features}

    return pd.DataFrame([row])


def predict_item(item: dict, model, features: list) -> dict:
    X = preprocess_item(item, features)

    prediction = int(model.predict(X)[0])
    probability = float(model.predict_proba(X)[0, 1])

    return {
        "prediction": prediction,
        "probability": probability
    }