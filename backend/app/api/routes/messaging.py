import uuid
from datetime import timedelta
from fastapi import APIRouter,Depends,HTTPException,Request
from pydantic import BaseModel,Field,ConfigDict,model_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database.session import get_db
from app.core.config import settings
from app.api.routes.whatsapp import authorize
from app.services.whatsapp import WhatsAppRecipient,WhatsAppDelivery,now
from app.services.messaging import ChannelPreference,Delivery,preferences,sms_config
from app.services.readiness import audit
from app.api.routes.readiness import actor
router=APIRouter(prefix='/messaging',tags=['Notification channels'],dependencies=[Depends(authorize)])
@router.get('/status')
def status():return {'sms':sms_config(),'whatsapp_test_configured':bool(settings.TWILIO_TEST_CONTENT_SID),'test_template_variables':{'1':'TEST ONLY','2':'test location','3':'N/A','4':'no action required','5':'test ID'}}
@router.get('/recipients')
def recipients(db:Session=Depends(get_db)):
    return [{'id':r.id,'name':r.name,'phone':r.phone,**preferences(db,r.id)} for r in db.query(WhatsAppRecipient).filter_by(active=True)]
class PreferenceInput(BaseModel):
    whatsapp:bool=True
    sms:bool=False
    sms_consent_reference:str=Field(default='',max_length=300)
    @model_validator(mode='after')
    def consent(self):
        if self.sms and len(self.sms_consent_reference.strip())<5:raise ValueError('Record explicit SMS consent before enabling SMS')
        return self
@router.put('/recipients/{recipient_id}')
def update(recipient_id:str,data:PreferenceInput,request:Request,db:Session=Depends(get_db)):
    if not db.get(WhatsAppRecipient,recipient_id):raise HTTPException(404,'Recipient not found')
    p=db.get(ChannelPreference,recipient_id)
    if not p:p=ChannelPreference(recipient_id=recipient_id);db.add(p)
    for k,v in data.model_dump().items():setattr(p,k,v)
    if not data.whatsapp:db.query(WhatsAppDelivery).filter_by(recipient_id=recipient_id).filter(WhatsAppDelivery.status.in_(['PENDING','RETRY'])).update({'status':'CANCELLED'},synchronize_session=False)
    for channel,enabled in [('sms',data.sms),('whatsapp',data.whatsapp)]:
        if not enabled:db.query(Delivery).filter_by(recipient_id=recipient_id,channel=channel).filter(Delivery.status.in_(['PENDING','RETRY'])).update({'status':'CANCELLED'},synchronize_session=False)
    audit(db,recipient_id,actor(request),'notification_preferences_changed',data.model_dump());db.commit();return data
class TestInput(BaseModel):
    recipient_id:str
    request_id:uuid.UUID
    channels:list[str]=Field(min_length=1,max_length=2)
    confirmed_test:bool=False
@router.post('/test')
def test_message(data:TestInput,request:Request,db:Session=Depends(get_db)):
    if not data.confirmed_test or set(data.channels)-{'sms','whatsapp'}:raise HTTPException(422,'Confirm a test and select SMS and/or WhatsApp')
    r=db.get(WhatsAppRecipient,data.recipient_id)
    if not r or not r.active:raise HTTPException(404,'Active registered recipient required')
    prefs=preferences(db,r.id);event='TEST-'+str(data.request_id)
    existing=db.query(Delivery).filter_by(event_id=event).all()
    if existing:
        if any(x.recipient_id!=r.id for x in existing) or {x.channel for x in existing}!=set(data.channels):raise HTTPException(409,'Test ID already used')
        return {'queued':[x.id for x in existing],'duplicate':True}
    if db.query(Delivery).filter(Delivery.recipient_id==r.id,Delivery.event_id.like('TEST-%'),Delivery.created_at>now()-timedelta(seconds=60)).first():raise HTTPException(429,'Wait one minute between tests for this recipient')
    for ch in set(data.channels):
        if not prefs[ch]:raise HTTPException(422,f'{ch} consent/channel is not enabled')
        ready=sms_config() if ch=='sms' else {'enabled':settings.WHATSAPP_ENABLED,'configured':bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_WHATSAPP_FROM and settings.TWILIO_TEST_CONTENT_SID)}
        if not ready['enabled'] or not ready['configured']:raise HTTPException(422,f'{ch} test sender/configuration is incomplete')
    ids=[]
    for ch in set(data.channels):
        ident=str(uuid.uuid4());ids.append(ident)
        db.add(Delivery(id=ident,event_id=event,recipient_id=r.id,channel=ch,data={'test':True,'body':'TEST ONLY: NEREWS notification setup check. No emergency. No action required. Reference '+event}))
    audit(db,event,actor(request),'test_notification_requested',{'recipient_id':r.id,'channels':data.channels})
    try:db.commit()
    except IntegrityError:
        db.rollback()
        existing=db.query(Delivery).filter_by(event_id=event).all()
        if existing and all(x.recipient_id==data.recipient_id for x in existing) and {x.channel for x in existing}==set(data.channels):
            return {'queued':[x.id for x in existing],'duplicate':True}
        raise HTTPException(409,'Test request conflicts with an existing request')
    return {'queued':ids,'duplicate':False,'notice':'Queued does not mean delivered'}
@router.get('/deliveries')
def deliveries(db:Session=Depends(get_db)):
    return [{'id':r.id,'channel':r.channel,'recipient_id':r.recipient_id,'event_id':r.event_id,'test':r.data.get('test',False),'status':r.status,'attempts':r.attempts,'twilio_sid':r.twilio_sid,'error':r.error,'created_at':r.created_at} for r in db.query(Delivery).order_by(Delivery.created_at.desc()).limit(100)]
