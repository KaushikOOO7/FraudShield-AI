# Development session report — 2026-11-21

This report consolidates the earlier implementation and this continuation.
The genuine SMS baseline and existing backend were preserved. The whole platform
is not complete; local implementation and external verification are separated
below. Changes appearing in the shared workspace were inspected and tested.

## Inspection

Inspected repository files, Python environments/dependency pins, FastAPI routes,
Pydantic contracts, authentication, request/file limits, SQLAlchemy schema and
repositories, SQLite/PostgreSQL migrations/RLS, redaction, retention, threat
adapters, real dataset/model manifests, splits/evaluation, tests and deployment.
Python is 3.14.4 in an isolated project environment. An earlier checkpoint had
119 passing tests; the resumed baseline had 202. The final verified suite has
214 passing tests. The workspace has no working
Git repository: managed .git is empty/read-only. No .env or live credentials
were present. SQLite is connected; Supabase communication is not verified.

## Implemented and verified locally

- Authenticated SMS investigation using the actual TF-IDF/Logistic Regression
  artifact, documented rules, redacted evidence, owner-scoped persistence,
  history/deletion and explicit unavailable-provider states. Its held-out
  measurements are historical spam/ham results, not Indian fraud accuracy.
- Persisted NetworkX observation graph and owner-scoped correlation, including
  genuine SMS-to-URL and decoded QR-to-URL linkage. Every edge cites evidence;
  repeated calls reuse identities; deletion/retention prune unsupported nodes.
- Owner-scoped unreviewed reports, watchlists, duplicate handling, preferences
  and opt-in alerts created only from actual high-risk assessments.
- PNG/JPEG QR uploads, real OpenCV decoding in a resource-limited child process,
  supported UPI syntax, URL routing, redaction, limits and cleanup. Missing
  payload is null. Payee identity/fraud are not inferred from syntax.
- Masked caller-format investigations with explicit unavailable reputation.
- URLhaus, PhishTank, AbuseIPDB, fixed com/net/org/in RDAP and crt.sh adapters,
  connected to URL services with validated outcomes, source attribution,
  bounded transport, caching and neutral/unsupported states. No live success
  is claimed. Contradictory no-match payloads are rejected.
- Optional Gemini selection of existing evidence/recommendation references.
  Unknown IDs, indices and invented fields are rejected. No generated factual
  prose or scores enter risk assessment; original investigations remain intact.
- Guarded APK upload and isolated Androguard adapter, with archive expansion,
  path/type/size controls. Missing parser returns 503 without fabricated data.
  Successful genuine APK parsing remains unverified.
- Original PhiUSIIL downloader, provenance guards, URL-text features, grouped
  RF/XGBoost comparison/training code, artifact guards and inference/provenance
  integration across URL/SMS/QR. No source was downloaded and no URL model was
  fitted/evaluated. The API remains model_not_trained, with null prediction.
- OpenAPI and Android contracts, all 21 Postman operations, deployment model
  mounts and OpenCV shared-library requirements. Docker build is not verified.
- Consistent JSON media validation for interpretation, rejection of contradictory
  provider no-match payloads, and Postman JSON serialization that preserves quotes,
  backslashes and newlines. Removed a duplicate OpenCV library install from the
  Dockerfile; Compose syntax and model mounts are verified separately from builds.

## Genuine model and data

The original UCI SMS source/license and mirror acquisition are registered in
DATASET_REGISTER.md. The local corpus contains 5,574 labeled records; after 415
normalized duplicates were removed, 5,159 remain. Five unlabelled continuation
lines were rejoined during the documented web export. The exported corpus is
not a byte-identical original ZIP download.

| Item | Actual value |
| --- | --- |
| Model version | sms-uci-tfidf-lr-v1-efcaf62d777d |
| Prepared corpus SHA-256 | 5a493718c50cb7e0043ff6aafd814a73ddc4c499cee9ec45cd3be5eb5c70365c |
| Artifact SHA-256 | b0f588b84eb01bd317bc7df8d3d49522baa39516922ab77cdd48da7ce96959d7 |
| Training/validation/test rows | 3,095 / 1,032 / 1,032, with disjoint text/template groups |
| Held-out accuracy / precision / recall / F1 | 0.988372 / 0.932836 / 0.976563 / 0.954198 |
| Test confusion matrix, ham/spam | [[895, 9], [3, 125]] |

