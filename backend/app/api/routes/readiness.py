import hashlib, json, os, secrets, uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database.session import get_db
from app.models.location import Location
from app.core.config import settings
from app.core.admin_auth import authenticated
from app.api.routes.whatsapp import authorize
from app.api.routes.operations import require_location, FieldReport
from app.services.readiness import Outlook, Audit, Device, Reading, Evaluation, now, stamp, collect, evaluate, audit

router=APIRouter(prefix='/readiness',tags=['Monitoring and validation'])
def actor(request):return os.getenv('ADMIN_USERNAME','administrator') if authenticated(request) else 'operations-key client'
class Strict(BaseModel):model_config=ConfigDict(extra='forbid',allow_inf_nan=False)

@router.get('/outlooks/{location_id}')
def outlooks(location_id:str,db:Session=Depends(get_db)):
    loc=require_location(db,location_id)
    rows=db.query(Outlook).filter_by(location_id=location_id).order_by(Outlook.created_at.desc()).limit(60).all()
    data=[{**r.data,'stale':(now()-stamp(r.data['retrieved_at'])).total_seconds()>3600} for r in rows]
    measurements=loc.latest_measurements or {}
    timestamp=measurements.get('observed_at') or measurements.get('timestamp')
    try:age=(now()-stamp(timestamp)).total_seconds() if timestamp else None
    except ValueError:age=None
    return {'history':data,'current_input':{'source':measurements.get('source','UNKNOWN'),'timestamp':timestamp,
        'stale':age is None or age>3600,'age_seconds':age,'notice':'Location inputs may be seeded, manual or simulated. Outlooks never create crisis alerts.'},
        'monitoring_enabled':os.getenv('MONITORING_ENABLED','false').lower()=='true',
        'site_scheduled':location_id in os.getenv('MONITOR_LOCATION_IDS','').split(',')}

@router.post('/outlooks/{location_id}/refresh',dependencies=[Depends(authorize)])
async def refresh(location_id:str,db:Session=Depends(get_db)):
    try:return await collect(db,require_location(db,location_id))
    except (httpx.HTTPError,ValueError,KeyError,TypeError):
        db.rollback();raise HTTPException(502,'Forecast unavailable or incomplete; previous snapshots retained. No simulated replacement was created.')

class Replay(Strict):
    rows:list[dict]=Field(min_length=1,max_length=2000)
    threshold:float=Field(default=.75,ge=0,le=1)
    baseline_mm:float=Field(default=100,gt=0,le=1500)
@router.post('/evaluations',dependencies=[Depends(authorize)])
def replay(data:Replay,request:Request,db:Session=Depends(get_db)):
    try:result=evaluate(data.rows,data.threshold,data.baseline_mm)
    except (ValueError,KeyError,TypeError) as e:raise HTTPException(422,str(e))
    row=Evaluation(id=str(uuid.uuid4()),data=result);db.add(row)
    audit(db,row.id,actor(request),'evaluation_created',{'cases':len(data.rows)});db.commit()
    return {'id':row.id,**result}
@router.get('/evaluations',dependencies=[Depends(authorize)])
def evaluations(db:Session=Depends(get_db)):
    return [{'id':r.id,'created_at':r.created_at,**{k:v for k,v in r.data.items() if k!='timeline'}} for r in db.query(Evaluation).order_by(Evaluation.created_at.desc()).limit(30)]
@router.get('/evaluations/{evaluation_id}',dependencies=[Depends(authorize)])
def evaluation(evaluation_id:str,db:Session=Depends(get_db)):
    row=db.get(Evaluation,evaluation_id)
    if not row:raise HTTPException(404,'Evaluation not found')
    return {'id':row.id,**row.data}

class NewDevice(Strict):
    location_id:str=Field(max_length=64)
    name:str=Field(min_length=2,max_length=100)
    kind:Literal['soil_moisture','rainfall','tilt','pore_pressure']
    calibration_reference:str=Field(min_length=5,max_length=300)
    expected_interval_seconds:int=Field(default=900,ge=30,le=86400)
    test_device:bool=True
@router.post('/devices',dependencies=[Depends(authorize)])
def create_device(data:NewDevice,request:Request,db:Session=Depends(get_db)):
    require_location(db,data.location_id);token=secrets.token_urlsafe(32);ident=str(uuid.uuid4())
    row=Device(id=ident,location_id=data.location_id,data={**data.model_dump(),'key_hash':hashlib.sha256(token.encode()).hexdigest(),'active':True})
    db.add(row);audit(db,ident,actor(request),'device_registered',{'name':data.name});db.commit()
    return {'id':ident,'token':token,'notice':'Copy once into your device configuration. Store privately.'}
