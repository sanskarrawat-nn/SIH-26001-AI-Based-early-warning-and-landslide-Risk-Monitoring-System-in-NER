import uuid
from datetime import timedelta
import pytest
from app.core.access import UserRole,COOKIE
from app.services.dispatch import User,Session,Attempt,Team,Incident,now,stamp
from app.models.location import Location
from app.api.routes.operations import FieldReport
from app.core.config import settings

@pytest.fixture(autouse=True)
def role_env(monkeypatch,db_session):
    monkeypatch.setenv('RBAC_ENABLED','true');monkeypatch.setattr(settings,'OPERATIONS_API_KEY','role-test-admin')
    yield
    db_session.rollback()
    for model in [UserRole,Session,Attempt,User,Incident,Team]:db_session.query(model).delete()
    db_session.query(FieldReport).delete();db_session.commit()
ADMIN={'X-Operations-Key':'role-test-admin'}
PASSWORD='Example-test-password-987'
def add(c,role,name=None,team_id=''):
    name=name or role+'test'
    r=c.post('/api/access/users',headers=ADMIN,json={'username':name,'name':name,'role':role,'team_id':team_id,'password':PASSWORD});assert r.status_code==201,r.text;return r.json()
def login(c,role,name=None):
    r=c.post('/api/access/login',json={'username':name or role+'test','password':PASSWORD,'role':role});assert r.status_code==200,r.text;return r
def team(db,kind):
    t=Team(id=str(uuid.uuid4()),data={'name':'Exercise '+kind,'kind':kind,'active':True,'coverage':['*'],'latitude':26,'longitude':91,'phone':'+15005550006','channels':[],'availability':'AVAILABLE','updated_at':stamp(),'personnel':5,'ambulances':1,'beds':8,'equipment':''});db.add(t);db.commit();return t
def report(db):
    loc=db.query(Location).first();return {'id':str(uuid.uuid4()),'location_id':loc.location_id,'officer':'Forged name','category':'crack','severity':'MODERATE','latitude':26,'longitude':91,'notes':'Exercise observation only','observed_at':stamp()}
@pytest.mark.parametrize('role,kind',[('admin',None),('coordinator',None),('field',None),('public',None),('rescue','RESCUE'),('medical','HOSPITAL'),('police','POLICE')])
def test_login_roles_and_wrong_portal(client,db_session,role,kind):
    t=team(db_session,kind) if kind else None;add(client,role,team_id=t.id if t else '')
    r=client.post('/api/access/login',json={'username':role+'test','password':PASSWORD,'role':'public' if role!='public' else 'admin'});assert r.status_code==401
    r=login(client,role);assert client.get('/api/access/session').json()['role']==role
    assert 'HttpOnly' in r.headers['set-cookie'] and 'SameSite=lax' in r.headers['set-cookie']
    assert client.get('/api/access/session').headers['cache-control']=='no-store'
    assert client.post('/api/access/logout',json={}).status_code==200
    assert client.get('/api/access/session').json()['role']=='guest'
@pytest.mark.parametrize('role',['public','field','rescue','medical','police','coordinator'])
def test_no_admin_escalation(client,db_session,role):
    kind={'rescue':'RESCUE','medical':'HOSPITAL','police':'POLICE'}.get(role);t=team(db_session,kind) if kind else None
    add(client,role,team_id=t.id if t else '');login(client,role)
    for path in ['/api/access/users','/api/whatsapp/recipients','/api/readiness/models']:assert client.get(path).status_code==403,(role,path)
    assert client.post('/api/access/users',json={'username':'intruder','name':'Intruder','role':'admin','password':PASSWORD}).status_code==403
    assert client.put('/api/settings/thresholds',json={}).status_code==403
    if role=='coordinator':assert client.get('/api/dispatch/users').status_code==403

def test_guest_and_csrf(client):
    assert client.get('/api/locations').status_code==200
    for path in ['/api/operations/reports','/api/access/reports','/api/access/users']:assert client.get(path).status_code==401
    for path in ['/api/predict','/api/locations']:assert client.post(path,json={}).status_code==401
    assert client.post('/api/access/login',headers={'Origin':'https://evil.example'},json={'username':'test','password':'test','role':'admin'}).status_code==403

