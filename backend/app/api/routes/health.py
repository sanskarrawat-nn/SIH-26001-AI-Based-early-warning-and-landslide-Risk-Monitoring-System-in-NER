from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.session import get_db
from app.ml.pipeline import get_or_load_model
from app.core.config import settings

router = APIRouter()

@router.get("/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    ml_status = "loaded"
    try:
        model = get_or_load_model()
        if not model:
            ml_status = "unloaded"
    except Exception as e:
        ml_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" and ml_status == "loaded" else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": db_status,
        "ml_engine": ml_status,
        "weather_provider": settings.WEATHER_PROVIDER
    }
