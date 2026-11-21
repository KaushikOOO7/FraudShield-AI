# API contract — version 1.6

The executable schema is `/openapi.json`, exported to `docs/openapi.json`.
Application version is 0.1.0. Android and web use the same Pydantic contracts.
No real investigation is fabricated as a documentation example.

| Method | Endpoint | Success |
| --- | --- | --- |
| GET | /health | 200: liveness only |
| GET | /api/v1/auth/me | 200: verified user_id |
| GET | /api/v1/system/status | 200: actual capability/configuration status |
| POST | /api/v1/analyze/sms | 201: committed investigation |
| POST | /api/v1/analyze/url | 201: committed investigation, currently partial |
| POST | /api/v1/analyze/qr | 201: actual decoded/empty QR partial investigation |
| POST | /api/v1/analyze/caller | 201: masked format investigation; reputation unavailable |
| POST | /api/v1/analyze/apk | Guards tested; currently 503 because Androguard is unavailable |
| GET | /api/v1/investigations | 200: items/limit/offset/has_more |
| GET | /api/v1/investigations/{investigation_id} | 200: owner-scoped stored response |
| POST | /api/v1/investigations/{investigation_id}/correlate | 200: evidence-backed observation graph |
| POST | /api/v1/investigations/{investigation_id}/interpret | 200: optional selection of existing evidence references; unavailable states explicit |
| DELETE | /api/v1/investigations/{investigation_id} | 204: empty body after deletion |
| POST/GET | /api/v1/reports | 201: unreviewed owner submission / 200: owner history |
| GET | /api/v1/reports/{record_id} | 200: owner report; unknown/other-user IDs give 404 |
| POST/GET | /api/v1/watchlist | 201: new entry, 200: existing entry / 200: owner list |
| DELETE | /api/v1/watchlist/{record_id} | 204: deleted owner entry |
| GET | /api/v1/alerts | 200: actual owner alert history, empty when no alerts exist |
| PATCH | /api/v1/alerts/preferences | 200: stored explicit in-app preference |

All except health require a current Supabase Bearer access token. No default
user or token-minting endpoint exists. Wrong/expired/unsigned tokens fail 401;
missing authentication configuration or unavailable signing keys fail 503.

JSON inputs use application/json UTF-8. SMS: content (1–5000 characters). URL:
absolute supported HTTP(S) url (up to 2048 characters). Both accept source
(android_share/android_manual/web_share/web_manual/api), optional registered
owner UUID device_id, and strict boolean use_threat_intelligence (default false).
Unknown fields, recognizable secrets and unsupported/private/credential URLs
are rejected. Limit is 32768 encoded body bytes; compressed input is rejected.

Creation returns an actual investigation_id and Location. Shared response:
status, subject, assessment, findings, sources, models, limitations,
recommended_actions, created_at and expires_at. Every finding references a
persisted source. Subject text/URLs are redacted. Stored JSON and normalized
evidence are committed together before success. Retrieval does not regenerate
predictions. Missing data stays null or empty.

Assessment has classification, risk_score, score_type, explanation,
methodology_version, confidence and missing_information. Current numeric values
are null. SAFE_INDICATORS, EXERCISE_CAUTION and HIGH_RISK are qualitative;
CONFIRMED_FRAUD is reserved for a future authoritative human review workflow.

SMS models return an actual ham/spam label only when inference status is
available, with model version/task, uncalibrated decision margin, explicit score
type and null confidence. Unavailable/incompatible/corrupt/out-of-vocabulary
results carry no fabricated label or score. URL ML remains model_not_trained.

Sources distinguish rule/model/threat_intelligence, status, reference, actual
observed_at and details. Provider absence/unrequested/error/stale/404/429 states
are not clean. A validated no-match is no_known_match, with no safety guarantee.
Cache hits preserve the actual earlier observation time.

History limit is 1–100 (default 20); offset 0–10000 (default 0). Empty history is
items: [] and has_more: false. Other-user/unknown IDs return 404. Expired cases
are hidden before physical retention cleanup. Deletion cascades evidence and
case-linked records; audit metadata follows separate retention.

