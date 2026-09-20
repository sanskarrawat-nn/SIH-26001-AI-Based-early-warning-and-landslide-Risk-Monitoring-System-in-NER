"""Independent SMS outbox and explicitly requested test messages."""
import asyncio,json,uuid,logging
from datetime import timedelta
import httpx
from sqlalchemy import Column,String,Boolean,JSON,DateTime,Integer,UniqueConstraint
from app.database.base import Base
from app.database.session import SessionLocal
from app.core.config import settings
from app.services.whatsapp import WhatsAppRecipient,Alert,eligible,now,auth,url
log=logging.getLogger(__name__)
class ChannelPreference(Base):
    __tablename__='notification_preferences'
    recipient_id=Column(String(64),primary_key=True)
    whatsapp=Column(Boolean,nullable=False,default=True)
    sms=Column(Boolean,nullable=False,default=False)
    sms_consent_reference=Column(String(300),nullable=False,default='')
class Delivery(Base):
    __tablename__='channel_deliveries'
    __table_args__=(UniqueConstraint('event_id','recipient_id','channel',name='uq_channel_event'),)
    id=Column(String(64),primary_key=True)
    event_id=Column(String(100),nullable=False)
    recipient_id=Column(String(64),nullable=False)
    channel=Column(String(16),nullable=False)
    data=Column(JSON,nullable=False)
    status=Column(String(32),default='PENDING',index=True)
    attempts=Column(Integer,default=0)
    twilio_sid=Column(String(64),nullable=True)
    error=Column(String(500),nullable=True)
    created_at=Column(DateTime,default=now)
    updated_at=Column(DateTime,default=now)
    next_attempt=Column(DateTime,default=now)

def sms_config():
    missing=[k for k in ['TWILIO_ACCOUNT_SID','TWILIO_AUTH_TOKEN'] if not getattr(settings,k)]
    if not (settings.TWILIO_SMS_FROM or settings.TWILIO_SMS_MESSAGING_SERVICE_SID):missing.append('TWILIO_SMS_FROM or TWILIO_SMS_MESSAGING_SERVICE_SID')
    return {'enabled':settings.SMS_ENABLED,'configured':not missing,'missing':missing}
def preferences(db,recipient_id):
    p=db.get(ChannelPreference,recipient_id)
    return {'whatsapp':p.whatsapp if p else True,'sms':p.sms if p else False,'sms_consent_reference':p.sms_consent_reference if p else ''}
def enqueue_sms(db):
    from sqlalchemy.exc import IntegrityError
    for a in db.query(Alert).filter(Alert.status.in_(['ACTIVE','ACKNOWLEDGED']),Alert.created_at>=now()-timedelta(minutes=30)).all():
        if not eligible(db,a):continue
        for r in db.query(WhatsAppRecipient).filter_by(active=True).all():
            if (r.location_id and r.location_id!=a.location_id) or not preferences(db,r.id)['sms']:continue
            event=a.alert_id+':'+a.severity
            if db.query(Delivery).filter_by(event_id=event,recipient_id=r.id,channel='sms').first():continue
            recent=db.query(Delivery).filter(Delivery.recipient_id==r.id,Delivery.channel=='sms',Delivery.created_at>=now()-timedelta(minutes=30),Delivery.status.notin_(['FAILED','CANCELLED'])).all()
            if any(x.data.get('location_id')==a.location_id and x.data.get('severity')==a.severity and not x.data.get('test') for x in recent):continue
            try:
                with db.begin_nested():
                    db.add(Delivery(id=str(uuid.uuid4()),event_id=event,recipient_id=r.id,channel='sms',data={'alert_id':a.alert_id,'location_id':a.location_id,'severity':a.severity,'test':False,
                        'body':f'Landslide warning {a.severity}. Location {a.location_id}. Risk {a.risk_score:.1f}/100. {(a.recommended_action or "Follow local authority instructions")[:300]}. Ref {a.alert_id}'}));db.flush()
            except IntegrityError:pass
    db.commit()

