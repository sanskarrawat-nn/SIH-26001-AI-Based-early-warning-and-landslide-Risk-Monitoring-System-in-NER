import asyncio,copy,uuid
from datetime import timedelta
import httpx,pytest
from app.core.config import settings
from app.core.access import UserRole
from app.services.dispatch import Team,Incident,Message,User,Session,Attempt,now,stamp,send_one
from app.api.routes.operations import FieldReport
from app.api.routes.verified_response import VerifiedEvidence
from app.models.location import Location

ADMIN={'X-Operations-Key':'verification-test-key'}
PWD='Workflow-Test-Password-4321'
PHOTO='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aOZsAAAAASUVORK5CYII='
@pytest.fixture(autouse=True)
def setup(monkeypatch,db_session):
    monkeypatch.setenv('RBAC_ENABLED','true');monkeypatch.setenv('DISPATCH_MESSAGING_ENABLED','false');monkeypatch.setattr(settings,'OPERATIONS_API_KEY','verification-test-key')
    yield
    db_session.rollback()
    for m in (VerifiedEvidence,Message,Incident,UserRole,Session,Attempt,User,Team,FieldReport):db_session.query(m).delete()
    db_session.commit()
def user(c,role,team_id=''):
    r=c.post('/api/access/users',headers=ADMIN,json={'username':'wf_'+role,'name':'Workflow '+role,'role':role,'team_id':team_id,'password':PWD});assert r.status_code==201,r.text;return r.json()
def login(c,role):
    r=c.post('/api/access/login',json={'username':'wf_'+role,'password':PWD,'role':role});assert r.status_code==200,r.text
def teams(c,**kw):
    result=[]
    for kind in ('RESCUE','HOSPITAL','POLICE'):
        payload={'name':'Exercise '+kind,'kind':kind,'coverage':['*'],'phone':'+15005550006','channels':['sms','whatsapp'],'consent_reference':'Exercise fixture consent','latitude':26,'longitude':91,'availability':'AVAILABLE','personnel':5,'beds':3,'ambulances':1,**kw}
        r=c.post('/api/dispatch/teams',headers=ADMIN,json=payload);assert r.status_code==201,r.text;result.append(r.json())
    return result
def submit(c,db,**kw):
    loc=db.query(Location).first()
    data={'id':str(uuid.uuid4()),'location_id':loc.location_id,'officer':'Spoofed author','category':'landslide','severity':'HIGH','latitude':26,'longitude':91,'notes':'Exercise observed landslide debris at site','observed_at':stamp(),'photo':PHOTO,'site_description':'Exercise hill road near school','estimated_people':12,'reported_injured':2,'access_condition':'blocked',**kw}
    r=c.post('/api/access/reports',json=data);return r,data
def preview(c,id):
    r=c.get('/api/dispatch/reports/'+id+'/verification-preview',headers=ADMIN);assert r.status_code==200,r.text;return r.json()
def approve(c,p,**kw):
    return c.post('/api/dispatch/reports/'+p['report']['id']+'/verify-alert',headers=ADMIN,json={'preview_token':p['preview_token'],'reason':'Reviewed coordinates and attached evidence','approved':True,'drill':True,'acknowledge_gaps':True,**kw})
def prepared(c,db):
    tt=teams(c);user(c,'field');user(c,'coordinator');login(c,'field');r,data=submit(c,db);assert r.status_code==201,r.text;c.post('/api/access/logout',json={});return tt,data

def test_field_submission_requires_media_and_does_not_alert_before_verification(client,db_session):
    user(client,'field');login(client,'field');r,_=submit(client,db_session,photo=None);assert r.status_code==422
    r,data=submit(client,db_session);assert r.status_code==201
    row=db_session.get(FieldReport,data['id']);assert row.data['officer']=='Workflow field'
    assert db_session.query(Incident).count()==0 and db_session.query(Message).count()==0
    assert client.get('/api/dispatch/review-reports').status_code==403
    assert client.post('/api/dispatch/reports/'+data['id']+'/verify-alert',json={'preview_token':'0'*64,'reason':'Unauthorized attempt','approved':True}).status_code==403

