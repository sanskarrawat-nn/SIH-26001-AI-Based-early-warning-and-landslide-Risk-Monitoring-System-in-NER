import asyncio, base64, json
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
import httpx
import pytest
from app.api.routes.operations import FieldReport
from app.api.routes.satellite import fetch_observation, NDVI, QUALITY, SatelliteObservation, decorate
from app.services.whatsapp import RecipientLanguage, WhatsAppDelivery, LANGUAGES, content_templates, enqueue, send_one
from app.core.config import settings
from tests.test_operations import asset, report
from tests.test_whatsapp import setup, cleanup


def test_video_roundtrip_and_legacy_idempotency(client,db_session):
    old={**report(),'id':'legacy-upload-01','status':'SUBMITTED','assigned_to':''}
    db_session.add(FieldReport(id=old['id'],data=old));db_session.commit()
    assert client.post('/api/operations/reports',json={**report(),'id':old['id']}).json()['duplicate']
    encoded='data:video/mp4;base64,'+base64.b64encode(b'\x00\x00\x00\x18ftypisom'+b'\0'*16).decode()
    payload={**report(),'id':'video-report-01','video':encoded}
    assert client.post('/api/operations/reports',json=payload).status_code==201
    assert client.post('/api/operations/reports',json=payload).json()['duplicate']
    listed=next(x for x in client.get('/api/operations/reports').json() if x['id']==payload['id'])
    assert listed['has_video'] and 'video' not in listed and 'photo' not in listed
    assert client.get('/api/operations/reports/'+payload['id']).json()['video']==encoded
    assert client.post('/api/operations/reports',json={**payload,'notes':'Changed observation'}).status_code==409
    for video in ['data:text/html;base64,PGgxPg==','data:video/mp4;base64,YWJj','data:video/webm;base64,YWJj']:
        assert client.post('/api/operations/reports',json={**payload,'id':'invalid-video-01','video':video}).status_code==422
    db_session.query(FieldReport).filter(FieldReport.id.in_([old['id'],payload['id']])).delete(synchronize_session=False);db_session.commit()


