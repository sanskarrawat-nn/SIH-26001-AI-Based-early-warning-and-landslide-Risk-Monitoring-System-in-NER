from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.session import get_db
from app.models.prediction import Prediction
from app.schemas.prediction import PredictionInput, PredictionOutput, PredictionRecord
from app.services.prediction_service import process_prediction

router = APIRouter(tags=["Predictions"])

@router.post("/predict", response_model=PredictionOutput, status_code=status.HTTP_200_OK)
def predict_landslide(payload: PredictionInput, db: Session = Depends(get_db)):
    """
    Main Landslide Risk Prediction Engine API.
    Ingests environmental & geographical parameters, executes feature engineering,
    runs calibrated ML model, produces risk probability/score/level, provides explainability,
    and automatically issues alerts if thresholds are breached.
    """
    try:
        return process_prediction(db, payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Prediction failed: {str(e)}")

@router.get("/predictions", response_model=List[PredictionRecord])
def get_prediction_history(
    location_id: Optional[str] = Query(None, description="Filter by location identifier"),
    risk_level: Optional[str] = Query(None, description="Filter by risk category"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieve historical prediction records with feature snapshots and model outputs."""
    query = db.query(Prediction)
    if location_id:
        query = query.filter(Prediction.location_id == location_id)
    if risk_level:
        query = query.filter(Prediction.risk_level == risk_level.upper())
    
    return query.order_by(Prediction.timestamp.desc()).offset(offset).limit(limit).all()

@router.get("/predictions/stats")
def get_prediction_statistics(db: Session = Depends(get_db)):
    """Compute aggregate statistical indicators over all logged predictions."""
    total = db.query(func.count(Prediction.id)).scalar() or 0
    avg_score = db.query(func.avg(Prediction.risk_score)).scalar() or 0.0
    max_score = db.query(func.max(Prediction.risk_score)).scalar() or 0.0

    counts_by_level = {}
    for level in ["LOW", "MODERATE", "HIGH", "SEVERE"]:
        count = db.query(func.count(Prediction.id)).filter(Prediction.risk_level == level).scalar() or 0
        counts_by_level[level] = count

    return {
        "total_predictions": total,
        "average_risk_score": round(float(avg_score), 2),
        "maximum_risk_score": round(float(max_score), 2),
        "distribution_by_level": counts_by_level
    }