def test_coordinator_verifies_and_alerts_three_groups_exactly_once(client,db_session):
    tt,data=prepared(client,db_session);login(client,'coordinator')
    p=preview(client,data['id']);assert {t['group'] for t in p['recipients']}=={'medical','rescue','police'}
    r=approve(client,p);assert r.status_code==200,r.text;i=r.json()['incident']
    assert len(i['assignments'])==3 and i['verification']['by']=='Workflow coordinator'
    assert i['site_details']['reported_injured']==2 and r.json()['queued_messages']==6
    db_session.expire_all();assert len(db_session.get(Incident,i['id']).data['assignments'])==3
    assert db_session.get(FieldReport,data['id']).data['status']=='VERIFIED'
    assert db_session.get(VerifiedEvidence,i['id']).data['photo']==PHOTO
    again=approve(client,p);assert again.status_code==200 and again.json()['duplicate']
    assert db_session.query(Incident).count()==1 and db_session.query(Message).count()==6
    assert approve(client,p,drill=False).status_code==409

def test_approval_evidence_and_stale_preview_gates(client,db_session):
    tt,data=prepared(client,db_session);p=preview(client,data['id'])
    assert approve(client,p,approved=False).status_code==422
    assert approve(client,p,acknowledge_gaps=False).status_code==422
    row=db_session.get(FieldReport,data['id']);row.data={**row.data,'notes':'New evidence details','updated_at':stamp()};db_session.commit()
    assert approve(client,p).status_code==409
    p=preview(client,data['id']);t=db_session.get(Team,tt[0]['id']);t.version+=1;db_session.commit()
    assert approve(client,p).status_code==409
    row.data={**row.data,'photo':None};db_session.commit();assert approve(client,preview(client,data['id'])).status_code==422
    assert db_session.query(Incident).count()==0

def test_coverage_excludes_unrelated_and_disabled_teams_and_shows_gaps(client,db_session):
    tt,data=prepared(client,db_session)
    t=db_session.get(Team,tt[1]['id']);t.data={**t.data,'coverage':['UNRELATED']}
    t=db_session.get(Team,tt[2]['id']);t.data={**t.data,'active':False};db_session.commit()
    p=preview(client,data['id']);assert len(p['recipients'])==1 and set(p['missing_groups'])=={'medical','police'}
    assert approve(client,p,acknowledge_gaps=False).status_code==422
    r=approve(client,p);assert r.status_code==200 and len(r.json()['incident']['assignments'])==1

def test_no_recipient_cannot_claim_alert_success(client,db_session):
    tt,data=prepared(client,db_session)
    for t in db_session.query(Team):t.data={**t.data,'active':False}
    db_session.commit();assert approve(client,preview(client,data['id'])).status_code==422
    assert db_session.query(Incident).count()==0

def test_drill_messages_are_simulated_without_provider_calls(client,db_session):
    tt,data=prepared(client,db_session);r=approve(client,preview(client,data['id']));assert r.status_code==200
    def forbidden(request):raise AssertionError('No real HTTP allowed')
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(forbidden)) as http:
            for m in db_session.query(Message).all():await send_one(db_session,m.id,http)
    asyncio.run(run());assert {m.status for m in db_session.query(Message)}=={'SIMULATED'}

def test_evidence_is_frozen_and_team_scoped(client,db_session):
    tt,data=prepared(client,db_session);user(client,'rescue',tt[0]['id']);user(client,'public')
    r=approve(client,preview(client,data['id']));iid=r.json()['incident']['id']
    original=db_session.get(FieldReport,data['id']);original.data={**original.data,'notes':'Later edit'};db_session.commit()
    login(client,'rescue');assert len(client.get('/api/dispatch/incidents').json())==1
    e=client.get('/api/dispatch/incidents/'+iid+'/evidence');assert e.status_code==200 and e.json()['notes']==data['notes']
    client.post('/api/access/logout',json={});login(client,'public');assert client.get('/api/dispatch/incidents/'+iid+'/evidence').status_code==403

