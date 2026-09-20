from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.session import get_db
from app.models.historical import HistoricalLandslide
from app.models.prediction import Prediction
from app.models.location import Location
from app.schemas.historical import HistoricalLandslideResponse
from app.ml.pipeline import get_model_metadata

router = APIRouter(prefix="/analysis", tags=["Historical & Model Analysis"])

@router.get("/historical", response_model=List[HistoricalLandslideResponse])
def get_historical_landslides(
    state: Optional[str] = Query(None, description="Filter by State"),
    district: Optional[str] = Query(None, description="Filter by District"),
    severity: Optional[str] = Query(None, description="Filter by Severity: HIGH, CATASTROPHIC"),
    start_year: Optional[int] = Query(None, ge=1950, le=2030),
    end_year: Optional[int] = Query(None, ge=1950, le=2030),
    db: Session = Depends(get_db)
):
    """Retrieve cataloged historical landslide events in the North Eastern Region from GSI & NDMA records."""
    query = db.query(HistoricalLandslide)
    if state:
        query = query.filter(HistoricalLandslide.state.ilike(f"%{state}%"))
    if district:
        query = query.filter(HistoricalLandslide.district.ilike(f"%{district}%"))
    if severity:
        query = query.filter(HistoricalLandslide.severity == severity.upper())
    if start_year:
        query = query.filter(func.extract('year', HistoricalLandslide.event_date) >= start_year)
    if end_year:
        query = query.filter(func.extract('year', HistoricalLandslide.event_date) <= end_year)

    return query.order_by(HistoricalLandslide.event_date.desc()).all()

@router.get("/trends")
def get_risk_and_weather_trends(
    location_id: Optional[str] = Query(None, description="Filter by location"),
    limit: int = Query(60, ge=10, le=300),
    db: Session = Depends(get_db)
):
    """
    Returns time-series correlation between cumulative rainfall,
    soil moisture, and predicted landslide risk score.
    """
    query = db.query(Prediction)
    if location_id:
        query = query.filter(Prediction.location_id == location_id)
    
    records = list(reversed(query.order_by(Prediction.timestamp.desc()).limit(limit).all()))

    timeseries = []
    for r in records:
        feat = r.input_features or {}
        timeseries.append({
            "timestamp": r.timestamp.strftime("%b %d, %H:%M"),
            "location_id": r.location_id,
            "risk_score": r.risk_score,
            "risk_level": r.risk_level,
            "rainfall_24h": feat.get("rainfall_24h", 0.0),
            "rainfall_1h": feat.get("rainfall_1h", 0.0),
            "soil_moisture": feat.get("soil_moisture", 0.0)
        })

    # Summary by state across monitored locations
    locs = db.query(Location).all()
    state_aggregates = {}
    for l in locs:
        if l.state not in state_aggregates:
            state_aggregates[l.state] = {"count": 0, "total_risk": 0.0, "high_risk_count": 0}
        state_aggregates[l.state]["count"] += 1
        state_aggregates[l.state]["total_risk"] += l.current_risk_score
        if l.risk_level in ["HIGH", "SEVERE"]:
            state_aggregates[l.state]["high_risk_count"] += 1

    state_stats = [
        {
            "state": st,
            "monitored_sites": data["count"],
            "avg_risk": round(data["total_risk"] / max(1, data["count"]), 1),
            "critical_sites": data["high_risk_count"]
        }
        for st, data in state_aggregates.items()
    ]

    return {
        "timeseries": timeseries,
        "state_breakdown": state_stats
    }

@router.get("/model-performance")
def get_model_performance():
    """
    Returns live ML model evaluation metrics, confusion matrix,
    feature importance ranking, and validation curves.
    """
    try:
        metrics = get_model_metadata()
        return {
            "status": "active",
            "model_architecture": metrics.get("model_architecture"),
            "accuracy": metrics.get("accuracy"),
            "precision": metrics.get("precision"),
            "recall": metrics.get("recall"),
            "f1_score": metrics.get("f1_score"),
            "roc_auc": metrics.get("roc_auc"),
            "confusion_matrix": metrics.get("confusion_matrix"),
            "feature_importances": metrics.get("feature_importances", [])
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
