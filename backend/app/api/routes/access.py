"""Separate role logins, administrator-provisioned accounts and owned field reports."""
import hashlib, os, secrets
from datetime import timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session as DB
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from app.database.session import get_db
from app.core.access import COOKIE, UserRole, account_role, identity, signed_in, administrator
from app.core import admin_auth
from app.services.dispatch import User, Team, Session, Attempt, now, stamp, ident, password_hash, check_password
from app.services.readiness import audit
from app.api.routes.operations import FieldReport, ReportInput, require_location, report_payload_matches
router=APIRouter(prefix='/access',tags=['Role accounts'])
Role=Literal['admin','coordinator','field','rescue','medical','police','public']
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Login(Strict):
    username:str=Field(min_length=1,max_length=100)
    password:str=Field(min_length=1,max_length=512)
    role:Role

def clear_sessions(request,response,db):
    for cookie,path in [(COOKIE,'/api'),('ews_responder_session','/api/dispatch')]:
        token=request.cookies.get(cookie)
        if token:db.query(Session).filter_by(token=hashlib.sha256(token.encode()).hexdigest()).delete()
        response.delete_cookie(cookie,path=path)
    if request.cookies.get(admin_auth.COOKIE):admin_auth.logout(request,response)

@router.get('/session')
def session(request:Request,response:Response,db:DB=Depends(get_db)):
    response.headers['Cache-Control']='no-store'
    return identity(request,db) or {'role':'guest'}
@router.post('/login')
def login(data:Login,request:Request,response:Response,db:DB=Depends(get_db)):
    admin_auth.check_origin(request)
    key=hashlib.sha256(('roles:'+(request.client.host if request.client else 'unknown')).encode()).hexdigest()
    a=db.get(Attempt,key)
    if a and a.start<now()-timedelta(minutes=15):db.delete(a);db.commit();a=None
    if not a:
        db.add(Attempt(id=key,count=0,start=now()))
        try:db.commit()
        except IntegrityError:db.rollback()
    db.query(Attempt).filter_by(id=key).update({'count':Attempt.count+1},synchronize_session=False);db.commit()
    db.expire_all();a=db.get(Attempt,key)
    if a.count>10:raise HTTPException(429,'Too many login attempts; try again in 15 minutes')
    u=db.query(User).filter_by(username=data.username.strip().lower()).first()
    valid=check_password(data.password,u.password if u else '0'*32+':'+'0'*64)
    if data.role=='admin' and admin_auth.configured():
        name,pwd=admin_auth.credentials()
        if secrets.compare_digest(data.username.encode(),name.encode()) and secrets.compare_digest(data.password.encode(),pwd.encode()):
            clear_sessions(request,response,db);db.delete(a);db.commit()
            admin_auth.login(admin_auth.Login(username=data.username,password=data.password),request,response)
            return {'role':'admin','name':name,'user_id':'bootstrap','team_id':''}
    if not valid or not u or not u.active or account_role(db,u)!=data.role:raise HTTPException(401,'Incorrect credentials, disabled account, or wrong role login page')
    if data.role in ('rescue','medical','police'):
        t=db.get(Team,u.team_id)
        allowed={'rescue':{'RESCUE','COORDINATOR'},'medical':{'HOSPITAL','AMBULANCE'},'police':{'POLICE'}}[data.role]
        if not t or not t.data['active'] or t.data['kind'] not in allowed:raise HTTPException(401,'Your team is inactive or its capability does not match this role')
    clear_sessions(request,response,db)
    token=secrets.token_urlsafe(48);db.add(Session(token=hashlib.sha256(token.encode()).hexdigest(),user_id=u.id,expires=now()+timedelta(hours=8)));db.delete(a)
    audit(db,u.id,u.name,'role_login',{'role':data.role});db.commit()
    response.set_cookie(COOKIE,token,max_age=28800,httponly=True,secure=request.url.scheme=='https' or os.getenv('ADMIN_COOKIE_SECURE','').lower()=='true',samesite='lax',path='/api')
    response.headers['Cache-Control']='no-store'
    return {'role':data.role,'name':u.name,'user_id':u.id,'team_id':u.team_id}
