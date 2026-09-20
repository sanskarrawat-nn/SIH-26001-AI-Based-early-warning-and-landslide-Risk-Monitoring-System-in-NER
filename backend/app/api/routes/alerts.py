from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.session import get_db
from app.models.alert import Alert
from app.models.location import Location
from app.schemas.alert import AlertResponse, AlertAcknowledgeRequest, AlertResolveRequest

router = APIRouter(prefix="/alerts", tags=["Early Warnings & Alerts"])

def utc_now():
    return datetime.now(timezone.utc)

def enrich_alert_response(alert: Alert, db: Session) -> AlertResponse:
    loc = db.query(Location).filter(Location.location_id == alert.location_id).first()
    return AlertResponse(
        id=alert.id,
        alert_id=alert.alert_id,
        location_id=alert.location_id,
        severity=alert.severity,
        status=alert.status,
        risk_score=alert.risk_score,
        title=alert.title,
        message=alert.message,
        triggering_factors=alert.triggering_factors or [],
        recommended_action=alert.recommended_action,
        sop_actions=alert.sop_actions or [],
        created_at=alert.created_at,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by=alert.acknowledged_by,
        resolved_at=alert.resolved_at,
        resolved_by=alert.resolved_by,
        resolution_notes=alert.resolution_notes,
        location_name=loc.name if loc else alert.location_id,
        state=loc.state if loc else "NER",
        district=loc.district if loc else "Sector"
    )

@router.get("", response_model=List[AlertResponse])
def get_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity: SEVERE, HIGH, MODERATE"),
    status: Optional[str] = Query(None, description="Filter by status: ACTIVE, ACKNOWLEDGED, RESOLVED"),
    location_id: Optional[str] = Query(None, description="Filter by location identifier"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieve all triggered early warning alerts and emergency advisories."""
    query = db.query(Alert)
    if severity:
        query = query.filter(Alert.severity == severity.upper())
    if status:
        query = query.filter(Alert.status == status.upper())
    if location_id:
        query = query.filter(Alert.location_id == location_id)

    alerts = query.order_by(Alert.created_at.desc()).offset(offset).limit(limit).all()
    return [enrich_alert_response(a, db) for a in alerts]

@router.get("/stats")
def get_alert_statistics(db: Session = Depends(get_db)):
    """Summary counts of early warning alerts by severity and state."""
    active_count = db.query(func.count(Alert.id)).filter(Alert.status == "ACTIVE").scalar() or 0
    ack_count = db.query(func.count(Alert.id)).filter(Alert.status == "ACKNOWLEDGED").scalar() or 0
    res_count = db.query(func.count(Alert.id)).filter(Alert.status == "RESOLVED").scalar() or 0

    severe_active = db.query(func.count(Alert.id)).filter(
        Alert.status == "ACTIVE", Alert.severity == "SEVERE"
    ).scalar() or 0
    high_active = db.query(func.count(Alert.id)).filter(
        Alert.status == "ACTIVE", Alert.severity == "HIGH"
    ).scalar() or 0

    return {
        "active_alerts": active_count,
        "severe_active": severe_active,
        "high_active": high_active,
        "acknowledged_alerts": ack_count,
        "resolved_alerts": res_count,
        "total_generated": active_count + ack_count + res_count
    }

@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    """Retrieve single alert details by UUID or ID."""
    alert = db.query(Alert).filter(
        (Alert.alert_id == alert_id) | (Alert.id == int(alert_id) if alert_id.isdigit() else False)
    ).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert '{alert_id}' not found")
    return enrich_alert_response(alert, db)

@router.put("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(alert_id: str, payload: AlertAcknowledgeRequest, db: Session = Depends(get_db)):
    """Acknowledge receipt of an active early warning alert by emergency responder."""
    alert = db.query(Alert).filter(
        (Alert.alert_id == alert_id) | (Alert.id == int(alert_id) if alert_id.isdigit() else False)
    ).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert '{alert_id}' not found")
    
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = utc_now()
    alert.acknowledged_by = payload.acknowledged_by
    db.commit()
    db.refresh(alert)
    return enrich_alert_response(alert, db)

@router.put("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(alert_id: str, payload: AlertResolveRequest, db: Session = Depends(get_db)):
    """Resolve an alert after slope threat has cleared or stabilization measures deployed."""
    alert = db.query(Alert).filter(
        (Alert.alert_id == alert_id) | (Alert.id == int(alert_id) if alert_id.isdigit() else False)
    ).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert '{alert_id}' not found")

    alert.status = "RESOLVED"
    alert.resolved_at = utc_now()
    alert.resolved_by = payload.resolved_by
    alert.resolution_notes = payload.resolution_notes
    db.commit()
    db.refresh(alert)
    return enrich_alert_response(alert, db)
