import copy, hashlib, math, os, secrets
from datetime import timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session as DB
from sqlalchemy.exc import IntegrityError
from app.database.session import get_db
from app.core.config import settings
from app.core.admin_auth import authenticated, check_origin
from app.services.dispatch import Team,Incident,User,Session,Attempt,Message,Shelter,now,stamp,parsed,ident,render,save,entry,queue,config,password_hash,check_password
from app.services.readiness import audit
from app.api.routes.operations import FieldReport
from app.models.location import Location
from app.models.alert import Alert

router=APIRouter(prefix='/dispatch',tags=['Response coordination'])
COOKIE='ews_responder_session'
class Strict(BaseModel):model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
def principal(request:Request,db:DB):
    from app.core.access import identity, COOKIE as ROLE_COOKIE
    account=identity(request,db)
    if account:
        if account['role'] in ('admin','coordinator'):
            return {**account,'account_role':account['role'],'role':'coordinator'}
        if account['role'] in ('rescue','medical','police'):
            return {**account,'account_role':account['role'],'role':'responder'}
        raise HTTPException(403,'This role does not have response-team access')
    if request.cookies.get(ROLE_COOKIE):raise HTTPException(401,'Your session expired. Sign in again.')

    if authenticated(request):return {'role':'coordinator','name':os.getenv('ADMIN_USERNAME','administrator')}
    key=settings.OPERATIONS_API_KEY
    if key and secrets.compare_digest(request.headers.get('X-Operations-Key',''),key):return {'role':'coordinator','name':'operations-key coordinator'}
    token=request.cookies.get(COOKIE,'');s=db.get(Session,hashlib.sha256(token.encode()).hexdigest()) if token else None
    u=db.get(User,s.user_id) if s and s.expires>now() else None
    team=db.get(Team,u.team_id) if u and u.active else None
    if u and u.active and team and team.data['active']:return {'role':'responder','name':u.name,'user_id':u.id,'team_id':u.team_id}
    raise HTTPException(401,'Sign in as coordinator in Settings or use responder sign-in')
def coordinator(request:Request,db:DB=Depends(get_db)):
    p=principal(request,db)
    if p['role']!='coordinator':raise HTTPException(403,'Coordinator access required')
    return p
def record(db,model,id):
    r=db.get(model,id)
    if not r:raise HTTPException(404,'Record not found')
    return r
def backup_view(row,p):
    return p['role']=='responder' and row.data.get('backup_team_id')==p['team_id'] and any(a.get('escalated') for a in row.data['assignments'])
def incident_access(db,id,p):
    row=record(db,Incident,id)
    if p['role']!='coordinator' and not backup_view(row,p) and not any(a['team_id']==p['team_id'] for a in row.data['assignments']):raise HTTPException(403,'This incident is not assigned to your team')
    return row
def present_incident(row,p):
    d=render(row)
    d['backup_view']=backup_view(row,p)
    if p['role']!='coordinator' and not d['backup_view']:
        d['assignments']=[a for a in d['assignments'] if a['team_id']==p['team_id']]
        d['resources']=[r for r in d['resources'] if r['team_id']==p['team_id']]
        d['timeline']=[e for e in d['timeline'] if e.get('actor')==p['name'] or e['action'] in ['CREATED','CLOSE','CANCEL']]
        d.pop('approval_reason',None)
    return d

@router.get('/session')
def session(request:Request,response:Response,db:DB=Depends(get_db)):
    response.headers['Cache-Control']='no-store'
    try:return principal(request,db)
    except HTTPException:return {'role':'guest'}
class Login(Strict):
    username:str=Field(min_length=1,max_length=100)
    password:str=Field(min_length=1,max_length=512)
