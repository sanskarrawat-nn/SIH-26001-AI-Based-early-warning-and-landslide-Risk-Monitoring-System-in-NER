# Verification of the feature update

- **Backend: 37 tests passed.** Includes the original API, prediction, operations and notification tests, plus video/legacy-report compatibility, road connectivity and stale-status handling, satellite quality filtering and failure preservation, multilingual template selection, matching translation catalogs and additive database upgrade checks.
- **Frontend: TypeScript and Vite production build passed.** The build also generates the versioned service-worker cache.
- **Browser workflows passed with local SQLite and simulated environmental data:** legacy queue migration, road registration and connectivity, road map layer, map drawer stacking, four alert languages, cached app reopening while the backend was stopped, video persistence, upload after the reconnect event, video playback metadata and a 390 px mobile viewport without horizontal document overflow. No page JavaScript exceptions were recorded in that run.
- The browser's network emulation was inconsistent across navigation, so the final outage test stopped and restarted the actual local backend. A reconnect event was dispatched to exercise automatic synchronization. This does not validate every physical device/browser or background-sync scheduler.
- No real WhatsApp messages were sent. Twilio tests use controlled provider responses. Live satellite access could not be verified; provider parsing, scaling, quality rejection and failure handling use controlled responses.
- Live Render deployment, PostgreSQL execution, real GPS hardware, external basemap availability, signed Android builds and real-world model accuracy were not verified. The synthetic model and existing operational prediction behavior are unchanged.

## Repeat the checks

From `backend`, with its dependencies installed:

```sh
python -m pytest -q
```

From `frontend`:

```sh
npm ci
npm run build
```

Optional browser verification uses Playwright only as a development tool. From `frontend`, install it without changing application manifests and download its browser:

```sh
npm install --no-save --package-lock=false playwright
npx playwright install chromium
node ../verification/browser-check.mjs
```

The browser script starts an isolated test backend on port 8134 with a temporary database, stops/restarts it to test the cached shell, and writes screenshots and `browser-results.json` in `verification`. Ensure that port is free. Set `PYTHON` if your Python executable has another name. Existing application dependencies must be installed in that Python environment.

See `FEATURES-SETUP.md` for feature usage, deployment and live-service configuration. Earlier verification screenshots are retained as historical evidence; the current screenshots are `map-drawer.png` and `mobile-field-report.png`.