Tests reproduce the saved holdout metrics using the actual artifact and corpus.
Validation recall is lower (0.875969); split variance, historical sampling,
multilingual/Indian financial-fraud and independent external evaluation remain
limitations. Numeric risk/confidence is null; margins are uncalibrated.

## Files created

Earlier foundation: backend/app/main.py; core configuration/security/error/limit
modules; database models, connections, repositories and initial migrations;
API v1 auth/system/SMS/URL/history routes; schemas and SMS/URL/risk services;
ML data validation, preprocessing, SMS training/inference; real corpus/model
artifacts; tests; requirements; Docker/CI definitions and the required docs.
PROJECT_ASSESSMENT.md records the initially empty visible workspace.

Correlation: backend/app/schemas/correlation.py, backend/app/graph/__init__.py,
backend/app/graph/network.py, backend/app/database/correlation.py,
backend/app/database/graph_cleanup.py, backend/tests/test_correlation.py,
backend/migrations/sqlite/0002_correlation_indexes.sql,
backend/migrations/postgresql/0003_correlation_indexes.sql, docs/CORRELATION.md.

User records: backend/app/utils/indicators.py, backend/app/schemas/community.py,
backend/app/database/community.py, backend/app/api/v1/community.py,
backend/tests/test_community.py, docs/COMMUNITY_AND_ALERTS.md.

QR/caller: backend/app/services/qr_worker.py, qr_decoder.py, qr_service.py and
caller_service.py; backend/app/utils/upi.py; backend/app/schemas/caller.py;
backend/app/api/v1/qr.py and caller.py; backend/tests/test_qr.py, test_caller.py
and test_qr_canonical_urls.py;
docs/QR_ANALYSIS.md and docs/CALLER_ANALYSIS.md.

Providers: backend/app/intelligence/urlhaus.py, phishtank.py, abuseipdb.py,
whois_lookup.py, crtsh.py and gemini.py; backend/app/schemas/interpretation.py;
backend/app/database/interpretation.py; backend/app/api/v1/interpretation.py;
backend/tests/test_extra_intelligence.py, test_domain_intelligence.py,
test_provider_pipeline.py and test_gemini.py; docs/GEMINI.md.

APK: backend/app/schemas/apk.py, backend/app/services/apk_worker.py and
apk_service.py, backend/app/api/v1/apk.py, backend/requirements-apk.txt,
backend/tests/test_apk_guards.py, docs/APK_ANALYSIS.md.

URL pipeline: backend/app/ml/url/__init__.py, features.py and train.py;
backend/app/ml/inference/urls.py; scripts/download_url_dataset.py;
backend/requirements-url-training.txt; backend/tests/test_url_acquisition.py
and test_url_pipeline.py; docs/URL_ML_PIPELINE.md and this SESSION_REPORT.md.

## Existing files modified/maintained

README.md, .env.example, backend/requirements.txt, backend/constraints.txt,
backend/app/main.py, core/config.py, core/errors.py, core/middleware.py,
database/models.py, database/repositories.py, database/retention.py,
services/bundle.py, services/sms_service.py, services/url_service.py,
schemas/investigation.py, intelligence/base.py, intelligence/engine.py,
api/v1/system.py, tests/conftest.py, tests/test_database.py,
tests/test_investigation_api.py, tests/test_contract_snapshot.py,
backend/Dockerfile, docker-compose.yml and required assessment/architecture/
roadmap/dataset/API/Android/security/risk/model/provider documentation.
OpenAPI and Postman collection were refreshed. Existing short authorization/
persistence transactions and deployment definitions were preserved.
This continuation also updated test_gemini.py and test_extra_intelligence.py
with the media-type and contradictory-provider regression cases. The Postman
collection names the stable /api/v1 path and refers to the authoritative revision
documents; API and Android documents currently use contract 1.6.
No reliable Git diff/commit is available in this managed workspace.

## Commands and actual results

