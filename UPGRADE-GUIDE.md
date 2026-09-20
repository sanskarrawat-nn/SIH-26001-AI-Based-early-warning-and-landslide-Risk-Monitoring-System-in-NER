# Updated app: setup and verification

This update adds village/infrastructure exposure assets and GIS markers, an explainable response-priority queue, mobile-accessible field reports with GPS/photo evidence and a local retry queue, and observational CSV validation/candidate training. Existing tabs are retained. Assets start empty: register surveyed assets and sources instead of using invented populations.

## Run on Windows, macOS or Linux

1. Back up your existing database, environment file and model. Extract this source into a new directory. Do not copy old node_modules or venv folders.
2. In backend, create/activate a Python 3.11+ virtual environment and run `python -m pip install -r requirements.txt`.
3. In frontend, run `npm ci` then `npm run build` (Node 22+).
4. In backend, run `python -m app.ml.train` to generate the demonstration model for the installed scikit-learn version. Then `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
5. Open http://127.0.0.1:8000 . New tables are created automatically. For a frontend development server use `npm run dev` in frontend while backend is running.
6. Run `python -m pytest -q` in backend for regression tests.

For deployment, retain your database URL and deploy the supplied Dockerfile to the existing Render service. A source ZIP is not a deployment; the live service remains unchanged until you deploy it. Set OPERATIONS_API_KEY to a strong private key for a shared deployment. Enter it in Field Operations > Deployment access key. It protects API mutations and field-report reads. Empty means an openly editable local demonstration. A shared key is not per-user authentication; use an authenticated gateway/role system for multi-user production.

## Android

Set VITE_API_URL to your deployed backend URL ending in /api before `npm run build:android`. For example in PowerShell:

```powershell
$env:VITE_API_URL="https://ner-landslide-command-center.onrender.com/api"
npm run build:android
```

Then open the Android project with Android Studio and build/sign it using your SDK. The updated backend must be deployed first. The build command fails clearly if the API URL is missing; it will not create another package pointing at device-local /api.

## Workflows

- Field Operations > Vulnerability assets: register/edit/delete surveyed villages, hospitals, schools, bridges, roads and shelters. The source, people exposed, vulnerability and access state are editable. Assets link to an existing monitored location's hazard estimate; this is not a spatial vulnerability model.
- GIS Explorer: toggle the village/infrastructure exposure layer; click a marker for its score and source.
- Response queue: inspect score contributions. Verify reports before they can raise a location's hazard used in prioritisation; assign and mark dispatched/resolved. Triage weights are heuristics, not calibrated loss probabilities or automatic dispatch.
- Field report: capture GPS or enter coordinates, attach a JPEG/PNG/WebP photo under 2.8 MB, add notes and submit. The device outbox saves first, retries while the page is open when connectivity returns, and reuses submission IDs to avoid duplicate reports. Keep the device until pending count is zero. Storage quota failures are shown. Full offline app startup, offline basemaps, background push and video capture are not implemented.
- Observational data: validate CSV and follow OBSERVATIONAL-DATA.md to train/evaluate a separate candidate from real audited records.

## Corrections included

Telemetry sync now persists prediction/measurement history and generates high/severe alerts. Simulator calls set simulation=true and do not update operational locations/alerts. Trend queries select the newest records. Weather calculations exclude future hours and report volumetric moisture as percent; incomplete readings trigger the explicitly simulated fallback. Dashboard initial requests can fail independently with a retry message and a labelled location cache. New severe alerts on polling can sound after the audio option is enabled. Mobile navigation is available. The basemap previously labelled Topographic is labelled Street map.

## Limits

No vetted observational dataset was supplied, no physical sensors were connected and no SMS/push service was configured. Demonstration seed readings are labelled DEMO_SEEDED_DATA. No claims of real disaster-warning reliability or zero possible runtime errors are made. Protect access, validate local thresholds/data with authorities and test your deployed environment before operational use.
