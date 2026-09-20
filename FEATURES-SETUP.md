# Feature additions — September 2026

This update adds the requested checklist features to your uploaded app. Existing prediction logic, risk thresholds, navigation, database records, map drawer stacking fix and deployment architecture are preserved. The machine-learning model remains a synthetic-data prototype; these additions do not turn it into a validated operational warning system.

| Checklist item | Available in this update | Setup / limits |
| --- | --- | --- |
| Geo-tagged photo/video reporting | Field Operations → Field report. GPS or manually entered coordinates, photo and video evidence, review and status changes. | JPEG/PNG/WebP photos under 2.8 MB; MP4/WebM videos under 10 MB. Playback depends on the device's codec support. No video transcoding. |
| Road connectivity layer/status | Field Operations → Road connectivity. Register, edit, reconfirm and remove connections. Check connectivity between assets; toggle the road layer in GIS Explorer. | Register real surveyed assets and links. Open/restricted/blocked/unknown statuses; observations older than 24 hours become unknown. Only fresh open links participate in connectivity checks. |
| Offline PWA + sync | Installable app shell, IndexedDB report/evidence outbox, old-queue migration, retry/backoff, manual sync and supported-browser background sync. | First visit must be online over HTTPS or localhost. Live APIs, external map tiles and uncached information require connectivity. Keep the device until its pending count reaches zero. |
| Multilingual alerts | English, Hindi, Assamese and Bengali alert summaries in Early Warnings and the warning banner. Per-recipient WhatsApp language. | Incident-specific English details and SOPs remain visible. This is not automatic translation of arbitrary officer notes. Review local-language wording before operational use. |
| Real notification workflow | Existing durable Twilio WhatsApp delivery queue retained and extended to choose a language-specific approved template. | Requires server credentials, an approved sender/templates, recipient opt-in and enabling delivery. The delivered status comes from Twilio, not merely submitting a request. |
| Satellite/NDVI integration | Field Operations → Satellite NDVI fetches a real MODIS observation; Prediction Engine can explicitly load that saved observation into a simulation. | NASA ORNL DAAC service access required. 250 m / 16-day composite, not live imagery. Only good-quality pixels accepted. Observations older than 32 days are marked stale and cannot be loaded into the simulator. Operational predictions are not silently changed. |

## Apply the update

1. Back up the deployed database and your current application folder.
2. Replace application source with this version, retaining your existing `.env`, production environment variables and database. Do not copy development test databases into production.
3. Build the frontend using the existing commands:

   ```sh
   cd frontend
   npm ci
   npm run build
   ```

4. Run the backend as before, with its existing dependencies and database URL:

   ```sh
   cd backend
   python -m pip install -r requirements.txt
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

   Run each `cd` from the project folder. The existing Docker/Render build also runs the updated frontend build automatically.

5. Startup creates three new tables if absent: `road_segments`, `satellite_observations` and `whatsapp_recipient_languages`. No existing table is dropped or altered. Existing recipients default to English; older reports remain readable and retryable.
6. After redeploying, close old app tabs/windows and reopen online so the new service worker can activate. Do not clear site storage while reports are pending.

The supplied ZIP includes rebuilt `frontend/dist`. No dependencies were added to the application package or backend requirements. The online font choice is retained; fonts now load without blocking offline startup, and Leaflet CSS is bundled locally.

## Offline use

Visit the built app online once and allow its service worker to install. Use your browser's Install app / Add to Home Screen command where available. The field-report screen then reopens using the cached shell and saved location list. Cached information is not a live hazard feed.

Reports are written to IndexedDB before upload. Successful uploads remove the local copy; failures remain listed with their reason and can be retried or exported. Failed items do not prevent attempts on other items. Browser Web Locks coordinate page/worker uploads where supported, and server submission IDs prevent duplicate records. Retry delays increase up to five minutes; reconnect and manual sync can retry immediately.

For deployments with an access key, the key normally stays in the browser session. The optional checkbox stores it only with that pending report so a background worker can authenticate after the page closes. Use this only on a trusted device. Successful upload or discarding the report deletes its saved key. Exported reports do not contain the key. If this option is not selected, open the app and re-enter the access key when necessary.

Background Sync depends on browser support and scheduling; it is not guaranteed to run immediately after the app closes. Foreground retries and the Sync button remain available. Browser storage quotas, clearing site data or device loss can remove unsent work; export pending reports when needed.

## Roads

Register at least two vulnerability assets, then create a road connection between them. Supply its observed status, time and survey/officer reference. Optionally provide a WGS84 line as `[[longitude, latitude], ...]` from the first asset to the second. Without geometry, the map displays a dashed, explicitly schematic connection between endpoints.

Deleting an endpoint asset makes a connection unknown. Reconfirm observations after 24 hours. The connectivity result finds the fewest recorded open links; it is not a live traffic service or an approved evacuation route. Road status is separate from the existing asset access field and does not change existing priority-score calculations.

## Multilingual WhatsApp

Follow `TWILIO-SETUP.md` for the existing sender, credentials, access key, opt-in and activation workflow. Keep `TWILIO_CONTENT_SID` for the existing English template, or configure an English entry in the mapping below.

Create and approve a Content Template in each required language, then set the backend variable:

```dotenv
TWILIO_CONTENT_SIDS={"en":"HX_REPLACE_WITH_APPROVED_ENGLISH_SID","hi":"HX_REPLACE_WITH_APPROVED_HINDI_SID","as":"HX_REPLACE_WITH_APPROVED_ASSAMESE_SID","bn":"HX_REPLACE_WITH_APPROVED_BENGALI_SID"}
```

Replace these explanatory placeholders with actual 34-character `HX…` SIDs; placeholders are intentionally not accepted. Twilio credentials and template IDs belong on the backend, not in frontend variables.

Use the same five template variables:

1. Severity (translated for the selected language)
2. Location name
3. Risk score
4. Response guidance (localized general guidance for non-English templates)
5. Alert ID

Choose the recipient's language during registration. Existing recipients remain English; to change a recipient, remove and register them again with current consent. A missing template leaves delivery pending/retry with an explanatory error, rather than sending in an unintended language. It is cancelled once the underlying alert is no longer eligible. Template language must match its mapping key.

No messages were sent to real phones during development. Test delivery with your own opted-in test recipient after setup. Demo/seeded/simulated alerts remain excluded from the existing operational notification workflow.

## Satellite observations

Select a monitoring site and fetch its latest MODIS composite. The backend requests NDVI and pixel-reliability bands from NASA ORNL DAAC, accepts reliability `0`, applies the product scale `0.0001`, and stores source/date/quality metadata. Cloud, snow, marginal, missing and out-of-range pixels are rejected. Provider errors retain the previous observation and show a failure instead of fabricating a value.

Successful lookups are cached for one hour. In Prediction Engine, “Use saved satellite NDVI in simulation” loads a non-stale saved value. Presets or manual edits can still change the simulator inputs. This integration does not automatically replace operational telemetry or retrain the model.

Provider scaling, quality rejection and failure handling were tested with controlled responses. An end-to-end live satellite retrieval could not be verified in the development environment; verify provider reachability from your deployment. No external NDVI subscription credentials are embedded.

References: [ORNL DAAC web service](https://modis.ornl.gov/data/modis_webservice.html), [ORNL DAAC response/quality-control tutorial](https://github.com/ornldaac/modis_restservice_qc_filter_Python), [Twilio Content API](https://www.twilio.com/docs/content/content-api-resources).
