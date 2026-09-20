import asyncio,copy,uuid
from datetime import timedelta
import httpx,pytest
from app.core.config import settings
from app.models.location import Location
from app.services.dispatch import Team,Incident,User,Session,Attempt,Message,Shelter,now,escalate,send_one
@pytest.fixture(autouse=True)
def isolation(db_session,monkeypatch):
    monkeypatch.setenv('DISPATCH_MESSAGING_ENABLED','false')
    yield
    db_session.rollback()
    for m in [Message,Session,Attempt,User,Incident,Team,Shelter]:db_session.query(m).delete()
    db_session.commit()
@pytest.fixture
def h(monkeypatch):
    monkeypatch.setattr(settings,'OPERATIONS_API_KEY','dispatch-test-key');return {'X-Operations-Key':'dispatch-test-key'}
def team(c,h,**kw):
    d=dict(name='Exercise rescue',kind='RESCUE',coverage=['*'],phone='+15005550006',channels=['sms','whatsapp'],consent_reference='Test fixture consent',latitude=26,longitude=91,availability='AVAILABLE',personnel=4,ambulances=1,beds=0)
    r=c.post('/api/dispatch/teams',headers=h,json={**d,**kw});assert r.status_code==201,r.text;return r.json()
def incident(c,h,db,**kw):
    loc=db.query(Location).first();d=dict(id=str(uuid.uuid4()),title='Exercise incident',location_id=loc.location_id,latitude=loc.latitude,longitude=loc.longitude,kind='PRECAUTIONARY_WARNING',severity='HIGH',description='EXERCISE ONLY no real emergency',drill=True,ack_minutes=1);d.update(kw)
    r=c.post('/api/dispatch/incidents',headers=h,json=d);assert r.status_code==201,r.text;return r.json(),d
def assign(c,h,i,t,**kw):
    return c.post('/api/dispatch/incidents/'+i['id']+'/assign',headers=h,json={'version':i['version'],'team_id':t['id'],'task':'Exercise inspection','approval_reason':'Coordinator approves exercise','approved':True,**kw})
def progress(c,h,i,s):
    r=c.post(f'/api/dispatch/incidents/{i["id"]}/assignments/{i["assignments"][0]["id"]}',headers=h,json={'version':i['version'],'status':s,'note':'Exercise status update','eta_minutes':10});assert r.status_code==200,r.text;return r.json()
def send_all(db,handler=None):
    def fail(request):raise AssertionError('External request forbidden')
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler or fail)) as c:
            for m in db.query(Message).all():await send_one(db,m.id,c)
    asyncio.run(run())
def create_user(c,h,t):
    r=c.post('/api/dispatch/users',headers=h,json={'username':'responder1','name':'Demo responder','team_id':t['id'],'password':'Demo-password-1234'});assert r.status_code==201,r.text;return r.json()
def login(c):
    r=c.post('/api/dispatch/login',json={'username':'responder1','password':'Demo-password-1234'});assert r.status_code==200,r.text

def test_dispatch_auth_and_csrf(client,h):
    for p in ['teams','users','incidents','shelters','config']:assert client.get('/api/dispatch/'+p).status_code==401
    assert client.post('/api/dispatch/logout',headers={'Origin':'https://untrusted.example'},json={}).status_code==403
    assert client.get('/api/dispatch/session').json()['role']=='guest'
    assert client.get('/api/dispatch/teams',headers=h).headers['cache-control']=='no-store'

def test_draft_idempotency_approval_and_duplicate_dispatch(client,h,db_session):
    t=team(client,h);i,p=incident(client,h,db_session)
    assert client.post('/api/dispatch/incidents',headers=h,json=p).json()['id']==i['id']
    assert client.post('/api/dispatch/incidents',headers=h,json={**p,'title':'Different incident'}).status_code==409
    assert db_session.query(Message).count()==0
    assert assign(client,h,i,t,approved=False).status_code==422
    r=assign(client,h,i,t);assert r.status_code==200,r.text
    assert db_session.query(Message).count()==2
    assert assign(client,h,r.json(),t).status_code==409

def test_drill_no_external_send_and_no_auto_acceptance(client,h,db_session):
    t=team(client,h);i,_=incident(client,h,db_session);assign(client,h,i,t);send_all(db_session)
    assert {m.status for m in db_session.query(Message)}=={'SIMULATED'}
    assert db_session.get(Incident,i['id']).data['assignments'][0]['status']=='AWAITING'

