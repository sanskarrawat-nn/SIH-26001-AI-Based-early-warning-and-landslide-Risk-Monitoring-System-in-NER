from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class HistoricalLandslide(Base):
    __tablename__ = "historical_landslides"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(64), unique=True, index=True, nullable=False)
    location_name = Column(String(128), nullable=False, index=True)
    state = Column(String(64), nullable=False, index=True)
    district = Column(String(64), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    event_date = Column(DateTime, nullable=False, index=True)
    
    severity = Column(String(32), default="HIGH")          # MODERATE, HIGH, CATASTROPHIC
    triggering_rainfall_24h = Column(Float, nullable=True) # in mm
    triggering_rainfall_7d = Column(Float, nullable=True)  # in mm
    slope = Column(Float, nullable=True)                   # degrees
    elevation = Column(Float, nullable=True)               # meters
    estimated_volume_m3 = Column(Float, nullable=True)     # cubic meters
    casualties = Column(Integer, default=0)
    infrastructure_damage = Column(Text, nullable=True)
    geological_formation = Column(Text, nullable=True)
    data_source = Column(String(128), default="GSI (Geological Survey of India) / NDMA")
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now)
