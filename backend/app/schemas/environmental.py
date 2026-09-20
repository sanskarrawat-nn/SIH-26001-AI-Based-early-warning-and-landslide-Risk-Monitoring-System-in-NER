from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class EnvironmentalBase(BaseModel):
    rainfall_1h: float = Field(..., ge=0.0, le=500.0, description="1-hour rainfall in mm")
    rainfall_24h: float = Field(..., ge=0.0, le=1500.0, description="24-hour cumulative rainfall in mm")
    rainfall_7d: float = Field(..., ge=0.0, le=3000.0, description="7-day cumulative rainfall in mm")
    rainfall_intensity: Optional[float] = Field(0.0, ge=0.0, description="Rainfall intensity in mm/h")
    soil_moisture: float = Field(..., ge=0.0, le=100.0, description="Soil moisture volumetric percentage (0-100%)")
    soil_saturation: Optional[float] = Field(0.0, ge=0.0, le=1.0, description="Soil saturation index (0-1)")
    soil_temperature: Optional[float] = Field(20.0, description="Soil temperature in °C")
    vegetation_index: Optional[float] = Field(0.5, ge=-0.2, le=1.0, description="NDVI vegetation index")
    land_cover_type: Optional[str] = Field("Dense Vegetation")
    temperature: Optional[float] = Field(22.0, description="Air temperature in °C")
    humidity: Optional[float] = Field(75.0, ge=0.0, le=100.0, description="Relative humidity %")
    pressure: Optional[float] = Field(1010.0, description="Atmospheric pressure hPa")

class EnvironmentalCreate(EnvironmentalBase):
    location_id: str
    source: Optional[str] = "SENSOR"

class EnvironmentalResponse(EnvironmentalBase):
    id: int
    location_id: str
    timestamp: datetime
    source: str
    raw_payload: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
