import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List
from app.core.config import settings
from app.ml.feature_engineering import engineer_features, FEATURE_COLUMNS
from app.ml.train import train_and_save_model

_LOADED_MODEL_ARTIFACT = None

_LOADED_MODEL_PATH = None

def get_or_load_model() -> dict:
    global _LOADED_MODEL_ARTIFACT, _LOADED_MODEL_PATH
    from app.services.model_registry import active_path, digest, LOCK
    from pathlib import Path
    with LOCK:
        artifact_path = active_path()
        if not os.path.exists(artifact_path):
            train_and_save_model(artifact_path)
        signature = (artifact_path, os.stat(artifact_path).st_mtime_ns)
        if _LOADED_MODEL_ARTIFACT is not None and signature == _LOADED_MODEL_PATH:
            return _LOADED_MODEL_ARTIFACT
        artifact = joblib.load(artifact_path)
        artifact['_sha256'] = digest(Path(artifact_path))
        _LOADED_MODEL_ARTIFACT = artifact
        _LOADED_MODEL_PATH = signature
        return artifact

def predict_landslide_risk(
    raw_input: Dict[str, float],
    thresholds: Tuple[float, float, float] = (25.0, 50.0, 75.0)
) -> Dict[str, Any]:
    """
    Executes dynamic ML prediction for landslide risk.
    """
    artifact = get_or_load_model()
    model = artifact["model"]
    base_rf = artifact["base_estimator"]
    scaler = artifact["scaler"]
    feature_cols = artifact["feature_columns"]

    # 1. Feature Engineering
    engineered = engineer_features(raw_input)
    feature_df = pd.DataFrame([{col: engineered[col] for col in feature_cols}])

    # 2. Scaling & Inference
    scaled_vector = scaler.transform(feature_df)
    prob_array = model.predict_proba(scaled_vector)[0]
    prob_landslide = float(prob_array[1])

    # 3. Risk Score (0 - 100)
    # Calibrated probability scaled to 0-100 index
    risk_score = round(prob_landslide * 100.0, 1)

    # 4. Determine Risk Category based on configurable thresholds
    th_low, th_mod, th_high = thresholds
    if risk_score < th_low:
        risk_level = "LOW"
    elif risk_score < th_mod:
        risk_level = "MODERATE"
    elif risk_score < th_high:
        risk_level = "HIGH"
    else:
        risk_level = "SEVERE"

    # 5. Model Confidence
    # Calibrated distance from pure uncertainty (0.50) + tree voting variance
    tree_preds = [tree.predict_proba(scaled_vector)[0][1] for tree in base_rf.estimators_]
    tree_std = float(np.std(tree_preds))
    confidence = round(max(0.0, min(1.0, 1.0 - (tree_std * 2.0))), 3)

    # 6. Feature Attribution & Risk Factors
    # Calculate feature contribution score (standardized deviation from mean * weight)
    mean_vals = scaler.mean_
    scale_vals = scaler.scale_
    importances = dict(zip(feature_cols, base_rf.feature_importances_))

    risk_factors = []
    factor_descriptions = {
        "rainfall_24h": ("24-Hour Rainfall", "Cumulative 24h precipitation volume"),
        "rainfall_1h": ("1-Hour Rainfall Surge", "Cloudburst or sudden storm intensity"),
        "antecedent_rainfall_index": ("Antecedent Rainfall Index (ARI)", "Multi-day cumulative moisture buildup"),
        "soil_moisture": ("Soil Moisture Saturation", "High pore-water pressure reducing shear strength"),
        "slope": ("Slope Steepness", "Gravitational driving shear stress along incline"),
        "critical_rainfall_ratio": ("Himalayan Critical Threshold Ratio", "Ratio of rainfall exceeding geological safety boundary"),
        "pore_pressure_index": ("Pore-Water Destabilization", "Hydraulic pressure pushing soil grains apart"),
        "vegetation_index": ("Vegetation Cover / NDVI", "Biotechnical slope stabilization from root cohesion"),
        "elevation": ("Elevation Relief", "Orographic amplification and hydraulic head"),
        "terrain_roughness": ("Terrain Roughness", "Micro-topographic heterogeneity")
    }

    # Rank features by contribution
    contributions = []
    for i, col in enumerate(feature_cols):
        val = engineered[col]
        # Normalized z-score
        z = (val - mean_vals[i]) / scale_vals[i]
        weight = float(importances.get(col, 0.05))
        # Positive impact towards landslide
        contrib = z * weight
        contributions.append((col, contrib, val))

    contributions.sort(key=lambda x: x[1], reverse=True)

    for col, contrib, val in contributions[:5]:
        title, desc = factor_descriptions.get(col, (col.replace("_", " ").title(), "Environmental condition"))
        
        if contrib > 0.10:
            impact = "CRITICAL"
        elif contrib > 0.02:
            impact = "HIGH"
        elif contrib > -0.02:
            impact = "MODERATE"
        else:
            impact = "LOW"

        # Specialized descriptive text
        if col == "rainfall_24h":
            detail = f"{val:.1f} mm in 24h ({'severely elevated' if val > 80 else 'moderate'})"
        elif col == "soil_moisture":
            detail = f"{val:.1f}% volumetric moisture content ({'approaching saturation' if val > 75 else 'stable'})"
        elif col == "slope":
            detail = f"{val:.1f}° inclination ({'critical failure slope' if val > 35 else 'moderate grade'})"
        elif col == "critical_rainfall_ratio":
            pct = int(val * 100)
            detail = f"{pct}% of the regional geotechnical failure threshold"
        elif col == "vegetation_index":
            detail = f"NDVI {val:.2f} ({'sparse cover' if val < 0.35 else 'dense vegetative root binding'})"
        else:
            detail = f"Current value: {val:.1f}"

        risk_factors.append({
            "factor": title,
            "impact": impact,
            "weight": round(float(abs(contrib)), 3),
            "description": f"{desc} ({detail})"
        })

    return {
        "model_version": artifact.get("_sha256", "unknown"),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "probability": round(prob_landslide, 4),
        "confidence": confidence,
        "risk_factors": risk_factors,
        "engineered_features": engineered
    }

def get_model_metadata() -> dict:
    artifact = get_or_load_model()
    return artifact["metrics"]
