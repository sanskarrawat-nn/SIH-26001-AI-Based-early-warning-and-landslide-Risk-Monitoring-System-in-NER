import asyncio
import pytest
import httpx
from app.services.whatsapp import WhatsAppRecipient,WhatsAppDelivery,now,enqueue,send_one,poll_status
from app.models.location import Location
from app.models.alert import Alert
from app.core.config import settings

@pytest.fixture(autouse=True)
def approved_test_template(monkeypatch):
    # Sending tests model a configured deployment; no actual provider is contacted.
    monkeypatch.setattr(settings, 'TWILIO_CONTENT_SID', 'HX' + '0' * 32)


def setup(db):
    db.query(Alert).filter_by(location_id='LOC-AS-01').update({'status':'RESOLVED'},synchronize_session=False)
    loc=db.get(Location,'LOC-AS-01');loc.risk_level='SEVERE';loc.latest_measurements={'source':'REAL_SENSOR'}
    alert=Alert(alert_id='WA-TEST',location_id=loc.location_id,severity='SEVERE',status='ACTIVE',risk_score=95,title='Test',message='Test',recommended_action='Follow authorities',created_at=now())
    db.add(alert);db.add(WhatsAppRecipient(id='wa-person',name='Test',phone='+919999999999',location_id=None,active=True,opted_in_at=now(),consent_reference='test fixture'))
    db.commit();return alert

def cleanup(db):
    db.query(WhatsAppDelivery).delete();db.query(WhatsAppRecipient).delete();db.query(Alert).filter(Alert.alert_id=='WA-TEST').delete();db.commit()

def test_dedup_and_simulated_exclusion(db_session):
    db=db_session;setup(db);enqueue(db);enqueue(db)
    assert db.query(WhatsAppDelivery).filter_by(alert_id='WA-TEST').count()==1
    db.query(WhatsAppDelivery).delete();db.get(Location,'LOC-AS-01').latest_measurements={'source':'SIMULATED_SENSOR_NETWORK'};db.commit();enqueue(db)
    assert db.query(WhatsAppDelivery).filter_by(alert_id='WA-TEST').count()==0
    cleanup(db)

def test_send_template_and_no_duplicate(db_session):
    db=db_session;setup(db);enqueue(db);row=db.query(WhatsAppDelivery).filter_by(alert_id='WA-TEST').first();calls=[]
    async def handler(request):
        calls.append(request);assert b'ContentSid=' in request.content and b'ContentVariables=' in request.content
        return httpx.Response(201,json={'sid':'SMtest','status':'queued'})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await send_one(db,row.id,client);await send_one(db,row.id,client)
    asyncio.run(run());db.refresh(row);assert row.status=='QUEUED' and row.twilio_sid=='SMtest' and len(calls)==1
    cleanup(db)

def test_timeout_is_unknown_not_retried(db_session):
    db=db_session;setup(db);enqueue(db);row=db.query(WhatsAppDelivery).filter_by(alert_id='WA-TEST').first();calls=[]
    async def handler(request):calls.append(request);raise httpx.ReadTimeout('uncertain')
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await send_one(db,row.id,client);await send_one(db,row.id,client)
    asyncio.run(run());db.refresh(row);assert row.status=='UNKNOWN' and len(calls)==1;cleanup(db)

def test_optout_cancels_pending(db_session):
    db=db_session;setup(db);enqueue(db);row=db.query(WhatsAppDelivery).filter_by(alert_id='WA-TEST').first();db.get(WhatsAppRecipient,'wa-person').active=False;db.commit()
    async def handler(request):raise AssertionError('No message should be sent')
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:await send_one(db,row.id,client)
    asyncio.run(run());db.refresh(row);assert row.status=='CANCELLED';cleanup(db)

def test_rate_limit_retry_and_delivered(db_session):
    from datetime import timedelta
    db=db_session;setup(db);enqueue(db);row=db.query(WhatsAppDelivery).filter_by(alert_id='WA-TEST').first()
    async def handler(request):return httpx.Response(429)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:await send_one(db,row.id,client)
    asyncio.run(run());db.refresh(row);assert row.status=='RETRY' and row.next_attempt>now()
    row.status='SENT';row.twilio_sid='SMtest';row.updated_at=now()-timedelta(minutes=1);db.commit()
    async def delivered(request):return httpx.Response(200,json={'status':'delivered','error_code':None})
    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(delivered)) as client:await poll_status(db,client)
    asyncio.run(check());db.refresh(row);assert row.status=='DELIVERED';cleanup(db)

def test_recipient_security_consent_and_validation(client,monkeypatch):
    monkeypatch.setattr(settings,'OPERATIONS_API_KEY','wa-test-key')
    assert client.get('/api/whatsapp/recipients').status_code==401
    headers={'X-Operations-Key':'wa-test-key'}
    payload={'name':'Test Person','phone':'+918888888888','opted_in':True,'consent_reference':'Signed test form'}
    assert client.post('/api/whatsapp/recipients',headers=headers,json={**payload,'opted_in':False}).status_code==422
    assert client.post('/api/whatsapp/recipients',headers=headers,json={**payload,'phone':'123'}).status_code==422
    r=client.post('/api/whatsapp/recipients',headers=headers,json=payload);assert r.status_code==201
    assert client.post('/api/whatsapp/recipients',headers=headers,json=payload).status_code==409
    assert client.delete('/api/whatsapp/recipients/'+r.json()['id'],headers=headers).status_code==200

def test_crisis_scope_escalation_and_stale(db_session):
    from datetime import timedelta
    db=db_session;alert=setup(db)
    db.add(WhatsAppRecipient(id='wa-other',name='Other site',phone='+917777777777',location_id='LOC-ML-01',active=True,opted_in_at=now(),consent_reference='test consent'));db.commit()
    alert.severity='HIGH';db.commit();enqueue(db)
    assert db.query(WhatsAppDelivery).filter_by(alert_id='WA-TEST').count()==1
    alert.severity='SEVERE';db.commit();enqueue(db)
    assert db.query(WhatsAppDelivery).filter_by(alert_id='WA-TEST').count()==2
    db.query(WhatsAppDelivery).delete();alert.created_at=now()-timedelta(hours=1);db.commit();enqueue(db)
    assert db.query(WhatsAppDelivery).filter_by(alert_id='WA-TEST').count()==0
    cleanup(db)

def test_worker_disabled(monkeypatch):
    from app.services import whatsapp
    monkeypatch.setattr(settings,'WHATSAPP_ENABLED',False)
    def forbidden():raise AssertionError('Disabled worker must not open database or send')
    monkeypatch.setattr(whatsapp,'SessionLocal',forbidden)
    asyncio.run(whatsapp.tick())