@router.post('/logout')
def logout(request:Request,response:Response,db:DB=Depends(get_db)):
    admin_auth.check_origin(request);clear_sessions(request,response,db);db.commit();return {'role':'guest'}

class Account(Strict):
    username:str=Field(min_length=3,max_length=100,pattern=r'^(?:[a-zA-Z0-9_.-]{3,100}|[a-zA-Z0-9._+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,63})$')
    name:str=Field(min_length=2,max_length=120)
    role:Role
    team_id:str=''
    password:str=Field(min_length=12,max_length=128)
def validate_team(db,role,team_id):
    if role not in ('rescue','medical','police'):return ''
    t=db.get(Team,team_id)
    allowed={'rescue':{'RESCUE'},'medical':{'HOSPITAL','AMBULANCE'},'police':{'POLICE'}}[role]
    if not t or not t.data['active'] or t.data['kind'] not in allowed:raise HTTPException(422,'Choose an active team with the matching capability')
    return team_id
def view(db,u):return {'id':u.id,'username':u.username,'name':u.name,'role':account_role(db,u),'team_id':u.team_id,'active':bool(u.active)}
@router.get('/users')
def users(p=Depends(administrator),db:DB=Depends(get_db)):return [view(db,u) for u in db.query(User).all()]
@router.post('/users',status_code=201)
def create(data:Account,p=Depends(administrator),db:DB=Depends(get_db)):
    if data.username.lower()==os.getenv('ADMIN_USERNAME','').lower():raise HTTPException(409,'Username reserved for the bootstrap administrator')
    tid=validate_team(db,data.role,data.team_id)
    u=User(id=ident(),username=data.username.lower(),name=data.name,team_id=tid,password=password_hash(data.password),active=1)
    db.add(u);db.add(UserRole(user_id=u.id,role=data.role));audit(db,u.id,p['name'],'account_created',{'role':data.role})
    try:db.commit()
    except IntegrityError:db.rollback();raise HTTPException(409,'Username already exists')
    return view(db,u)
class Edit(Strict):
    active:bool
    role:Role
    team_id:str=''
    password:str|None=Field(default=None,min_length=12,max_length=128)
@router.put('/users/{id}')
def edit(id:str,data:Edit,p=Depends(administrator),db:DB=Depends(get_db)):
    u=db.get(User,id)
    if not u:raise HTTPException(404,'Account not found')
    if id==p['user_id'] and (not data.active or data.role!='admin'):raise HTTPException(409,'Use another administrator to change your own access')
    tid=validate_team(db,data.role,data.team_id)
    u.team_id=tid;u.active=int(data.active)
    if data.password:u.password=password_hash(data.password)
    binding=db.get(UserRole,id)
    if not binding:binding=UserRole(user_id=id);db.add(binding)
    binding.role=data.role
    db.query(Session).filter_by(user_id=id).delete();audit(db,id,p['name'],'account_access_changed',{'role':data.role,'active':data.active});db.commit()
    return view(db,u)
class Password(Strict):
    current_password:str=Field(max_length=512)
    new_password:str=Field(min_length=12,max_length=128)
@router.post('/password')
def password(data:Password,p=Depends(signed_in),db:DB=Depends(get_db)):
    u=db.get(User,p['user_id'])
    if not u:raise HTTPException(400,'Bootstrap administrator password is managed in server environment settings')
    if not check_password(data.current_password,u.password):raise HTTPException(401,'Current password is incorrect')
    u.password=password_hash(data.new_password);db.query(Session).filter_by(user_id=u.id).delete();db.commit();return {'message':'Password changed. Sign in again.'}

