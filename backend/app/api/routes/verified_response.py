"""Coordinator verification atomically creates scoped alerts and a durable message outbox."""
import copy, hashlib, json, uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, JSON
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DB
from sqlalchemy.orm.attributes import flag_modified
from app.database.base import Base
from app.database.session import get_db
from app.api.routes.dispatch import coordinator, principal, incident_access, present_incident
from app.api.routes.operations import FieldReport
from app.services.dispatch import Team, Incident, Message, stamp, now, parsed, ident, entry, queue, config, render
from app.services.readiness import audit

router=APIRouter(prefix='/dispatch',tags=['Verified report alerts'])
class VerifiedEvidence(Base):
    __tablename__='verified_incident_evidence'
    incident_id=Column(String(64),primary_key=True)
    data=Column(JSON,nullable=False)
GROUPS={'RESCUE':'rescue','HOSPITAL':'medical','AMBULANCE':'medical','POLICE':'police'}
TASKS={
    'rescue':'Verified landslide: acknowledge, report rescue/evacuation readiness and coordinate deployment with the duty coordinator.',
    'medical':'Verified landslide: acknowledge, confirm available ambulances and beds, and coordinate medical response with the duty coordinator.',
    'police':'Verified landslide: acknowledge, confirm road/access conditions and coordinate site security with the duty coordinator.'}

def incident_id(report_id):return str(uuid.uuid5(uuid.NAMESPACE_URL,'ner-verified-landslide:'+report_id))
def report_row(db,id):
    r=db.get(FieldReport,id)
    if not r:raise HTTPException(404,'Field report not found')
    if r.data['category']!='landslide':raise HTTPException(422,'This workflow is for reported landslides')
    return r

def preview_data(db,r):
    teams=[t for t in db.query(Team).order_by(Team.id).all() if t.data.get('active') and t.data.get('kind') in GROUPS and ('*' in t.data.get('coverage',[]) or r.data['location_id'] in t.data.get('coverage',[]))]
    recipients=[]
    for t in teams:
        stale=now()-parsed(t.data['updated_at'])>timedelta(hours=12)
        recipients.append({'id':t.id,'version':t.version,'name':t.data['name'],'kind':t.data['kind'],'group':GROUPS[t.data['kind']],'channels':t.data.get('channels',[]),'availability':t.data['availability'],'stale':stale})
    missing=[g for g in ('rescue','medical','police') if not any(t['group']==g for t in recipients)]
    # Preview is bound to exact report/evidence and recipient versions; a changed report cannot be approved from an old screen.
    token=hashlib.sha256(json.dumps({'report':r.data,'teams':[(t.id,t.version,t.data) for t in teams]},sort_keys=True,default=str).encode()).hexdigest()
    c=config();gaps=[]
    if missing:gaps.append('No active covering team for: '+', '.join(missing))
    for t in recipients:
        if not t['channels']:gaps.append(t['name']+': in-app alert only; no messaging channels selected')
        if t['availability']!='AVAILABLE' or t['stale']:gaps.append(t['name']+': availability unavailable, busy or stale; acknowledgement does not confirm capacity')
    if not c['enabled']:gaps.append('External dispatch messaging is disabled')
    elif not c['public_url_configured']:gaps.append('Public response URL is missing')
    for channel in ('sms','whatsapp'):
        if any(channel in t['channels'] for t in recipients) and not c[channel+'_ready']:gaps.append(channel.upper()+' sender/template configuration is incomplete')
    linked=db.query(Incident).filter(Incident.data['report_id'].as_string()==r.id).first()
    return {'linked_incident_id':linked.id if linked else None,'preview_token':token,'recipients':recipients,'missing_groups':missing,'gaps':gaps,'messaging':c,'already_verified':bool(db.get(Incident,incident_id(r.id)))},teams

@router.get('/review-reports')
def review_reports(p=Depends(coordinator),db:DB=Depends(get_db)):
    keys=['location_id','officer','category','severity','notes','observed_at','status','received_at','updated_at','verified_incident_id','site_description','estimated_people','reported_injured','access_condition']
    columns=[FieldReport.id]+[FieldReport.data[k].as_string().label(k) for k in keys]
    columns += [(FieldReport.data['photo'].as_string().isnot(None)).label('has_photo'),(FieldReport.data['video'].as_string().isnot(None)).label('has_video')]
    return [dict(x._mapping) for x in db.query(*columns).filter(FieldReport.data['category'].as_string()=='landslide').order_by(FieldReport.created_at.desc()).limit(500).all()]

@router.get('/reports/{id}/verification-preview')
def preview(id:str,p=Depends(coordinator),db:DB=Depends(get_db)):
    r=report_row(db,id);result,_=preview_data(db,r)
    return {**result,'report':{'id':r.id,**r.data}}

class Verify(BaseModel):
    model_config=ConfigDict(extra='forbid')
    preview_token:str=Field(pattern=r'^[0-9a-f]{64}$')
    reason:str=Field(min_length=10,max_length=1000)
    approved:bool
    drill:bool=True
    acknowledge_gaps:bool=False