def test_coverage_stale_and_unavailable_team(client,h,db_session):
    t=team(client,h,coverage=['OTHER']);i,_=incident(client,h,db_session);assert assign(client,h,i,t).status_code==422
    row=db_session.get(Team,t['id']);row.data={**row.data,'coverage':['*'],'updated_at':(now()-timedelta(days=1)).isoformat()+'Z'};db_session.commit();assert assign(client,h,i,t).status_code==422

def test_responder_ownership_progress_and_revocation(client,h,db_session):
    t=team(client,h);other=team(client,h,name='Other team');u=create_user(client,h,t)
    i,_=incident(client,h,db_session);i=assign(client,h,i,t).json();foreign,_=incident(client,h,db_session);assign(client,h,foreign,other)
    login(client);assert len(client.get('/api/dispatch/incidents').json())==1
    assert client.get('/api/dispatch/incidents/'+foreign['id']).status_code==403
    assert client.get('/api/dispatch/teams').status_code==403
    assert assign(client,{},i,other).status_code==403
    mt=client.get('/api/dispatch/my-team').json()
    assert client.post('/api/dispatch/my-team/availability',json={'version':mt['version'],'availability':'BUSY','personnel':2,'ambulances':0,'beds':0}).status_code==200
    for s in ['ACCEPTED','EN_ROUTE','ARRIVED','COMPLETED']:i=progress(client,{},i,s)
    assert i['assignments'][0]['completed_at']
    assert client.put('/api/dispatch/users/'+u['id'],headers=h,json={'active':False}).status_code==200
    assert client.get('/api/dispatch/session').json()['role']=='guest'

def test_invalid_transition_and_stale_write(client,h,db_session):
    t=team(client,h);i,_=incident(client,h,db_session);i=assign(client,h,i,t).json();path=f'/api/dispatch/incidents/{i["id"]}/assignments/{i["assignments"][0]["id"]}'
    assert client.post(path,headers=h,json={'version':i['version'],'status':'COMPLETED','note':'Invalid jump'}).status_code==409
    i=progress(client,h,i,'ACCEPTED')
    assert client.post(path,headers=h,json={'version':i['version']-1,'status':'EN_ROUTE','note':'Stale update'}).status_code==409
    send_all(db_session);assert {m.status for m in db_session.query(Message)}=={'CANCELLED'}

def test_reminder_escalation_once(client,h,db_session):
    t=team(client,h);b=team(client,h,name='Backup',kind='COORDINATOR');i,_=incident(client,h,db_session,backup_team_id=b['id']);assign(client,h,i,t)
    r=db_session.get(Incident,i['id']);d=copy.deepcopy(r.data);d['assignments'][0]['due_at']=(now()-timedelta(minutes=4)).isoformat()+'Z';r.data=d;db_session.commit()
    escalate(db_session);escalate(db_session)
    assert db_session.query(Message).count()==6
    assert sum(m.data['event']=='ESCALATION' and m.data['team_id']==b['id'] for m in db_session.query(Message))==2

def test_resources_close_and_export(client,h,db_session):
    t=team(client,h);i,_=incident(client,h,db_session);i=assign(client,h,i,t).json()
    def close(i):return client.post('/api/dispatch/incidents/'+i['id']+'/action',headers=h,json={'version':i['version'],'action':'CLOSE','note':'Exercise completed'})
    assert close(i).status_code==409
    r=client.post('/api/dispatch/incidents/'+i['id']+'/resources',headers=h,json={'version':i['version'],'item':'Stretcher','quantity':2,'team_id':t['id'],'note':'Exercise request'});assert r.status_code==200,r.text;i=r.json();rid=i['resources'][0]['id']
    for s in ['ALLOCATED','FULFILLED']:
        r=client.post(f'/api/dispatch/incidents/{i["id"]}/resources/{rid}',headers=h,json={'version':i['version'],'status':s,'note':'Exercise resource update'});assert r.status_code==200,r.text;i=r.json()
    for s in ['ACCEPTED','EN_ROUTE','ARRIVED','COMPLETED']:i=progress(client,h,i,s)
    assert close(i).status_code==200
    report=client.get('/api/dispatch/incidents/'+i['id']+'/export',headers=h).json();assert report['incident']['status']=='CLOSED';assert report['response_times'][0]['completed_minutes'] is not None

