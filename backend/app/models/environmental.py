from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class EnvironmentalMeasurement(Base):
    __tablename__ = "environmental_measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_id = Column(String(64), ForeignKey("locations.location_id", ondelete="CASCADE"), index=True, nullable=False)
    timestamp = Column(DateTime, default=utc_now, index=True)
    
    # Rainfall metrics
    rainfall_1h = Column(Float, default=0.0)      # mm/h
    rainfall_24h = Column(Float, default=0.0)     # mm
    rainfall_7d = Column(Float, default=0.0)      # mm
    rainfall_intensity = Column(Float, default=0.0) # mm/h
    
    # Soil metrics
    soil_moisture = Column(Float, default=0.0)    # volumetric percentage 0-100% or 0-1 m3/m3
    soil_saturation = Column(Float, default=0.0)  # saturation ratio 0-1
    soil_temperature = Column(Float, default=20.0)# degrees C
    
    # Satellite / Remote sensing
    vegetation_index = Column(Float, default=0.5) # NDVI -0.2 to 1.0
    land_cover_type = Column(String(64), default="Dense Vegetation")
    
    # Atmospheric
    temperature = Column(Float, default=22.0)
    humidity = Column(Float, default=75.0)
    pressure = Column(Float, default=1010.0)
    
    source = Column(String(64), default="OPEN_METEO")  # OPEN_METEO, SIMULATED, SENSOR_TELEMETRY
    raw_payload = Column(JSON, nullable=True)

    location = relationship("Location", back_populates="environmental_records")
