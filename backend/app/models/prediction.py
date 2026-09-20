from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_id = Column(String(64), ForeignKey("locations.location_id", ondelete="CASCADE"), index=True, nullable=False)
    timestamp = Column(DateTime, default=utc_now, index=True)
    
    # Model Outputs
    risk_score = Column(Float, nullable=False)           # 0.0 - 100.0
    risk_level = Column(String(16), nullable=False)       # LOW, MODERATE, HIGH, SEVERE
    probability = Column(Float, nullable=False)          # 0.0 - 1.0
    confidence = Column(Float, nullable=False)           # 0.0 - 1.0
    
    # Feature attribution & explainability
    risk_factors = Column(JSON, nullable=False, default=list)  # Top contributing factors
    recommendation = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)             # Natural language AI geotechnical narrative
    
    # Ingested Input Snapshot
    input_features = Column(JSON, nullable=False)
    model_version = Column(String(32), default="v1.0.0-rf-ensemble")

    location = relationship("Location", back_populates="predictions")