@router.post('/login')
def login(data:Login,request:Request,response:Response,db:DB=Depends(get_db)):
    address=request.client.host if request.client else 'unknown';key=hashlib.sha256(address.encode()).hexdigest()
    attempt=db.get(Attempt,key)
    if attempt and attempt.start<now()-timedelta(minutes=15):db.delete(attempt);db.flush();attempt=None
    if not attempt:attempt=Attempt(id=key,count=0,start=now());db.add(attempt);db.flush()
    db.query(Attempt).filter_by(id=key).update({'count':Attempt.count+1},synchronize_session=False);db.commit();db.refresh(attempt)
    if attempt.count>10:raise HTTPException(429,'Too many attempts; try again in 15 minutes')
    user=db.query(User).filter_by(username=data.username.lower().strip()).first()
    # A fixed-work dummy hash avoids skipping the password check for unknown usernames.
    valid=check_password(data.password,user.password if user else '0'*32+':'+'0'*64)
    team=db.get(Team,user.team_id) if user else None
    if not valid or not user or not user.active or not team or not team.data['active']:raise HTTPException(401,'Incorrect or disabled responder credentials')
    from app.core.access import UserRole
    if db.get(UserRole,user.id):raise HTTPException(401,'Use your dedicated role login page')
    token=secrets.token_urlsafe(48);db.add(Session(token=hashlib.sha256(token.encode()).hexdigest(),user_id=user.id,expires=now()+timedelta(hours=8)));db.commit()
    response.set_cookie(COOKIE,token,max_age=28800,httponly=True,secure=request.url.scheme=='https' or os.getenv('ADMIN_COOKIE_SECURE','').lower()=='true',samesite='lax',path='/api/dispatch')
    response.headers['Cache-Control']='no-store';return {'role':'responder','name':user.name,'team_id':user.team_id}
@router.post('/logout')
def logout(request:Request,response:Response,db:DB=Depends(get_db)):
    db.query(Session).filter_by(token=hashlib.sha256(request.cookies.get(COOKIE,'').encode()).hexdigest()).delete();db.commit();response.delete_cookie(COOKIE,path='/api/dispatch');return {'ok':True}
@router.get('/config')
def configuration(p=Depends(coordinator)):return config()

class TeamInput(Strict):
    name:str=Field(min_length=2,max_length=120)
    kind:Literal['RESCUE','HOSPITAL','AMBULANCE','POLICE','COORDINATOR']
    coverage:list[str]=Field(min_length=1,max_length=50)
    phone:str=Field(pattern=r'^\+[1-9][0-9]{7,14}$')
    channels:list[Literal['sms','whatsapp']]=Field(default_factory=list,max_length=2)
    consent_reference:str=Field(default='',max_length=300)
    latitude:float=Field(ge=-90,le=90)
    longitude:float=Field(ge=-180,le=180)
    availability:Literal['AVAILABLE','BUSY','UNAVAILABLE']='AVAILABLE'
    personnel:int=Field(default=0,ge=0,le=10000)
    ambulances:int=Field(default=0,ge=0,le=1000)
    beds:int=Field(default=0,ge=0,le=100000)
    equipment:str=Field(default='',max_length=500)
    active:bool=True
    @model_validator(mode='after')
    def consent(self):
        if self.channels and len(self.consent_reference.strip())<5:raise ValueError('Record consent for the selected notification channels')
        self.channels=sorted(set(self.channels));self.coverage=sorted(set(x.strip() for x in self.coverage if x.strip()))
        if not self.coverage:raise ValueError('Coverage site IDs required; * means all sites')
        return self
class TeamEdit(TeamInput):version:int
@router.get('/teams')
def teams(p=Depends(coordinator),db:DB=Depends(get_db)):
    return [{**render(t),'stale':now()-parsed(t.data['updated_at'])>timedelta(hours=12)} for t in db.query(Team).all()]
@router.post('/teams',status_code=201)
def create_team(data:TeamInput,p=Depends(coordinator),db:DB=Depends(get_db)):
    t=Team(id=ident(),data={**data.model_dump(),'updated_at':stamp()});db.add(t);audit(db,t.id,p['name'],'response_team_created',{'name':data.name});db.commit();return render(t)
