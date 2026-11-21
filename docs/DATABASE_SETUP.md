# Database setup

The schema contains the 25 requested entities plus an internal API quota table
and migration tracking. SQLAlchemy types, primary/foreign keys, owner indexes,
unique/check constraints and timestamps are defined in `database/models.py`.
Investigation-linked rows use composite `(investigation_id, owner_id)` foreign
keys; source, device, URL-domain and graph references preserve owner identity.
Graph edges require an evidence FK; no graph records are seeded.

## Local SQLite

Default `.env.example` uses `sqlite:///./data/fraudshield.sqlite3`. Run explicitly:

```bash
.venv/bin/python -m backend.app.database.migrate
```

Migrations are ordered SQL revisions with recorded SHA-256 checksums. Applied
files must never be edited; create a new revision. Startup does not run DDL.
Missing or mismatched migrations yield explicit unavailable status. SQLite
foreign keys are enabled for every connection. Tests exercise actual storage,
rollback, owner filters, composite constraints and cascade deletion.

## Supabase PostgreSQL — live verification pending

Use a dedicated project. Obtain its real PostgreSQL TLS connection and Auth
project URL. Install the optional, release-pinned driver:

```bash
.venv/bin/python -m pip install -r backend/requirements-postgres.txt
```

Configure `DATABASE_URL` using `postgresql+psycopg://`, URL-encode credentials,
and require `sslmode=verify-full` plus the appropriate trusted CA/root certificate
configuration. Native database credentials are backend-only. The driver and
Supabase network connectivity were unavailable here, so PostgreSQL execution
and RLS enforcement are not claimed tested.

Apply revisions using the real migration-owner credential. The PostgreSQL
security revision expects actual Supabase `auth.users`, `auth.uid()`, `anon`
and `authenticated` roles. It links the public user mirror to `auth.users` and
creates a `fraudshield_api` role with NOLOGIN, NOSUPERUSER and NOBYPASSRLS.
No password or fake account is inserted.

Provision this role's actual login secret through secure administrative tools,
then enable LOGIN. Do not put that secret in scripts, client builds or source
control. Grant no superuser/BYPASSRLS or privileged role memberships. Set the
API's connection to this role, keeping migration/maintenance credentials separate.

The migration enables and forces RLS on every application table and migration
tracking; revokes client/default-public table access; grants the API role only
required operations; and enforces `auth.uid()` ownership on private tables.
System model/provider/quota rows are backend-managed. The table owner retains
maintenance rights. Direct Android writes cannot forge predictions or evidence.

Each owned transaction sets verified JWT subject/claims using parameterized
transaction-local settings. Application queries also filter ownership. Runtime
refuses a PostgreSQL role other than `fraudshield_api` or one with bypass/superuser
privileges. Foreign keys prevent cross-tenant child references. Auth user deletion
cascades the associated public mirror/private records.

Analysis first commits a short authorization/quota/device-check transaction,
then performs model/provider work without holding a database write transaction.
Persistence commits the complete validated response and normalized evidence
before `201` is sent. Storage failure returns an error and rolls back evidence.
History uses short function-scoped transactions and hides expired records.

SQLAlchemy disables prepared-statement reuse for transaction-pooler compatibility
and sets bounded pool/connect/statement/idle timeouts. Verify the project's actual
pooler host/port, certificate and role configuration rather than copying an
unverified connection example.

Official references:
https://supabase.com/docs/guides/auth/jwts and
https://supabase.com/docs/guides/database/postgres/row-level-security .

## Retention

Run the maintenance command on a schedule with a separate database owner/maintenance
credential. The API role cannot perform cross-user PostgreSQL cleanup.

```bash
.venv/bin/python -m backend.app.database.retention
```

It deletes actual expired investigations, cascades evidence/predictions/URLs,
removes orphan domains, and removes audit metadata older than configured policy
(default 180 days) and old quota buckets. It prints actual deletion counts; it
does not create dashboard statistics. Backups and legal holds need separate
deployment policy. Full account-erasure API and Supabase Storage are pending.


Correlation adds sqlite/0002_correlation_indexes.sql and postgresql/0003_correlation_indexes.sql. Apply explicitly with the existing migration command. Deletion/retention now prune orphan graph nodes while preserving nodes with surviving observation edges.
