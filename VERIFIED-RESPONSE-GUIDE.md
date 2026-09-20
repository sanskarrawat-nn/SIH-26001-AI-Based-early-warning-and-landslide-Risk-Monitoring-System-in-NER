# Verified landslide reports → hospital, rescue and police alerts

This update changes the field-report workflow and adds richer responder dashboards. It retains the existing model, role logins, accounts, database records, team progress, resources, shelters and messaging configuration. It has not been deployed to your live website.

## What happens now

1. **Field officer reports the site.** Select `landslide`, enter the monitoring site, actual coordinates/GPS, observation time, severity and observations. Add landmarks/site details, estimated people affected, reported injuries and access conditions when known. A field-officer landslide report must include at least one photo or video. Other observation categories retain their existing behaviour.
2. **Coordinator receives an in-app review item.** The dashboard verification inbox refreshes every 15 seconds. Open **Response Coordination → Verify field reports** to inspect photos/video, coordinates and reported conditions. Submission alone creates no team alert or external message.
3. **Coordinator reviews recipients.** The preview lists all active rescue, hospital/ambulance and police teams whose coverage includes the report's site (or `*`). It also shows missing team groups, unavailable/stale teams, missing channels and incomplete external messaging configuration.
4. **Coordinator chooses Verify & alert response teams.** Supply a verification reason, approve the recipient list and acknowledge any listed gaps. This single action marks the report verified, creates one response incident, creates team acknowledgement requests and queues each selected team's configured SMS/WhatsApp channels. There is no second manual incident-creation/assignment step.
5. **Teams respond.** Their dashboards show the incident, coordinator verification, estimated affected/injured counts, access condition, location and team task. Open the incident to view the frozen photo/video evidence and acknowledge/update progress, ETA and resource requests.

The existing Field Operations `verified` action now opens this workflow for landslide reports. Older direct verification endpoints reject attempts to skip it. Other report categories and the existing manual incident workflow remain available.

## Recipient and delivery behaviour

- Alerts target **registered, active teams covering the site**, not every hospital or police station in the country. Register and maintain teams under Response Coordination → Team directory.
- Rescue, hospital, ambulance and police teams are included. Multiple covering teams can all be notified. The coordinator sees the exact list before approval.
- A busy/unavailable/stale team can receive an alert asking it to acknowledge and report readiness. Alerting it does **not** declare it available, reserve beds or deploy personnel automatically. Tasks explicitly request coordination with the duty coordinator.
- If a group is missing, a warning is shown and explicit acknowledgement is required. Verification does not invent recipients or claim that a missing group was alerted. If no relevant team exists, verification is blocked.
- A team without SMS/WhatsApp channels still receives its in-app incident, provided its staff have accounts attached to that team. The interface labels it **In-app only**.
- External channel entries are durable queue records. Queued, simulated, sent and delivered are different states. Provider delivery is not team acceptance.
- The existing 30-minute queue expiry, uncertain-delivery handling, acknowledgement reminders and escalation behaviour still apply. This workflow does not automatically pick a backup coordinator; one should be handled through the existing coordinator workflow/local procedure.
- Retrying approval uses the same report-derived incident ID and does not create duplicate messages. A report already linked to a manual incident must be handled through that incident instead.
- The report and its verification/evidence/alerts are saved in one database transaction. Stale report/team previews are rejected and must be refreshed.

## Exercise vs real notifications

**EXERCISE is checked by default.** Exercise incidents show an EXERCISE label and the worker simulates external messages. The field-submission page does not send messages itself.

For real messaging:

1. Register real covering teams with correct contact numbers and recorded consent. Select SMS and/or WhatsApp per team.
2. Configure the existing `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_SMS_FROM` or SMS Messaging Service, `TWILIO_WHATSAPP_FROM`, and approved `TWILIO_DISPATCH_CONTENT_SID` template.
3. Set `PUBLIC_APP_URL` to your HTTPS app address and `DISPATCH_MESSAGING_ENABLED=true`.
4. In the verification preview, review any configuration gaps and uncheck EXERCISE only for a real approved response.
5. Monitor notification delivery and team acknowledgement in the incident screen.

