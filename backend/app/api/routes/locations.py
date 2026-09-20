from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.location import LocationCreate, LocationUpdate, LocationResponse
from app.services.location_service import (
    list_locations,
    get_location_by_id,
    create_location,
    update_location,
    delete_location,
    sync_location_environmental_telemetry
)

router = APIRouter(prefix="/locations", tags=["Locations"])

@router.get("", response_model=List[LocationResponse])
def get_locations(
    state: Optional[str] = Query(None, description="Filter by State"),
    district: Optional[str] = Query(None, description="Filter by District"),
    risk_level: Optional[str] = Query(None, description="Filter by Risk Level: LOW, MODERATE, HIGH, SEVERE"),
    monitoring_status: Optional[str] = Query(None, description="Filter by Monitoring Status: ACTIVE, INACTIVE"),
    db: Session = Depends(get_db)
):
    """Retrieve all monitored vulnerable locations across the North Eastern Region."""
    return list_locations(db, state=state, district=district, risk_level=risk_level, monitoring_status=monitoring_status)

@router.get("/{location_id}", response_model=LocationResponse)
def get_location(location_id: str, db: Session = Depends(get_db)):
    """Retrieve detailed telemetry and profile for a specific location."""
    loc = get_location_by_id(db, location_id)
    if not loc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location '{location_id}' not found")
    return loc

@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
def add_location(loc_in: LocationCreate, db: Session = Depends(get_db)):
    """Register a new vulnerable location or settlement for continuous landslide monitoring."""
    existing = get_location_by_id(db, loc_in.location_id)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Location '{loc_in.location_id}' already exists")
    return create_location(db, loc_in)

@router.put("/{location_id}", response_model=LocationResponse)
def modify_location(location_id: str, loc_update: LocationUpdate, db: Session = Depends(get_db)):
    """Update geographical, geological or monitoring attributes for a location."""
    updated = update_location(db, location_id, loc_update)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location '{location_id}' not found")
    return updated

@router.delete("/{location_id}", status_code=status.HTTP_200_OK)
def remove_location(location_id: str, db: Session = Depends(get_db)):
    """Remove a location from continuous monitoring."""
    success = delete_location(db, location_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location '{location_id}' not found")
    return {"message": f"Location '{location_id}' successfully removed from monitoring"}

@router.post("/{location_id}/sync", response_model=LocationResponse)
async def sync_telemetry(location_id: str, db: Session = Depends(get_db)):
    """Poll live weather/soil moisture sensors and run inference to update location risk status."""
    loc = await sync_location_environmental_telemetry(db, location_id)
    if not loc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location '{location_id}' not found")
    return loc
