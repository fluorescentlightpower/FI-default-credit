import pickle

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

def train_model():
    df = pd.read_csv('../data/raw/UCI_Credit_Card.csv.zip')

    if "ID" in df.columns:
        df = df.drop(columns=["ID"])

    X = df.drop(columns=['default.payment.next.month'])
    y = df['default.payment.next.month']

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight="balanced",
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_proba)

    artifact = {
        'model': model,
        'features': list(X.columns)
    }

    with open('model_v1.pkl', "wb") as f:
        pickle.dump(artifact, f)

    print('Model saved')
    print(f"Accuracy: {acc:.4f}")
    print(f"F1: {f1:.4f}")
    print(f"ROC AUC: {roc_auc:.4f}")


if __name__ == "__main__":
    train_model()