def test_legacy_verification_cannot_skip_alert_workflow(client,db_session):
    tt,data=prepared(client,db_session)
    assert client.patch('/api/operations/reports/'+data['id'],headers=ADMIN,json={'status':'VERIFIED'}).status_code==409
    assert client.post('/api/readiness/reports/'+data['id']+'/review',headers=ADMIN,json={'status':'VERIFIED','reason':'Review evidence'}).status_code==409

def test_real_mode_with_disabled_messaging_stays_queued_not_delivered(client,db_session):
    tt,data=prepared(client,db_session);r=approve(client,preview(client,data['id']),drill=False);assert r.status_code==200
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: (_ for _ in ()).throw(AssertionError('No HTTP')))) as http:
            for m in db_session.query(Message).all():await send_one(db_session,m.id,http)
    asyncio.run(run());assert {m.status for m in db_session.query(Message)}=={'PENDING'}
    assert all('disabled' in m.error for m in db_session.query(Message))

def test_preexisting_manual_incident_prevents_duplicate_response(client,db_session):
    tt,data=prepared(client,db_session)
    row=db_session.get(FieldReport,data['id']);row.data={**row.data,'status':'VERIFIED'};db_session.commit()
    r=client.post('/api/dispatch/incidents',headers=ADMIN,json={'id':str(uuid.uuid4()),'title':'Existing manual response','location_id':data['location_id'],'latitude':26,'longitude':91,'kind':'REPORTED_LANDSLIDE','severity':'HIGH','description':'Existing coordinator response','report_id':data['id'],'drill':True});assert r.status_code==201,r.text
    p=preview(client,data['id']);assert p['linked_incident_id']==r.json()['id']
    assert approve(client,p).status_code==409
    assert db_session.query(Incident).count()==1 and db_session.query(Message).count()==0

def test_verified_report_routes_both_channels_with_mocked_provider(client,db_session,monkeypatch):
    import json
    from urllib.parse import parse_qs
    tt,data=prepared(client,db_session)
    monkeypatch.setenv('DISPATCH_MESSAGING_ENABLED','true');monkeypatch.setenv('PUBLIC_APP_URL','https://demo.invalid');monkeypatch.setenv('TWILIO_DISPATCH_CONTENT_SID','HX'+'0'*32)
    monkeypatch.setattr(settings,'TWILIO_ACCOUNT_SID','AC'+'0'*32);monkeypatch.setattr(settings,'TWILIO_AUTH_TOKEN','mock-token')
    monkeypatch.setattr(settings,'TWILIO_WHATSAPP_FROM','whatsapp:+15005550006');monkeypatch.setattr(settings,'TWILIO_SMS_FROM','+15005550006');monkeypatch.setattr(settings,'TWILIO_SMS_MESSAGING_SERVICE_SID','')
    r=approve(client,preview(client,data['id']),drill=False);assert r.status_code==200,r.text
    sent=[]
    def provider(request):
        body=parse_qs(request.content.decode());sent.append(body)
        if 'Body' in body:assert 'VERIFIED_REPORT' in body['Body'][0] and r.json()['incident']['id'] in body['Body'][0]
        else:
            vars=json.loads(body['ContentVariables'][0]);assert 'VERIFIED_REPORT' in vars['1'] and vars['5'].startswith('https://demo.invalid/')
        return httpx.Response(201,json={'sid':'SM'+str(len(sent)).zfill(32),'status':'queued'})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as http:
            for m in db_session.query(Message).all():await send_one(db_session,m.id,http)
    asyncio.run(run());assert len(sent)==6 and sum('Body' in b for b in sent)==3
    assert {m.status for m in db_session.query(Message)}=={'QUEUED'}
