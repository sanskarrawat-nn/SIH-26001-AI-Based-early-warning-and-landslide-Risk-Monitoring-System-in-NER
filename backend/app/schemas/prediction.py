from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class PredictionInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    simulation: bool = False
    location_id: str = Field(..., description="Unique location identifier")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude")
    rainfall_1h: float = Field(..., ge=0.0, le=500.0, description="Current 1-hour rainfall in mm")
    rainfall_24h: float = Field(..., ge=0.0, le=1500.0, description="Cumulative 24-hour rainfall in mm")
    rainfall_7d: float = Field(..., ge=0.0, le=3000.0, description="Cumulative 7-day rainfall in mm")
    soil_moisture: float = Field(..., ge=0.0, le=100.0, description="Soil moisture volumetric % (0-100)")
    slope: float = Field(..., ge=0.0, le=90.0, description="Slope inclination in degrees")
    elevation: float = Field(..., ge=0.0, le=9000.0, description="Elevation in meters")
    terrain_roughness: float = Field(..., ge=0.0, le=100.0, description="Terrain roughness index")
    vegetation_index: float = Field(..., ge=-0.2, le=1.0, description="NDVI vegetation index (-0.2 to 1.0)")

class RiskFactor(BaseModel):
    factor: str
    impact: str  # POSITIVE, NEGATIVE, CRITICAL
    weight: float
    description: str

class PredictionOutput(BaseModel):
    location_id: str
    risk_score: float = Field(..., description="0 - 100 risk score")
    risk_level: str = Field(..., description="LOW, MODERATE, HIGH, SEVERE")
    probability: float = Field(..., description="0.0 - 1.0 probability")
    confidence: float = Field(..., description="0.0 - 1.0 confidence score")
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    timestamp: str
    recommendation: str
    explanation: Optional[str] = None
    input_features: Optional[Dict[str, Any]] = None

class PredictionRecord(BaseModel):
    id: int
    location_id: str
    risk_score: float
    risk_level: str
    probability: float
    confidence: float
    risk_factors: List[Any]
    timestamp: datetime
    recommendation: str
    explanation: Optional[str] = None
    input_features: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
