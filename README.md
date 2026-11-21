# FraudShield AI

The first working feature is authenticated SMS investigation with a genuine
TF-IDF/Logistic Regression spam baseline, documented rules, redacted evidence,
SQLAlchemy storage, history and deletion. URL structure analysis and Google Safe
Browsing/VirusTotal adapters use the same investigation response contract.
URLhaus, PhishTank, AbuseIPDB, fixed-registry RDAP and crt.sh adapters are also connected; live verification requires configuration.
Evidence-backed SMS/URL/QR observation correlation connects stored, owner-scoped observations
through a persisted NetworkX graph, without changing investigation risk ratings.

The historical UCI model detects **spam/ham**. Indian financial-fraud,
multilingual and current-campaign performance remain unevaluated. Trained URL ML,
successful genuine APK parsing,
verified brand matching, caller reputation, advanced campaign correlation and
LangGraph remain pending. No users, incidents or threat reports are seeded.

Owner-scoped reports, watchlists and opt-in in-app alert history are implemented.
Reports are unreviewed submissions with no verified reputation claim. No push
notification or external message delivery is implied.

QR image decoding/UPI syntax validation and masked caller-format investigations
are implemented with explicit partial results. Neither invents a fraud model,
recipient verification or caller reputation.

APK upload/archive guards and an optional isolated Androguard adapter are present.
The parser is unavailable here; genuine static parsing remains unverified. The
optional Gemini endpoint selects existing evidence references only, with explicit
opt-in and validated structured responses. It has fixture tests and no verified
live provider call.

Reproducible raw-URL features, original-source acquisition and RF/XGBoost training
code are prepared. PhiUSIIL acquisition failed in the restricted environment;
there is no trained URL artifact or fabricated evaluation.

## Run locally

Python **3.14** is tested; this session used 3.14.4. Dependencies are pinned in
`backend/requirements.txt` and the tested closure in `backend/constraints.txt`.

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
cp .env.example .env
.venv/bin/python -m backend.app.database.migrate
```

For the already acquired local dataset:

```bash
.venv/bin/python -m backend.app.ml.sms.train
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

The trained artifact is `backend/app/ml/models/sms_pipeline.joblib`, with its
actual provenance/evaluation and split records alongside it. Startup never
downloads data or trains a replacement.

On a fresh clone with networking, acquire the original source:

```bash
.venv/bin/python scripts/download_sms_dataset.py
.venv/bin/python -m backend.app.ml.sms.train --dataset data/datasets/uci_sms_official.jsonl
.venv/bin/python -m pytest backend/tests -q
```

Datasets and binary models are excluded from Git. Original-source acquisition
creates its own checksum/version. This session's corpus is a documented mirror
web export because shell downloads were blocked. Downloads fail explicitly
without inventing or substituting data.

Set the actual `SUPABASE_URL` before using protected endpoints. Android/web
clients sign in through Supabase Auth and send their access token. Missing
authentication gives `401`/`503`. No development user or unsigned-token bypass
exists. SQLite is local storage; production requires the role, TLS and RLS setup
in [DATABASE_SETUP.md](docs/DATABASE_SETUP.md).

Open `/docs` or `/openapi.json`. `/health` reports liveness; authenticated
`/api/v1/system/status` reports actual capability and provider availability.

| Method | Implemented endpoint | Authentication |
| --- | --- | --- |
| GET | `/health` | Public |
| GET | `/api/v1/auth/me` | Supabase token |
| GET | `/api/v1/system/status` | Supabase token |
| POST | `/api/v1/analyze/sms` | Supabase token |
| POST | `/api/v1/analyze/url` | Supabase token |
| POST | `/api/v1/analyze/qr` | Supabase token, multipart PNG/JPEG |
| POST | `/api/v1/analyze/caller` | Supabase token |
| POST | `/api/v1/analyze/apk` | Supabase token; parser currently unavailable |
| POST | `/api/v1/analyze/apk` | Supabase token; parser currently unavailable |
| GET | `/api/v1/investigations` | Owner only |
| GET | `/api/v1/investigations/{investigation_id}` | Owner only |
| POST | `/api/v1/investigations/{investigation_id}/correlate` | Owner only |
| POST | `/api/v1/investigations/{investigation_id}/interpret` | Owner only; Gemini opt-in |
| POST | `/api/v1/investigations/{investigation_id}/interpret` | Owner only; Gemini opt-in |
| DELETE | `/api/v1/investigations/{investigation_id}` | Owner only |
| POST/GET | `/api/v1/reports` | Owner only |
| GET | `/api/v1/reports/{record_id}` | Owner only |
| POST/GET | `/api/v1/watchlist` | Owner only |
| DELETE | `/api/v1/watchlist/{record_id}` | Owner only |
| GET | `/api/v1/alerts` | Owner only |
| PATCH | `/api/v1/alerts/preferences` | Owner only |

Analysis returns `201` only with a stored record. URL analysis currently returns
`partial` and `model_not_trained`. Numeric risk/confidence are null. A spam model
prediction cannot confirm fraud.

Correlation returns observed shared URL hashes and exact hostnames with evidence
IDs and timestamps. No identifiers gives an empty graph; no related records gives
`no_matches`. Shared identifiers do not prove common ownership or a fraud campaign.
See [CORRELATION.md](docs/CORRELATION.md). Apply the new index migration explicitly.

See [USER_RECORDS.md](docs/USER_RECORDS.md) for actual report/watchlist/alert
contracts, ownership, redaction and empty states.

Upload details: [QR_ANALYSIS.md](docs/QR_ANALYSIS.md). Caller limitations:
[CALLER_ANALYSIS.md](docs/CALLER_ANALYSIS.md). Guarded APK status:
[APK_ANALYSIS.md](docs/APK_ANALYSIS.md).

## Verification and operations

Tests use actual model outputs and genuine corpus records. Test identities,
HTTP responses and negative security strings are explicitly non-production
fixtures in disposable databases. Live Supabase/provider communication remains
unverified until configured and exercised.

The sandbox denies socket writes used to wake TestClient's event loop. A
test-only polling timer in `backend/tests/http_client.py` lets the real ASGI
application execute. It does not replace inference, JWT verification or storage.

```bash
.venv/bin/python -m backend.app.database.retention
.venv/bin/python scripts/export_openapi.py
.venv/bin/python -m pip check
```

Retention defaults: investigations 30 days, audit metadata 180 days. Schedule
the maintenance command; PostgreSQL requires a separate maintenance role.
TLS deployment, operational logs/jurisdiction, backups and Indian privacy
obligations require operational/legal review. No compliance claim is made.

The Android handoff is [ANDROID_API_INTEGRATION.md](docs/ANDROID_API_INTEGRATION.md).
See [SESSION_REPORT.md](docs/SESSION_REPORT.md) for files, commands and test results,
and [IMPLEMENTATION_ROADMAP.md](docs/IMPLEMENTATION_ROADMAP.md) for phased status.

Raw-URL acquisition/features/RF-XGBoost comparison/inference code is connected. No URL model is trained yet: the genuine source download fails in this environment. See [URL_ML_PIPELINE.md](docs/URL_ML_PIPELINE.md). Optional Gemini selection returns existing evidence only; see [GEMINI.md](docs/GEMINI.md).
