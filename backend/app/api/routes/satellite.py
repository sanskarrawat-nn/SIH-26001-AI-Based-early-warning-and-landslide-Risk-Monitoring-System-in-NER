"""On-demand, quality-filtered MODIS observations; never substitute fabricated NDVI."""
import asyncio
from datetime import date, datetime, timezone
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Column, String, JSON
from sqlalchemy.orm import Session
from app.database.base import Base
from app.database.session import get_db
from app.api.routes.operations import require_location

BASE = 'https://modis.ornl.gov/rst/api/v1/MOD13Q1'
NDVI = '250m_16_days_NDVI'
QUALITY = '250m_16_days_pixel_reliability'
class SatelliteObservation(Base):
    __tablename__ = 'satellite_observations'
    location_id = Column(String(64), primary_key=True)
    data = Column(JSON, nullable=False)

router = APIRouter(prefix='/operations/satellite', tags=['Satellite NDVI'])

def decorate(data):
    age = (date.today() - date.fromisoformat(data['composite_date'])).days
    return {**data, 'age_days': age, 'stale': age > 32}

async def fetch_observation(latitude, longitude, client):
    params = {'latitude': latitude, 'longitude': longitude}
    response = await client.get(BASE + '/dates', params=params)
    response.raise_for_status()
    dates = sorted(response.json()['dates'], key=lambda x: x['calendar_date'])
    dates = [d for d in dates if d['calendar_date'] <= date.today().isoformat()]
    if not dates: raise ValueError('No satellite composites available at this location')
    latest = dates[-1]
    params.update(startDate=latest['modis_date'], endDate=latest['modis_date'], kmAboveBelow=0, kmLeftRight=0)
    values, quality = await asyncio.gather(*[client.get(BASE+'/subset', params={**params, 'band': band}) for band in [NDVI, QUALITY]])
    values.raise_for_status(); quality.raise_for_status()
    v, q = values.json(), quality.json()
    record = next(s for s in v['subset'] if s['band'] == NDVI and s['calendar_date'] == latest['calendar_date'])
    qc = next(s for s in q['subset'] if s['band'] == QUALITY and s['calendar_date'] == latest['calendar_date'])
    if len(record['data']) != 1 or len(qc['data']) != 1:
        raise ValueError('Expected a single matching satellite pixel')
    raw, reliability = float(record['data'][0]), int(qc['data'][0])
    if reliability != 0 or not -2000 <= raw <= 10000:
        raise ValueError('Latest satellite pixel is cloudy, snow-covered, marginal or missing; no quality-approved NDVI available')
    return {'ndvi': round(raw * 0.0001, 4), 'raw_value': raw, 'scale': 0.0001,
            'composite_date': latest['calendar_date'], 'modis_date': latest['modis_date'],
            'product': 'MOD13Q1', 'source': 'NASA ORNL DAAC TESViS', 'source_url': BASE,
            'resolution_m': 250, 'composite_days': 16, 'quality': 'good (pixel reliability 0)',
            'latitude': latitude, 'longitude': longitude, 'retrieved_at': datetime.now(timezone.utc).isoformat()}

@router.get('/{location_id}')
def get_observation(location_id: str, db: Session = Depends(get_db)):
    require_location(db, location_id)
    row = db.get(SatelliteObservation, location_id)
    return {'observation': decorate(row.data) if row else None}

@router.post('/{location_id}/refresh')
async def refresh_observation(location_id: str, db: Session = Depends(get_db)):
    loc = require_location(db, location_id)
    row = db.get(SatelliteObservation, location_id)
    if row and (datetime.now(timezone.utc) - datetime.fromisoformat(row.data['retrieved_at'])).total_seconds() < 3600:
        return {'observation': decorate(row.data), 'cached': True}
    try:
        async with httpx.AsyncClient(timeout=12, headers={'Accept': 'application/json'}) as client:
            data = await asyncio.wait_for(fetch_observation(loc.latitude, loc.longitude, client), timeout=28)
    except (httpx.HTTPError, asyncio.TimeoutError):
        raise HTTPException(502, 'Satellite service unavailable. Existing observations are retained; retry later.')
    except (KeyError, StopIteration, ValueError, TypeError, RuntimeError):
        raise HTTPException(422, 'Latest composite has no usable quality-approved pixel or an unexpected format. Existing observations are retained.')
    if row: row.data = data
    else: db.add(SatelliteObservation(location_id=location_id, data=data))
    db.commit()
    return {'observation': decorate(data), 'cached': False}
