> Latest workflow update: [VERIFIED-RESPONSE-GUIDE.md](VERIFIED-RESPONSE-GUIDE.md) supersedes the earlier manual field-report-to-response instructions. Existing role accounts are unchanged.

> This copy includes seven pre-created demo accounts. See [DEMO-LOGINS.md](DEMO-LOGINS.md). The setup instructions below also cover deployments using a separate existing database.

# Role logins and permissions

This release uses one shared, teal login form: select a role first, then enter a username/email and password. It provides seven role-specific workspaces to the existing landslide app. It is an update to the response-coordination release. The app has not been deployed automatically, and no real alerts or messages were sent while developing this release.

## Role options and compatible login URLs

Use your app's existing domain followed by the path below. For local production serving, start with http://127.0.0.1:8000.

| Role | Login path | Workspace and permissions |
| --- | --- | --- |
| Administrator | `/login/admin` | All existing dashboard tools, settings, monitoring, response coordination and the new User Accounts page. Creates accounts, assigns roles/teams, resets passwords and disables access. |
| Government / disaster coordinator | `/login/coordinator` | Risk dashboard, map, predictions, history, warnings, field operations and response coordination. Reviews reports, assigns field officers, approves team dispatch and manages resources. Cannot manage user accounts, messaging credentials, ML models or system settings. |
| Field officer | `/login/field` | Area warnings, own reports and assigned reports. Submit GPS/manual coordinates, photos and video; amend own unreviewed/rejected reports; add progress notes to assigned reports. Cannot verify reports or dispatch teams. |
| Rescue / evacuation team | `/login/rescue` | Area warnings, assigned incidents, team acknowledgement/progress, resource requests, team availability and shelter information. |
| Hospital / ambulance team | `/login/medical` | Assigned response incidents, acknowledgement/progress, resource requests, manually reported beds/ambulances/personnel and shelter information. |
| Police | `/login/police` | Assigned incidents and response progress, own team availability, resource requests and updates to registered road conditions. |
| Public user | `/login/public` | Area warnings and the user's own observation reports. No other users' reports, internal incident records, recipient phone directories or staff resolution notes. |

`/login` and the signed-out home page show the shared login form with a role dropdown. Older `/login/<role>` links still work and preselect that role in the same form. Hospital and ambulance personnel share the medical role; each account is attached to its own hospital or ambulance team. Roles are not self-selected during registration. Public accounts are also provisioned by the administrator in this version.

## First-time setup

1. Back up your existing deployed database and environment configuration before updating. Extract this ZIP to a new folder; keep your existing production database rather than replacing it with a bundled demonstration database.
2. Copy the root `.env.example` to `backend/.env` for local use, or configure the equivalent variables in your hosting service. Preserve your existing weather, database and Twilio configuration.
3. Set `ADMIN_USERNAME` to a username you choose and `ADMIN_PASSWORD` to a strong password of at least 12 characters. The bundled SQLite database now includes demo accounts documented in DEMO-LOGINS.md; these environment credentials are an optional separate bootstrap administrator. Keep `RBAC_ENABLED=true` (also the default when absent).
4. Install the existing backend dependencies: in `backend`, run `python -m pip install -r requirements.txt` in your virtual environment.
5. Start the backend from `backend`: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. The ZIP includes a rebuilt `frontend/dist`, which FastAPI serves directly. If using the frontend development server, run `npm ci` and `npm run dev` in `frontend` instead.
6. Open `/login/admin`, sign in with your configured administrator credentials, and open **Response Coordination → Team directory**. Register rescue, hospital, ambulance and police teams as needed. Drill data must be clearly labelled; don't use real contacts for test exercises.
7. Open **User Accounts**. Enter the user's name, unique username, assigned role and password. Rescue, medical and police accounts require an active team of the matching capability. Administrator, coordinator, field and public accounts do not require a team.
8. Give each person their role-specific URL and credentials privately. Use separate browser profiles to demonstrate concurrent users; one browser profile has one active role session.

Keep HTTPS enabled for deployed sites. Cookies are HTTP-only, SameSite=Lax and secure on HTTPS; `ADMIN_COOKIE_SECURE=true` can be set explicitly behind an HTTPS reverse proxy. Retain existing allowed-origin configuration for separately hosted frontend/backend deployments. Configure `ADMIN_SESSION_DB` on persistent storage if retaining bootstrap administrator sessions. Named user accounts and sessions use the configured application database.

