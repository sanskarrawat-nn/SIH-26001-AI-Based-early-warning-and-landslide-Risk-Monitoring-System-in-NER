"""Isolated, officer-approved dispatch. Drill notifications never leave this process."""
import asyncio, copy, hashlib, json, logging, os, secrets, uuid
from datetime import datetime, timedelta
from urllib.parse import urlparse
import httpx
from fastapi import HTTPException
from sqlalchemy import Column, String, Integer, JSON, DateTime
from app.database.base import Base
from app.database.session import SessionLocal
from app.core.config import settings

log=logging.getLogger(__name__)
def now(): return datetime.utcnow()
def stamp(): return now().isoformat()+'Z'
def parsed(value):return datetime.fromisoformat(value.replace('Z','+00:00')).replace(tzinfo=None)
def ident():return str(uuid.uuid4())
class Team(Base):
    __tablename__='dispatch_teams'
    id=Column(String(64),primary_key=True)
    version=Column(Integer,nullable=False,default=1)
    data=Column(JSON,nullable=False)
class Incident(Base):
    __tablename__='dispatch_incidents'
    id=Column(String(64),primary_key=True)
    version=Column(Integer,nullable=False,default=1)
    data=Column(JSON,nullable=False)
class User(Base):
    __tablename__='dispatch_users'
    id=Column(String(64),primary_key=True)
    username=Column(String(100),unique=True,nullable=False)
    team_id=Column(String(64),nullable=False)
    name=Column(String(120),nullable=False)
    password=Column(String(300),nullable=False)
    active=Column(Integer,nullable=False,default=1)
class Session(Base):
    __tablename__='dispatch_sessions'
    token=Column(String(64),primary_key=True)
    user_id=Column(String(64),nullable=False)
    expires=Column(DateTime,nullable=False)
class Attempt(Base):
    __tablename__='dispatch_login_attempts'
    id=Column(String(64),primary_key=True)
    count=Column(Integer,nullable=False)
    start=Column(DateTime,nullable=False)
class Message(Base):
    __tablename__='dispatch_messages'
    id=Column(String(64),primary_key=True)
    incident_id=Column(String(64),nullable=False,index=True)
    data=Column(JSON,nullable=False)
    status=Column(String(32),nullable=False,default='PENDING')
    attempts=Column(Integer,nullable=False,default=0)
    sid=Column(String(64))
    error=Column(String(500))
    due=Column(DateTime,default=now,nullable=False)
    updated=Column(DateTime,default=now,nullable=False)
class Shelter(Base):
    __tablename__='dispatch_shelters'
    id=Column(String(64),primary_key=True)
    version=Column(Integer,nullable=False,default=1)
    data=Column(JSON,nullable=False)

def password_hash(password):
    salt=secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),310000).hex()
def check_password(password,encoded):
    salt,want=encoded.split(':')
    return secrets.compare_digest(want,hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),310000).hex())
def save(db,row,data,version):
    model=type(row)
    if row.version!=version:raise HTTPException(409,'Record changed. Refresh before saving.')
    changed=db.query(model).filter(model.id==row.id,model.version==version).update({'data':data,'version':version+1},synchronize_session=False)
    if not changed:raise HTTPException(409,'Record changed. Refresh before saving.')
    db.flush();db.expire(row)
def entry(data,actor,action,detail):
    data.setdefault('timeline',[]).append({'id':ident(),'at':stamp(),'actor':actor,'action':action,'detail':detail})
def render(row):return {'id':row.id,'version':row.version,**row.data}
def config():
    root=os.getenv('PUBLIC_APP_URL','').rstrip('/')
    u=urlparse(root)
    valid=u.scheme=='https' and bool(u.netloc) and not u.username and not u.query and not u.fragment
    credentials=bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN)
    return {'enabled':os.getenv('DISPATCH_MESSAGING_ENABLED','false').lower()=='true',
      'public_url_configured':bool(valid),'public_url':root if valid else '',
      'sms_ready':credentials and bool(settings.TWILIO_SMS_FROM or settings.TWILIO_SMS_MESSAGING_SERVICE_SID),
      'whatsapp_ready':credentials and bool(settings.TWILIO_WHATSAPP_FROM and os.getenv('TWILIO_DISPATCH_CONTENT_SID')),
      'drill_delivery':'SIMULATED; no external messages'}
