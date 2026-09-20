from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class HistoricalLandslideBase(BaseModel):
    event_id: str
    location_name: str
    state: str
    district: str
    latitude: float
    longitude: float
    event_date: datetime
    severity: str = "HIGH"
    triggering_rainfall_24h: Optional[float] = None
    triggering_rainfall_7d: Optional[float] = None
    slope: Optional[float] = None
    elevation: Optional[float] = None
    estimated_volume_m3: Optional[float] = None
    casualties: int = 0
    infrastructure_damage: Optional[str] = None
    geological_formation: Optional[str] = None
    data_source: Optional[str] = "GSI / NDMA"
    notes: Optional[str] = None

class HistoricalLandslideCreate(HistoricalLandslideBase):
    pass

class HistoricalLandslideResponse(HistoricalLandslideBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
