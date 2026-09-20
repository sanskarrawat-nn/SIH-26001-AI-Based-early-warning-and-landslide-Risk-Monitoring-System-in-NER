"""Asset exposure and field operations. Scores are transparent triage heuristics."""
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.orm import Session
from app.database.base import Base
from app.database.session import get_db
from app.models.location import Location

class Asset(Base):
    __tablename__ = 'exposure_assets'
    id = Column(String(64), primary_key=True)
    data = Column(JSON, nullable=False)

class FieldReport(Base):
    __tablename__ = 'field_reports'
    id = Column(String(64), primary_key=True)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AssetInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    location_id: str = Field(min_length=1, max_length=64)
    kind: Literal['village','hospital','school','bridge','road','shelter']
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    population: int = Field(ge=0, le=10000000)
    vulnerability: float = Field(ge=0, le=1)
    access: Literal['open','restricted','blocked'] = 'open'
    source: str = Field(min_length=3, max_length=300)
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class ReportInput(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), min_length=8, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')
    location_id: str = Field(min_length=1, max_length=64)
    officer: str = Field(min_length=2, max_length=120)
    category: Literal['crack','slope_movement','blocked_road','landslide','other']
    severity: Literal['LOW','MODERATE','HIGH','SEVERE']
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    notes: str = Field(min_length=5, max_length=3000)
    observed_at: datetime
    site_description: str = Field(default='', max_length=1000)
    estimated_people: Optional[int] = Field(default=None, ge=0, le=10000000)
    reported_injured: Optional[int] = Field(default=None, ge=0, le=10000000)
    access_condition: Literal['unknown','open','restricted','blocked'] = 'unknown'
    photo: Optional[str] = Field(default=None, max_length=4000000)
    video: Optional[str] = Field(default=None, max_length=14000000)
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

    @field_validator('video')
    @classmethod
    def valid_video(cls, value):
        if value:
            import base64
            prefix, _, encoded = value.partition(',')
            if prefix not in ['data:video/mp4;base64', 'data:video/webm;base64']:
                raise ValueError('Use an MP4 or WebM video')
            try:
                raw = base64.b64decode(encoded, validate=True)
            except Exception:
                raise ValueError('Invalid video encoding')
            if len(raw) > 10000000:
                raise ValueError('Video must be under 10 MB')
            valid = (prefix == 'data:video/mp4;base64' and len(raw) >= 16 and raw[4:8] == b'ftyp') or (prefix == 'data:video/webm;base64' and raw.startswith(bytes.fromhex('1a45dfa3')) and b'webm' in raw[:4096])
            if not valid:
                raise ValueError('Video contents do not match MP4/WebM format')
        return value

    @field_validator('photo')
    @classmethod
    def valid_photo(cls, value):
        if value:
            import base64
            if not value.startswith(('data:image/jpeg;base64,','data:image/png;base64,','data:image/webp;base64,')):
                raise ValueError('Use a JPEG, PNG or WebP photo')
            try:
                raw = base64.b64decode(value.split(',',1)[1], validate=True)
            except Exception:
                raise ValueError('Invalid image encoding')
            if not (raw.startswith(b'\xff\xd8\xff') or raw.startswith(b'\x89PNG\r\n\x1a\n') or (raw.startswith(b'RIFF') and raw[8:12]==b'WEBP')):
                raise ValueError('Invalid image contents')
        return value

class ReportUpdate(BaseModel):
    status: Literal['SUBMITTED','VERIFIED','DISPATCHED','RESOLVED','REJECTED']
    assigned_to: str = Field(default='', max_length=120)

router = APIRouter(prefix='/operations', tags=['Field operations'])

def require_location(db, location_id):
    loc = db.get(Location, location_id)
    if not loc:
        raise HTTPException(404, 'Monitoring location not found')
    return loc

@router.get('/assets')
def assets(db: Session = Depends(get_db)):
    return [{'id':a.id, **a.data} for a in db.query(Asset).all()]

@router.post('/assets', status_code=201)
def create_asset(data: AssetInput, db: Session = Depends(get_db)):
    require_location(db, data.location_id)
    row = Asset(id=str(uuid.uuid4()), data=data.model_dump())
    db.add(row); db.commit()
    return {'id':row.id, **row.data}

@router.put('/assets/{asset_id}')
def update_asset(asset_id: str, data: AssetInput, db: Session = Depends(get_db)):
    row = db.get(Asset, asset_id)
    if not row: raise HTTPException(404,'Asset not found')
    require_location(db,data.location_id)
    row.data=data.model_dump(); db.commit()
    return {'id':row.id, **row.data}

@router.delete('/assets/{asset_id}')
def delete_asset(asset_id: str, db: Session = Depends(get_db)):
    row=db.get(Asset,asset_id)
    if not row: raise HTTPException(404,'Asset not found')
    db.delete(row);db.commit()
    return {'deleted':asset_id}

@router.get('/reports')
def reports(db: Session = Depends(get_db)):
    # Project metadata in SQL so list/triage requests never load large video bodies.
    keys = ['location_id','officer','category','severity','latitude','longitude','notes','observed_at','status','assigned_to','received_at','updated_at']
    columns = [FieldReport.id] + [FieldReport.data[k].as_string().label(k) for k in keys]
    columns += [FieldReport.data['field_updates'].label('field_updates')]
    columns += [(FieldReport.data['photo'].as_string().isnot(None)).label('has_photo'), (FieldReport.data['video'].as_string().isnot(None)).label('has_video')]
    return [dict(row._mapping) for row in db.query(*columns).order_by(FieldReport.created_at.desc()).limit(500).all()]


