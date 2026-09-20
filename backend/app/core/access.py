"""Role accounts are additive: existing responder IDs, passwords and teams are retained."""
import hashlib, os, secrets
from fastapi import Depends, HTTPException, Request
from sqlalchemy import Column, String
from sqlalchemy.orm import Session as DB
from app.database.base import Base
from app.database.session import get_db
from app.services.dispatch import User, Session, Team, now
from app.core import admin_auth
from app.core.config import settings

ROLES=('admin','coordinator','field','rescue','medical','police','public')
COOKIE='ews_role_session'
class UserRole(Base):
    __tablename__='access_user_roles'
    user_id=Column(String(64),primary_key=True)
    role=Column(String(24),nullable=False)

def enabled(): return os.getenv('RBAC_ENABLED','true').lower()=='true'
def account_role(db,u):
    binding=db.get(UserRole,u.id)
    if binding:return binding.role
    team=db.get(Team,u.team_id)
    # Legacy backup coordinator team accounts remain responders, not dispatch approvers.
    return {'RESCUE':'rescue','HOSPITAL':'medical','AMBULANCE':'medical','POLICE':'police'}.get(team.data['kind'],'rescue') if team else None

def identity(request,db):
    token=request.cookies.get(COOKIE)
    if token:
        s=db.get(Session,hashlib.sha256(token.encode()).hexdigest())
        u=db.get(User,s.user_id) if s and s.expires>now() else None
        if not u or not u.active:return None
        role=account_role(db,u)
        if role in ('rescue','medical','police'):
            t=db.get(Team,u.team_id)
            expected={'rescue':{'RESCUE','COORDINATOR'},'medical':{'HOSPITAL','AMBULANCE'},'police':{'POLICE'}}[role]
            if not t or not t.data['active'] or t.data['kind'] not in expected:return None
        return {'role':role,'name':u.name,'user_id':u.id,'team_id':u.team_id,'username':u.username}
    if admin_auth.authenticated(request):return {'role':'admin','name':os.getenv('ADMIN_USERNAME','Administrator'),'user_id':'bootstrap','team_id':''}
    key=os.getenv('OPERATIONS_API_KEY',settings.OPERATIONS_API_KEY)
    if key and secrets.compare_digest(request.headers.get('X-Operations-Key',''),key):return {'role':'admin','name':'operations-key administrator','user_id':'service-key','team_id':''}
    return None

def signed_in(request:Request,db:DB=Depends(get_db)):
    p=identity(request,db)
    if not p:raise HTTPException(401,'Sign in through your role login page')
    return p

def administrator(p=Depends(signed_in)):
    if p['role']!='admin':raise HTTPException(403,'Only administrators can manage accounts and roles')
    return p

PUBLIC_GET=('/api/locations','/api/analysis','/api/environmental','/api/predictions','/api/health')
def api_guard(request:Request,db:DB=Depends(get_db)):
    if not enabled():return
    path=request.url.path.rstrip('/');method=request.method
    if method=='OPTIONS':return
    if method in ('POST','PUT','PATCH','DELETE'):admin_auth.check_origin(request)
    p=identity(request,db);request.state.access_identity=p
    # These routers have explicit account/ownership checks on every private endpoint.
    if path.startswith('/api/access/') or path.startswith('/api/auth/') or path.startswith('/api/dispatch/') or path=='/api/readiness/sensor-ingest':return
    if p and p['role']=='admin':return
    if method=='GET' and (path=='/api/settings/thresholds' or any(path==x or path.startswith(x+'/') for x in PUBLIC_GET)):return
    role=p['role'] if p else 'guest'
    if role=='coordinator':
        if method=='GET' and (path=='/api/alerts' or path.startswith('/api/alerts/')):return
        if path.startswith('/api/operations/') and not '/observations' in path:return
        if path.startswith('/api/alerts/') and method=='PUT':return
        if path.startswith('/api/locations/') and path.endswith('/sync') and method=='POST':return
        if path=='/api/predict' and method=='POST':return
    if role in ('coordinator','field','rescue','medical','police') and method=='GET':
        if path.startswith('/api/readiness/outlooks/') or path in ('/api/operations/assets','/api/operations/roads'):return
    if role=='police' and path.startswith('/api/operations/roads/') and method=='PUT':return
    raise HTTPException(403 if p else 401,'This action is not available for your role' if p else 'Sign in to access this feature')
