> Role-login release: account setup and sign-in instructions are superseded by [ROLE-LOGIN-GUIDE.md](ROLE-LOGIN-GUIDE.md). The response workflow below is retained.

# Response coordination: setup, features and demonstration

This release extends the uploaded monitoring app with a separate Response Coordination module. It does not automatically dispatch teams from a model score. Existing prediction, field reporting, monitoring and crisis-alert workflows remain available.

## What is included

| Feature | Behaviour |
|---|---|
| Team directory | Register rescue, hospital, ambulance, police and backup coordinator organisations, their location, coverage site IDs, contacts, channels and consent. |
| Availability | Record available/busy/unavailable status, personnel, ambulances, beds and equipment. Availability older than 12 hours becomes stale and cannot be used for a new assignment until refreshed. Values are manually reported, not reserved inventory. |
| Responder accounts | Coordinators create named accounts tied to one team. Passwords are salted and hashed. Responders sign in with an eight-hour HTTP-only session and can update their own team's assignments and availability. Disabling an account or resetting its password revokes sessions. |
| Incident drafts | Create a precautionary-warning or reported-landslide record with coordinates, severity, description and affected-person estimate (unknown allowed). A reported landslide is not independently confirmed by software. |
| Existing-app links | Early Warnings and reviewed field reports have Request emergency response buttons. They prefill an incident draft. Linked reports must have been reviewed and must match the selected monitoring site. |
| Officer-approved dispatch | Select a team, enter a specific task and approval reason, and confirm approval. No draft sends a notification. No prediction or report submission automatically dispatches a team. |
| Dual-channel notifications | Separate SMS and WhatsApp outbox records for each selected team channel. Dispatch uses its own enable flag and WhatsApp template; no dependence on the existing WhatsApp recipient registry. |
| Team progress | Awaiting → Accepted → En route → Arrived → Completed. Teams may decline or report unavailability. An administrator can cancel assignments. Delivery status never marks an assignment accepted. |
| ETA and notes | Team members enter an ETA in minutes and progress notes. ETA is a manually reported estimate with update time, not GPS tracking or routing time. |
| Reminders and escalation | One reminder after the chosen acknowledgement interval, then one escalation after twice that interval. Declined/unavailable assignments escalate on the next worker pass. The configured backup coordinator is notified and receives read access to the escalated incident. Only an administrator can approve further assignments. |
| Suggestions | Lists teams covering the monitoring site, prioritising fresh availability, then straight-line distance. Team type and reported capacity are shown for human selection. Capability selection is manual. Distance is not travel time. |
| Resource requests | Assigned teams or coordinators can request quantities of resources. Coordinators record Requested → Allocated → Fulfilled or Cancelled. This does not automatically order equipment or reserve ambulances/beds. |
| Shelters | Register shelters and update capacity, occupancy, status and source. Data older than 12 hours is marked stale. This is a directory, not an accommodation booking system. |
| Duplicate incidents | Suggests open records at the same monitoring site created within 24 hours and with the same drill mode. A coordinator can merge an undispatched draft into an open incident. Both histories retain the merge; linked report IDs are collected. Already dispatched incidents are not automatically merged. |
| Incident history and export | Coordinator notes, approvals, status changes and resource actions are recorded. Download an incident JSON report including recorded acknowledgement, arrival and completion durations. Durations depend on entered updates, not independently verified arrival. |
| Drill mode | Enabled by default on a new incident and immutable after creation. Every incident screen and export retains its drill flag. Messages are SIMULATED inside the backend: no Twilio calls, charges or real dispatch notifications. |
| Road context | Incident coordinates open a map. Existing Field Operations → Road connectivity remains the access-status reference. No automatic safe evacuation route is claimed. |

## Run the updated app

1. Back up your current database, environment configuration and model directory.
2. Extract this ZIP into a new project folder. Keep your existing production DATABASE_URL; never replace a production database with the ZIP's supplied sample database.
3. Install backend requirements, and install/build frontend dependencies if needed. The ZIP includes the production frontend build.

