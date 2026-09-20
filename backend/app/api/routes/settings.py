from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.settings import SystemSettings
from app.schemas.settings import ThresholdSettingsUpdate, ThresholdSettingsResponse
from app.core.config import settings as app_settings

router = APIRouter(prefix="/settings", tags=["Configuration & Administration"])

def utc_now():
    return datetime.now(timezone.utc)

@router.get("/thresholds", response_model=ThresholdSettingsResponse)
def get_thresholds(db: Session = Depends(get_db)):
    """Retrieve current operational risk category thresholds."""
    record = db.query(SystemSettings).filter(SystemSettings.key == "landslide_thresholds").first()
    if not record:
        record = SystemSettings(
            key="landslide_thresholds",
            threshold_low=app_settings.DEFAULT_THRESHOLD_LOW,
            threshold_moderate=app_settings.DEFAULT_THRESHOLD_MODERATE,
            threshold_high=app_settings.DEFAULT_THRESHOLD_HIGH,
            updated_by="SYSTEM_DEFAULT",
            notes="Default GSI calibration"
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    return record

@router.put("/thresholds", response_model=ThresholdSettingsResponse)
def update_thresholds(payload: ThresholdSettingsUpdate, db: Session = Depends(get_db)):
    """Update risk classification thresholds dynamically across the early warning engine."""
    if not (payload.threshold_low < payload.threshold_moderate < payload.threshold_high):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thresholds must satisfy strict order: threshold_low < threshold_moderate < threshold_high"
        )

    record = db.query(SystemSettings).filter(SystemSettings.key == "landslide_thresholds").first()
    if not record:
        record = SystemSettings(key="landslide_thresholds")
        db.add(record)

    record.threshold_low = payload.threshold_low
    record.threshold_moderate = payload.threshold_moderate
    record.threshold_high = payload.threshold_high
    record.updated_by = payload.updated_by or "ADMIN"
    record.notes = payload.notes or "Operational threshold reconfiguration"
    record.updated_at = utc_now()

    db.commit()
    db.refresh(record)
    return record