@router.put('/teams/{id}')
def update_team(id:str,data:TeamEdit,p=Depends(coordinator),db:DB=Depends(get_db)):
    t=record(db,Team,id);save(db,t,{**data.model_dump(exclude={'version'}),'updated_at':stamp()},data.version);audit(db,id,p['name'],'response_team_updated',{'active':data.active});db.commit();return render(t)
class NewUser(Strict):
    username:str=Field(pattern=r'^[a-zA-Z0-9_.-]{3,100}$')
    name:str=Field(min_length=2,max_length=120)
    team_id:str
    password:str=Field(min_length=12,max_length=128)
@router.post('/users',status_code=201)
def create_user(data:NewUser,p=Depends(coordinator),db:DB=Depends(get_db)):
    if p.get('account_role')=='coordinator':raise HTTPException(403,'Administrator access required for accounts')
    record(db,Team,data.team_id)
    u=User(id=ident(),username=data.username.lower(),name=data.name,team_id=data.team_id,password=password_hash(data.password));db.add(u);audit(db,u.id,p['name'],'responder_created',{'username':u.username})
    try:db.commit()
    except IntegrityError:db.rollback();raise HTTPException(409,'Username already exists')
    return {'id':u.id,'username':u.username}
@router.get('/users')
def users(p=Depends(coordinator),db:DB=Depends(get_db)):
    if p.get('account_role')=='coordinator':raise HTTPException(403,'Administrator access required for accounts')
    return [{'id':u.id,'username':u.username,'name':u.name,'team_id':u.team_id,'active':bool(u.active)} for u in db.query(User).all()]
class UserEdit(Strict):
    active:bool
    password:str|None=Field(default=None,min_length=12,max_length=128)
@router.put('/users/{id}')
def edit_user(id:str,data:UserEdit,p=Depends(coordinator),db:DB=Depends(get_db)):
    if p.get('account_role')=='coordinator':raise HTTPException(403,'Administrator access required for accounts')
    u=record(db,User,id);u.active=int(data.active)
    if data.password:u.password=password_hash(data.password)
    db.query(Session).filter_by(user_id=id).delete();audit(db,id,p['name'],'responder_access_updated',{'active':data.active});db.commit();return {'ok':True}

class NewIncident(Strict):
    id:str=Field(pattern=r'^[a-f0-9-]{36}$')
    title:str=Field(min_length=5,max_length=140)
    location_id:str=Field(max_length=64)
    latitude:float=Field(ge=-90,le=90)
    longitude:float=Field(ge=-180,le=180)
    kind:Literal['PRECAUTIONARY_WARNING','REPORTED_LANDSLIDE']
    severity:Literal['LOW','MODERATE','HIGH','SEVERE']
    description:str=Field(min_length=10,max_length=2000)
    affected_people:int|None=Field(default=None,ge=0,le=10000000)
    drill:bool=True
    report_id:str|None=None
    alert_id:str|None=None
    ack_minutes:int=Field(default=5,ge=1,le=120)
    backup_team_id:str|None=None
@router.post('/incidents',status_code=201)
def create_incident(data:NewIncident,p=Depends(coordinator),db:DB=Depends(get_db)):
    submitted=data.model_dump();old=db.get(Incident,data.id)
    if old:
        if old.data['submitted']!=submitted:raise HTTPException(409,'Incident submission ID already used')
        return render(old)
    record(db,Location,data.location_id)
    if data.report_id:
        r=record(db,FieldReport,data.report_id)
        if r.data['location_id']!=data.location_id:raise HTTPException(422,'Report location does not match')
        if r.data['status'] not in ['VERIFIED','DISPATCHED','RESOLVED']:raise HTTPException(422,'Review the report before creating a linked incident')
    if data.alert_id:
        a=db.query(Alert).filter_by(alert_id=data.alert_id).first()
        if not a or a.location_id!=data.location_id:raise HTTPException(422,'Alert not found at this site')
    if data.backup_team_id:
        b=record(db,Team,data.backup_team_id)
        if b.data['kind']!='COORDINATOR' or not b.data['active']:raise HTTPException(422,'Choose an active backup coordinator')
    d={**submitted,'submitted':submitted,'created_at':stamp(),'status':'DRAFT','assignments':[],'resources':[],'timeline':[],'linked_reports':[data.report_id] if data.report_id else []}
    entry(d,p['name'],'CREATED','EXERCISE — NO REAL EMERGENCY' if data.drill else data.kind)
    row=Incident(id=data.id,data=d);db.add(row)
    try:db.commit()
    except IntegrityError:
        db.rollback();old=db.get(Incident,data.id)
        if not old or old.data['submitted']!=submitted:raise HTTPException(409,'Incident submission ID already used')
        return render(old)
    return render(row)