def queue(db,incident_id,data,assignment,team,event):
    for channel in team.data['channels']:
        key=hashlib.sha256(f'{incident_id}:{assignment["id"]}:{team.id}:{event}:{channel}'.encode()).hexdigest()
        if db.get(Message,key):continue
        db.add(Message(id=key,incident_id=incident_id,data={'team_id':team.id,'team_name':team.data['name'],'phone':team.data['phone'],'channel':channel,'assignment_id':assignment['id'],'event':event,'drill':data['drill'],'task':('CANCELLED: contact coordinator before continuing. '+assignment['task']) if event=='CANCELLATION' else assignment['task'],'expires_at':(now()+timedelta(minutes=30)).isoformat()+'Z'},status='PENDING'))

def escalate(db):
    for row in db.query(Incident).all():
        if row.data['status']!='ACTIVE':continue
        d=copy.deepcopy(row.data);changed=False
        for a in d['assignments']:
            overdue=now()>parsed(a['due_at'])
            failure=a['status'] in ['DECLINED','UNAVAILABLE']
            if a['status']=='AWAITING' and overdue and not a.get('reminded'):
                t=db.get(Team,a['team_id'])
                if t:queue(db,row.id,d,a,t,'REMINDER')
                a['reminded']=stamp();entry(d,'scheduler','REMINDER',a['team_name']);changed=True
            escalation_due=now()>parsed(a['due_at'])+timedelta(minutes=d['ack_minutes'])
            if (failure or (a['status']=='AWAITING' and escalation_due)) and not a.get('escalated'):
                backup=db.get(Team,d['backup_team_id']) if d.get('backup_team_id') else None
                if backup:queue(db,row.id,d,a,backup,'ESCALATION')
                a['escalated']=stamp();entry(d,'scheduler','ESCALATION',f'{a["team_name"]}: '+('backup coordinator notified in queue' if backup else 'no backup configured; coordinator action required'));changed=True
        if changed:save(db,row,d,row.version)
    db.commit()

def message_valid(db,row):
    incident=db.get(Incident,row.incident_id);team=db.get(Team,row.data['team_id'])
    if not incident or not team or not team.data['active']:return False
    if parsed(row.data.get('expires_at','2000-01-01T00:00:00Z'))<now():return False
    if team.data['phone']!=row.data['phone'] or row.data['channel'] not in team.data['channels']:return False
    a=next((x for x in incident.data['assignments'] if x['id']==row.data['assignment_id']),None)
    if not a:return False
    if row.data['event']=='CANCELLATION':return a['status']=='CANCELLED'
    if incident.data['status']!='ACTIVE':return False
    return a['status'] in (['AWAITING','DECLINED','UNAVAILABLE'] if row.data['event']=='ESCALATION' else ['AWAITING'])
