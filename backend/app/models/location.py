from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class Location(Base):
    __tablename__ = "locations"

    location_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False, index=True)
    state = Column(String(64), nullable=False, index=True)  # Assam, Meghalaya, Sikkim, etc.
    district = Column(String(64), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation = Column(Float, nullable=False)  # in meters
    slope = Column(Float, nullable=False)  # in degrees
    aspect = Column(String(32), default="SE")  # N, NE, E, SE, S, SW, W, NW
    terrain_roughness = Column(Float, default=15.0)
    geology_type = Column(String(128), default="Weathered Shale and Sandstone")
    vegetation_type = Column(String(128), default="Sub-tropical Hill Forest")
    monitoring_status = Column(String(32), default="ACTIVE")  # ACTIVE, INACTIVE, MAINTENANCE
    risk_level = Column(String(16), default="LOW")  # LOW, MODERATE, HIGH, SEVERE
    current_risk_score = Column(Float, default=12.0)
    alert_status = Column(String(32), default="NORMAL")  # NORMAL, WARNING, CRITICAL
    
    # Store latest cached environmental measurement snapshot
    latest_measurements = Column(JSON, nullable=True)
    latest_prediction = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    predictions = relationship("Prediction", back_populates="location", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="location", cascade="all, delete-orphan")
    environmental_records = relationship("EnvironmentalMeasurement", back_populates="location", cascade="all, delete-orphan")
