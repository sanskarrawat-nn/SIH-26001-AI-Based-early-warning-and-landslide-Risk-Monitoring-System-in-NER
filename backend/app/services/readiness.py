"""Experimental outlooks and replay evaluation. Never emits crisis alerts."""
import asyncio, math, os, uuid, logging
from datetime import datetime, timedelta, timezone
import httpx
from sqlalchemy import Column, String, JSON, DateTime
from app.database.base import Base
from app.database.session import SessionLocal
from app.models.location import Location

log=logging.getLogger(__name__)
def now(): return datetime.now(timezone.utc)
def stamp(value):
    d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if d.tzinfo is None: raise ValueError('Timestamp must include timezone')
    return d.astimezone(timezone.utc)
def finite(value):
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value): raise ValueError('Missing or invalid numeric observation')
    return float(value)
class Outlook(Base):
    __tablename__='experimental_outlooks'
    id=Column(String(64),primary_key=True)
    location_id=Column(String(64),index=True,nullable=False)
    created_at=Column(DateTime(timezone=True),default=now,index=True)
    data=Column(JSON,nullable=False)
class Audit(Base):
    __tablename__='operation_audit'
    id=Column(String(64),primary_key=True)
    entity_id=Column(String(128),index=True,nullable=False)
    created_at=Column(DateTime(timezone=True),default=now)
    data=Column(JSON,nullable=False)
class Device(Base):
    __tablename__='sensor_devices'
    id=Column(String(64),primary_key=True)
    location_id=Column(String(64),nullable=False)
    data=Column(JSON,nullable=False)
class Reading(Base):
    __tablename__='sensor_readings'
    id=Column(String(128),primary_key=True)
    device_id=Column(String(64),index=True,nullable=False)
    observed_at=Column(DateTime(timezone=True),nullable=False)
    received_at=Column(DateTime(timezone=True),default=now)
    data=Column(JSON,nullable=False)
class Evaluation(Base):
    __tablename__='replay_evaluations'
    id=Column(String(64),primary_key=True)
    created_at=Column(DateTime(timezone=True),default=now)
    data=Column(JSON,nullable=False)

def audit(db,entity,actor,action,details):
    db.add(Audit(id=str(uuid.uuid4()),entity_id=entity,data={'actor':actor,'action':action,**details}))

def build_outlook(data, location_id, fetched=None):
    fetched=fetched or now()
    hourly=data['hourly'];times=[datetime.fromisoformat(t).replace(tzinfo=timezone.utc) for t in hourly['time']]
    if len(set(times))!=len(times) or times!=sorted(times):raise ValueError('Invalid forecast timestamps')
    rain=hourly['precipitation'];moisture=hourly['soil_moisture_0_to_1cm']
    if len(times)!=len(rain) or len(times)!=len(moisture):raise ValueError('Incomplete forecast arrays')
    anchor=fetched.replace(minute=0,second=0,microsecond=0)
    def rainfall_window(start,end):
        selected=[(t,finite(rain[i])) for i,t in enumerate(times) if start<t<=end]
        expected=int((end-start).total_seconds()/3600)
        if len(selected)!=expected or any(v<0 or v>500 for _,v in selected):raise ValueError('Incomplete or invalid hourly rainfall window')
        if [t for t,_ in selected]!=[start+timedelta(hours=i) for i in range(1,expected+1)]:raise ValueError('Rainfall interval gaps')
        return sum(v for _,v in selected)
    recent=rainfall_window(anchor-timedelta(hours=24),anchor)
    latest=[finite(moisture[i]) for i,t in enumerate(times) if t==anchor]
    if not latest or not 0<=latest[0]<=1:raise ValueError('No valid current shallow-soil moisture')
    windows=[]
    for h in [3,6,12,24]:
        end=anchor+timedelta(hours=h)
        total=rainfall_window(anchor,end)
        rolling=rainfall_window(end-timedelta(hours=24),end)
        # Explicit demonstration rule. Not a landslide model or operational threshold.
        ratio=rolling/100.0
        windows.append({'hours':h,'valid_from':anchor.isoformat(),'valid_to':end.isoformat(),
            'forecast_rain_mm':round(total,2),'rolling_24h_mm':round(rolling,2),
            'rainfall_screen_ratio':round(ratio,3),'screen':'ABOVE_DEMO_REFERENCE' if ratio>=1 else 'BELOW_DEMO_REFERENCE'})
    return {'location_id':location_id,'source':'OPEN_METEO_FORECAST','retrieved_at':fetched.isoformat(),
        'provider_issue_time':None,'reference_time':anchor.isoformat(),'recent_24h_mm':round(recent,2),
        'shallow_soil_moisture_percent':round(latest[0]*100,2),'windows':windows,
        'status':'EXPERIMENTAL_NOT_VALIDATED','automatic_alerts':False,
        'method':'Rolling 24-hour rainfall screen against a demonstration reference of 100 mm; not a calibrated landslide probability.',
        'limitations':['Gridded forecast, not a local sensor measurement','100 mm is a demonstration reference, not an approved regional trigger','Provider issue time unavailable; retrieval time is not model issue time','No ground-movement measurements included']}