```sh
python -m pip install -r backend/requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Use the same Python environment as your existing app. Sign in as administrator through Settings, then open Response Coordination and click Refresh access. No new default administrator password is supplied.

New tables are created on startup; the existing table schemas are unchanged. The uploaded application database is preserved in the ZIP without the temporary test data. Credentials, session databases, dependency folders and test caches are excluded.

Use one application worker for this prototype's background schedulers. Version checks and unique message IDs protect against duplicate writes, but this release has not been validated as a distributed dispatch service. Keep the database and existing administrator-session path on persistent storage. Responder accounts/sessions, team data and dispatch outbox records live in the application database.

## Ten-minute local drill

1. Open Team directory. Register a team named **EXERCISE Rescue A** with kind RESCUE, coverage `*`, a fictional test contact such as `+15005550006`, and AVAILABLE status. Choose SMS and WhatsApp only for this isolated drill and enter `EXERCISE fixture only - no real recipient` as the source of the test setting. Do not reuse fictitious contact/consent records for live dispatch.
2. Add a hospital, police team and backup coordinator in the same way if you want to show the different roles. A COORDINATOR team is a backup contact; its responder accounts do not gain administrator privileges.
3. Under Responder accounts, create a named user with a password of at least 12 characters for Rescue A. Share credentials through your own secure process; the app does not email or text account passwords.
4. Create an incident draft at an existing site. Keep **EXERCISE — simulate messages only** checked. Use a title and description explicitly saying it is fictional. Set acknowledgement interval to one minute for a short demonstration and choose the backup coordinator.
5. Select Rescue A, enter its task and approval reason, check approval and click Approve and assign. Repeat for medical/police teams if appropriate. Their tasks are separately entered by the coordinator.
6. Click Refresh data after about ten seconds. The notification rows should say SIMULATED. Assignment status stays AWAITING.
7. Open a private window or separate browser profile, visit the app, open Response Coordination and sign in as the responder. Do not keep an administrator session in this profile; administrator access takes precedence when both sessions are present.
8. Accept the assignment, report an ETA, then move through En route, Arrived and Completed with notes. The coordinator clicks Refresh data to see updates. The UI does not currently push updates automatically.
9. Request two stretchers while the incident is active. In the coordinator profile, allocate and fulfil the request. Register a sample shelter to demonstrate occupancy.
10. Close the incident after all assignments and requests are completed or cancelled, then export its JSON report.

To demonstrate escalation, leave another assignment awaiting acknowledgement. A reminder is queued after one minute and a backup escalation after two minutes, evaluated on the ten-second worker cycle. Backup accounts can then view the escalated incident, but must contact the administrator to approve reassignment. Without a backup, the timeline records that coordinator action is required.

## Enable real notifications

Do this only after testing with your own consenting contacts and verifying that the intended response organisations have agreed to this process. Software does not enrol public emergency services automatically.

Set backend variables:

```dotenv
DISPATCH_MESSAGING_ENABLED=true
PUBLIC_APP_URL=https://your-app.onrender.com
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_SMS_FROM=+your_sms_capable_sender
# Or use TWILIO_SMS_MESSAGING_SERVICE_SID instead of TWILIO_SMS_FROM.
TWILIO_WHATSAPP_FROM=whatsapp:+your_approved_sender
TWILIO_DISPATCH_CONTENT_SID=your_approved_dispatch_template_sid
```

The separate dispatch flag does not change the existing SMS_ENABLED / WHATSAPP_ENABLED crisis-alert workflow. Each team must have the relevant channels and consent enabled. A usable HTTPS PUBLIC_APP_URL is required for live delivery. A link opens the Response Coordination page with an incident ID; it does not contain an access token or bypass sign-in. The URL is not a live GPS tracker.

The dedicated WhatsApp template must use five variables:

1. Message event and incident kind (DISPATCH, REMINDER, ESCALATION or CANCELLATION).
2. Incident identifier.
3. Latitude and longitude.
4. Assigned task.
5. Response page link.

Example template wording to configure and have approved:
`NEREWS {{1}}. Incident {{2}}. Coordinates {{3}}. Task: {{4}}. Sign in to respond: {{5}}.`

Do not substitute an unrelated existing crisis template. Both channels are independent; a failure of one does not block the other. SMS segmentation/provider charges and WhatsApp account/template restrictions still apply. See the official provider documentation: https://www.twilio.com/docs/messaging/api/message-resource

Create a new non-drill incident and explicitly approve an assignment only when you intend to notify the selected organisation. High risk by itself never confirms an accident.

## Delivery and cancellation details

- PENDING: not sent; configuration errors remain visible on the message row.
- SIMULATED: drill processed locally; nothing was sent.
- QUEUED / SENT / DELIVERED: provider transport states, not team acceptance.
- FAILED: rejected or retry limit reached; inspect the displayed provider error.
- RETRY: limited retry after rate limiting or connection failure.
- UNKNOWN: outcome uncertain; inspect Twilio before contacting again. There is no blind retry for uncertain outcomes.
- CANCELLED: recipient/assignment changed, incident closed, or the pending notification expired.

Pending notification attempts expire after 30 minutes. Expiry does not close the assignment. The worker rechecks incident state, recipient activation, selected channel, contact number and assignment status before sending. Already submitted provider messages cannot be recalled. A state change during an in-flight provider request may still allow that message to arrive.

Cancellation queues a cancellation notice to active team contacts with enabled channels and cancels obsolete pending dispatches when processed. For time-critical cancellations, coordinators should confirm by their established communication procedure; a queued cancellation is not confirmed receipt. If contact consent is removed or a team is deactivated, the app cannot notify that contact.

## Permissions and limitations

- Coordinator: existing administrator session or existing operations key; full dispatch administration.
- Responder: assigned incidents, own-team progress/resources and own-team availability. No team-directory administration or dispatch approval.
- Backup responder: read access to incidents escalated to its coordinator team. It cannot accept another team's task or approve new dispatches.
- All authenticated response users can read the shelter directory. No public incident feed is added.
- Disabling accounts or teams removes future responder access; current incidents remain in coordinator records for resolution.
- Drill mode is specific to this new module. It does not turn off the older crisis messaging workers globally.
- Resource, hospital and shelter capacity figures require human updates. No real hospital database, ambulance GPS or police control-room integration is claimed.
- Existing landslide-model and experimental-forecast validation limitations remain unchanged.

## Verification

The release is tested with isolated SQLite databases and mocked messaging. No real emergency teams were contacted. The included verification/dispatch-release.json records final test/build results and the changed-file list. Browser visual verification could not run because the available Chromium binary failed to start; TypeScript and the production build were checked. Production PostgreSQL, live Twilio accounts, physical response operations and load behaviour have not been validated here.