def report_user(p):
    if p['role'] not in ('field','public'):raise HTTPException(403,'Use Field Operations for coordinator report management')
@router.get('/reports')
def reports(p=Depends(signed_in),db:DB=Depends(get_db)):
    report_user(p)
    condition=FieldReport.data['owner_user_id'].as_string()==p['user_id']
    if p['role']=='field':condition=or_(condition,FieldReport.data['assigned_to'].as_string().in_([p['user_id'],p['username']]))
    rows=db.query(FieldReport).filter(condition).order_by(FieldReport.created_at.desc()).limit(500).all()
    return [{**{k:v for k,v in r.data.items() if k not in ('photo','video')},'id':r.id,'is_owner':r.data.get('owner_user_id')==p['user_id'],'is_assigned':r.data.get('assigned_to') in [p['user_id'],p.get('username')]} for r in rows]
@router.post('/reports',status_code=201)
def report(data:ReportInput,p=Depends(signed_in),db:DB=Depends(get_db)):
    report_user(p);require_location(db,data.location_id)
    if p['role']=='field' and data.category=='landslide' and not (data.photo or data.video):raise HTTPException(422,'Attach a photo or video when reporting a landslide')
    payload={**data.model_dump(mode='json'),'officer':p['name'],'owner_user_id':p['user_id']}
    old=db.get(FieldReport,data.id)
    if old:
        if not report_payload_matches(old.data,payload):raise HTTPException(409,'Report ID already exists; refresh before submitting')
        return {'id':old.id,'status':old.data['status']}
    row=FieldReport(id=data.id,data={**payload,'status':'SUBMITTED','assigned_to':'','received_at':stamp()});db.add(row);audit(db,row.id,p['name'],'owned_report_submitted',{'role':p['role']})
    try:db.commit()
    except IntegrityError:db.rollback();raise HTTPException(409,'Report already submitted; refresh your reports')
    return {'id':row.id,'status':'SUBMITTED'}
class Note(Strict):notes:str=Field(min_length=5,max_length=3000)
@router.patch('/reports/{id}')
def amend_report(id:str,data:Note,p=Depends(signed_in),db:DB=Depends(get_db)):
    report_user(p);r=db.get(FieldReport,id)
    if not r or r.data.get('owner_user_id')!=p['user_id']:raise HTTPException(404,'Report not found')
    if r.data['status'] not in ('SUBMITTED','REJECTED'):raise HTTPException(409,'Reviewed report is locked; submit a follow-up report')
    before=r.data;r.data={**before,'notes':data.notes,'status':'SUBMITTED','updated_at':stamp()};audit(db,id,p['name'],'owned_report_amended',{'previous_notes':before['notes']});db.commit();return {'id':id,'status':'SUBMITTED'}

@router.get('/warnings')
def warnings(db:DB=Depends(get_db)):
    from app.models.alert import Alert
    fields=('alert_id','location_id','severity','risk_score','title','message','recommended_action','status','created_at')
    return [{k:getattr(a,k) for k in fields} for a in db.query(Alert).order_by(Alert.created_at.desc()).limit(500).all()]

@router.post('/reports/{id}/updates')
def field_update(id:str,data:Note,p=Depends(signed_in),db:DB=Depends(get_db)):
    if p['role']!='field':raise HTTPException(403,'Field officer access required')
    r=db.get(FieldReport,id)
    if not r or r.data.get('assigned_to') not in (p['user_id'],p['username']):raise HTTPException(404,'Assigned report not found')
    if r.data['status'] in ('RESOLVED','REJECTED'):raise HTTPException(409,'This report is closed; contact the coordinator')
    note={'actor':p['name'],'at':stamp(),'notes':data.notes}
    r.data={**r.data,'field_updates':[*r.data.get('field_updates',[]),note],'updated_at':stamp()}
    audit(db,id,p['name'],'assigned_field_update',note);db.commit();return {'id':id,'status':r.data['status']}
