from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class ThresholdSettingsUpdate(BaseModel):
    threshold_low: float = Field(..., ge=10.0, le=40.0, description="LOW risk boundary (default 25.0)")
    threshold_moderate: float = Field(..., ge=30.0, le=70.0, description="MODERATE risk boundary (default 50.0)")
    threshold_high: float = Field(..., ge=60.0, le=90.0, description="HIGH risk boundary (default 75.0)")
    updated_by: Optional[str] = "SYSTEM_ADMIN"
    notes: Optional[str] = None

class ThresholdSettingsResponse(BaseModel):
    threshold_low: float
    threshold_moderate: float
    threshold_high: float
    updated_at: datetime
    updated_by: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
