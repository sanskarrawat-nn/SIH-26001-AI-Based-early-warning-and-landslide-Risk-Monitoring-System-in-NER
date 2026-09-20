from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.location import Location
from app.schemas.location import LocationCreate, LocationUpdate
from app.services.environmental_provider import get_environmental_provider
from app.services.alert_engine import get_active_thresholds
from app.ml.pipeline import predict_landslide_risk

def list_locations(
    db: Session,
    state: Optional[str] = None,
    district: Optional[str] = None,
    risk_level: Optional[str] = None,
    monitoring_status: Optional[str] = None
) -> List[Location]:
    query = db.query(Location)
    if state:
        query = query.filter(Location.state.ilike(f"%{state}%"))
    if district:
        query = query.filter(Location.district.ilike(f"%{district}%"))
    if risk_level:
        query = query.filter(Location.risk_level == risk_level.upper())
    if monitoring_status:
        query = query.filter(Location.monitoring_status == monitoring_status.upper())
    return query.order_by(Location.current_risk_score.desc()).all()

def get_location_by_id(db: Session, location_id: str) -> Optional[Location]:
    return db.query(Location).filter(Location.location_id == location_id).first()

def create_location(db: Session, loc_in: LocationCreate) -> Location:
    loc = Location(
        location_id=loc_in.location_id,
        name=loc_in.name,
        state=loc_in.state,
        district=loc_in.district,
        latitude=loc_in.latitude,
        longitude=loc_in.longitude,
        elevation=loc_in.elevation,
        slope=loc_in.slope,
        aspect=loc_in.aspect,
        terrain_roughness=loc_in.terrain_roughness,
        geology_type=loc_in.geology_type,
        vegetation_type=loc_in.vegetation_type,
        monitoring_status=loc_in.monitoring_status or "ACTIVE",
        risk_level="LOW",
        current_risk_score=15.0,
        alert_status="NORMAL"
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc

def update_location(db: Session, location_id: str, loc_update: LocationUpdate) -> Optional[Location]:
    loc = get_location_by_id(db, location_id)
    if not loc:
        return None
    
    update_data = loc_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(loc, field, value)
    
    db.commit()
    db.refresh(loc)
    return loc

def delete_location(db: Session, location_id: str) -> bool:
    loc = get_location_by_id(db, location_id)
    if not loc:
        return False
    db.delete(loc)
    db.commit()
    return True

async def sync_location_environmental_telemetry(db: Session, location_id: str) -> Optional[Location]:
    """
    Fetches real-time or simulated sensor conditions for the location's lat/lon,
    runs inference, and updates the location's telemetry cache.
    """
    loc = get_location_by_id(db, location_id)
    if not loc:
        return None

    provider = get_environmental_provider()
    env_data = await provider.get_current_conditions(loc.latitude, loc.longitude)

    # Ingest into prediction pipeline
    thresholds = get_active_thresholds(db)
    pred_input = {
        "location_id": loc.location_id,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "rainfall_1h": env_data["rainfall_1h"],
        "rainfall_24h": env_data["rainfall_24h"],
        "rainfall_7d": env_data["rainfall_7d"],
        "soil_moisture": env_data["soil_moisture"],
        "slope": loc.slope,
        "elevation": loc.elevation,
        "terrain_roughness": loc.terrain_roughness or 15.0,
        "vegetation_index": env_data.get("vegetation_index", 0.6)
    }

    from app.services.prediction_service import process_prediction
    from app.schemas.prediction import PredictionInput
    process_prediction(db, PredictionInput(**pred_input), source=env_data.get("source", "UNKNOWN"))
    loc.latest_measurements = env_data
    db.commit()
    db.refresh(loc)
    return loc