def test_road_connectivity_stale_blocked_and_removed_assets(client):
    ids=[client.post('/api/operations/assets',json={**asset(),'name':name}).json()['id'] for name in ['Road start','Road middle','Road end']]
    data={'name':'Survey road','from_asset':ids[0],'to_asset':ids[1],'status':'open','source':'Officer inspection','observed_at':datetime.now(timezone.utc).isoformat()}
    r=client.post('/api/operations/roads',json=data);assert r.status_code==201
    first=r.json()['id'];data2={**data,'from_asset':ids[1],'to_asset':ids[2]}
    second=client.post('/api/operations/roads',json=data2).json()['id']
    def check():return client.get('/api/operations/roads/connectivity/check',params={'from_asset':ids[0],'to_asset':ids[2]}).json()
    assert check()['connected'] and len(check()['road_ids'])==2
    for status in ['blocked','restricted','unknown']:
        assert client.put('/api/operations/roads/'+second,json={**data2,'status':status}).status_code==200
        assert not check()['connected']
    client.put('/api/operations/roads/'+second,json={**data2,'observed_at':(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()})
    assert not check()['connected']
    assert any(r['stale'] and r['effective_status']=='unknown' for r in client.get('/api/operations/roads').json())
    assert client.post('/api/operations/roads',json={**data,'coordinates':[[181,26],[92,26]]}).status_code==422
    assert client.post('/api/operations/roads',json={**data,'to_asset':ids[0]}).status_code==422
    client.delete('/api/operations/assets/'+ids[1]);assert not check()['connected']
    for rid in [first,second]:client.delete('/api/operations/roads/'+rid)
    for aid in [ids[0],ids[2]]:client.delete('/api/operations/assets/'+aid)


def satellite_transport(quality=0):
    today=date.today().isoformat()
    def handler(request):
        if request.url.path.endswith('/dates'):return httpx.Response(200,json={'dates':[{'calendar_date':today,'modis_date':'A2026254'}]})
        band=request.url.params['band']
        return httpx.Response(200,json={'subset':[{'band':band,'calendar_date':today,'data':[7000 if band==NDVI else quality]}]})
    return httpx.MockTransport(handler)


def test_satellite_scaling_and_cloud_rejection():
    async def run(q):
        async with httpx.AsyncClient(transport=satellite_transport(q)) as client:return await fetch_observation(26.1,91.7,client)
    data=asyncio.run(run(0));assert data['ndvi']==.7 and data['source']=='NASA ORNL DAAC TESViS'
    for q in [1,2,3,-1]:
        with pytest.raises(ValueError):asyncio.run(run(q))
    data['composite_date']=(date.today()-timedelta(days=45)).isoformat();assert decorate(data)['stale']


def test_satellite_failure_preserves_existing(client,db_session,monkeypatch):
    from app.api.routes import satellite
    old={'ndvi':.5,'composite_date':(date.today()-timedelta(days=40)).isoformat(),'retrieved_at':(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()}
    db_session.add(SatelliteObservation(location_id='LOC-AS-01',data=old));db_session.commit()
    async def unavailable(*args):raise httpx.ConnectError('offline')
    original_client=httpx.AsyncClient
    monkeypatch.setattr(satellite.httpx,'AsyncClient',lambda **kwargs:original_client(transport=satellite_transport()))
    monkeypatch.setattr(satellite,'fetch_observation',unavailable)
    assert client.post('/api/operations/satellite/LOC-AS-01/refresh').status_code==502
    assert client.get('/api/operations/satellite/LOC-AS-01').json()['observation']['ndvi']==.5
    db_session.query(SatelliteObservation).delete();db_session.commit()


def test_localized_template_selection_and_missing_template(db_session,monkeypatch):
    db=db_session;setup(db);db.add(RecipientLanguage(recipient_id='wa-person',language='hi'));db.commit()
    monkeypatch.setattr(settings,'TWILIO_CONTENT_SIDS',json.dumps({'hi':'HX'+'1'*32}))
    enqueue(db);row=db.query(WhatsAppDelivery).filter_by(alert_id='WA-TEST').first();requests=[]
    async def handler(request):
        from urllib.parse import parse_qs
        body=parse_qs(request.content.decode());assert body['ContentSid']==['HX'+'1'*32]
        values=json.loads(body['ContentVariables'][0]);assert values['1']==LANGUAGES['hi']['levels']['SEVERE'] and '_language' not in values
        requests.append(request);return httpx.Response(201,json={'sid':'SMtest','status':'queued'})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:await send_one(db,row.id,client)
    monkeypatch.setattr(settings,'TWILIO_CONTENT_SIDS','{}');asyncio.run(run());db.refresh(row);assert row.status=='RETRY' and not requests and row.attempts==0
    monkeypatch.setattr(settings,'TWILIO_CONTENT_SIDS',json.dumps({'hi':'HX'+'1'*32}));row.next_attempt=datetime.utcnow();db.commit();asyncio.run(run());assert len(requests)==1
    db.query(RecipientLanguage).delete();db.commit();cleanup(db)


def test_catalogs_match_and_malformed_templates(monkeypatch):
    frontend=Path(__file__).resolve().parents[2]/'frontend/src/data/alert-languages.json'
    assert json.loads(frontend.read_text(encoding='utf-8'))==LANGUAGES
    for invalid in ['bad-json','[]','null']:
        monkeypatch.setattr(settings,'TWILIO_CONTENT_SIDS',invalid);assert isinstance(content_templates(),dict)


def test_upgrade_keeps_existing_tables_and_records():
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.orm import Session
    from app.database.base import Base
    from app.services.whatsapp import WhatsAppRecipient, recipient_language, now
    engine=create_engine('sqlite:///:memory:')
    added={'road_segments','satellite_observations','whatsapp_recipient_languages'}
    Base.metadata.create_all(engine,tables=[t for t in Base.metadata.sorted_tables if t.name not in added])
    before={name:[c['name'] for c in inspect(engine).get_columns(name)] for name in inspect(engine).get_table_names()}
    with Session(engine) as db:
        db.add(WhatsAppRecipient(id='legacy-person',name='Existing recipient',phone='+919999999991',active=True,opted_in_at=now(),consent_reference='Existing consent'))
        db.add(FieldReport(id='legacy-record',data={**report(),'id':'legacy-record','status':'VERIFIED'}));db.commit()
    Base.metadata.create_all(engine);Base.metadata.create_all(engine)
    for name,columns in before.items():assert [c['name'] for c in inspect(engine).get_columns(name)]==columns
    with Session(engine) as db:
        assert db.get(FieldReport,'legacy-record').data['status']=='VERIFIED'
        assert db.get(WhatsAppRecipient,'legacy-person').name=='Existing recipient'
        assert recipient_language(db,'legacy-person')=='en'
    assert added.issubset(set(inspect(engine).get_table_names()))
