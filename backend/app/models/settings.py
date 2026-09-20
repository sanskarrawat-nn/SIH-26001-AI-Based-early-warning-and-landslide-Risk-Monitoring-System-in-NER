from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), unique=True, index=True, nullable=False)
    threshold_low = Column(Float, default=25.0)       # 0 - 25: LOW
    threshold_moderate = Column(Float, default=50.0)  # 26 - 50: MODERATE
    threshold_high = Column(Float, default=75.0)      # 51 - 75: HIGH, >75: SEVERE
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    updated_by = Column(String(64), default="SYSTEM_ADMIN")
    notes = Column(Text, nullable=True)