def test_owned_report_privacy(client,db_session):
    a=add(client,'public','personone');add(client,'public','persontwo');login(client,'public','personone')
    p=report(db_session);r=client.post('/api/access/reports',json=p);assert r.status_code==201,r.text
    assert client.post('/api/access/reports',json=p).status_code==201
    row=db_session.get(FieldReport,p['id']);assert row.data['officer']=='personone' and row.data['owner_user_id']==a['id']
    assert len(client.get('/api/access/reports').json())==1
    assert client.get('/api/operations/reports/'+p['id']).status_code==403
    assert client.get('/api/dispatch/incidents').status_code==403
    client.post('/api/access/logout',json={});login(client,'public','persontwo')
    assert client.get('/api/access/reports').json()==[]
    assert client.patch('/api/access/reports/'+p['id'],json={'notes':'Hijacked report'}).status_code==404
    assert client.post('/api/access/reports',json=p).status_code==409

def test_coordinator_workflow(client,db_session):
    add(client,'coordinator');login(client,'coordinator')
    for path in ['/api/operations/reports','/api/dispatch/teams','/api/dispatch/incidents']:assert client.get(path).status_code==200
    assert client.post('/api/dispatch/users',json={'username':'intruder','name':'Intruder','team_id':'none','password':PASSWORD}).status_code==403
    loc=db_session.query(Location).first()
    r=client.post('/api/dispatch/incidents',json={'id':str(uuid.uuid4()),'title':'Exercise draft','location_id':loc.location_id,'latitude':26,'longitude':91,'kind':'PRECAUTIONARY_WARNING','severity':'HIGH','description':'Exercise only not an emergency','drill':True});assert r.status_code==201,r.text

def test_named_admin_legacy_protected_routes(client):
    add(client,'admin');login(client,'admin')
    assert client.get('/api/auth/session').json()['authenticated'] is True
    for p in ['/api/whatsapp/recipients','/api/readiness/models','/api/access/users']:assert client.get(p).status_code==200

def test_disable_revokes_session(client):
    u=add(client,'field');login(client,'field');token=client.cookies.get(COOKIE);client.cookies.clear()
    r=client.put('/api/access/users/'+u['id'],headers=ADMIN,json={'role':'public','active':False});assert r.status_code==200,r.text
    client.cookies.set(COOKIE,token);assert client.get('/api/access/session').json()['role']=='guest'
    assert client.get('/api/access/reports').status_code==401

def test_password_change(client):
    add(client,'field');login(client,'field')
    assert client.post('/api/access/password',json={'current_password':'wrong','new_password':PASSWORD+'new'}).status_code==401
    assert client.post('/api/access/password',json={'current_password':PASSWORD,'new_password':PASSWORD+'new'}).status_code==200
    assert client.get('/api/access/session').json()['role']=='guest'

def test_no_legacy_login_bypass(client,db_session):
    t=team(db_session,'POLICE');add(client,'police',team_id=t.id)
    assert client.post('/api/dispatch/login',json={'username':'policetest','password':PASSWORD}).status_code==401

def test_team_validation_and_disable(client,db_session):
    t=team(db_session,'RESCUE')
    r=client.post('/api/access/users',headers=ADMIN,json={'username':'medicaluser','name':'Medical User','role':'medical','team_id':t.id,'password':PASSWORD});assert r.status_code==422
    add(client,'rescue',team_id=t.id);login(client,'rescue');t.data={**t.data,'active':False};db_session.commit()
    assert client.get('/api/access/session').json()['role']=='guest'
    assert client.get('/api/dispatch/incidents').status_code==401

def test_expired_session(client,db_session):
    u=add(client,'field');login(client,'field');s=db_session.query(Session).filter_by(user_id=u['id']).first();s.expires=now()-timedelta(seconds=1);db_session.commit()
    assert client.get('/api/access/session').json()['role']=='guest'

