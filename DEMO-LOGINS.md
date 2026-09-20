# Demo login credentials

These seven accounts are already created in the bundled SQLite database. Select the role first, then enter its username and password. Treat these as demo credentials and change them before exposing the app publicly.

| Role | Username | Password |
| --- | --- | --- |
| Administrator | `demo_admin` | `Ews!5c141ccbd1beac` |
| Government / disaster coordinator | `demo_coordinator` | `Ews!3db9ef43f982ce` |
| Field officer | `demo_field` | `Ews!4ab6e9df6865bc` |
| Rescue / evacuation team | `demo_rescue` | `Ews!0a013faf863011` |
| Hospital / ambulance team | `demo_medical` | `Ews!63f6267f286e15` |
| Police | `demo_police` | `Ews!d62f4002c0eb6d` |
| Public user | `demo_public` | `Ews!262fb1e28e38da` |

## Using these accounts

- Start the app with the bundled `backend/landslide_system.db` and the default SQLite database configuration. No bootstrap ADMIN_USERNAME/ADMIN_PASSWORD is needed to sign into the named demo administrator account.
- If your app uses PostgreSQL or an existing deployed database, these accounts will not appear there automatically. Do not replace a populated production database with this demo database.
- The three demo response teams have messaging channels disabled and availability set to UNAVAILABLE. They are not real rescue teams, hospitals or police units.
- The administrator can change passwords under User Accounts. Other named accounts can use My password where shown; coordinator passwords can be reset by the administrator.
- The database stores password hashes; this file intentionally contains the requested demo credentials. Do not publish it or retain it in a public repository.
