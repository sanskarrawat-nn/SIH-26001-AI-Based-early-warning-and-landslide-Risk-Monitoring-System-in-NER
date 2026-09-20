from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class AlertBase(BaseModel):
    location_id: str
    severity: str = Field(..., description="LOW, MODERATE, HIGH, SEVERE")
    risk_score: float
    title: str
    message: str
    triggering_factors: List[Any] = Field(default_factory=list)
    recommended_action: str
    sop_actions: Optional[List[str]] = None

class AlertCreate(AlertBase):
    pass

class AlertAcknowledgeRequest(BaseModel):
    acknowledged_by: str = Field("OPERATOR_ON_DUTY", description="Name/ID of the responder")

class AlertResolveRequest(BaseModel):
    resolved_by: str = Field("FIELD_COORDINATOR", description="Name/ID of the authority")
    resolution_notes: Optional[str] = Field("Threat subsided, ground stabilized", description="Resolution justification")

class AlertResponse(AlertBase):
    id: int
    alert_id: str
    status: str  # ACTIVE, ACKNOWLEDGED, RESOLVED
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    location_name: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