@router.get('/incidents')
def incidents(request:Request,db:DB=Depends(get_db)):
    p=principal(request,db);rows=db.query(Incident).all()
    return [present_incident(r,p) for r in sorted(rows,key=lambda r:r.data['created_at'],reverse=True) if p['role']=='coordinator' or backup_view(r,p) or any(a['team_id']==p['team_id'] for a in r.data['assignments'])]
@router.get('/incidents/{id}')
def get_incident(id:str,request:Request,db:DB=Depends(get_db)):
    p=principal(request,db);return present_incident(incident_access(db,id,p),p)
class Assign(Strict):
    version:int
    team_id:str
    task:str=Field(min_length=5,max_length=500)
    approval_reason:str=Field(min_length=10,max_length=1000)
    approved:bool=False
@router.post('/incidents/{id}/assign')
def assign(id:str,data:Assign,p=Depends(coordinator),db:DB=Depends(get_db)):
    row=record(db,Incident,id);t=record(db,Team,data.team_id);d=copy.deepcopy(row.data)
    if not data.approved:raise HTTPException(422,'Explicit dispatch approval required')
    if d['status'] not in ['DRAFT','ACTIVE']:raise HTTPException(409,'Incident is closed')
    if not t.data['active']:raise HTTPException(422,'Team is inactive')
    if t.data['availability']!='AVAILABLE' or now()-parsed(t.data['updated_at'])>timedelta(hours=12):raise HTTPException(422,'Refresh team availability before dispatch')
    if '*' not in t.data['coverage'] and d['location_id'] not in t.data['coverage']:raise HTTPException(422,'Team is outside this site coverage')
    if any(a['team_id']==t.id for a in d['assignments']):raise HTTPException(409,'This team already has an assignment for this incident')
    a={'id':ident(),'team_id':t.id,'team_name':t.data['name'],'task':data.task,'status':'AWAITING','assigned_at':stamp(),'due_at':(now()+timedelta(minutes=d['ack_minutes'])).isoformat()+'Z','eta_minutes':None,'updates':[]}
    d['assignments'].append(a);d['status']='ACTIVE';d['approval_reason']=data.approval_reason
    entry(d,p['name'],'DISPATCH_APPROVED',{'team':t.data['name'],'task':data.task,'reason':data.approval_reason})
    save(db,row,d,data.version);queue(db,id,d,a,t,'DISPATCH');db.commit();return render(row)
class Progress(Strict):
    version:int
    status:Literal['ACCEPTED','EN_ROUTE','ARRIVED','COMPLETED','DECLINED','UNAVAILABLE','CANCELLED']
    note:str=Field(min_length=5,max_length=1000)
    eta_minutes:int|None=Field(default=None,ge=0,le=2880)