@router.post('/reports/{id}/verify-alert')
def verify(id:str,data:Verify,p=Depends(coordinator),db:DB=Depends(get_db)):
    r=report_row(db,id);iid=incident_id(id);existing=db.get(Incident,iid)
    if existing:
        if existing.data['drill']!=data.drill:raise HTTPException(409,'Report already verified in a different drill mode; no additional alerts were sent')
        return {'incident':render(existing),'duplicate':True,'queued_messages':db.query(Message).filter_by(incident_id=iid).count()}
    linked=db.query(Incident).filter(Incident.data['report_id'].as_string()==id).first()
    if linked:raise HTTPException(409,'A response incident already references this report; open it instead of sending duplicate alerts')
    if not data.approved:raise HTTPException(422,'Coordinator approval is required')
    if r.data['status'] not in ('SUBMITTED','VERIFIED'):raise HTTPException(409,'Report is not awaiting verification; refresh the queue')
    if not r.data.get('photo') and not r.data.get('video'):raise HTTPException(422,'Photo or video evidence is required before verifying a landslide alert')
    preview,teams=preview_data(db,r)
    if data.preview_token!=preview['preview_token']:raise HTTPException(409,'Report or team directory changed; refresh and review again')
    if not teams:raise HTTPException(422,'Register at least one active response team covering this site before verification')
    if preview['gaps'] and not data.acknowledge_gaps:raise HTTPException(422,'Review and acknowledge the displayed coverage, availability and messaging gaps')
    rd=copy.deepcopy(r.data);at=stamp()
    d={'title':'Verified landslide — '+rd['location_id'],'location_id':rd['location_id'],'latitude':rd['latitude'],'longitude':rd['longitude'],'kind':'REPORTED_LANDSLIDE','severity':rd['severity'],'description':rd['notes'],'affected_people':rd.get('estimated_people'),'drill':data.drill,'report_id':id,'alert_id':None,'ack_minutes':5,'backup_team_id':None,'created_at':at,'status':'ACTIVE','assignments':[],'resources':[],'timeline':[],'linked_reports':[id],'verification':{'by':p['name'],'at':at,'reason':data.reason,'officer':rd['officer'],'observed_at':rd['observed_at']},'site_details':{k:rd.get(k) for k in ('site_description','estimated_people','reported_injured','access_condition')},'notification_gaps':preview['gaps'],'missing_groups':preview['missing_groups'],'approval_reason':data.reason}
    entry(d,p['name'],'CREATED','EXERCISE — NO REAL EMERGENCY' if data.drill else 'Coordinator-verified field report')
    entry(d,p['name'],'REPORT_VERIFIED',{'report_id':id,'reason':data.reason,'gaps':preview['gaps']})
    incident=Incident(id=iid,data=d);db.add(incident)
    # Unique deterministic incident ID makes retries and concurrent verification duplicate-safe.
    try:db.flush()
    except IntegrityError:
        db.rollback();existing=db.get(Incident,iid)
        if existing and existing.data['drill']==data.drill:return {'incident':render(existing),'duplicate':True,'queued_messages':db.query(Message).filter_by(incident_id=iid).count()}
        raise HTTPException(409,'Report was already processed; reload the queue')
    for t in teams:
        a={'id':str(uuid.uuid5(uuid.NAMESPACE_URL,iid+':'+t.id)),'team_id':t.id,'team_name':t.data['name'],'task':TASKS[GROUPS[t.data['kind']]],'status':'AWAITING','assigned_at':at,'due_at':(now()+timedelta(minutes=5)).isoformat()+'Z','eta_minutes':None,'updates':[],'source':'VERIFIED_REPORT','availability_at_alert':t.data['availability']}
        d['assignments'].append(a);queue(db,iid,d,a,t,'VERIFIED_REPORT')
    entry(d,p['name'],'TEAM_ALERTS_QUEUED',{'teams':[t.data['name'] for t in teams],'notice':'In-app alerts created. External delivery and team readiness are tracked separately.'})
    incident.data=copy.deepcopy(d);flag_modified(incident,'data')
    db.add(VerifiedEvidence(incident_id=iid,data={k:rd.get(k) for k in ('photo','video','notes','officer','observed_at','latitude','longitude','site_description','estimated_people','reported_injured','access_condition')}))
    updated={**rd,'status':'VERIFIED','reviewed_by':p['name'],'review_reason':data.reason,'updated_at':at,'verified_incident_id':iid}
    changed=db.query(FieldReport).filter(FieldReport.id==id,FieldReport.data['updated_at'].as_string()==rd.get('updated_at'),FieldReport.data['status'].as_string()==rd['status']).update({'data':updated},synchronize_session=False)
    if not changed:db.rollback();raise HTTPException(409,'Report changed during approval; refresh and retry')
    audit(db,id,p['name'],'verified_and_alerted',{'incident_id':iid,'team_ids':[t.id for t in teams],'drill':data.drill,'reason':data.reason});db.commit()
    return {'incident':render(incident),'duplicate':False,'queued_messages':db.query(Message).filter_by(incident_id=iid).count()}

@router.get('/incidents/{id}/evidence')
def evidence(id:str,request:Request,db:DB=Depends(get_db)):
    incident_access(db,id,principal(request,db));r=db.get(VerifiedEvidence,id)
    if not r:raise HTTPException(404,'No verified evidence snapshot attached to this incident')
    return r.data
