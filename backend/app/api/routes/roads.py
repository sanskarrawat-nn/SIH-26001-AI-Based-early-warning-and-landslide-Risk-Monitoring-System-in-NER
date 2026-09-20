"""Surveyed connectivity only; independent of risk scores and asset access fields."""
import uuid
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict, model_validator
from sqlalchemy import Column, String, JSON
from sqlalchemy.orm import Session
from app.database.base import Base
from app.database.session import get_db
from app.api.routes.operations import Asset

class RoadSegment(Base):
    __tablename__ = 'road_segments'
    id = Column(String(64), primary_key=True)
    data = Column(JSON, nullable=False)

class RoadInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    from_asset: str = Field(max_length=64)
    to_asset: str = Field(max_length=64)
    status: Literal['open', 'restricted', 'blocked', 'unknown'] = 'unknown'
    source: str = Field(min_length=3, max_length=300)
    observed_at: datetime
    # Optional surveyed intermediate vertices; endpoint-only connections are explicitly schematic.
    coordinates: list[list[float]] | None = Field(default=None, min_length=2, max_length=2000)
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

    @model_validator(mode='after')
    def validate_input(self):
        if self.from_asset == self.to_asset:
            raise ValueError('Choose two different assets')
        if self.observed_at.tzinfo is None:
            raise ValueError('Observation time must include a timezone')
        if self.observed_at > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError('Observation cannot be in the future')
        for point in self.coordinates or []:
            if len(point) != 2 or not -180 <= point[0] <= 180 or not -90 <= point[1] <= 90:
                raise ValueError('Coordinates must be [longitude, latitude] in WGS84')
        return self

router = APIRouter(prefix='/operations/roads', tags=['Road connectivity'])

def present(row, assets):
    data = dict(row.data)
    start, end = assets.get(data['from_asset']), assets.get(data['to_asset'])
    observed = datetime.fromisoformat(data['observed_at'])
    stale = observed < datetime.now(timezone.utc) - timedelta(hours=24)
    missing = not start or not end
    coords = data.get('coordinates')
    if not coords and not missing:
        coords = [[start.data['longitude'], start.data['latitude']], [end.data['longitude'], end.data['latitude']]]
    return {'id': row.id, **data, 'coordinates': coords or [], 'schematic': not bool(data.get('coordinates')),
            'stale': stale, 'missing_endpoint': missing, 'effective_status': 'unknown' if stale or missing else data['status']}

@router.get('')
def list_roads(db: Session = Depends(get_db)):
    assets = {a.id: a for a in db.query(Asset).all()}
    return [present(r, assets) for r in db.query(RoadSegment).all()]

def check_assets(data, db):
    for asset_id in [data.from_asset, data.to_asset]:
        if not db.get(Asset, asset_id):
            raise HTTPException(404, 'Road endpoint asset not found')

@router.post('', status_code=201)
def create_road(data: RoadInput, db: Session = Depends(get_db)):
    check_assets(data, db)
    row = RoadSegment(id=str(uuid.uuid4()), data=data.model_dump(mode='json'))
    db.add(row); db.commit()
    return {'id': row.id, **row.data}

@router.put('/{road_id}')
def update_road(road_id: str, data: RoadInput, db: Session = Depends(get_db)):
    row = db.get(RoadSegment, road_id)
    if not row: raise HTTPException(404, 'Road not found')
    check_assets(data, db)
    row.data = data.model_dump(mode='json'); db.commit()
    return {'id': row.id, **row.data}

@router.delete('/{road_id}')
def delete_road(road_id: str, db: Session = Depends(get_db)):
    row = db.get(RoadSegment, road_id)
    if not row: raise HTTPException(404, 'Road not found')
    db.delete(row); db.commit()
    return {'deleted': road_id}

@router.get('/connectivity/check')
def connectivity(from_asset: str, to_asset: str, db: Session = Depends(get_db)):
    assets = {a.id: a for a in db.query(Asset).all()}
    if from_asset not in assets or to_asset not in assets:
        raise HTTPException(404, 'Endpoint asset not found')
    graph = {}
    for row in db.query(RoadSegment).all():
        road = present(row, assets)
        if road['effective_status'] != 'open': continue
        for a, b in [(road['from_asset'], road['to_asset']), (road['to_asset'], road['from_asset'])]:
            graph.setdefault(a, []).append((b, road['id']))
    queue = deque([(from_asset, [])]); seen = {from_asset}
    while queue:
        current, path = queue.popleft()
        if current == to_asset:
            return {'connected': True, 'road_ids': path, 'basis': 'Fewest surveyed open links; observations expire after 24 hours. Not a certified evacuation route.'}
        for node, road_id in graph.get(current, []):
            if node not in seen:
                seen.add(node); queue.append((node, path + [road_id]))
    return {'connected': False, 'road_ids': [], 'basis': 'No connection in the recorded, fresh open links. Restricted, blocked, unknown and stale links are excluded.'}