def test_cancellation_notifies_and_stops_original(client,h,db_session):
    t=team(client,h);i,_=incident(client,h,db_session);i=assign(client,h,i,t).json()
    r=client.post('/api/dispatch/incidents/'+i['id']+'/action',headers=h,json={'version':i['version'],'action':'CANCEL','note':'Exercise cancelled'});assert r.status_code==200,r.text
    assert r.json()['assignments'][0]['status']=='CANCELLED';send_all(db_session)
    assert {m.status for m in db_session.query(Message) if m.data['event']=='CANCELLATION'}=={'SIMULATED'}
    assert {m.status for m in db_session.query(Message) if m.data['event']=='DISPATCH'}=={'CANCELLED'}

def test_duplicate_suggestions_merge(client,h,db_session):
    i,_=incident(client,h,db_session);t,_=incident(client,h,db_session)
    assert t['id'] in [d['id'] for d in client.get('/api/dispatch/incidents/'+i['id']+'/suggestions',headers=h).json()['possible_duplicates']]
    r=client.post('/api/dispatch/incidents/'+i['id']+'/merge',headers=h,json={'version':i['version'],'target_id':t['id'],'target_version':t['version'],'reason':'Same exercise event reported twice'});assert r.status_code==200,r.text
    assert db_session.get(Incident,i['id']).data['status']=='MERGED'

def test_shelter_validation(client,h,db_session):
    loc=db_session.query(Location).first();d=dict(name='Demo shelter',location_id=loc.location_id,latitude=26,longitude=91,capacity=100,occupied=20,status='OPEN',source='Exercise update')
    assert client.post('/api/dispatch/shelters',headers=h,json={**d,'occupied':101}).status_code==422
    assert client.post('/api/dispatch/shelters',headers=h,json=d).status_code==201
    assert client.get('/api/dispatch/shelters',headers=h).json()[0]['available_spaces']==80

def test_live_channels_independent_mock_provider(client,h,db_session,monkeypatch):
    t=team(client,h);i,_=incident(client,h,db_session,drill=False);assign(client,h,i,t)
    monkeypatch.setenv('DISPATCH_MESSAGING_ENABLED','true');monkeypatch.setenv('PUBLIC_APP_URL','https://example.org');monkeypatch.setenv('TWILIO_DISPATCH_CONTENT_SID','HX'+'1'*32)
    for k,v in {'TWILIO_ACCOUNT_SID':'AC'+'1'*32,'TWILIO_AUTH_TOKEN':'fake','TWILIO_SMS_FROM':'+15005550006','TWILIO_WHATSAPP_FROM':'+15005550006'}.items():monkeypatch.setattr(settings,k,v)
    calls=[]
    def mock(req):
        calls.append(req.content.decode())
        if 'ContentSid' in calls[-1]:return httpx.Response(400,json={'code':63016,'message':'Rejected'})
        return httpx.Response(201,json={'sid':'SM'+'2'*32,'status':'queued'})
    send_all(db_session,mock);assert len(calls)==2;assert {m.status for m in db_session.query(Message)}=={'FAILED','QUEUED'}
    assert db_session.get(Incident,i['id']).data['assignments'][0]['status']=='AWAITING'

def test_login_rate_limit(client):
    for _ in range(11):r=client.post('/api/dispatch/login',json={'username':'missing','password':'incorrect'})
    assert r.status_code==429

def test_backup_can_view_escalation_but_cannot_change_other_team(client,h,db_session):
    t=team(client,h);b=team(client,h,name='Backup',kind='COORDINATOR');create_user(client,h,b)
    i,_=incident(client,h,db_session,backup_team_id=b['id']);i=assign(client,h,i,t).json();login(client)
    assert client.get('/api/dispatch/incidents/'+i['id']).status_code==403
    row=db_session.get(Incident,i['id']);d=copy.deepcopy(row.data);d['assignments'][0]['due_at']=(now()-timedelta(minutes=4)).isoformat()+'Z';row.data=d;db_session.commit();escalate(db_session)
    r=client.get('/api/dispatch/incidents/'+i['id']);assert r.status_code==200,r.text
    assert r.json()['backup_view'] is True
    assert len(client.get('/api/dispatch/incidents').json())==1
    r=client.post(f'/api/dispatch/incidents/{i["id"]}/assignments/{i["assignments"][0]["id"]}',json={'version':r.json()['version'],'status':'ACCEPTED','note':'Cannot accept other team task'})
    assert r.status_code==403

def test_notification_expires_and_contact_optout(client,h,db_session):
    t=team(client,h);i,_=incident(client,h,db_session);assign(client,h,i,t)
    for m in db_session.query(Message):m.data={**m.data,'expires_at':(now()-timedelta(minutes=1)).isoformat()+'Z'}
    db_session.commit();send_all(db_session)
    assert {m.status for m in db_session.query(Message)}=={'CANCELLED'}