No real notifications were sent during development/testing. The bundled demonstration teams remain unchanged: their external messaging channels are disabled and their manually reported availability may be UNAVAILABLE. Do not mistake these demo teams for real organisations.

## Dashboard additions

| Role | New information |
| --- | --- |
| Government coordinator / administrator | Live verification-inbox count, evidence review, recipient preview, coverage/configuration gaps, Verify & alert action, linked incident and verification history. |
| Hospital / ambulance | Pending/overdue acknowledgement counts, active/completed assignments, reported beds and ambulances, personnel, injured/affected estimates, access conditions, verified site evidence and response tasks. |
| Rescue | Pending/overdue acknowledgement counts, active/completed assignments, personnel/equipment, reported affected counts, site access, recently reported open shelter capacity, evidence and response tasks. |
| Police | Pending/overdue acknowledgement counts, active/completed assignments, personnel/equipment, recorded blocked/restricted/unknown roads, verified site details and response tasks. |
| Field officer | Photo/video preview, required evidence for landslide reports, site landmarks, affected/injured estimates and access-condition fields. |

Responder overview data refreshes every 15 seconds while that page is open. New incident arrivals show an in-app banner. Search/filter the incident list, open the site map or open the alert to respond. The detailed response editor retains its explicit Refresh data action so background polling does not replace unsaved form edits.

Capacity counts are manually reported. Road and shelter summaries are directory totals, not incident-specific safe-route recommendations. Unknown counts remain “Unknown”; they are not treated as zero. Reported figures and coordinator verification do not substitute for independent field/medical validation.

## Login interactions

The same teal role-first form now includes:

- Step indicator: choose role, then sign in.
- Live description of the selected role's workspace.
- Show/hide password control and Caps Lock warning.
- Busy indicator during sign-in, keyboard focus highlighting and modest transitions.
- Reduced-motion support.

Roles and backend permissions are unchanged. Existing usernames/passwords in your uploaded database are preserved. No new credentials are assigned in this update.

## Upgrade and demonstration

Back up your current database and deployment settings. Use the updated source/build with your existing database. A new `verified_incident_evidence` table is added automatically at backend startup; existing tables and data are retained. Do not replace a populated production database with a demo database.

For a local demonstration:

1. Sign in as field officer and submit a landslide report with a small photo or video.
2. Sign out and sign in as government coordinator. Open the verification inbox.
3. Inspect the evidence and team list. Leave EXERCISE checked, acknowledge demo-team/configuration gaps and choose Verify & alert response teams.
4. Sign in separately as medical, rescue and police users. Each account must be attached to an active team covering the report's site. Observe the new incident on its dashboard.
5. Open evidence, accept the request and update progress. Check the incident from the coordinator account.

Only authorized coordinators and assigned response teams can fetch the evidence snapshot. Public users and unrelated teams cannot access it. Photos/videos are loaded on demand rather than included in every dashboard poll.

## Verification

- Full backend suite: 117 tests passed after resolving compatibility with older offline reports.
- Extended verified-response tests: 11 passed, including protection against pre-existing manual incidents and mocked SMS/WhatsApp provider routing.
- Production frontend TypeScript, Vite and PWA build: passed.
- Checked evidence requirements, no alerts before verification, coordinator-only approval, recipient coverage, missing-team handling, duplicate retries, preview conflicts, evidence ownership/snapshot integrity, drill simulation and real-mode queuing with messaging disabled.
- Visual browser testing remains unverified: the available Chromium runtime previously failed to launch in this workspace. Test the interface on your target browsers before deployment.

The system remains a prototype with the existing model and operational limitations. This update does not provide automatic photo-based landslide detection or guarantee real-world delivery.
