# Monitoring and validation update

Open the existing app and select **Monitoring**. This release adds the following four core monitoring/evaluation capabilities, with supporting controls in the same app:

1. **Experimental forecast outlook:** Open-Meteo rainfall for the next 3, 6, 12 and 24 hours, with rolling 24-hour totals and modelled shallow-soil moisture. The 100 mm comparison is a demonstration reference, not an approved landslide trigger or a calibrated probability.
2. **Continuous monitoring and history:** optional collection every 10 minutes for explicitly configured sites; saved snapshots, current input source, timestamps and stale-data indicators. Missing forecasts produce an error instead of invented fallback data.
3. **Historical replay:** upload archived, timestamped predictions and verified outcomes; move through individual cases and save/reload evaluations. This replays imported predictions; it does not rerun a historical weather or ML model.
4. **Evaluation and baseline comparison:** confusion counts, precision, recall, false-alarm ratio, false-positive rate, Brier score and mean detected lead time, compared with a rainfall baseline. Input availability must precede issuance; outcomes must cover the full forecast window. Uploader-attested evidence is not independently certified.

Supporting tabs include authenticated sensor registration/ingestion, manual photo annotations and report review with audit history, independent SMS and WhatsApp notification settings/tests, and trusted model version activation/rollback. Existing navigation and workflows remain available. Separate government/field-officer dashboards and separate user roles are not part of this release; the existing administrator access remains.

## Install and start

Keep your existing deployment environment variables and database. Back up the database and model directory before replacing source. Do not overwrite a production database with the sample database from this ZIP. No private .env files or login-session databases are included.

From the extracted project folder:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r backend/requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Open http://localhost:8000. The ZIP also contains the production frontend build. Dependencies and virtual environments are intentionally omitted, so the ZIP is much smaller than a development folder containing node_modules.

The startup creates additive database tables. Existing tables do not need ALTER TABLE. Keep DATABASE_URL, the model directory and the administrator session path on persistent storage. PostgreSQL is supported by the existing application, but the automated tests for this release used SQLite. Use a single application worker for the in-process scheduler/model activation controls; distributed scheduling and cross-instance model promotion need an external coordinator.

Configure your own ADMIN_USERNAME and ADMIN_PASSWORD using the existing ADMIN-LOGIN-SETUP.md. Sign in through Settings. No new default password is introduced. Server environment variables take precedence over .env files. Administrative endpoints accept the existing admin session or the optional X-Operations-Key header. Sensor endpoints accept only their own device token.

## Scheduled forecast collection

Set backend environment variables, then restart:

```dotenv
MONITORING_ENABLED=true
MONITOR_LOCATION_IDS=LOC-AS-01
```

Use IDs from your app's /api/locations endpoint; multiple IDs are comma-separated. Up to 20 sites are scheduled. The default is disabled. Manual **Fetch forecast** works after admin login. Snapshots are cached for 10 minutes; snapshots older than one hour are marked stale; stored snapshots are retained for 30 days. The UI lists up to 60 snapshots per site. No forecast outlook creates a crisis alert or sends a message. Forecast retrieval time is shown; provider model issue time is unavailable.

## WhatsApp and SMS

Keep credentials on the backend only:

```dotenv
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
WHATSAPP_ENABLED=true
TWILIO_WHATSAPP_FROM=whatsapp:+your_approved_sender
TWILIO_CONTENT_SID=your_approved_crisis_template_sid
TWILIO_TEST_CONTENT_SID=your_approved_test_template_sid
SMS_ENABLED=true
TWILIO_SMS_FROM=+your_sms_capable_twilio_number
# Alternatively to TWILIO_SMS_FROM:
# TWILIO_SMS_MESSAGING_SERVICE_SID=your_messaging_service_sid
```

The crisis template variables remain: 1 severity, 2 location, 3 risk score, 4 recommended action, 5 alert ID. Existing TWILIO_CONTENT_SIDS language mapping remains supported. The separate test template uses the same five slots filled with explicit TEST / NO EMERGENCY wording, a setup-check location, N/A, no action required, and a test ID. Have the test template approved with those variable meanings; do not reuse an emergency-only template for tests.

1. Configure the sender and templates in Twilio. For Sandbox WhatsApp, recipients must join your actual sandbox using the code shown in your Twilio console. Production WhatsApp requires the appropriate approved sender/templates.
2. Register consenting recipients in the existing Settings page.
3. Under Monitoring → Notification channels, record SMS consent and enable SMS. Existing WhatsApp recipients stay enabled for WhatsApp; SMS defaults off.
4. Save preferences, then use the explicitly confirmed **Send test to saved channels** button. This sends real messages and may incur provider charges when enabled.
5. Refresh delivery history and inspect error codes. Queued is not delivered. UNKNOWN means check the Twilio console before manually sending another test. Operational WhatsApp history remains in Settings.