Errors share error.code/message/details/request_id. Details use safe field
names and omit raw inputs. Codes/statuses and client handling are documented
in ANDROID_API_INTEGRATION.md. All responses carry X-Request-ID; 429 also has
Retry-After. Owner-scoped storage requests are limited to 30/minute/user via the
shared database, with 120/minute/IP/process ingress protection. A deployment
gateway must enforce a shared ingress policy across replicas.

Caller reputation, verified brand references, Supabase Storage and LangGraph
remain unavailable. Reserved database tables do not imply a working capability.
Breaking changes require a documented new contract version; update OpenAPI,
Android guidance and contract tests together.

Correlation accepts no body and query limit 1–100/default 20. It returns directly shared stored URL hashes/hostnames, observations, sources, graph nodes/edges and related investigation IDs. Status is matched/no_matches/no_identifiers; no identifiers gives empty lists. Original analysis schemas and risk assessments are unchanged. See CORRELATION.md.

Contract 1.2 adds owner-scoped POST/GET reports, GET report by ID, POST/GET watchlist,
DELETE watchlist by ID, GET alert history and PATCH alert preferences. Exact
request/response definitions, retention and unreviewed status are documented in
USER_RECORDS.md and the executable OpenAPI. These are real user-record operations;
unreviewed reports do not become verified threat intelligence. No push delivery
is implemented. Existing investigation schemas and risk rules are preserved.

Contract 1.3 adds multipart PNG/JPEG QR analysis (2 MiB default upload cap,
source and literal true/false opt-in form fields) and caller JSON input with
phone_number plus submission metadata. QR decoding/supported UPI syntax and
phone syntax are genuine observations; fraud/recipient/caller identity remains
unverified. Responses use the existing InvestigationResponse and partial status.
See QR_ANALYSIS.md and CALLER_ANALYSIS.md. No raw uploaded image is retained.

Contract 1.4 documents the guarded multipart APK endpoint and optional Gemini
evidence-selection endpoint. Existing SMS/URL input fields and investigation
response structure are preserved.

APK accepts file/source form fields, Android APK or octet-stream media, and a
20 MiB default file cap plus 32 KiB multipart overhead. Without Androguard it
returns 503 apk_parser_unavailable, without an investigation. Archive/media/size
guards are tested; successful genuine static parsing is not yet verified.
See [APK_ANALYSIS.md](APK_ANALYSIS.md).

Interpretation accepts application/json with strict boolean use_gemini, default
false. It verifies ownership and consumes the existing user quota before an
optional external call. The response includes investigation_id, status, provider,
model_used, checked_at, selected_findings, recommended_actions, null confidence
and limitations. Only IDs/action indices referring to existing server findings
and recommendations are accepted. Unknown references, extra fields or malformed
model responses produce invalid_response with empty outputs. The original
assessment is preserved. Configuration, opt-in, insufficient-evidence, provider
error and rate-limit states remain explicit; no live Gemini success is verified.
See [ANDROID_API_INTEGRATION.md](ANDROID_API_INTEGRATION.md).

Raw-URL feature/training/inference code is present, but the real PhiUSIIL corpus
has not been downloaded and neither RF nor XGBoost has been trained/evaluated.
URL APIs therefore still return model_not_trained. No published dataset metrics
or model outputs substitute for a local evaluation.

Contract 1.5: correlation methodology observed-identifiers-v2 includes actual QR/parsed-APK URL observations. ModelResult.label additionally permits legitimate/phishing for a genuinely trained raw-URL model; SMS remains ham/spam. Actual URL weights/evaluation are currently unavailable. Numeric model/risk confidence remains null. Original analysis request fields and response field names are preserved. See URL_ML_PIPELINE.md.

Contract 1.6: subject.value is nullable when no actual subject content is available. A readable image with no QR payload returns null rather than placeholder content; decode_status remains no_qr_found. Android/web clients must preserve this null. Existing supplied SMS/URL/caller/APK subject values remain actual redacted strings.