@router.post('/incidents/{id}/assignments/{aid}')
def progress(id:str,aid:str,data:Progress,request:Request,db:DB=Depends(get_db)):
    p=principal(request,db);row=incident_access(db,id,p);d=copy.deepcopy(row.data)
    if d['status']!='ACTIVE':raise HTTPException(409,'Incident is not active')
    a=next((a for a in d['assignments'] if a['id']==aid),None)
    if not a:raise HTTPException(404,'Assignment not found')
    if p['role']!='coordinator' and a['team_id']!=p['team_id']:raise HTTPException(403,'Only your team can update this assignment')
    allowed={'AWAITING':['ACCEPTED','DECLINED','UNAVAILABLE'],'ACCEPTED':['EN_ROUTE','UNAVAILABLE'],'EN_ROUTE':['ARRIVED','UNAVAILABLE'],'ARRIVED':['COMPLETED','UNAVAILABLE']}
    if data.status=='CANCELLED':
        if p['role']!='coordinator' or a['status'] in ['COMPLETED','CANCELLED']:raise HTTPException(403,'Coordinator cancellation required')
    elif data.status not in allowed.get(a['status'],[]) and not (data.status==a['status'] and a['status'] in ['ACCEPTED','EN_ROUTE','ARRIVED']):raise HTTPException(409,'Invalid status transition')
    a['status']=data.status;a['eta_minutes']=data.eta_minutes;a['updated_at']=stamp()
    a.setdefault(data.status.lower()+'_at',stamp());a['updates'].append({'at':stamp(),'actor':p['name'],'note':data.note,'status':data.status})
    entry(d,p['name'],'TEAM_STATUS',{'team':a['team_name'],**data.model_dump(exclude={'version'})})
    save(db,row,d,data.version)
    if data.status=='CANCELLED':
        t=db.get(Team,a['team_id'])
        if t:queue(db,id,d,a,t,'CANCELLATION')
    db.commit();return present_incident(row,p)
class IncidentAction(Strict):
    version:int
    action:Literal['CLOSE','CANCEL','NOTE']
    note:str=Field(min_length=5,max_length=1000)
@router.post('/incidents/{id}/action')
def action(id:str,data:IncidentAction,p=Depends(coordinator),db:DB=Depends(get_db)):
    row=record(db,Incident,id);d=copy.deepcopy(row.data)
    if d['status'] not in ['DRAFT','ACTIVE']:raise HTTPException(409,'Incident is closed')
    if data.action=='CLOSE':
        if any(a['status'] not in ['COMPLETED','CANCELLED','DECLINED','UNAVAILABLE'] for a in d['assignments']) or any(r['status'] not in ['FULFILLED','CANCELLED'] for r in d['resources']):raise HTTPException(409,'Complete/cancel outstanding assignments and resource requests first')
        d['status']='CLOSED';d['closed_at']=stamp()
    if data.action=='CANCEL':
        d['status']='CANCELLED';d['closed_at']=stamp()
        for a in d['assignments']:
            if a['status'] not in ['COMPLETED','DECLINED','UNAVAILABLE','CANCELLED']:
                a['status']='CANCELLED'
                t=db.get(Team,a['team_id'])
                if t:queue(db,id,d,a,t,'CANCELLATION')
        for r in d['resources']:
            if r['status']!='FULFILLED':r['status']='CANCELLED'
    entry(d,p['name'],data.action,data.note);save(db,row,d,data.version);db.commit();return render(row)
class ResourceInput(Strict):
    version:int
    item:str=Field(min_length=2,max_length=120)
    quantity:int=Field(ge=1,le=10000)
    team_id:str
    note:str=Field(min_length=5,max_length=500)
@router.post('/incidents/{id}/resources')
def resource(id:str,data:ResourceInput,request:Request,db:DB=Depends(get_db)):
    p=principal(request,db);row=incident_access(db,id,p);d=copy.deepcopy(row.data)
    if d['status']!='ACTIVE':raise HTTPException(409,'Incident is not active')
    if p['role']!='coordinator' and data.team_id!=p['team_id']:raise HTTPException(403,'Only request for your own team')
    if not any(a['team_id']==data.team_id for a in d['assignments']):raise HTTPException(422,'Team must be assigned to this incident')
    r={**data.model_dump(exclude={'version'}),'id':ident(),'status':'REQUESTED','created_at':stamp()};d['resources'].append(r)
    entry(d,p['name'],'RESOURCE_REQUESTED',r);save(db,row,d,data.version);db.commit();return present_incident(row,p)
