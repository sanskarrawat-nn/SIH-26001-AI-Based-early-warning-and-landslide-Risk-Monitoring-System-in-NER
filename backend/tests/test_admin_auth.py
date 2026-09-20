import os
import sqlite3
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from app.core.admin_auth import router, COOKIE
from app.api.routes.whatsapp import authorize

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('ADMIN_USERNAME','admin')
    monkeypatch.setenv('ADMIN_PASSWORD','a-long-test-password')
    monkeypatch.setenv('ADMIN_SESSION_DB',str(tmp_path/'sessions.db'))
    app=FastAPI();app.include_router(router,prefix='/api')
    @app.get('/api/private',dependencies=[Depends(authorize)])
    def private():return {'ok':True}
    return TestClient(app,base_url='https://testserver')

def login(client):
    return client.post('/api/auth/login',json={'username':'admin','password':'a-long-test-password'})

def test_login_persistence_logout(client):
    assert client.get('/api/private').status_code in (401,503)
    assert client.post('/api/auth/login',json={'username':'admin','password':'wrong'}).status_code==401
    r=login(client);assert r.status_code==200
    for attr in ['HttpOnly','Secure','Max-Age=2592000']:assert attr in r.headers['set-cookie']
    token=client.cookies.get(COOKIE)
    assert client.get('/api/private').status_code==200
    assert client.get('/api/auth/session').json()['authenticated']
    assert client.post('/api/auth/logout').status_code==200
    client.cookies.set(COOKIE,token)
    assert not client.get('/api/auth/session').json()['authenticated']

def test_tampering_expiry_rotation(client,monkeypatch):
    login(client);monkeypatch.setenv('ADMIN_PASSWORD','changed-long-password')
    assert not client.get('/api/auth/session').json()['authenticated']
    monkeypatch.setenv('ADMIN_PASSWORD','a-long-test-password')
    with sqlite3.connect(os.environ['ADMIN_SESSION_DB']) as db:db.execute('UPDATE sessions SET expires=0')
    assert not client.get('/api/auth/session').json()['authenticated']
    client.cookies.clear();client.cookies.set(COOKIE,'fake-session')
    assert not client.get('/api/auth/session').json()['authenticated']

def test_origin_and_throttle(client):
    assert client.post('/api/auth/login',headers={'Origin':'https://evil.example'},json={'username':'admin','password':'a-long-test-password'}).status_code==403
    assert client.post('/api/auth/login',headers={'Origin':'http://localhost.evil.com'},json={'username':'admin','password':'a-long-test-password'}).status_code==403
    assert client.post('/api/auth/login',headers={'Origin':'http://localhost:5175'},json={'username':'admin','password':'a-long-test-password'}).status_code==200
    assert client.post('/api/auth/login',headers={'Origin':'http://127.0.0.1:5175'},json={'username':'admin','password':'a-long-test-password'}).status_code==200
    for _ in range(10):assert client.post('/api/auth/login',json={'username':'admin','password':'wrong'}).status_code==401
    assert login(client).status_code==429

def test_unconfigured(client,monkeypatch):
    monkeypatch.delenv('ADMIN_PASSWORD');assert login(client).status_code==503
