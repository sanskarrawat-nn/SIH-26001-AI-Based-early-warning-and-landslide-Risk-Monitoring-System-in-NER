import io,csv
from app.models.alert import Alert
from app.models.prediction import Prediction
from app.models.environmental import EnvironmentalMeasurement
from app.ml.observations import validate_csv,COLUMNS

def asset():
    return dict(name='Surveyed village',location_id='LOC-AS-01',kind='village',latitude=26.1,longitude=91.7,population=2000,vulnerability=.8,access='blocked',source='Field survey 2026-09-10')

def report():
    return dict(id='test-report-unique',location_id='LOC-AS-01',officer='Test Officer',category='blocked_road',severity='SEVERE',latitude=26.1,longitude=91.7,notes='Road blocked after slope movement',observed_at='2026-09-10T10:00:00Z')

def test_asset_and_report_lifecycle(client):
    a=client.post('/api/operations/assets',json=asset());assert a.status_code==201
    aid=a.json()['id']
    assert client.get('/api/operations/priorities').json()[0]['priority_score']>=0
    r=client.post('/api/operations/reports',json=report());assert r.status_code==201
    assert client.post('/api/operations/reports',json=report()).json()['duplicate']
    assert client.patch('/api/operations/reports/test-report-unique',json={'status':'VERIFIED','assigned_to':'Rescue team'}).status_code==200
    item=next(x for x in client.get('/api/operations/priorities').json() if x['asset_id']==aid)
    assert item['verified_reports']==1 and item['risk_score']>=90
    changed={**asset(),'access':'open'}
    assert client.put('/api/operations/assets/'+aid,json=changed).status_code==200
    assert client.delete('/api/operations/assets/'+aid).status_code==200
    assert client.post('/api/operations/assets',json={**asset(),'location_id':'missing'}).status_code==404
    assert client.post('/api/operations/reports',json={**report(),'id':'invalid-photo','photo':'data:image/jpeg;base64,YWJj'}).status_code==422

def prediction():
    return dict(location_id='LOC-AS-01',latitude=26.1,longitude=91.7,rainfall_1h=35,rainfall_24h=200,rainfall_7d=500,soil_moisture=96,slope=45,elevation=650,terrain_roughness=40,vegetation_index=.3)

def test_simulator_does_not_mutate(client,db_session):
    before=[db_session.query(m).count() for m in [Alert,Prediction,EnvironmentalMeasurement]]
    loc=client.get('/api/locations/LOC-AS-01').json()
    result=client.post('/api/predict',json={**prediction(),'simulation':True})
    assert result.status_code==200 and result.json()['risk_level']=='SEVERE'
    assert before==[db_session.query(m).count() for m in [Alert,Prediction,EnvironmentalMeasurement]]
    assert client.get('/api/locations/LOC-AS-01').json()==loc

def test_sync_persists_prediction_and_alert(client,db_session,monkeypatch):
    from app.services import location_service
    class Provider:
        async def get_current_conditions(self,*args):return {**prediction(),'source':'TEST_SENSOR'}
    monkeypatch.setattr(location_service,'get_environmental_provider',lambda:Provider())
    before=db_session.query(Prediction).count()
    r=client.post('/api/locations/LOC-AS-01/sync')
    assert r.status_code==200 and r.json()['risk_level']=='SEVERE'
    assert db_session.query(Prediction).count()==before+1
    assert db_session.query(Alert).filter_by(location_id='LOC-AS-01',status='ACTIVE').count()>=1

def test_observation_validation(client):
    row={**prediction(),'observed_at':'2026-09-10T10:00:00Z','source':'audited-station-record','verified':'true','landslide_occurred':'1'}
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=COLUMNS);writer.writeheader();writer.writerow(row)
    assert client.post('/api/operations/observations/validate',json={'csv':out.getvalue()}).json()['valid']
    writer.writerow(row)
    summary=validate_csv(out.getvalue())[1];assert not summary['valid'] and summary['error_count']==1
    assert client.post('/api/operations/observations/validate',json={'csv':'bad,columns\n1,2'}).status_code==422