@router.get('/devices',dependencies=[Depends(authorize)])
def devices(db:Session=Depends(get_db)):
    output=[]
    for row in db.query(Device).all():
        reading=db.query(Reading).filter_by(device_id=row.id).order_by(Reading.observed_at.desc()).first()
        observed=reading.data['observed_at'] if reading else None
        stale=not observed or (now()-stamp(observed)).total_seconds()>max(300,2*row.data['expected_interval_seconds'])
        output.append({'id':row.id,**{k:v for k,v in row.data.items() if k!='key_hash'},'latest':reading.data if reading else None,'stale':stale})
    return output
@router.post('/devices/{device_id}/revoke',dependencies=[Depends(authorize)])
def revoke(device_id:str,request:Request,db:Session=Depends(get_db)):
    row=db.get(Device,device_id)
    if not row:raise HTTPException(404,'Device not found')
    row.data={**row.data,'active':False};audit(db,row.id,actor(request),'device_revoked',{});db.commit();return {'revoked':True}
class SensorInput(Strict):
    device_id:str=Field(max_length=64)
    sequence_id:str=Field(min_length=1,max_length=50,pattern=r'^[A-Za-z0-9_-]+$')
    observed_at:datetime
    value:float
    unit:Literal['percent','mm','degrees','kPa']
    @field_validator('observed_at')
    @classmethod
    def aware(cls,v):
        if v.tzinfo is None:raise ValueError('Timezone required')
        if v>now()+timedelta(minutes=2) or v<now()-timedelta(days=7):raise ValueError('Reading timestamp outside accepted window')
        return v
@router.post('/sensor-ingest')
def ingest(data:SensorInput,x_sensor_key:str=Header(default=''),db:Session=Depends(get_db)):
    row=db.get(Device,data.device_id)
    if not row or not row.data['active'] or not secrets.compare_digest(row.data['key_hash'],hashlib.sha256(x_sensor_key.encode()).hexdigest()):raise HTTPException(401,'Invalid or revoked device token')
    units={'soil_moisture':('percent',0,100),'rainfall':('mm',0,1500),'tilt':('degrees',-180,180),'pore_pressure':('kPa',-100,10000)}
    unit,low,high=units[row.data['kind']]
    if data.unit!=unit or not low<=data.value<=high:raise HTTPException(422,'Invalid unit or sensor range')
    ident=data.device_id+':'+data.sequence_id;payload=data.model_dump(mode='json');payload.update(kind=row.data['kind'],test_device=row.data['test_device'],source='TEST_SENSOR' if row.data['test_device'] else 'DEVICE_OBSERVATION')
    old=db.get(Reading,ident)
    if old:
        if old.data!=payload:raise HTTPException(409,'Sequence ID already used with different data')
        return {'id':ident,'duplicate':True}
    db.add(Reading(id=ident,device_id=row.id,observed_at=data.observed_at,data=payload))
    try:db.commit()
    except IntegrityError:
        db.rollback();old=db.get(Reading,ident)
        if old and old.data==payload:return {'id':ident,'duplicate':True}
        raise HTTPException(409,'Sequence ID already used with different data')
    return {'id':ident,'duplicate':False,'automatic_alerts':False}
@router.get('/devices/{device_id}/readings',dependencies=[Depends(authorize)])
def readings(device_id:str,db:Session=Depends(get_db)):
    return [r.data for r in db.query(Reading).filter_by(device_id=device_id).order_by(Reading.observed_at.desc()).limit(200)]

class Review(Strict):
    status:Literal['VERIFIED','REJECTED','DISPATCHED','RESOLVED']
    reason:str=Field(min_length=5,max_length=1000)
    assigned_to:str=Field(default='',max_length=120)
    expected_updated_at:str|None=None
    annotations:list[dict]=Field(default_factory=list,max_length=20)
    @field_validator('annotations')
    @classmethod
    def boxes(cls,values):
        for b in values:
            if set(b)!={'x','y','width','height','label'}:raise ValueError('Annotations require x,y,width,height,label')
            from app.services.readiness import finite
            for k in ['x','y','width','height']:
                if not 0<=finite(b[k])<=1:raise ValueError('Use normalized image coordinates')
            if b['width']<=0 or b['height']<=0 or b['x']+b['width']>1 or b['y']+b['height']>1:raise ValueError('Invalid box dimensions')
            if not isinstance(b['label'],str) or not 1<=len(b['label'])<=120:raise ValueError('Annotation label required')
        return values
