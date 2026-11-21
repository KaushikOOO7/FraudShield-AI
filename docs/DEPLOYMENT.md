# Deployment status and commands

Docker and GitHub Actions definitions are provided. They have not been built,
deployed or run on GitHub in this session. Local Python/ASGI/database tests are
the verification evidence. The visible managed `.git` directory is empty and
read-only; no commit, push or published service is claimed.

Development Docker sequence, after actual configuration and local training:

```bash
docker compose build
docker compose run --rm api python -m backend.app.database.migrate
docker compose up api
```

Compose exposes localhost only and mounts the trusted model directory read-only.
Its named database volume is separate from raw training data. Ensure the container
UID (1000 by default) can read the trained artifact and write its data volume.
The image excludes datasets, secrets and binary model artifacts; absent/unreadable
models remain unavailable. Migrations are an explicit command, never automatic
API startup. PostgreSQL requires the optional driver and separate migration role;
adapt/build the image with `backend/requirements-postgres.txt` before production.

Production needs a configured Supabase Auth project, verify-full PostgreSQL
TLS/CA, restricted API role/RLS, HTTPS gateway and explicit allowed hosts. If TLS
terminates at a proxy, configure Uvicorn's trusted forwarded IPs to that actual
gateway; do not accept spoofed forwarding headers from arbitrary clients. The
HTTP localhost Docker health probe is development liveness only; use a deployment-
appropriate HTTPS probe when APP_ENV=production.

The tested OpenCV wheel is the full distribution; native GL/GLib runtime packages
are included for image parsing. Docker build remains unverified here. Replacing
it with a headless wheel requires compatibility verification, not an assumed
silent dependency swap.

Schedule retention with the maintenance credential. Configure shared ingress
limits, outbound destinations, operational log retention/jurisdiction, backup
recovery and alerting for real provider/database failures. Verify the deployment
with genuine, authorized inputs before claiming production readiness.

GitHub Actions acquires the original licensed UCI source, trains the fixed
baseline and runs real model/API/security tests. It requires network access.
Download failure stops the job; no fabricated corpus or skip substitutes for the
required model tests. A source checksum change results in a different model
version. Source definitions: https://github.com/actions/checkout and
https://github.com/actions/setup-python .
