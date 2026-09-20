import asyncio, uuid
from datetime import datetime, timedelta, timezone
import httpx, pytest
from app.core.config import settings
from app.services.readiness import build_outlook, evaluate
from app.services.whatsapp import WhatsAppRecipient, configuration, now
from app.services.messaging import ChannelPreference, Delivery, send
from app.models.location import Location
from app.api.routes.operations import FieldReport

def forecast():
    anchor=datetime(2026,9,15,12,tzinfo=timezone.utc)
    times=[anchor+timedelta(hours=i) for i in range(-24,25)]
    return anchor,{'hourly':{'time':[t.strftime('%Y-%m-%dT%H:%M') for t in times], 'precipitation':[1 if t<=anchor else 2 for t in times], 'soil_moisture_0_to_1cm':[.4]*len(times)}}
def test_outlook_windows_and_no_alerts():
    anchor,data=forecast();r=build_outlook(data,'site',anchor)
    assert r['recent_24h_mm']==24
    assert [w['forecast_rain_mm'] for w in r['windows']]==[6,12,24,48]
    assert r['windows'][0]['rolling_24h_mm']==27
    assert r['automatic_alerts'] is False
@pytest.mark.parametrize('bad',[None,float('nan'),-1,501])
def test_outlook_rejects_invalid_rain(bad):
    anchor,data=forecast();data['hourly']['precipitation'][-1]=bad
    with pytest.raises(ValueError):build_outlook(data,'site',anchor)
def case():
    return dict(case_id='one',location_id='site',source='reviewed archive',model_version='hash',verified=True,issued_at='2025-06-01T00:00:00Z',inputs_available_at='2025-06-01T00:00:00Z',window_end='2025-06-01T06:00:00Z',outcome_observed_until='2025-06-01T06:00:00Z',event_at='2025-06-01T04:00:00Z',probability=.9,rainfall_24h_mm=120)
def test_replay_metrics_and_baseline():
    a=case();b={**a,'case_id':'two','event_at':None,'probability':.8,'rainfall_24h_mm':10}
    r=evaluate([a,b]);assert r['model']['precision']==.5
    assert r['baseline']['precision']==1
    assert r['mean_detected_lead_hours']==4
    assert r['brier_score']==pytest.approx(.325)
@pytest.mark.parametrize('change',[{'inputs_available_at':'2025-06-01T01:00:00Z'},{'outcome_observed_until':'2025-06-01T05:00:00Z'},{'verified':False},{'probability':float('nan')},{'event_at':'2025-06-01T00:00:00Z'}])
def test_replay_rejects_bad_evidence(change):
    with pytest.raises(ValueError):evaluate([{**case(),**change}])
def test_replay_duplicate_cases():
    with pytest.raises(ValueError):evaluate([case(),case()])
def admin(monkeypatch):
    monkeypatch.setattr(settings,'OPERATIONS_API_KEY','test-private-key')
    return {'X-Operations-Key':'test-private-key'}
def test_sensor_token_idempotence_validation_revoke(client,db_session,monkeypatch):
    headers=admin(monkeypatch);loc=db_session.query(Location).first();before=dict(loc.latest_measurements or {})
    created=client.post('/api/readiness/devices',headers=headers,json={'name':'Test gauge','location_id':loc.location_id,'kind':'soil_moisture','calibration_reference':'bench calibration'})
    assert created.status_code==200,created.text
    d=created.json();payload={'device_id':d['id'],'sequence_id':'one','observed_at':datetime.now(timezone.utc).isoformat(),'value':40,'unit':'percent'}
    assert client.post('/api/readiness/sensor-ingest',json=payload).status_code==401
    h={'X-Sensor-Key':d['token']}
    assert client.post('/api/readiness/sensor-ingest',headers=h,json=payload).json()['duplicate'] is False
    assert client.post('/api/readiness/sensor-ingest',headers=h,json=payload).json()['duplicate'] is True
    assert client.post('/api/readiness/sensor-ingest',headers=h,json={**payload,'value':50}).status_code==409
    assert client.post('/api/readiness/sensor-ingest',headers=h,json={**payload,'sequence_id':'two','unit':'mm'}).status_code==422
    assert client.post('/api/readiness/devices/'+d['id']+'/revoke',headers=headers).status_code==200
    assert client.post('/api/readiness/sensor-ingest',headers=h,json=payload).status_code==401
    db_session.refresh(loc);assert loc.latest_measurements==before

def test_review_audit_and_stale_decision(client,db_session,monkeypatch):
    h=admin(monkeypatch);ident=str(uuid.uuid4());db_session.add(FieldReport(id=ident,data={'status':'SUBMITTED','updated_at':'old','photo':None}));db_session.commit()
    payload={'status':'VERIFIED','reason':'Verified by field inspection','expected_updated_at':'old'}
    response=client.post('/api/readiness/reports/'+ident+'/review',headers=h,json=payload)
    assert response.status_code==200,response.text
    assert response.json()['status']=='VERIFIED'
    assert client.post('/api/readiness/reports/'+ident+'/review',headers=h,json=payload).status_code==409
    assert client.get('/api/readiness/audit/'+ident,headers=h).json()[0]['action']=='report_reviewed'