| Command/action | Actual result |
| --- | --- |
| rg --files, file reads, interpreter/dependency/config inventory | Existing backend/data/model identified; no secret values printed |
| git status --short | Not a Git repository; no commit/push made |
| .venv/bin/python -m pytest backend/tests -q --junitxml=/tmp/fraudshield-final-tests.xml | Final observed regression: 214 passed, 1 deprecation warning in 23.35 seconds; no failures/skips |
| .venv/bin/python -m pytest backend/tests/test_gemini.py backend/tests/test_input_security.py backend/tests/test_security_boundaries.py -q | 50 passed, 1 warning |
| .venv/bin/python -m pytest backend/tests/test_extra_intelligence.py backend/tests/test_provider_pipeline.py backend/tests/test_intelligence.py backend/tests/test_domain_intelligence.py -q | 39 passed, 1 warning |
| Offline pip wheel installs | NetworkX 3.7, Pillow 12.3.0, OpenCV 5.0.0.93, python-multipart 0.0.32 installed from genuine local cache |
| .venv/bin/python -m pip --disable-pip-version-check --no-cache-dir check | No broken requirements found in the isolated environment |
| .venv/bin/python -m backend.app.database.migrate | New SQLite correlation index revision applied, then already up to date |
| .venv/bin/python scripts/export_openapi.py | Executable schema exported; contract snapshot tested |
| .venv/bin/python -m compileall -q backend/app backend/tests scripts | Passed |
| .venv/bin/python scripts/download_url_dataset.py | ConnectError; no replacement source generated |
| .venv/bin/python -m backend.app.ml.url.train | DatasetValidationError before fitting; no fake model/evaluation generated |
| Earlier checkpoint: .venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log | Application startup completed; listener bind failed with PermissionError/EPERM; no listener is claimed. Current ASGI startup is exercised by tests |
| docker compose --env-file .env.example config --no-env-resolution --quiet | Configuration syntax validated; no image build/deployment claimed |
| One-off OpenAPI/Postman verification with node --check and isolated JSON serialization fixtures | 21/21 operations covered; 12 script syntax checks and 5 escaping runtime checks passed; no saved responses or populated token/input variables |
| Read-only SQL integrity/count verification | 26 application tables, all empty; SQLite quick_check ok; zero foreign-key violations |

Regression cases reproduced the incorrect non-JSON interpretation status and
contradictory provider payloads returning no_match. Current code rejects them
with the documented media/invalid-response states. Code tests passed on a saved
snapshot; subsequent changes were documentation/Compose metadata, not runtime
Python or model changes. The Compose check passed after its final update.
The remaining warning is Starlette's TestClient/httpx deprecation.

Actual local investigations/reports/watchlists/alerts counts are all zero.
No test identity, fake incident or HTTP threat fixture was inserted into
application storage. SMS binary/provenance and measured historical evaluation
were preserved; no Indian financial-fraud performance claim was added.

## Outstanding work and required configuration

Supabase: actual SUPABASE_URL, restricted PostgreSQL DATABASE_URL/role, optional
PostgreSQL driver, TLS/CA, real Auth/JWKS and RLS verification. No service-role
key is exposed to clients.

Optional live integrations: GOOGLE_SAFE_BROWSING_API_KEY, VIRUSTOTAL_API_KEY,
URLHAUS_API_KEY, PHISHTANK_API_KEY, ABUSEIPDB_API_KEY; explicit ENABLE_RDAP and
ENABLE_CRTSH; GEMINI_API_KEY and an actually supported GEMINI_MODEL. Provider
account permissions/terms and successful real communication remain unverified.

URL: actual licensed corpus acquisition and optional CPU XGBoost installation,
then genuine RF/XGBoost fitting/comparison/holdout evaluation and positive API
inference. No URL metrics or trained artifact exists yet.

APK: install Androguard 4.1.4 and test against an identifiable legitimate APK.
No dynamic APK execution is implemented. Caller reputation is unavailable.

LangGraph agents, verified brand/OCR/logo references, privacy-policy analysis,
advanced campaign/phone/UPI/APK-hash correlation, moderated reputation, background
watchlist monitoring, push delivery, retained Supabase Storage evidence and
account erasure remain separate unfinished work. Production deployment, HTTPS
termination, distributed ingress limits, backups/operations/legal review and
independent Kotlin client integration are not claimed complete.

## Next implementation task

Acquire the original PhiUSIIL corpus with network access, install the optional
CPU comparator, run the real URL training pipeline, verify its held-out metrics
and positive inference/storage through FastAPI, then update model documentation.
In parallel operational setup requires real Supabase credentials and RLS tests.