class ResourceUpdate(Strict):
    version:int
    status:Literal['ALLOCATED','FULFILLED','CANCELLED']
    note:str=Field(min_length=5,max_length=500)
@router.post('/incidents/{id}/resources/{rid}')
def resource_update(id:str,rid:str,data:ResourceUpdate,p=Depends(coordinator),db:DB=Depends(get_db)):
    row=record(db,Incident,id);d=copy.deepcopy(row.data)
    if d['status']!='ACTIVE':raise HTTPException(409,'Incident is not active')
    r=next((x for x in d['resources'] if x['id']==rid),None)
    if not r:raise HTTPException(404,'Resource request not found')
    allowed={'REQUESTED':['ALLOCATED','CANCELLED'],'ALLOCATED':['FULFILLED','CANCELLED']}
    if data.status not in allowed.get(r['status'],[]):raise HTTPException(409,'Invalid resource transition')
    r.update(status=data.status,coordinator_note=data.note,updated_at=stamp());entry(d,p['name'],'RESOURCE_UPDATED',r);save(db,row,d,data.version);db.commit();return render(row)

@router.get('/incidents/{id}/suggestions')
def suggestions(id:str,p=Depends(coordinator),db:DB=Depends(get_db)):
    row=record(db,Incident,id);d=row.data
    def distance(t):
        lat1,lat2=map(math.radians,[d['latitude'],t.data['latitude']]);dl=math.radians(t.data['longitude']-d['longitude']);a=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dl/2)**2
        return round(6371*2*math.asin(min(1,math.sqrt(a))),1)
    teams=[]
    for t in db.query(Team).all():
        if t.data['active'] and ('*' in t.data['coverage'] or d['location_id'] in t.data['coverage']):
            stale=now()-parsed(t.data['updated_at'])>timedelta(hours=12)
            teams.append({'id':t.id,'name':t.data['name'],'kind':t.data['kind'],'available':t.data['availability']=='AVAILABLE' and not stale,'stale':stale,'distance_km':distance(t),'personnel':t.data['personnel'],'ambulances':t.data['ambulances'],'beds':t.data['beds'],'equipment':t.data['equipment']})
    duplicates=[{'id':r.id,'title':r.data['title'],'status':r.data['status']} for r in db.query(Incident).all() if r.id!=id and r.data['status'] in ['DRAFT','ACTIVE'] and r.data['drill']==d['drill'] and r.data['location_id']==d['location_id'] and abs((parsed(r.data['created_at'])-parsed(d['created_at'])).total_seconds())<=86400]
    return {'teams':sorted(teams,key=lambda t:(not t['available'],t['distance_km'])),'possible_duplicates':duplicates,'notice':'Coverage and availability first; straight-line distance is not road travel time. Select the required team capability manually.'}
class Merge(Strict):
    version:int
    target_id:str
    target_version:int
    reason:str=Field(min_length=10,max_length=1000)
@router.post('/incidents/{id}/merge')
def merge(id:str,data:Merge,p=Depends(coordinator),db:DB=Depends(get_db)):
    if id==data.target_id:raise HTTPException(422,'Choose another incident')
    row=record(db,Incident,id);target=record(db,Incident,data.target_id);d=copy.deepcopy(row.data);t=copy.deepcopy(target.data)
    if d['status']!='DRAFT' or d['assignments'] or t['status'] not in ['DRAFT','ACTIVE'] or d['drill']!=t['drill'] or d['location_id']!=t['location_id']:raise HTTPException(422,'Only an undispatched draft can merge into an open incident at the same site and drill mode')
    t['linked_reports']=list(set(t['linked_reports']+d['linked_reports']));t.setdefault('merged_incidents',[]).append(id);d['status']='MERGED';d['merged_into']=target.id
    entry(d,p['name'],'MERGED',{'target':target.id,'reason':data.reason});entry(t,p['name'],'MERGED_REPORT',{'source':id,'reason':data.reason})
    save(db,row,d,data.version);save(db,target,t,data.target_version);db.commit();return render(target)
