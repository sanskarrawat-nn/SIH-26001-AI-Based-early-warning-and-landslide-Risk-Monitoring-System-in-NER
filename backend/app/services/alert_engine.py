import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from app.models.alert import Alert
from app.models.location import Location
from app.models.settings import SystemSettings
from app.core.config import settings
from app.services.explanation_engine import generate_recommendations

def utc_now():
    return datetime.now(timezone.utc)

def get_active_thresholds(db: Session) -> Tuple[float, float, float]:
    """
    Retrieves dynamically configurable thresholds from DB,
    falling back to system defaults if unconfigured.
    """
    setting = db.query(SystemSettings).filter(SystemSettings.key == "landslide_thresholds").first()
    if setting:
        return (setting.threshold_low, setting.threshold_moderate, setting.threshold_high)
    return (
        settings.DEFAULT_THRESHOLD_LOW,
        settings.DEFAULT_THRESHOLD_MODERATE,
        settings.DEFAULT_THRESHOLD_HIGH
    )


def evaluate_and_generate_alert(
    db: Session,
    location: Location,
    prediction_result: Dict[str, Any]
) -> Optional[Alert]:
    """
    Evaluates prediction outcome against active thresholds and triggers alerts.
    """
    risk_score = prediction_result["risk_score"]
    risk_level = prediction_result["risk_level"]
    risk_factors = prediction_result.get("risk_factors", [])
    features = prediction_result.get("engineered_features", {})

    recs = generate_recommendations(risk_level, features)
    sop_actions = recs.get("sop_actions", [])
    recommended_action = recs.get("recommendation", "")

    # Update location's current status
    location.current_risk_score = risk_score
    location.risk_level = risk_level
    location.updated_at = utc_now()

    if risk_level in ["HIGH", "SEVERE"]:
        location.alert_status = "CRITICAL" if risk_level == "SEVERE" else "WARNING"
        
        # Check if an ACTIVE alert already exists for this location to avoid duplicate spam
        existing_alert = db.query(Alert).filter(
            Alert.location_id == location.location_id,
            Alert.status == "ACTIVE"
        ).order_by(Alert.created_at.desc()).first()

        title = f"{risk_level} Landslide Warning: {location.name}, {location.district}"
        message = (
            f"Landslide risk score has surged to {risk_score:.1f}/100 ({risk_level}). "
            f"Active environmental conditions indicate dangerous slope instability. "
            f"Location: {location.name}, {location.state} ({location.latitude}°N, {location.longitude}°E)."
        )

        if existing_alert:
            # Upgrade or refresh the existing active alert
            existing_alert.severity = risk_level
            existing_alert.risk_score = risk_score
            existing_alert.title = title
            existing_alert.message = message
            existing_alert.triggering_factors = risk_factors
            existing_alert.recommended_action = recommended_action
            existing_alert.sop_actions = sop_actions
            existing_alert.created_at = utc_now()
            db.commit()
            db.refresh(existing_alert)
            return existing_alert
        else:
            # Create a new alert
            new_alert = Alert(
                alert_id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
                location_id=location.location_id,
                severity=risk_level,
                status="ACTIVE",
                risk_score=risk_score,
                title=title,
                message=message,
                triggering_factors=risk_factors,
                recommended_action=recommended_action,
                sop_actions=sop_actions,
                created_at=utc_now()
            )
            db.add(new_alert)
            db.commit()
            db.refresh(new_alert)
            return new_alert
    else:
        # LOW or MODERATE - normal or routine watch
        location.alert_status = "NORMAL"
        db.commit()
        return None
