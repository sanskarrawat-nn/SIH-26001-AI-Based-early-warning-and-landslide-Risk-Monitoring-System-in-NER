from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import relationship
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(64), unique=True, index=True, nullable=False)
    location_id = Column(String(64), ForeignKey("locations.location_id", ondelete="CASCADE"), index=True, nullable=False)
    severity = Column(String(16), nullable=False, index=True)   # LOW, MODERATE, HIGH, SEVERE
    status = Column(String(32), default="ACTIVE", index=True)   # ACTIVE, ACKNOWLEDGED, RESOLVED
    
    risk_score = Column(Float, nullable=False)
    title = Column(String(256), nullable=False)
    message = Column(Text, nullable=False)
    triggering_factors = Column(JSON, nullable=False, default=list)
    recommended_action = Column(Text, nullable=False)
    
    # Standard Operating Procedure (SOP) Checklist
    sop_actions = Column(JSON, nullable=True)
    
    # Audit tracking
    created_at = Column(DateTime, default=utc_now, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(64), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(64), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    location = relationship("Location", back_populates="alerts")