async def send(db,ident,client):
    row=db.get(Delivery,ident)
    if not row or row.status not in ['PENDING','RETRY'] or row.next_attempt>now():return
    r=db.get(WhatsAppRecipient,row.recipient_id);pref=preferences(db,row.recipient_id)
    valid=bool(r and r.active and pref[row.channel])
    if row.data.get('test'):
        valid=valid and row.created_at>now()-timedelta(minutes=10)
    else:
        a=db.query(Alert).filter_by(alert_id=row.data['alert_id']).first()
        valid=valid and eligible(db,a) and a.severity==row.data['severity'] and (not r.location_id or r.location_id==a.location_id)
    if not valid:row.status='CANCELLED';db.commit();return
    ready=sms_config() if row.channel=='sms' else {'enabled':settings.WHATSAPP_ENABLED,'configured':bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_WHATSAPP_FROM and settings.TWILIO_TEST_CONTENT_SID)}
    if not ready['enabled'] or not ready['configured']:return
    claimed=db.query(Delivery).filter(Delivery.id==ident,Delivery.status.in_(['PENDING','RETRY'])).update({'status':'SENDING','attempts':Delivery.attempts+1,'updated_at':now()},synchronize_session=False);db.commit()
    if not claimed:return
    db.refresh(row)
    if row.channel=='sms':
        body={'To':r.phone,'Body':row.data['body']}
        if settings.TWILIO_SMS_MESSAGING_SERVICE_SID:body['MessagingServiceSid']=settings.TWILIO_SMS_MESSAGING_SERVICE_SID
        else:body['From']=settings.TWILIO_SMS_FROM
    else:
        sender=settings.TWILIO_WHATSAPP_FROM
        if not sender.startswith('whatsapp:'):sender='whatsapp:'+sender
        body={'To':'whatsapp:'+r.phone,'From':sender,'ContentSid':settings.TWILIO_TEST_CONTENT_SID,
            'ContentVariables':json.dumps({'1':'TEST ONLY — NO EMERGENCY','2':'Notification setup check','3':'N/A','4':'This is a test. No action required.','5':row.event_id})}
    try:
        response=await client.post(url(),data=body,auth=auth())
        if response.status_code==429:
            row.status='RETRY' if row.attempts<5 else 'FAILED';row.error='Twilio rate limit';row.next_attempt=now()+timedelta(seconds=min(300,30*2**row.attempts))
        elif response.status_code>=500:row.status='UNKNOWN';row.error='Provider outcome uncertain; inspect Twilio before resending'
        elif response.is_error:
            d=response.json();row.status='FAILED';row.error=f"Twilio {d.get('code')}: {str(d.get('message','Rejected'))[:400]}"
        else:
            d=response.json()
            if not str(d.get('sid','')).startswith('SM'):raise ValueError('No message SID')
            row.twilio_sid=d['sid'];row.status=d.get('status','queued').upper();row.error=None
    except (httpx.ConnectError,httpx.ConnectTimeout):
        row.status='RETRY' if row.attempts<5 else 'FAILED';row.error='Connection failed';row.next_attempt=now()+timedelta(seconds=min(300,30*2**row.attempts))
    except Exception:row.status='UNKNOWN';row.error='Outcome uncertain; inspect Twilio before resending'
    row.updated_at=now();db.commit()
async def tick():
    with SessionLocal() as db:
        db.query(Delivery).filter(Delivery.status=='SENDING',Delivery.twilio_sid.is_(None),Delivery.updated_at<now()-timedelta(minutes=2)).update({'status':'UNKNOWN','error':'Worker interrupted; verify provider before resending'},synchronize_session=False)
        db.commit()
        c=sms_config()
        if c['enabled'] and c['configured']:enqueue_sms(db)
        async with httpx.AsyncClient(timeout=15) as client:
            ids=[r.id for r in db.query(Delivery).filter(Delivery.status.in_(['PENDING','RETRY']),Delivery.next_attempt<=now()).order_by(Delivery.created_at).limit(20)]
            for ident in ids:await send(db,ident,client)
            for r in db.query(Delivery).filter(Delivery.twilio_sid.isnot(None),Delivery.status.in_(['QUEUED','ACCEPTED','SENDING','SENT']),Delivery.updated_at<now()-timedelta(seconds=30)).limit(20):
                try:
                    response=await client.get(url().replace('Messages.json',f'Messages/{r.twilio_sid}.json'),auth=auth())
                    if response.is_success:
                        d=response.json();r.status=d['status'].upper();r.error=f"Twilio error {d['error_code']}" if d.get('error_code') else None
                    r.updated_at=now();db.commit()
                except Exception:db.rollback()
async def worker():
    while True:
        try:await tick()
        except asyncio.CancelledError:raise
        except Exception:log.exception('Independent notification worker failed')
        await asyncio.sleep(10)