The new role-binding table is created at startup. Existing responder IDs, password hashes, team records, incidents and reports are retained. Existing rescue, hospital/ambulance and police responders can sign in through their corresponding new role pages. Legacy backup-coordinator team accounts remain response-only accounts until an administrator explicitly grants the coordinator role; team membership alone never grants dispatch authority. Use User Accounts to review these legacy accounts before adoption.

## Account management and session behaviour

- Edit an account to change its role/team, reset its password, or disable it. Changes revoke its existing named/legacy responder sessions.
- The administrator cannot demote or disable their own named account through that same session. Use another administrator or the server-configured bootstrap administrator.
- Field/responder/public users have **My password**. Named administrators can reset their password in User Accounts. The bootstrap administrator's credentials are changed in backend environment settings.
- Role accounts expire after eight hours. The existing bootstrap administrator session retains its prior 30-day lifetime.
- Wrong-role credentials are rejected: a valid public password cannot be used on the administrator page.
- Signing in replaces prior role/legacy sessions in that browser. Sign out using the top bar to switch roles. Session validity is rechecked on browser focus and every minute; every protected API operation independently verifies access.
- Passwords use salted PBKDF2 hashes; session tokens are stored hashed. Login attempts are throttled per IP. Account changes and role sign-ins are audited.
- Role permissions are enforced in the backend. Hiding dashboard tabs is not the security boundary.

## Field reports and assignments

Public and field users use **My reports**. Their name and ownership are attached by the backend, regardless of the name sent in the request. They cannot read or amend somebody else's report. A public/field submission does not automatically trigger emergency dispatch.

For field assignment, coordinators use **Field Operations → Response queue → Field report review**. When the existing assignment prompt appears, enter the field officer's exact username (or account ID), not their display name. That officer sees the report in **My reports and assignments** and can add field updates until it is resolved or rejected. Updates are visible to coordinators and do not change verification status.

The new role report form accepts GPS/manual coordinates, optional images and videos. It currently requires connectivity and does not add a separate offline outbox; keep the form open after a failed submission. The existing offline Field Operations outbox remains available to administrators/coordinators. Old reports without ownership are not automatically exposed to public/field accounts; assign a report deliberately if field access is needed.

## Response-team demonstration

1. Administrator registers an exercise rescue team and a rescue account.
2. Coordinator signs in on `/login/coordinator`, creates a **drill** incident and explicitly approves an assignment to that team.
3. Rescuer signs in on `/login/rescue` in a separate browser profile, opens **Assignments and availability**, and sees only the team's assigned incidents.
4. Rescuer advances through accepted, en route, arrived and completed, providing notes. Coordinator refreshes to see progress.
5. Repeat with a hospital/ambulance or police team. Medical availability is manually reported; it does not reserve hospital beds. Police can update registered road records, which still require local verification.

Drill notifications remain simulated. Real SMS/WhatsApp delivery still requires the existing Twilio sender/template/consent configuration and explicit dispatch approval. Different role pages do not change the prediction model or provider delivery requirements.

## Verification and limits

- 106 backend tests passed: 77 existing regression tests plus 29 role/access tests.
- Existing regression tests explicitly use the legacy single-operator guard setting; new access tests enable the production-default role guard. This distinction is documented in `backend/tests/conftest.py`.
- Access tests cover all seven login roles, wrong-role rejection, privilege escalation, bootstrap login, ownership, assigned field updates, team-scoped incidents, session expiry/revocation, public warning redaction, team mismatch/disable, password changes, CSRF rejection and login throttling.
- TypeScript compilation, Vite production build and PWA generation passed.
- Visual/browser interaction testing could not be completed because Chromium exits at launch in this workspace. Perform a browser smoke test on your target devices before deployment.
- This is still a prototype. No guarantee of zero errors or operational disaster-readiness is implied. The prediction model, its synthetic-data limitations and existing response-coordination limitations are unchanged.

For backend tests, run `python -m pytest -q` from `backend` after installing requirements and test dependencies. Tests use isolated fixtures and simulated messaging. Never point test scripts at a production database.

## Screenshot-style login update

The role-card chooser has been replaced with the requested centered teal/dark login panel. Select your role, enter your username/email and password, then click LOGIN. Credentials are disabled until a role is selected.

An administrator can now create an account using either a username or an email address as its login ID. Enter that exact identifier on the login page; a separately stored email alias is not inferred for existing username-only accounts. No email verification or email-based password reset service is added.

Remember username saves only the identifier on that browser, never the password. Forgot password and Request an account display administrator-contact instructions. They do not create privileged accounts or pretend to send emails.

For this UI update, the production frontend build and 31 role-access tests passed, including email identifiers and malformed-email rejection. Earlier full-suite results above remain the results of the prior role release. Visual browser testing remains unavailable in this workspace.