async def send_one(db,row_id,client):
    row=db.get(Message,row_id)
    if not row or row.status not in ['PENDING','RETRY'] or row.due>now():return
    if not message_valid(db,row):row.status='CANCELLED';row.error='Assignment no longer awaiting response or contact disabled';db.commit();return
    if row.data['drill']:
        row.status='SIMULATED';row.error=None;row.updated=now();db.commit();return
    c=config();channel=row.data['channel']
    if not c['enabled'] or not c['public_url_configured'] or not c[channel+'_ready']:
        row.error='Dispatch messaging disabled or channel configuration incomplete';db.commit();return
    incident=db.get(Incident,row.incident_id)
    link=c['public_url']+'/?response='+incident.id
    event=row.data['event']+' '+incident.data['kind']+' '+incident.data['severity']
    location=f'{incident.data["latitude"]:.5f}, {incident.data["longitude"]:.5f}'
    task=row.data['task'][:180]
    if channel=='sms':
        body={'To':row.data['phone'],'Body':f'NEREWS {event}. Incident {incident.id}. Location {location}. Task: {task}. Sign in to respond: {link}'}
        body.update({'MessagingServiceSid':settings.TWILIO_SMS_MESSAGING_SERVICE_SID} if settings.TWILIO_SMS_MESSAGING_SERVICE_SID else {'From':settings.TWILIO_SMS_FROM})
    else:
        sender=settings.TWILIO_WHATSAPP_FROM
        body={'To':'whatsapp:'+row.data['phone'],'From':sender if sender.startswith('whatsapp:') else 'whatsapp:'+sender,'ContentSid':os.getenv('TWILIO_DISPATCH_CONTENT_SID'),'ContentVariables':json.dumps({'1':event,'2':incident.id,'3':location,'4':task,'5':link})}
    changed=db.query(Message).filter(Message.id==row.id,Message.status.in_(['PENDING','RETRY'])).update({'status':'SENDING','attempts':Message.attempts+1,'updated':now()},synchronize_session=False);db.commit()
    if not changed:return
    db.refresh(row)
    url=f'https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json'
    try:
        r=await client.post(url,data=body,auth=(settings.TWILIO_ACCOUNT_SID,settings.TWILIO_AUTH_TOKEN))
        if r.status_code==429:
            row.status='RETRY' if row.attempts<5 else 'FAILED';row.error='Provider rate limit';row.due=now()+timedelta(seconds=min(300,30*2**row.attempts))
        elif r.status_code>=500:row.status='UNKNOWN';row.error='Provider outcome uncertain; inspect Twilio before contacting again'
        elif r.is_error:
            data=r.json();row.status='FAILED';row.error=f'Twilio {data.get("code")}: {str(data.get("message","Rejected"))[:350]}'
        else:
            data=r.json();sid=data.get('sid','')
            if len(sid)!=34 or not sid.startswith('SM'):raise ValueError('Invalid provider response')
            row.sid=sid;row.status=str(data.get('status','queued')).upper();row.error=None
    except (httpx.ConnectError,httpx.ConnectTimeout):
        row.status='RETRY' if row.attempts<5 else 'FAILED';row.error='Connection failed before delivery was confirmed';row.due=now()+timedelta(seconds=min(300,30*2**row.attempts))
    except Exception:row.status='UNKNOWN';row.error='Outcome uncertain; inspect Twilio before contacting again'
    row.updated=now();db.commit()
async def tick():
    with SessionLocal() as db:
        db.query(Message).filter(Message.status=='SENDING',Message.sid.is_(None),Message.updated<now()-timedelta(minutes=2)).update({'status':'UNKNOWN','error':'Worker interrupted; inspect provider'},synchronize_session=False);db.commit()
        escalate(db)
        async with httpx.AsyncClient(timeout=15) as client:
            ids=[r.id for r in db.query(Message).filter(Message.status.in_(['PENDING','RETRY']),Message.due<=now()).limit(30)]
            for i in ids:await send_one(db,i,client)
            if config()['enabled']:
                for r in db.query(Message).filter(Message.sid.isnot(None),Message.status.in_(['QUEUED','ACCEPTED','SENDING','SENT']),Message.updated<now()-timedelta(seconds=30)).limit(20):
                    try:
                        response=await client.get(f'https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages/{r.sid}.json',auth=(settings.TWILIO_ACCOUNT_SID,settings.TWILIO_AUTH_TOKEN))
                        if response.is_success:
                            data=response.json();r.status=str(data['status']).upper();r.error=str(data.get('error_code')) if data.get('error_code') else None
                        r.updated=now();db.commit()
                    except Exception:db.rollback()
        db.query(Session).filter(Session.expires<now()).delete();db.query(Attempt).filter(Attempt.start<now()-timedelta(minutes=15)).delete();db.commit()
async def worker():
    while True:
        try:await tick()
        except asyncio.CancelledError:raise
        except Exception:log.exception('Response coordination worker failed')
        await asyncio.sleep(10)
