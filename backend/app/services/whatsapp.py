"""Durable WhatsApp outbox. Twilio failures never run inside prediction transactions."""
import asyncio, json, uuid, logging
from pathlib import Path

LANGUAGES = json.loads(Path(__file__).with_name("alert-languages.json").read_text(encoding="utf-8"))
from datetime import datetime, timedelta
import httpx
from sqlalchemy import Column, String, Boolean, DateTime, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import Session
from app.database.base import Base
from app.database.session import SessionLocal
from app.models.alert import Alert
from app.models.location import Location
from app.core.config import settings

log=logging.getLogger(__name__)
def now(): return datetime.utcnow()

class WhatsAppRecipient(Base):
    __tablename__='whatsapp_recipients'
    id=Column(String(64),primary_key=True)
    name=Column(String(120),nullable=False)
    phone=Column(String(20),unique=True,nullable=False)
    location_id=Column(String(64),nullable=True)
    active=Column(Boolean,default=True,nullable=False)
    opted_in_at=Column(DateTime,nullable=False)
    consent_reference=Column(String(300),nullable=False)

class RecipientLanguage(Base):
    # Additive table: existing recipient schemas do not need ALTER TABLE.
    __tablename__ = 'whatsapp_recipient_languages'
    recipient_id = Column(String(64), primary_key=True)
    language = Column(String(8), nullable=False, default='en')

def recipient_language(db, recipient_id):
    row = db.get(RecipientLanguage, recipient_id)
    return row.language if row else 'en'

def content_templates():
    try:
        mapping = json.loads(settings.TWILIO_CONTENT_SIDS)
        if not isinstance(mapping, dict): mapping = {}
    except (ValueError, TypeError): mapping = {}
    templates = {k: v for k, v in mapping.items() if k in LANGUAGES and isinstance(v, str) and v.startswith('HX') and len(v) == 34}
    if settings.TWILIO_CONTENT_SID: templates.setdefault('en', settings.TWILIO_CONTENT_SID)
    return templates

class WhatsAppDelivery(Base):
    __tablename__='whatsapp_deliveries'
    __table_args__=(UniqueConstraint('alert_id','recipient_id','severity',name='uq_wa_alert_recipient_severity'),)
    id=Column(String(64),primary_key=True)
    alert_id=Column(String(64),index=True,nullable=False)
    recipient_id=Column(String(64),nullable=False)
    location_id=Column(String(64),index=True,nullable=False)
    severity=Column(String(16),nullable=False)
    payload=Column(JSON,nullable=False)
    status=Column(String(32),default='PENDING',index=True,nullable=False)
    attempts=Column(Integer,default=0,nullable=False)
    twilio_sid=Column(String(64),nullable=True)
    error=Column(String(300),nullable=True)
    created_at=Column(DateTime,default=now,nullable=False)
    updated_at=Column(DateTime,default=now,nullable=False)
    next_attempt=Column(DateTime,default=now,nullable=False)

def configuration():
    fields=['TWILIO_ACCOUNT_SID','TWILIO_AUTH_TOKEN','TWILIO_WHATSAPP_FROM']
    missing=[f for f in fields if not getattr(settings,f)]
    if not content_templates(): missing.append('TWILIO_CONTENT_SID or TWILIO_CONTENT_SIDS')
    return {'languages':{k:{'name':v['name'],'configured':bool(content_templates().get(k))} for k,v in LANGUAGES.items()},'enabled':settings.WHATSAPP_ENABLED,'configured':not missing,'missing':missing,'trigger':'HIGH or SEVERE operational alerts; seeded/simulated sources excluded','template_variables':{'1':'severity','2':'location name','3':'risk score','4':'recommended action','5':'alert ID'}}