SMS and WhatsApp are independent jobs for the same eligible alert. Failure of one channel does not block the other. Arrival at exactly the same time cannot be guaranteed. Operational messaging retains the existing HIGH/SEVERE alert and source eligibility rules; forecasts and newly ingested sensor observations do not generate alerts. Duplicate alerts are suppressed; pending messages are cancelled when consent is removed. Tests use idempotent request IDs and a per-recipient one-minute rate limit.

Destination permissions, trial verification, sender capability, account balance and country-specific routing must be configured in your Twilio account. This release does not bypass these restrictions. No real messages were sent during automated verification.

Official provider documentation: https://www.twilio.com/docs/messaging/api/message-resource and https://www.twilio.com/docs/whatsapp/sandbox

## Sensors

Register each device under Monitoring → Sensors. Set its site, measurement kind, expected interval and calibration reference. Test devices are labelled by default. Copy the token once to the device. Send JSON to POST /api/readiness/sensor-ingest with header X-Sensor-Key containing that token:

```json
{
  "device_id": "the-returned-device-id",
  "sequence_id": "reading-0001",
  "observed_at": "2026-09-15T12:00:00Z",
  "value": 40,
  "unit": "percent"
}
```

Replace the example timestamp with the real observation time. Use unique sequence IDs per device. Accepted units: soil_moisture=percent, rainfall=mm, tilt=degrees, pore_pressure=kPa. Rainfall is the amount measured over your device's documented sampling interval; store that interval/calibration context when registering. These readings are retained as observations, not interpreted as 24-hour model rainfall. Times need a timezone and must be no more than seven days old or two minutes ahead. Exact duplicates are acknowledged; conflicting sequence IDs are rejected. Revoking a device immediately stops ingestion with its token. Tokens are stored hashed, not displayed again.

Reading history shows up to 200 readings per device. A reading is stale after twice the expected interval, with a minimum five-minute tolerance. Actual hardware calibration, connectivity and any future sensor-to-model mapping must be validated separately.

## Replay and evaluation

Download the JSON input template from Historical replay. Fill it with archived predictions, their model hash, data source, input-availability time, issue time, window end, complete outcome follow-up and event time (null for no event). Mark verified=true only after checking the source. All records must share a forecast horizon and model version. Maximum 2,000 cases and 2 MB through the UI.

Case-level metrics are not event-level validation. Overlapping cases can inflate performance. No-event records require full follow-up; a missing event timestamp alone does not prove no event happened. Threshold selection and model training must use separate data from the evaluation set. A high score on invented/synthetic records is not real-world accuracy.

## Report review and model controls

Select an existing report in Report review. For a photo, click two corners to mark a region and label your observation. Provide a review reason, assignment and status; saving records an audit entry. A stale review is rejected so another reviewer’s update is not silently overwritten. These are human annotations, not an AI crack detector.

Install trusted candidate joblib files under backend/app/ml/artifacts/candidates (or MODEL_DIR/candidates). Never place untrusted pickle/joblib files there; loading them can execute code. The app does not accept binary model uploads. Keep old artifact files for rollback. Model versions lists SHA-256 identifiers. Promotion requires compatible inference, a matching evaluation with at least 30 attested cases containing both event classes, and a review reason. This is a procedural gate, not scientific certification. Rollback is restricted to a version recorded as previously active. The active-model.json pointer and database audit must both persist. Back them up together; a machine/process failure during activation can require operator reconciliation.

## Verification and limits

- Frontend TypeScript/Vite/PWA production build passed.
- 62 backend tests passed, including the 42 existing tests and 20 new cases covering forecast windows/invalid input, replay metrics/leakage, sensor tokens/idempotency/revocation, report review conflict/audit, access checks, independent mocked channel failure, test consent/idempotency, model integrity and promotion evidence gates.
- Browser visual verification could not run because the available Chromium process failed to start. The frontend build passed; visual layout is not independently verified in this release.
- Live Twilio delivery, real hardware, production PostgreSQL and scientific forecasting accuracy were not verified in this environment.
- The existing prediction model and its synthetic-training limitations remain. This update does not establish that the app can reliably predict a landslide before it happens.

Prediction records retain the existing 32-character model-version column for database compatibility. The complete SHA-256 is saved in input_features._model_sha256 and the latest prediction snapshot; model activation and replay use the complete hash.