@router.get('/reports/{report_id}')
def report_detail(report_id: str, db: Session = Depends(get_db)):
    row=db.get(FieldReport,report_id)
    if not row: raise HTTPException(404,'Report not found')
    return {'id':row.id, **row.data}

def report_payload_matches(stored, submitted):
    # Older offline reports predate these optional scene fields.
    defaults={'site_description':'','estimated_people':None,'reported_injured':None,'access_condition':'unknown'}
    return all(stored.get(k,defaults.get(k))==v for k,v in submitted.items())

@router.post('/reports', status_code=201)
def create_report(data: ReportInput, db: Session = Depends(get_db)):
    existing=db.get(FieldReport,data.id)
    if existing:
        submitted=data.model_dump(mode='json')
        if not report_payload_matches(existing.data,submitted):
            raise HTTPException(409,'Submission ID already belongs to a different report')
        return {'id':existing.id,'status':existing.data['status'],'duplicate':True}
    require_location(db,data.location_id)
    row=FieldReport(id=data.id,data={**data.model_dump(mode='json'),'status':'SUBMITTED','assigned_to':'','received_at':datetime.now(timezone.utc).isoformat()})
    db.add(row)
    try:
        db.commit()
    except Exception as error:
        from sqlalchemy.exc import IntegrityError
        db.rollback()
        if not isinstance(error, IntegrityError): raise
        existing = db.get(FieldReport, data.id)
        if not existing: raise
        if not report_payload_matches(existing.data,data.model_dump(mode='json')):
            raise HTTPException(409, 'Submission ID already belongs to a different report')
        return {'id':existing.id, 'status':existing.data['status'], 'duplicate':True}
    return {'id':row.id,'status':'SUBMITTED','duplicate':False}

@router.patch('/reports/{report_id}')
def update_report(report_id: str, data: ReportUpdate, request: Request, db: Session = Depends(get_db)):
    row=db.get(FieldReport,report_id)
    if not row: raise HTTPException(404,'Report not found')
    from app.core.access import enabled
    if enabled() and row.data.get('category')=='landslide' and data.status=='VERIFIED':
        raise HTTPException(409,'Use Response Coordination > Verify field reports to verify and alert teams together')
    if row.data.get('verified_incident_id') and data.status in ('SUBMITTED','REJECTED'):
        raise HTTPException(409,'Cancel the linked response incident before changing the verified report')
    from app.services.readiness import audit
    from app.core.admin_auth import authenticated
    import os
    audit(db,report_id,getattr(request.state,'access_identity',None).get('name') if getattr(request.state,'access_identity',None) else (os.getenv('ADMIN_USERNAME','administrator') if authenticated(request) else 'operations client'),'legacy_report_update',{'before':{k:row.data.get(k) for k in ['status','assigned_to']},'after':data.model_dump(),'notice':'No reason supplied through legacy editor'})
    row.data={**row.data,**data.model_dump(),'updated_at':datetime.now(timezone.utc).isoformat()};db.commit()
    return {'id':row.id,'status':row.data['status'],'assigned_to':row.data['assigned_to']}

@router.get('/priorities')
def priorities(db: Session = Depends(get_db)):
    locs={x.location_id:x for x in db.query(Location).all()}
    reports=[dict(r._mapping) for r in db.query(*[FieldReport.data[k].as_string().label(k) for k in ['location_id','status','severity']]).all()]
    result=[]
    for asset in db.query(Asset).all():
        a=asset.data; loc=locs.get(a['location_id'])
        if not loc: continue
        relevant=[r for r in reports if r['location_id']==loc.location_id and r['status'] in ['VERIFIED','DISPATCHED']]
        severity=max([{'LOW':10,'MODERATE':35,'HIGH':65,'SEVERE':90}[r['severity']] for r in relevant] or [0])
        risk=max(loc.current_risk_score or 0,severity)
        population=min(a['population']/5000,1)*15
        critical=10 if a['kind'] in ['hospital','bridge','school'] else 0
        access={'open':0,'restricted':7,'blocked':15}[a['access']]
        score=round(min(100, risk*.45+a['vulnerability']*15+population+critical+access),1)
        result.append({'asset_id':asset.id,**a,'risk_score':risk,'priority_score':score,'priority':'URGENT' if score>=65 else 'HIGH' if score>=45 else 'WATCH', 'verified_reports':len(relevant),'reasons':{'hazard':round(risk*.45,1),'vulnerability':round(a['vulnerability']*15,1),'population':round(population,1),'critical_asset':critical,'access':access},'data_source':(loc.latest_measurements or {}).get('source','UNVERIFIED_BASELINE')})
    return sorted(result,key=lambda x:(-x['priority_score'],x['name']))

class DatasetInput(BaseModel):
    csv: str = Field(min_length=1, max_length=8000000)

@router.post('/observations/validate')
def validate_observations(data: DatasetInput):
    from app.ml.observations import validate_csv
    try:
        _, summary=validate_csv(data.csv)
        return summary
    except ValueError as e: raise HTTPException(422,str(e))

@router.get('/observations/template')
def observation_template():
    from fastapi.responses import Response
    from app.ml.observations import COLUMNS
    return Response(','.join(COLUMNS)+'\n',media_type='text/csv',headers={'Content-Disposition':'attachment; filename=observations-template.csv'})
