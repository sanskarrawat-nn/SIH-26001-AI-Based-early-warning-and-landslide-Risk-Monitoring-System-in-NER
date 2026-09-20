"""Server-side administrator sessions. No deployment secret reaches the browser."""
from contextlib import contextmanager
import hashlib
import os
import secrets
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

# Ensure environment variables from .env are loaded
_env_backend = Path(__file__).resolve().parents[2] / '.env'
if _env_backend.exists():
    load_dotenv(_env_backend, override=False)
_env_root = Path(__file__).resolve().parents[3] / '.env'
if _env_root.exists():
    load_dotenv(_env_root, override=False)
load_dotenv(override=False)

router = APIRouter(prefix='/auth', tags=['Administrator'])
COOKIE = 'ews_admin_session'
TTL = 30 * 24 * 60 * 60

def credentials():
    return os.getenv('ADMIN_USERNAME', ''), os.getenv('ADMIN_PASSWORD', '')

def configured():
    u, p = credentials()
    return bool(u and len(p) >= 12)

@contextmanager
def connection():
    path = os.getenv('ADMIN_SESSION_DB', str(Path(__file__).resolve().parents[2] / 'admin_sessions.db'))
    db = sqlite3.connect(path, timeout=10)
    db.execute('CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, expires REAL, credential TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS attempts (address TEXT PRIMARY KEY, count INTEGER, start REAL)')
    try:
        with db:
            yield db
    finally:
        db.close()

def fingerprint():
    u, p = credentials()
    return hashlib.sha256((u + '\0' + p).encode()).hexdigest()

def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()

def authenticated(request: Request):
    role_identity = getattr(request.state, 'access_identity', None)
    if role_identity:
        return role_identity['role'] == 'admin'

    token = request.cookies.get(COOKIE)
    if not token or not configured():
        return False
    with connection() as db:
        row = db.execute('SELECT expires, credential FROM sessions WHERE token=?', (digest(token),)).fetchone()
    return bool(row and row[0] > time.time() and secrets.compare_digest(row[1], fingerprint()))

def is_trusted_origin(origin: str, allowed: set) -> bool:
    if not origin:
        return False
    norm = origin.strip().rstrip('/')
    if norm in allowed:
        return True
    try:
        parsed = urlparse(norm)
        if parsed.scheme in ('http', 'https'):
            host = (parsed.hostname or '').lower()
            if host in ('localhost', '127.0.0.1', '::1', '[::1]', '0.0.0.0'):
                return True
    except Exception:
        pass
    return False

def check_origin(request: Request):
    # Browsers provide Origin on cross-origin writes. Reject cross-site cookie requests.
    origin = request.headers.get('origin')
    allowed = {str(request.base_url).rstrip('/')}
    allowed.update(x.strip().rstrip('/') for x in os.getenv('ADMIN_ALLOWED_ORIGINS', '').split(',') if x.strip())
    allowed.update([
        'http://localhost:5173', 'http://localhost:5174', 'http://localhost:5175',
        'http://127.0.0.1:5173', 'http://127.0.0.1:5174', 'http://127.0.0.1:5175',
        'http://localhost:8000', 'http://127.0.0.1:8000'
    ])
    sec_fetch_site = request.headers.get('sec-fetch-site')
    if origin and not is_trusted_origin(origin, allowed):
        raise HTTPException(403, 'Untrusted request origin')
    if sec_fetch_site == 'cross-site' and (not origin or not is_trusted_origin(origin, allowed)):
        raise HTTPException(403, 'Untrusted request origin')

class Login(BaseModel):
    username: str = Field(max_length=120)
    password: str = Field(max_length=512)

@router.get('/session')
def session(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return {'authenticated': authenticated(request), 'configured': configured()}

@router.post('/login')
def login(data: Login, request: Request, response: Response):
    check_origin(request)
    if not configured():
        raise HTTPException(503, 'Set ADMIN_USERNAME and ADMIN_PASSWORD (at least 12 characters) on the backend.')
    address = request.client.host if request.client else 'unknown'
    now = time.time()
    with connection() as db:
        db.execute('DELETE FROM attempts WHERE start < ?', (now - 900,))
        db.execute('DELETE FROM sessions WHERE expires < ?', (now,))
        db.execute('INSERT INTO attempts VALUES (?, 1, ?) ON CONFLICT(address) DO UPDATE SET count=count+1', (address, now))
        count = db.execute('SELECT count FROM attempts WHERE address=?', (address,)).fetchone()[0]
    if count > 10:
        raise HTTPException(429, 'Too many login attempts. Try again in 15 minutes.')
    u, p = credentials()
    valid_user = secrets.compare_digest(data.username.encode(), u.encode())
    valid_password = secrets.compare_digest(data.password.encode(), p.encode())
    if not (valid_user and valid_password):
        raise HTTPException(401, 'Incorrect username or password')
    token = secrets.token_urlsafe(48)
    with connection() as db:
        db.execute('DELETE FROM attempts WHERE address=?', (address,))
        old = request.cookies.get(COOKIE)
        if old:
            db.execute('DELETE FROM sessions WHERE token=?', (digest(old),))
        db.execute('INSERT INTO sessions VALUES (?, ?, ?)', (digest(token), now + TTL, fingerprint()))
    cookie_secure_env = os.getenv('ADMIN_COOKIE_SECURE')
    is_secure = (cookie_secure_env.lower() not in ('false', '0', 'no')) if cookie_secure_env is not None else (request.url.scheme == 'https')
    response.set_cookie(COOKIE, token, max_age=TTL, httponly=True, secure=is_secure, samesite='lax', path='/api')
    response.headers['Cache-Control'] = 'no-store'
    return {'authenticated': True}

@router.post('/logout')
def logout(request: Request, response: Response):
    check_origin(request)
    with connection() as db:
        db.execute('DELETE FROM sessions WHERE token=?', (digest(request.cookies.get(COOKIE, '')),))
    response.delete_cookie(COOKIE, path='/api')
    return {'authenticated': False}
