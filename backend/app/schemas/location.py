from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class LocationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=128, description="Name of the vulnerable site")
    state: str = Field(..., min_length=2, max_length=64, description="North Eastern State")
    district: str = Field(..., min_length=2, max_length=64, description="District name")
    latitude: float = Field(..., ge=20.0, le=32.0, description="Latitude (NER bounds ~20-30°N)")
    longitude: float = Field(..., ge=88.0, le=98.0, description="Longitude (NER bounds ~88-98°E)")
    elevation: float = Field(..., ge=0, le=8000, description="Elevation in meters a.s.l.")
    slope: float = Field(..., ge=0, le=90, description="Slope inclination in degrees")
    aspect: Optional[str] = Field("SE", description="Slope aspect: N, NE, E, SE, S, SW, W, NW")
    terrain_roughness: Optional[float] = Field(15.0, ge=0, description="Terrain roughness index")
    geology_type: Optional[str] = Field("Weathered Shale and Sandstone")
    vegetation_type: Optional[str] = Field("Sub-tropical Hill Forest")
    monitoring_status: Optional[str] = Field("ACTIVE", description="ACTIVE, INACTIVE, MAINTENANCE")

class LocationCreate(LocationBase):
    location_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=20.0, le=32.0)
    longitude: Optional[float] = Field(None, ge=88.0, le=98.0)
    elevation: Optional[float] = Field(None, ge=0, le=8000)
    slope: Optional[float] = Field(None, ge=0, le=90)
    aspect: Optional[str] = None
    terrain_roughness: Optional[float] = None
    geology_type: Optional[str] = None
    vegetation_type: Optional[str] = None
    monitoring_status: Optional[str] = None
    risk_level: Optional[str] = None
    current_risk_score: Optional[float] = None
    alert_status: Optional[str] = None

class LocationResponse(LocationBase):
    location_id: str
    risk_level: str
    current_risk_score: float
    alert_status: str
    latest_measurements: Optional[Dict[str, Any]] = None
    latest_prediction: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
