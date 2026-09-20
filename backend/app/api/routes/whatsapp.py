import uuid,secrets
from typing import Optional, Literal
from fastapi import APIRouter,Depends,HTTPException,Header,Request
from pydantic import BaseModel,Field,field_validator
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.location import Location
from app.core.config import settings
from app.services.whatsapp import WhatsAppRecipient,WhatsAppDelivery,configuration,now,RecipientLanguage,recipient_language

from app.core.admin_auth import authenticated

def authorize(request: Request, x_operations_key: str=Header(default='')):
    if authenticated(request):return
    if not settings.OPERATIONS_API_KEY:raise HTTPException(503,'Set OPERATIONS_API_KEY on the backend to manage WhatsApp recipients')
    if not secrets.compare_digest(x_operations_key,settings.OPERATIONS_API_KEY):raise HTTPException(401,'Sign in as administrator in Settings > WhatsApp crisis alerts')

router=APIRouter(prefix='/whatsapp',tags=['WhatsApp'])
class RecipientInput(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    phone:str=Field(pattern=r'^\+[1-9][0-9]{7,14}$')
    location_id:Optional[str]=None
    consent_reference:str=Field(min_length=5,max_length=300)
    language:Literal['en','hi','as','bn']='en'
    opted_in:bool
    @field_validator('opted_in')
    @classmethod
    def consent(cls,value):
        if not value:raise ValueError('Recipient opt-in is required')
        return value

@router.get('/status')
def status():return configuration()

@router.get('/recipients',dependencies=[Depends(authorize)])
def recipients(db:Session=Depends(get_db)):
    return [{'id':r.id,'name':r.name,'phone':r.phone,'location_id':r.location_id,'active':r.active,'opted_in_at':r.opted_in_at,'language':recipient_language(db,r.id)} for r in db.query(WhatsAppRecipient).order_by(WhatsAppRecipient.name).all()]

@router.post('/recipients',dependencies=[Depends(authorize)],status_code=201)
def register(data:RecipientInput,db:Session=Depends(get_db)):
    if data.location_id and not db.get(Location,data.location_id):raise HTTPException(404,'Location not found')
    if db.query(WhatsAppRecipient).filter_by(phone=data.phone).first():raise HTTPException(409,'Number already registered; remove it before registering fresh consent')
    row=WhatsAppRecipient(id=str(uuid.uuid4()),name=data.name,phone=data.phone,location_id=data.location_id or None,consent_reference=data.consent_reference,opted_in_at=now(),active=True)
    db.add(row);db.add(RecipientLanguage(recipient_id=row.id,language=data.language));db.commit();return {'id':row.id,'active':True}

@router.delete('/recipients/{recipient_id}',dependencies=[Depends(authorize)])
def remove(recipient_id:str,db:Session=Depends(get_db)):
    row=db.get(WhatsAppRecipient,recipient_id)
    if not row:raise HTTPException(404,'Recipient not found')
    db.query(WhatsAppDelivery).filter(WhatsAppDelivery.recipient_id==row.id,WhatsAppDelivery.status.in_(['PENDING','RETRY'])).update({'status':'CANCELLED'},synchronize_session=False)
    preference=db.get(RecipientLanguage,recipient_id)
    if preference:db.delete(preference)
    db.delete(row);db.commit();return {'removed':recipient_id}

@router.get('/deliveries',dependencies=[Depends(authorize)])
def deliveries(db:Session=Depends(get_db)):
    return [{'id':r.id,'alert_id':r.alert_id,'recipient_name':(db.get(WhatsAppRecipient,r.recipient_id).name if db.get(WhatsAppRecipient,r.recipient_id) else 'Removed recipient'),'severity':r.severity,'language':r.payload.get('_language','en'),'status':r.status,'attempts':r.attempts,'twilio_sid':r.twilio_sid,'error':r.error,'created_at':r.created_at} for r in db.query(WhatsAppDelivery).order_by(WhatsAppDelivery.created_at.desc()).limit(100).all()]