def test_throttled_login(client):
    for _ in range(10):assert client.post('/api/access/login',json={'username':'missing','password':'wrong','role':'admin'}).status_code==401
    assert client.post('/api/access/login',json={'username':'missing','password':'wrong','role':'admin'}).status_code==429

def test_public_warning_redaction(client):
    add(client,'public');login(client,'public')
    assert client.get('/api/alerts').status_code==403
    r=client.get('/api/access/warnings');assert r.status_code==200
    for a in r.json():assert not {'resolution_notes','acknowledged_by','resolved_by'}&a.keys()

def test_field_assignment_updates_without_review_rights(client,db_session):
    u=add(client,'field');p=report(db_session)
    row=FieldReport(id=p['id'],data={**p,'status':'VERIFIED','assigned_to':u['username']});db_session.add(row);db_session.commit();login(client,'field')
    mine=client.get('/api/access/reports').json();assert len(mine)==1 and mine[0]['is_assigned'] and not mine[0]['is_owner']
    assert client.patch('/api/access/reports/'+p['id'],json={'notes':'Replace other author'}).status_code==404
    r=client.post('/api/access/reports/'+p['id']+'/updates',json={'notes':'Exercise field inspection completed'});assert r.status_code==200,r.text
    db_session.refresh(row);assert row.data['status']=='VERIFIED' and len(row.data['field_updates'])==1
    assert client.patch('/api/operations/reports/'+p['id'],json={'status':'RESOLVED'}).status_code==403

@pytest.mark.parametrize('role,kind',[('rescue','RESCUE'),('medical','AMBULANCE'),('police','POLICE')])
def test_new_responder_assignment_scope(client,db_session,role,kind):
    from test_dispatch import incident,assign
    t=team(db_session,kind);other=team(db_session,'RESCUE');add(client,role,team_id=t.id)
    i,_=incident(client,ADMIN,db_session);i=assign(client,ADMIN,i,{'id':t.id}).json()
    foreign,_=incident(client,ADMIN,db_session);assign(client,ADMIN,foreign,{'id':other.id})
    login(client,role)
    assert len(client.get('/api/dispatch/incidents').json())==1
    assert client.get('/api/dispatch/incidents/'+foreign['id']).status_code==403
    assert client.post('/api/dispatch/incidents/'+i['id']+'/assign',json={'version':i['version'],'team_id':other.id,'task':'Exercise task','approval_reason':'Exercise approved','approved':True}).status_code==403
    r=client.post('/api/dispatch/incidents/'+i['id']+'/assignments/'+i['assignments'][0]['id'],json={'version':i['version'],'status':'ACCEPTED','note':'Exercise accepted'});assert r.status_code==200,r.text
    assert client.get('/api/dispatch/my-team').json()['id']==t.id

def test_bootstrap_admin_role_login(client,monkeypatch,tmp_path):
    monkeypatch.setenv('ADMIN_USERNAME','bootstrapuser');monkeypatch.setenv('ADMIN_PASSWORD',PASSWORD);monkeypatch.setenv('ADMIN_SESSION_DB',str(tmp_path/'sessions.db'))
    r=client.post('/api/access/login',json={'username':'bootstrapuser','password':PASSWORD,'role':'admin'});assert r.status_code==200,r.text
    assert client.get('/api/access/session').json()['role']=='admin'
    assert client.get('/api/access/users').status_code==200
    client.post('/api/access/logout',json={});assert client.get('/api/access/session').json()['role']=='guest'

def test_email_login_identifier(client):
    add(client,'public','person.demo+ews@example.com')
    r=client.post('/api/access/login',json={'username':'PERSON.DEMO+EWS@EXAMPLE.COM','password':PASSWORD,'role':'public'})
    assert r.status_code==200,r.text
    assert client.get('/api/access/session').json()['role']=='public'

def test_invalid_email_identifier_rejected(client):
    r=client.post('/api/access/users',headers=ADMIN,json={'username':'bad email@example','name':'Test user','role':'public','password':PASSWORD})
    assert r.status_code==422