@router.post('/reports/{report_id}/review',dependencies=[Depends(authorize)])
def review(report_id:str,data:Review,request:Request,db:Session=Depends(get_db)):
    row=db.get(FieldReport,report_id)
    if not row:raise HTTPException(404,'Report not found')
    from app.core.access import enabled
    if enabled() and row.data.get('category')=='landslide' and data.status=='VERIFIED':raise HTTPException(409,'Use Response Coordination > Verify field reports to verify and alert teams together')
    if row.data.get('verified_incident_id') and data.status=='REJECTED':raise HTTPException(409,'Cancel the linked response incident before changing the verified report')
    if data.expected_updated_at!=row.data.get('updated_at'):raise HTTPException(409,'Report changed. Reload before reviewing.')
    if data.annotations and not row.data.get('photo'):raise HTTPException(422,'Photo required for annotations')
    previous={k:row.data.get(k) for k in ['status','assigned_to','updated_at']}
    updated={**row.data,'status':data.status,'assigned_to':data.assigned_to,'updated_at':now().isoformat(),'review_reason':data.reason,'annotations':data.annotations,'reviewed_by':actor(request)}
    changed=db.query(FieldReport).filter(FieldReport.id==report_id,FieldReport.data['updated_at'].as_string()==data.expected_updated_at).update({'data':updated},synchronize_session=False)
    if not changed:
        db.rollback();raise HTTPException(409,'Report changed. Reload before reviewing.')
    audit(db,report_id,actor(request),'report_reviewed',{'before':previous,'after':data.model_dump(mode='json')});db.commit()
    db.refresh(row)
    return {'id':row.id,**row.data}
@router.get('/audit/{entity_id}',dependencies=[Depends(authorize)])
def history(entity_id:str,db:Session=Depends(get_db)):
    return [{'id':r.id,'time':r.created_at,**r.data} for r in db.query(Audit).filter_by(entity_id=entity_id).order_by(Audit.created_at.desc()).limit(100)]

@router.get('/models',dependencies=[Depends(authorize)])
def models(db:Session=Depends(get_db)):
    from app.services.model_registry import versions,active_path,digest
    path=Path(active_path());active=digest(path) if path.exists() else None
    return {'active':active,'versions':[{'id':v['id'],'name':v['name']} for v in versions().values()],
        'notice':'Only trusted server-installed artifacts. An approval records an operator decision, not scientific certification.'}
class Activation(Strict):
    model_id:str=Field(pattern=r'^[a-f0-9]{64}$')
    expected_active:str=Field(pattern=r'^[a-f0-9]{64}$')
    reason:str=Field(min_length=10,max_length=1000)
    evaluation_id:str|None=None
    rollback:bool=False
@router.post('/models/activate',dependencies=[Depends(authorize)])
def activate_model(data:Activation,request:Request,db:Session=Depends(get_db)):
    from app.services.model_registry import activate,active_path,digest,LOCK
    with LOCK:
        current=digest(Path(active_path()))
        if current!=data.expected_active:raise HTTPException(409,'Active model changed; reload first')
        if data.rollback:
            entries=db.query(Audit).filter_by(entity_id='model-registry').all()
            if not any(r.data.get('from_model')==data.model_id or r.data.get('to_model')==data.model_id for r in entries):raise HTTPException(422,'Rollback is restricted to previously active versions')
        else:
            evaluation=db.get(Evaluation,data.evaluation_id) if data.evaluation_id else None
            if not evaluation or evaluation.data['cases']<30:raise HTTPException(422,'Attach an evaluation with at least 30 verified cases')
            rows=evaluation.data['timeline']
            if any(r['model_version']!=data.model_id for r in rows) or len({r['actual'] for r in rows})<2:raise HTTPException(422,'Evaluation must reference the candidate hash and contain events and non-events')
        try:activate(data.model_id)
        except (ValueError,KeyError,TypeError) as e:raise HTTPException(422,str(e))
        audit(db,'model-registry',actor(request),'model_activated',{'from_model':current,'to_model':data.model_id,'reason':data.reason,'evaluation_id':data.evaluation_id,'rollback':data.rollback});db.commit()
    return {'active':data.model_id,'notice':'Activation recorded. This does not establish operational validation.'}