def eligible(db,alert):
    if not alert or alert.status not in ['ACTIVE','ACKNOWLEDGED'] or alert.severity not in ['HIGH','SEVERE']:return False
    if alert.created_at < now()-timedelta(minutes=30):return False
    loc=db.get(Location,alert.location_id)
    if not loc or loc.risk_level not in ['HIGH','SEVERE']:return False
    source=(loc.latest_measurements or {}).get('source','')
    return source in ['OPEN_METEO_API','MANUAL_INPUT','REAL_SENSOR']

def enqueue(db):
    from sqlalchemy.exc import IntegrityError
    alerts=db.query(Alert).filter(Alert.status.in_(['ACTIVE','ACKNOWLEDGED']),Alert.created_at>=now()-timedelta(minutes=30)).all()
    recipients=db.query(WhatsAppRecipient).filter_by(active=True).all()
    for alert in alerts:
        if not eligible(db,alert):continue
        loc=db.get(Location,alert.location_id)
        for recipient in recipients:
            from app.services.messaging import preferences
            if not preferences(db,recipient.id)['whatsapp']:continue
            if recipient.location_id and recipient.location_id!=alert.location_id:continue
            exists=db.query(WhatsAppDelivery).filter_by(alert_id=alert.alert_id,recipient_id=recipient.id,severity=alert.severity).first()
            if exists:continue
            # Acknowledging an incident can lead the legacy engine to create another alert ID.
            recent=db.query(WhatsAppDelivery).filter(WhatsAppDelivery.recipient_id==recipient.id,WhatsAppDelivery.location_id==alert.location_id,WhatsAppDelivery.severity==alert.severity,WhatsAppDelivery.created_at>=now()-timedelta(minutes=30),WhatsAppDelivery.status.notin_(['FAILED','CANCELLED'])).first()
            if recent:continue
            variables={'1':alert.severity,'2':loc.name[:120],'3':str(round(alert.risk_score,1)),'4':(alert.recommended_action or 'Follow local authority instructions')[:500],'5':alert.alert_id}
            language=recipient_language(db,recipient.id)
            if language!='en':
                variables['1']=LANGUAGES[language]['levels'][alert.severity]
                variables['4']=LANGUAGES[language]['action']
            variables['_language']=language
            try:
                with db.begin_nested():
                    db.add(WhatsAppDelivery(id=str(uuid.uuid4()),alert_id=alert.alert_id,recipient_id=recipient.id,location_id=alert.location_id,severity=alert.severity,payload=variables))
                    db.flush()
            except IntegrityError:pass
    db.commit()

def auth():return httpx.BasicAuth(settings.TWILIO_ACCOUNT_SID,settings.TWILIO_AUTH_TOKEN)
def url():return f'https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json'

