from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models.location import Location
from app.models.prediction import Prediction
from app.models.environmental import EnvironmentalMeasurement
from app.schemas.prediction import PredictionInput, PredictionOutput, RiskFactor
from app.ml.pipeline import predict_landslide_risk
from app.services.alert_engine import get_active_thresholds, evaluate_and_generate_alert
from app.services.explanation_engine import generate_geotechnical_explanation, generate_recommendations

def utc_now():
    return datetime.now(timezone.utc)

def process_prediction(
    db: Session,
    input_data: PredictionInput,
    source: str = "MANUAL_INPUT"
) -> PredictionOutput:
    """
    Core orchestrator: feature engineering -> ML prediction -> explainability ->
    early warning alert generation -> DB persistence -> structured response.
    """
    raw_dict = input_data.model_dump()
    thresholds = get_active_thresholds(db)

    # 1. Run Machine Learning Pipeline
    pred_res = predict_landslide_risk(raw_dict, thresholds=thresholds)

    risk_score = pred_res["risk_score"]
    risk_level = pred_res["risk_level"]
    prob = pred_res["probability"]
    confidence = pred_res["confidence"]
    raw_risk_factors = pred_res["risk_factors"]
    engineered = pred_res["engineered_features"]

    # 2. Generate Geotechnical Explanation & Recommendations
    explanation_text = generate_geotechnical_explanation(
        risk_level=risk_level,
        risk_score=risk_score,
        features=engineered,
        risk_factors=raw_risk_factors
    )
    rec_data = generate_recommendations(risk_level, engineered)
    recommendation_text = rec_data["recommendation"]

    # Format risk factors to schema
    formatted_factors = [
        RiskFactor(
            factor=rf["factor"],
            impact=rf["impact"],
            weight=rf["weight"],
            description=rf["description"]
        ) for rf in raw_risk_factors
    ]

    timestamp_str = utc_now().isoformat()

    if input_data.simulation:
        return PredictionOutput(location_id=input_data.location_id, risk_score=risk_score,
            risk_level=risk_level, probability=prob, confidence=confidence,
            risk_factors=formatted_factors, timestamp=timestamp_str,
            recommendation=recommendation_text, explanation=explanation_text, input_features=raw_dict)

    # 3. Find or Create Location Record
    loc = db.query(Location).filter(Location.location_id == input_data.location_id).first()
    if not loc:
        # Create a dynamically registered location if new
        loc = Location(
            location_id=input_data.location_id,
            name=f"Site {input_data.location_id}",
            state="North East Region",
            district="Monitored Sector",
            latitude=input_data.latitude,
            longitude=input_data.longitude,
            elevation=input_data.elevation,
            slope=input_data.slope,
            terrain_roughness=input_data.terrain_roughness,
            monitoring_status="ACTIVE",
            risk_level=risk_level,
            current_risk_score=risk_score,
            alert_status="NORMAL"
        )
        db.add(loc)
        db.commit()
        db.refresh(loc)

    # 4. Save Prediction Record
    pred_record = Prediction(
        location_id=loc.location_id,
        timestamp=utc_now(),
        risk_score=risk_score,
        risk_level=risk_level,
        probability=prob,
        confidence=confidence,
        risk_factors=[rf.model_dump() for rf in formatted_factors],
        recommendation=recommendation_text,
        explanation=explanation_text,
        input_features={**raw_dict, "_model_sha256": pred_res.get("model_version", "unknown")},
        model_version=pred_res.get("model_version", "unknown")[:32]
    )
    db.add(pred_record)

    # 5. Also log environmental measurement snapshot
    env_record = EnvironmentalMeasurement(
        location_id=loc.location_id,
        timestamp=utc_now(),
        rainfall_1h=input_data.rainfall_1h,
        rainfall_24h=input_data.rainfall_24h,
        rainfall_7d=input_data.rainfall_7d,
        rainfall_intensity=input_data.rainfall_1h,
        soil_moisture=input_data.soil_moisture,
        soil_saturation=min(1.0, input_data.soil_moisture / 80.0),
        vegetation_index=input_data.vegetation_index,
        source=source,
        raw_payload=raw_dict
    )
    db.add(env_record)

    # 6. Update Location Cache
    output_snapshot = {
        "model_sha256": pred_res.get("model_version", "unknown"),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "probability": prob,
        "confidence": confidence,
        "timestamp": timestamp_str,
        "recommendation": recommendation_text,
        "explanation": explanation_text
    }
    loc.latest_prediction = output_snapshot
    loc.latest_measurements = {
        "rainfall_1h": input_data.rainfall_1h,
        "rainfall_24h": input_data.rainfall_24h,
        "rainfall_7d": input_data.rainfall_7d,
        "soil_moisture": input_data.soil_moisture,
        "vegetation_index": input_data.vegetation_index,
        "timestamp": timestamp_str,
        "source": source
    }
    loc.current_risk_score = risk_score
    loc.risk_level = risk_level
    loc.updated_at = utc_now()

    # 7. Evaluate Early Warning Engine for High/Severe triggers
    evaluate_and_generate_alert(db, loc, {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_factors": [rf.model_dump() for rf in formatted_factors],
        "engineered_features": engineered
    })

    db.commit()

    return PredictionOutput(
        location_id=loc.location_id,
        risk_score=risk_score,
        risk_level=risk_level,
        probability=prob,
        confidence=confidence,
        risk_factors=formatted_factors,
        timestamp=timestamp_str,
        recommendation=recommendation_text,
        explanation=explanation_text,
        input_features=raw_dict
    )