@router.get('/incidents/{id}/export')
def export(id:str,p=Depends(coordinator),db:DB=Depends(get_db)):
    row=record(db,Incident,id);d=render(row);timings=[]
    for a in d['assignments']:
        times={'team':a['team_name'],'status':a['status']}
        for key in ['accepted_at','arrived_at','completed_at']:
            times[key.replace('_at','_minutes')]=round((parsed(a[key])-parsed(a['assigned_at'])).total_seconds()/60,2) if a.get(key) else None
        timings.append(times)
    return {'incident':d,'response_times':timings,'exported_at':stamp(),'notice':'User-reported statuses and ETAs; drill records are not real response performance.'}
@router.get('/incidents/{id}/messages')
def messages(id:str,request:Request,db:DB=Depends(get_db)):
    p=principal(request,db);incident_access(db,id,p)
    return [{'id':r.id,'status':r.status,'attempts':r.attempts,'sid':r.sid,'error':r.error,**{k:v for k,v in r.data.items() if k!='phone'}} for r in db.query(Message).filter_by(incident_id=id).all() if p['role']=='coordinator' or r.data['team_id']==p['team_id']]

class ShelterInput(Strict):
    name:str=Field(min_length=2,max_length=120)
    location_id:str
    latitude:float=Field(ge=-90,le=90)
    longitude:float=Field(ge=-180,le=180)
    capacity:int=Field(ge=0,le=100000)
    occupied:int=Field(ge=0,le=100000)
    status:Literal['OPEN','CLOSED','UNKNOWN']='UNKNOWN'
    source:str=Field(min_length=5,max_length=300)
    @model_validator(mode='after')
    def capacity_check(self):
        if self.occupied>self.capacity:raise ValueError('Occupancy cannot exceed capacity')
        return self
class ShelterEdit(ShelterInput):version:int
@router.get('/shelters')
def shelters(request:Request,db:DB=Depends(get_db)):
    principal(request,db)
    return [{**render(s),'available_spaces':s.data['capacity']-s.data['occupied'],'stale':now()-parsed(s.data['updated_at'])>timedelta(hours=12)} for s in db.query(Shelter).all()]
@router.post('/shelters',status_code=201)
def shelter_create(data:ShelterInput,p=Depends(coordinator),db:DB=Depends(get_db)):
    record(db,Location,data.location_id);s=Shelter(id=ident(),data={**data.model_dump(),'updated_at':stamp()});db.add(s);audit(db,s.id,p['name'],'shelter_created',{});db.commit();return render(s)
@router.put('/shelters/{id}')
def shelter_update(id:str,data:ShelterEdit,p=Depends(coordinator),db:DB=Depends(get_db)):
    record(db,Location,data.location_id);s=record(db,Shelter,id);save(db,s,{**data.model_dump(exclude={'version'}),'updated_at':stamp()},data.version);audit(db,s.id,p['name'],'shelter_updated',{});db.commit();return render(s)

@router.get('/my-team')
def my_team(request:Request,db:DB=Depends(get_db)):
    p=principal(request,db)
    if p['role']!='responder':raise HTTPException(400,'Responder sign-in required')
    return render(record(db,Team,p['team_id']))
class Availability(Strict):
    version:int
    availability:Literal['AVAILABLE','BUSY','UNAVAILABLE']
    personnel:int=Field(ge=0,le=10000)
    ambulances:int=Field(ge=0,le=1000)
    beds:int=Field(ge=0,le=100000)
@router.post('/my-team/availability')
def availability(data:Availability,request:Request,db:DB=Depends(get_db)):
    p=principal(request,db)
    if p['role']!='responder':raise HTTPException(400,'Responder sign-in required')
    t=record(db,Team,p['team_id']);save(db,t,{**t.data,**data.model_dump(exclude={'version'}),'updated_at':stamp()},data.version);audit(db,t.id,p['name'],'team_availability_updated',data.model_dump());db.commit();return render(t)