async def send_one(db,delivery_id,client):
    row=db.get(WhatsAppDelivery,delivery_id)
    if not row or row.status not in ['PENDING','RETRY'] or row.next_attempt>now():return
    recipient=db.get(WhatsAppRecipient,row.recipient_id);alert=db.query(Alert).filter_by(alert_id=row.alert_id).first()
    if not recipient or not recipient.active or not eligible(db,alert) or alert.severity!=row.severity or (recipient.location_id and recipient.location_id!=alert.location_id):
        row.status='CANCELLED';row.updated_at=now();db.commit();return
    from app.services.messaging import preferences
    if not preferences(db,row.recipient_id)['whatsapp']:
        row.status='CANCELLED';db.commit();return
    language=row.payload.get('_language','en')
    template=content_templates().get(language,'')
    if not template:
        row.status='RETRY';row.error=f'Approved {language} template is not configured';row.next_attempt=now()+timedelta(seconds=60);row.updated_at=now();db.commit();return
    claimed=db.query(WhatsAppDelivery).filter(WhatsAppDelivery.id==row.id,WhatsAppDelivery.status.in_(['PENDING','RETRY'])).update({'status':'SENDING','updated_at':now(),'attempts':WhatsAppDelivery.attempts+1},synchronize_session=False)
    db.commit()
    if not claimed:return
    db.refresh(row)
    sender = settings.TWILIO_WHATSAPP_FROM.strip()
    if not sender.startswith('whatsapp:'):
        sender = 'whatsapp:' + sender
    v = row.payload or {}
    text_message = f"🚨 Landslide warning: {v.get('1')}. Location: {v.get('2')}. Risk score: {v.get('3')}/100. Action: {v.get('4')}. Alert reference: {v.get('5')}."
    body={'From':sender,'To':'whatsapp:'+recipient.phone,'ContentSid':template,'ContentVariables':json.dumps({k:v for k,v in row.payload.items() if not k.startswith('_')})}
    try:
        response=await client.post(url(),data=body,auth=auth())
        if response.status_code==429:
            row.status='RETRY' if row.attempts<5 else 'FAILED';row.error='Twilio rate limit';row.next_attempt=now()+timedelta(seconds=min(300,30*2**row.attempts))
        elif response.status_code>=500:
            row.status='UNKNOWN';row.error='Provider response uncertain; check Twilio console before resending'
        elif response.is_error:
            err_data = response.json() if 'application/json' in response.headers.get('content-type', '') else {}
            err_code = err_data.get('code')
            row.status='FAILED'
            if err_code == 21654:
                row.error='Twilio 21654: ContentSid required. Check the approved template configuration.'
            elif err_code == 21608:
                row.error='Twilio 21608: Destination is not verified for this account. Check trial/compliance restrictions.'
            else:
                row.error=f"Twilio {err_code}: {str(err_data.get('message','Request rejected'))[:240]}"

        else:
            data=response.json();sid=data.get('sid','')
            if not sid.startswith('SM'):raise ValueError('Missing message SID')
            row.twilio_sid=sid;row.status=str(data.get('status','queued')).upper();row.error=None
    except (httpx.ConnectError,httpx.ConnectTimeout):
        row.status='RETRY' if row.attempts<5 else 'FAILED';row.error='Could not connect to Twilio';row.next_attempt=now()+timedelta(seconds=min(300,30*2**row.attempts))
    except Exception:
        row.status='UNKNOWN';row.error='Submission outcome uncertain; inspect Twilio console. Automatic resend stopped.'
    row.updated_at=now();db.commit()

async def poll_status(db,client):
    rows=db.query(WhatsAppDelivery).filter(WhatsAppDelivery.twilio_sid.isnot(None),WhatsAppDelivery.status.in_(['QUEUED','ACCEPTED','SENDING','SENT']),WhatsAppDelivery.updated_at<now()-timedelta(seconds=30)).limit(20).all()
    for row in rows:
        try:
            response=await client.get(url().replace('Messages.json',f'Messages/{row.twilio_sid}.json'),auth=auth())
            if response.is_success:
                data=response.json();row.status=str(data['status']).upper();row.error=f"Twilio error {data['error_code']}" if data.get('error_code') else None
            row.updated_at=now();db.commit()
        except Exception:db.rollback()

async def tick():
    if not settings.WHATSAPP_ENABLED or not configuration()['configured']:return
    db=SessionLocal()
    try:
        db.query(WhatsAppDelivery).filter_by(status='SENDING').filter(WhatsAppDelivery.twilio_sid.is_(None),WhatsAppDelivery.updated_at<now()-timedelta(minutes=2)).update({'status':'UNKNOWN','error':'Worker interrupted; verify in Twilio console before resending'},synchronize_session=False);db.commit()
        enqueue(db)
        ids=[r.id for r in db.query(WhatsAppDelivery).filter(WhatsAppDelivery.status.in_(['PENDING','RETRY']),WhatsAppDelivery.next_attempt<=now()).order_by(WhatsAppDelivery.created_at).limit(20).all()]
        async with httpx.AsyncClient(timeout=15) as client:
            for delivery_id in ids:await send_one(db,delivery_id,client)
            await poll_status(db,client)
    finally:db.close()

async def worker():
    while True:
        try:await tick()
        except asyncio.CancelledError:raise
        except Exception:log.warning('WhatsApp worker failed; will retry on next cycle')
        await asyncio.sleep(10)