def test_sensitive_routes_require_auth(client):
    for p in ['devices','models','evaluations','audit/private']:
        assert client.get('/api/readiness/'+p).status_code in (401,503)
    assert client.get('/api/messaging/recipients').status_code in (401,503)
def test_whatsapp_configuration_does_not_require_operations_key(monkeypatch):
    for key in ['TWILIO_ACCOUNT_SID','TWILIO_AUTH_TOKEN','TWILIO_WHATSAPP_FROM','TWILIO_CONTENT_SID']:monkeypatch.setattr(settings,key,'configured')
    monkeypatch.setattr(settings,'OPERATIONS_API_KEY','')
    assert configuration()['configured'] is True

def test_sms_and_whatsapp_independent_failure(db_session,monkeypatch):
    for k,v in {'SMS_ENABLED':True,'WHATSAPP_ENABLED':True,'TWILIO_ACCOUNT_SID':'ACtest','TWILIO_AUTH_TOKEN':'test','TWILIO_SMS_FROM':'+15005550006','TWILIO_WHATSAPP_FROM':'+15005550006','TWILIO_TEST_CONTENT_SID':'HXtest'}.items():monkeypatch.setattr(settings,k,v)
    ident=str(uuid.uuid4());db_session.add(WhatsAppRecipient(id=ident,name='Test only',phone='+1500555'+str(uuid.uuid4().int)[:6],active=True,opted_in_at=now(),consent_reference='test consent'));db_session.add(ChannelPreference(recipient_id=ident,whatsapp=True,sms=True,sms_consent_reference='test consent'))
    ids=[]
    for ch in ['whatsapp','sms']:
        i=str(uuid.uuid4());ids.append(i);db_session.add(Delivery(id=i,event_id='TEST-'+str(uuid.uuid4()),recipient_id=ident,channel=ch,data={'test':True,'body':'TEST ONLY'}))
    db_session.commit();calls=[]
    def mock(request):
        body=request.content.decode();calls.append(body)
        if 'ContentSid' in body:return httpx.Response(400,json={'code':21654,'message':'Template required'})
        return httpx.Response(201,json={'sid':'SMtest','status':'queued'})
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(mock)) as c:
            for i in ids:await send(db_session,i,c)
    asyncio.run(exercise())
    assert db_session.get(Delivery,ids[0]).status=='FAILED'
    assert db_session.get(Delivery,ids[1]).status=='QUEUED'
    assert len(calls)==2

def test_test_notification_consent_and_idempotency(client,db_session,monkeypatch):
    h=admin(monkeypatch)
    for k,v in {'SMS_ENABLED':True,'TWILIO_ACCOUNT_SID':'ACtest','TWILIO_AUTH_TOKEN':'test','TWILIO_SMS_FROM':'+15005550006'}.items():monkeypatch.setattr(settings,k,v)
    ident=str(uuid.uuid4());db_session.add(WhatsAppRecipient(id=ident,name='Test only',phone='+1500555'+str(uuid.uuid4().int)[:6],active=True,opted_in_at=now(),consent_reference='test consent'));db_session.commit()
    payload={'recipient_id':ident,'request_id':str(uuid.uuid4()),'channels':['sms'],'confirmed_test':True}
    assert client.post('/api/messaging/test',headers=h,json=payload).status_code==422
    assert client.put('/api/messaging/recipients/'+ident,headers=h,json={'sms':True,'sms_consent_reference':'Recorded test consent'}).status_code==200
    first=client.post('/api/messaging/test',headers=h,json=payload);assert first.status_code==200,first.text
    second=client.post('/api/messaging/test',headers=h,json=payload);assert second.json()['duplicate'] is True
    assert first.json()['queued']==second.json()['queued']

@pytest.fixture(autouse=True)
def cleanup_new_test_recipients(db_session):
    yield
    db_session.rollback()
    for r in db_session.query(WhatsAppRecipient).filter_by(name='Test only').all():
        db_session.query(Delivery).filter_by(recipient_id=r.id).delete()
        db_session.query(ChannelPreference).filter_by(recipient_id=r.id).delete()
        db_session.delete(r)
    db_session.commit()


def test_model_registry_integrity_and_inference(tmp_path,monkeypatch):
    import shutil
    from pathlib import Path
    from app.services.model_registry import digest, activate, active_path
    source=Path(settings.MODEL_DIR)/settings.MODEL_FILE_NAME
    target=tmp_path/settings.MODEL_FILE_NAME;shutil.copy2(source,target)
    monkeypatch.setattr(settings,'MODEL_DIR',str(tmp_path))
    sha=digest(target);assert activate(sha)==sha
    assert Path(active_path())==target
    target.write_bytes(b'changed')
    with pytest.raises(ValueError,match='integrity'):active_path()


def test_model_promotion_requires_evidence(client,monkeypatch):
    h=admin(monkeypatch);response=client.get('/api/readiness/models',headers=h)
    assert response.status_code==200,response.text
    sha=response.json()['active']
    result=client.post('/api/readiness/models/activate',headers=h,json={'model_id':sha,'expected_active':sha,'reason':'Reviewed by test operator'})
    assert result.status_code==422
