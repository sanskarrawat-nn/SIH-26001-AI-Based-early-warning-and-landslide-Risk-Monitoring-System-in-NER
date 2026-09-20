# Administrator login update

The deployment-key input in WhatsApp settings has been replaced with username/password login. The browser keeps an HttpOnly session cookie for up to 30 days. The backend stores only a hash of the session token. Logout revokes the session; changing administrator credentials invalidates existing sessions. Public read pages remain accessible. Existing operations-key clients are still supported.

## One-time backend configuration

Set these in your hosting environment before restarting the backend:

- ADMIN_USERNAME: your chosen administrator username.
- ADMIN_PASSWORD: a unique password of at least 12 characters.
- ADMIN_SESSION_DB: an absolute writable path on persistent storage, e.g. /var/data/admin_sessions.db. Without persistent storage, hosting restarts/redeployments may require signing in again. All workers must share this SQLite file; independent replicas require a shared session store.
- ADMIN_ALLOWED_ORIGINS: your exact public app origin, e.g. https://ner-landslide-command-center.onrender.com. Comma-separated if necessary. This supports trusted reverse-proxy origins.

Keep existing Twilio settings and OPERATIONS_API_KEY on the backend. Never add secrets to VITE variables or frontend code. No default username or password is shipped.

HTTPS is required by default. For local HTTP development only, set ADMIN_COOKIE_SECURE=false. Use a same-origin frontend/API deployment (or local Vite proxy). Arbitrary cross-site frontend/API cookie hosting is not supported by this change.

Open Settings > WhatsApp crisis alerts, sign in once, and use Sign out on shared devices. Cookie deletion, session expiry, or credential rotation requires a new login. A maximum of ten login attempts per client IP per 15 minutes is enforced; shared proxies may share this limit.

The production frontend build and focused authentication/authorization tests were run for this update. No live deployment or live Twilio delivery was performed. Browser visual verification was not performed for this update.

Installed dependencies, local environments, caches, and private environment files are excluded from the ZIP. The original application database/model files are preserved; no test database or administrator session database is shipped.