async def collect(db,loc):
    recent=db.query(Outlook).filter_by(location_id=loc.location_id).order_by(Outlook.created_at.desc()).first()
    if recent and (now()-stamp(recent.data['retrieved_at'])).total_seconds()<600:return recent.data
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.get('https://api.open-meteo.com/v1/forecast',params={'latitude':loc.latitude,'longitude':loc.longitude,
            'hourly':'precipitation,soil_moisture_0_to_1cm','past_days':2,'forecast_days':3,'timezone':'UTC'})
        r.raise_for_status();payload=build_outlook(r.json(),loc.location_id)
    db.add(Outlook(id=str(uuid.uuid4()),location_id=loc.location_id,data=payload))
    db.query(Outlook).filter(Outlook.created_at<now()-timedelta(days=30)).delete(synchronize_session=False)
    db.commit();return payload

def evaluate(rows, threshold=.75, baseline_mm=100):
    if not rows:raise ValueError('Provide at least one evaluation record')
    if len(rows)>2000:raise ValueError('Maximum 2000 records')
    checked=[];seen=set();horizons=set()
    for row in rows:
        for key in ['case_id','location_id','source','model_version']:
            if not isinstance(row.get(key),str) or not row[key].strip():raise ValueError(f'{key} is required')
        if row['case_id'] in seen:raise ValueError('Duplicate case_id')
        seen.add(row['case_id'])
        if row.get('verified') is not True:raise ValueError('Only verified cases are accepted')
        decision=stamp(row['issued_at']);available=stamp(row['inputs_available_at']);end=stamp(row['window_end'])
        if available>decision:raise ValueError('Future input leakage: inputs were unavailable at issuance')
        if end<=decision:raise ValueError('window_end must follow issued_at')
        horizon=(end-decision).total_seconds()/3600
        if horizon>168:raise ValueError('Maximum horizon is 168 hours')
        horizons.add(round(horizon,6))
        observed=stamp(row['outcome_observed_until'])
        if observed<end:raise ValueError('Incomplete outcome follow-up')
        event=stamp(row['event_at']) if row.get('event_at') else None
        if event and not decision<event<=end:raise ValueError('Event must occur after issuance and inside its window')
        p=finite(row['probability']);rain=finite(row['rainfall_24h_mm'])
        if not 0<=p<=1 or rain<0 or rain>1500:raise ValueError('Invalid probability or rainfall')
        checked.append({**row,'actual':int(event is not None),'predicted':int(p>=threshold),'baseline_predicted':int(rain>=baseline_mm),
            'lead_hours':round((event-decision).total_seconds()/3600,2) if event and p>=threshold else None})
    if len(horizons)!=1:raise ValueError('Use one common forecast horizon per evaluation')
    if len({r['model_version'] for r in checked})!=1:raise ValueError('Evaluate one model version at a time')
    def metrics(key):
        tp=sum(r[key]==1 and r['actual']==1 for r in checked);fp=sum(r[key]==1 and r['actual']==0 for r in checked)
        fn=sum(r[key]==0 and r['actual']==1 for r in checked);tn=sum(r[key]==0 and r['actual']==0 for r in checked)
        return {'tp':tp,'fp':fp,'fn':fn,'tn':tn,'precision':tp/(tp+fp) if tp+fp else None,
            'recall':tp/(tp+fn) if tp+fn else None,'false_alarm_ratio':fp/(tp+fp) if tp+fp else None,
            'false_positive_rate':fp/(fp+tn) if fp+tn else None}
    leads=[r['lead_hours'] for r in checked if r['lead_hours'] is not None]
    return {'cases':len(checked),'threshold':threshold,'baseline_mm':baseline_mm,'horizon_hours':next(iter(horizons)),
        'model':metrics('predicted'),'baseline':metrics('baseline_predicted'),
        'brier_score':sum((r['probability']-r['actual'])**2 for r in checked)/len(checked),
        'mean_detected_lead_hours':sum(leads)/len(leads) if leads else None,
        'timeline':sorted(checked,key=lambda r:stamp(r['issued_at'])),
        'notice':'Imported predictions are replayed, not regenerated. Verification is uploader-attested. Case-level metrics; overlapping cases can inflate event-level performance.'}

async def monitor():
    while True:
        if os.getenv('MONITORING_ENABLED','false').lower()=='true':
            # Explicit sites only; start with no network requests until configured.
            sites=[s.strip() for s in os.getenv('MONITOR_LOCATION_IDS','').split(',') if s.strip()][:20]
            for site in sites:
                with SessionLocal() as db:
                    loc=db.get(Location,site)
                    if loc:
                        try:await collect(db,loc)
                        except Exception:db.rollback();log.warning('Outlook monitoring unavailable for %s',site)
        await asyncio.sleep(600)
