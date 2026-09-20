from fastapi import APIRouter, Query, HTTPException, status
from app.services.environmental_provider import get_environmental_provider

router = APIRouter(prefix="/environmental", tags=["Environmental Telemetry"])

@router.get("/current")
async def get_current_environmental_data(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude")
):
    """
    Fetch real-time hydrometeorological conditions (1h/24h/7d rainfall, soil moisture,
    temperature, humidity) via pluggable Environmental Data Provider.
    """
    provider = get_environmental_provider()
    try:
        return await provider.get_current_conditions(latitude, longitude)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch environmental telemetry: {str(e)}"
        )

@router.get("/forecast")
async def get_rainfall_forecast(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    days: int = Query(3, ge=1, le=7)
):
    """Fetch multi-day precipitation forecast for proactive risk modeling."""
    provider = get_environmental_provider()
    try:
        return await provider.get_forecast(latitude, longitude, days)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch environmental forecast: {str(e)}"
        )
