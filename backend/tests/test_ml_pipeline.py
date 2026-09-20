import pytest
from app.ml.feature_engineering import engineer_features, FEATURE_COLUMNS
from app.ml.pipeline import predict_landslide_risk, get_model_metadata

def test_feature_engineering():
    raw = {
        "rainfall_1h": 15.0,
        "rainfall_24h": 120.0,
        "rainfall_7d": 350.0,
        "soil_moisture": 85.0,
        "slope": 42.0,
        "elevation": 1500.0,
        "terrain_roughness": 30.0,
        "vegetation_index": 0.4
    }
    features = engineer_features(raw)
    for col in FEATURE_COLUMNS:
        assert col in features, f"Missing feature column: {col}"
    
    assert features["antecedent_rainfall_index"] > 0
    assert features["critical_rainfall_ratio"] > 1.0  # 120mm on 42 deg slope exceeds threshold
    assert 0.0 <= features["soil_saturation_ratio"] <= 1.0

def test_predict_landslide_risk_severe():
    high_hazard_input = {
        "rainfall_1h": 25.0,
        "rainfall_24h": 180.0,
        "rainfall_7d": 450.0,
        "soil_moisture": 92.0,
        "slope": 45.0,
        "elevation": 1600.0,
        "terrain_roughness": 35.0,
        "vegetation_index": 0.3
    }
    result = predict_landslide_risk(high_hazard_input)
    assert result["risk_level"] in ["HIGH", "SEVERE"]
    assert result["risk_score"] >= 65.0
    assert result["probability"] > 0.60
    assert len(result["risk_factors"]) >= 3
    assert result["confidence"] > 0.6

def test_predict_landslide_risk_low():
    safe_input = {
        "rainfall_1h": 0.0,
        "rainfall_24h": 2.0,
        "rainfall_7d": 10.0,
        "soil_moisture": 18.0,
        "slope": 8.0,
        "elevation": 200.0,
        "terrain_roughness": 5.0,
        "vegetation_index": 0.8
    }
    result = predict_landslide_risk(safe_input)
    assert result["risk_level"] == "LOW"
    assert result["risk_score"] < 25.0
    assert result["probability"] < 0.25

def test_model_metadata():
    metadata = get_model_metadata()
    assert metadata["accuracy"] >= 0.90
    assert metadata["roc_auc"] >= 0.95
    assert len(metadata["feature_importances"]) > 0
