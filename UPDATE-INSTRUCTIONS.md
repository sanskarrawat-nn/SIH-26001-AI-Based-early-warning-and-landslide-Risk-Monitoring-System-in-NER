# NER–LEWS frontend update

This is a changed-files-only update for your uploaded landslide-early-warning-system(3).zip.
It is not a standalone application. Apply it inside your existing GitHub project.

## Install

1. Make a backup or commit any work already in your existing project.
2. Extract this update ZIP into a temporary directory.
3. Copy the included `frontend` directory into your existing project root (the directory already containing `frontend` and `backend`). Merge folders and replace the listed files. Do not place a second frontend folder inside frontend.
4. Keep your existing database, environment files, dependencies and Git folder.
5. In the terminal in your existing project root, run:

```sh
cd frontend
npm run build
cd ..
git status
git add frontend/src/App.tsx frontend/src/index.css frontend/src/command.css frontend/src/components/layout/Navbar.tsx frontend/src/components/common/AssignmentProgress.tsx frontend/src/pages/AccessPortal.tsx frontend/src/pages/DashboardPage.tsx frontend/src/pages/ResponsePage.tsx
git commit -m "Improve landslide dashboard navigation and response forms"
git push
```

If dependencies are not already installed, run `npm ci` in frontend before building.
For local development restart your existing frontend dev server and reload the page.
Production deployments must run their normal frontend build/deployment process; this update does not deploy automatically.
If your deployment explicitly tracks built frontend/dist files, inspect and commit those generated changes as your existing deployment requires.

## Changed files

- frontend/src/App.tsx — administrator/coordinator layout wrapper.
- frontend/src/components/layout/Navbar.tsx — all ten sections in grouped navigation, desktop collapse, mobile menu, siren control and warning count.
- frontend/src/pages/DashboardPage.tsx — terrain-themed introduction and map/warning/field/response shortcuts, with all existing dashboard components retained.
- frontend/src/pages/AccessPortal.tsx — shared account styling and role-specific dashboard action buttons; existing login and permissions retained.
- frontend/src/pages/ResponsePage.tsx — valid status choices and example placeholders.
- frontend/src/components/common/AssignmentProgress.tsx — readable assignment steps and server-compatible status options.
- frontend/src/command.css — responsive navy/teal theme, form styling, focus states and reduced-motion support.
- frontend/src/index.css — import the new presentation stylesheet.

## What changes on screen

Administrator and coordinator sections are grouped under Monitor, Respond and Manage. Every existing heading remains available to the same roles as before. On desktop, navigation can collapse to labelled-on-hover icons; on smaller screens use Explore sections.

The dashboard introduces the monitoring-to-response workflow with direct actions. Field/public dashboards have a report shortcut. Hospital, rescue and police dashboards have an assignments shortcut. Existing role data, warning cards and responder overview remain available.

The assignment form now shows Awaiting → Accepted → On the way → Arrived → Completed and only offers valid actions. Accepted, travelling and arrived teams can also keep their current status while updating a note/ETA. Coordinator cancellation remains available. The server still checks permissions, versions and transitions. An update from another session can still require refreshing data.

## Verification and limits

- TypeScript and production Vite/PWA build passed.
- Component checks passed for all ten headings, coordinator filtering, four active assignment states, same-status updates and coordinator-only cancellation.
- Backend source and database are not included or modified by this update.
- Browser visual/interaction checking was blocked by a Chromium startup crash in the editing environment. Check desktop and phone layouts after applying the files.
- No real SMS/WhatsApp notifications were sent. No live deployment was performed.

## Quick check after installing

1. Administrator: open each navigation section, collapse/expand navigation, and check the siren button.
2. Resize to phone width: open/close Explore sections and confirm the page fits.
3. Field officer: open Report an observation and check evidence previews and validation.
4. Responder drill: Accept assignment, then On the way, then Arrived, then Complete assignment. Save each step before continuing.
5. Coordinator: confirm verification, evidence and incident controls still open normally.

This update contains no new runtime dependencies and no backend changes.
