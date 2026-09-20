import os
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
from app.ml.dataset import generate_ner_landslide_dataset
from app.ml.feature_engineering import FEATURE_COLUMNS
from app.core.config import settings

def train_and_save_model(artifact_path: str = None) -> dict:
    """
    Trains an ensemble ML model for Landslide Early Warning
    and saves the serialized artifact.
    """
    if artifact_path is None:
        os.makedirs(settings.MODEL_DIR, exist_ok=True)
        artifact_path = os.path.join(settings.MODEL_DIR, settings.MODEL_FILE_NAME)

    print("Generating geotechnical training dataset for North East Region...")
    df = generate_ner_landslide_dataset(n_samples=2500, random_seed=42)

    X = df[FEATURE_COLUMNS]
    y = df["landslide_occurred"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # 1. Feature Scaler
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 2. Base Random Forest
    base_rf = RandomForestClassifier(
        n_estimators=160,
        max_depth=12,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )

    # 3. Calibrated Classifier for authentic posterior probabilities (5-fold CV)
    calibrated_model = CalibratedClassifierCV(estimator=base_rf, method="sigmoid", cv=5)
    calibrated_model.fit(X_train_scaled, y_train)

    # Fit a standalone base_rf for feature importances and tree variance
    base_rf.fit(X_train_scaled, y_train)

    # 4. Evaluation
    y_pred = calibrated_model.predict(X_test_scaled)
    y_prob = calibrated_model.predict_proba(X_test_scaled)[:, 1]

    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred))
    rec = float(recall_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred))
    auc = float(roc_auc_score(y_test, y_prob))
    cm = confusion_matrix(y_test, y_pred).tolist()

    # Feature importances from the base estimator
    importances = dict(zip(FEATURE_COLUMNS, [float(v) for v in base_rf.feature_importances_]))
    sorted_importances = sorted(importances.items(), key=lambda item: item[1], reverse=True)

    metrics = {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(auc, 4),
        "confusion_matrix": cm,
        "sample_size": len(df),
        "test_size": len(y_test),
        "feature_importances": sorted_importances,
        "model_architecture": "Calibrated Random Forest Ensemble (160 Estimators, Sigmoid Calibration)",
        "version": "1.0.0",
        "data_type": "SYNTHETIC_DEMONSTRATION"
    }

    artifact = {
        "model": calibrated_model,
        "base_estimator": base_rf,
        "scaler": scaler,
        "feature_columns": FEATURE_COLUMNS,
        "metrics": metrics
    }

    os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
    joblib.dump(artifact, artifact_path)
    print(f"Model saved successfully to {artifact_path} with AUC-ROC: {auc:.4f} and F1: {f1:.4f}")

    return metrics

if __name__ == "__main__":
    train_and_save_model()