def test_weather_ignores_future(monkeypatch):
    import asyncio
    from datetime import datetime,timedelta
    from app.services.environmental_provider import OpenMeteoProvider
    now=datetime(2026,9,10,12)
    times=[now+timedelta(hours=i) for i in range(-168,13)]
    data={'current':{'time':now.isoformat()},'hourly':{'time':[t.isoformat() for t in times],'precipitation':[1 if t<=now else 100 for t in times],'soil_moisture_0_to_1cm':[.2 if t<=now else .5 for t in times]}}
    class Response:
        def raise_for_status(self):pass
        def json(self):return data
    class HTTP:
        def __init__(self,*a,**k):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        async def get(self,*a,**k):return Response()
    monkeypatch.setattr('app.services.environmental_provider.httpx.AsyncClient',HTTP)
    r=asyncio.run(OpenMeteoProvider().get_current_conditions(25,92))
    assert r['rainfall_1h']==1 and r['rainfall_24h']==24 and r['rainfall_7d']==168 and r['soil_moisture']==20

def test_access_key(client,monkeypatch):
    monkeypatch.setenv('OPERATIONS_API_KEY','test-only-key')
    assert client.post('/api/operations/assets',json=asset()).status_code==401
    assert client.get('/api/operations/reports').status_code==401
    assert client.get('/api/operations/reports',headers={'X-Operations-Key':'test-only-key'}).status_code==200

def test_temporal_candidate_pipeline(tmp_path):
    from app.ml.observations import train_candidate
    from datetime import datetime,timedelta,timezone
    out=io.StringIO();w=csv.DictWriter(out,fieldnames=COLUMNS);w.writeheader()
    for i in range(120):
        row={**prediction(),'location_id':f'TEST-{i%5}','observed_at':(datetime(2025,1,1,tzinfo=timezone.utc)+timedelta(hours=i)).isoformat(),'source':'SYNTHETIC_TEST_FIXTURE_NOT_OBSERVATIONAL','verified':'true','landslide_occurred':str(i%2)}
        if i%2==0:row.update(rainfall_1h=0,rainfall_24h=2,rainfall_7d=10,soil_moisture=18,slope=8)
        w.writerow(row)
    metrics=train_candidate(out.getvalue(),tmp_path)
    assert metrics['training_rows']==96 and metrics['test_rows']==24
    assert metrics['deployment_status']=='CANDIDATE_NOT_PROMOTED'
    assert (tmp_path/'candidate.joblib').exists() and (tmp_path/'evaluation.json').exists()


def test_trends_newest_window(client,db_session):
    from datetime import datetime,timedelta
    for i in range(65):
        db_session.add(Prediction(location_id='LOC-AS-01',timestamp=datetime(2029,1,1)+timedelta(hours=i),risk_score=i,risk_level='LOW',probability=.1,confidence=.8,recommendation='Test',input_features={}))
    db_session.commit()
    rows=client.get('/api/analysis/trends?location_id=LOC-AS-01').json()['timeseries']
    assert len(rows)==60 and rows[0]['risk_score']==5 and rows[-1]['risk_score']==64

def test_admin_session_operations(client,monkeypatch,tmp_path):
    monkeypatch.setenv('ADMIN_USERNAME','admin')
    monkeypatch.setenv('ADMIN_PASSWORD','a-long-test-password')
    monkeypatch.setenv('ADMIN_COOKIE_SECURE','false')
    monkeypatch.setenv('ADMIN_SESSION_DB',str(tmp_path/'admin.db'))
    monkeypatch.setenv('OPERATIONS_API_KEY','backend-only-test-key')
    assert client.get('/api/locations').status_code==200
    assert client.get('/api/operations/reports').status_code==401
    assert client.post('/api/auth/login',json={'username':'admin','password':'a-long-test-password'}).status_code==200
    assert client.get('/api/operations/reports').status_code==200
    assert client.get('/api/whatsapp/recipients').status_code==200
    assert client.post('/api/operations/assets',json=asset(),headers={'origin':'https://evil.example'}).status_code==403
    assert client.post('/api/auth/logout').status_code==200
    assert client.get('/api/operations/reports').status_code==401
