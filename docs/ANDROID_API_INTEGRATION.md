# Android API integration — contract 1.6

2026-11-21: additive correlation operation. Existing SMS/URL analysis and history
request/response schemas remain unchanged. API path version remains `/api/v1`.

The same date adds owner-scoped report/watchlist/alert-history operations in
[USER_RECORDS.md](USER_RECORDS.md). Existing investigation contracts are preserved.

Contract 1.3 adds QR upload and masked caller-format analysis. Existing SMS/URL
schemas and risk methodology are preserved.

Contract 1.4 documents the guarded APK upload and optional Gemini selection of
existing findings. Existing investigation request/response structures remain
compatible; all analysis limitations must still be displayed.

Backend base URL is deployment-specific. Use HTTPS in production. In an Android
emulator, `10.0.2.2` can address a locally running host backend; allow that Host
explicitly in development `ALLOWED_HOSTS`. Release builds must use the HTTPS
deployment. No Android implementation is changed by this repository.

## Authentication

Sign in and refresh tokens using the actual Supabase Auth project. The Android
developer needs the project URL and publishable/anon client key. The backend
needs `SUPABASE_URL` and its restricted PostgreSQL credential. Never include a
service-role key, database password, legacy JWT verification secret, or provider
key in the Android build.

Send `Authorization: Bearer <current access_token>` on all routes except
`/health`. Tokens require a valid signature, matching project issuer, audience
`authenticated`, unexpired `exp`, valid `iat`, role `authenticated` and UUID `sub`.
ES256/RS256 use the project's configured JWKS origin; legacy HS256 requires
explicit backend configuration. `GET /api/v1/auth/me` returns the verified
`user_id`. It does not create or sign in a default user.

## Headers and limits

JSON requests require `Content-Type: application/json`, encoded as UTF-8.
Optional `X-Request-ID` is a UUID; otherwise the backend generates one. Responses
include `X-Request-ID` and `Cache-Control: no-store`. Creation responses include
a relative `Location` pointing to the stored investigation.

Limits: 32,768 encoded request bytes; SMS 1–5,000 characters; URL up to 2,048
characters; only standard web ports 80/443; up to five unique extracted SMS URL
substrings. Compressed requests are rejected. Rate limits are 30 owner-scoped
storage requests per minute per verified user (shared database counter), plus
120 API requests/minute/IP/process. `429` includes `Retry-After`. Production
needs a shared gateway ingress limit across processes/replicas.

**Remove OTP values, passwords, UPI PINs and banking/card credentials on the
device before submission.** Server recognition/rejection is additional
protection and is not a guarantee of complete redaction. Do not forward these
values to analysis services. Recognizable sensitive input gets `422
sensitive_input`, with no reflected value. Persistent SMS/URL data is redacted.

## Analyze SMS

`POST /api/v1/analyze/sms` → `201` and an actual stored investigation.
This example is a request contract, not a fraud incident:

```json
{
  "content": "User-supplied content after sensitive-value redaction",
  "source": "android_share",
  "device_id": null,
  "use_threat_intelligence": false
}
```

`source`: `android_share`, `android_manual`, `web_share`, `web_manual`, or `api`
(default). `device_id` must be a registered device UUID belonging to the token's
user. Device registration API is pending: omit it or use null for the initial
integration. Never invent a device ID. Unknown/other-user IDs return `404`.

`use_threat_intelligence` is an explicit JSON boolean, default false. True
permits forwarding validated extracted URLs to configured third parties; it
does not mean a provider is configured or returned a result. No raw SMS is
sent to an LLM. Model inference is local.

## Analyze URL

`POST /api/v1/analyze/url` → `201`. Contract-only benign URL example:

```json
{
  "url": "https://example.com/",
  "source": "android_share",
  "use_threat_intelligence": false
}
```

Only absolute HTTP(S) URLs are supported. Credentials, known sensitive query
values, private/local IP literals/hosts, ambiguous numeric hosts, controls and
nonstandard ports are rejected. Arbitrary pages/redirects are not fetched.
URL ML is not trained; the current result is `partial`, with actual structure
rules and any permitted, available provider information.

## Shared response

Use the exact schema in [openapi.json](openapi.json). No fabricated response
instance is supplied here.

| Field | Meaning |
| --- | --- |
| investigation_id | Actual server UUID; save only after a `201` response. |
| status | `completed` or `partial`; neither is a safety verdict. |
| subject | Type, redacted value, actual parsed/extracted attributes. |
| assessment | Classification, null risk score/type/confidence, explanation, methodology version and missing information. |
| findings | Evidence UUID, code, description, severity, verification status, source UUID, time and factual attributes. |
| sources | UUID, name/kind/status/reference, actual check time and details. Missing-provider status is not a clean verdict. |
| models | Name/version/task/status; actual ham/spam label only for completed SMS inference; uncalibrated decision margin; null confidence. |
| limitations | Unavailable capabilities and uncertainty. |
| recommended_actions | Recommendations based on observed findings. |
| created_at / expires_at | Server UTC ISO-8601 timestamps. |

Classifications: `SAFE_INDICATORS`, `EXERCISE_CAUTION`, `HIGH_RISK`,
`CONFIRMED_FRAUD`. The last is reserved and never returned automatically.
Keep numeric fields nullable. Do not display margins as percentages or replace
null with zero. Display limitations and source statuses. Use strings for model
labels/statuses and handle unknown future values safely.

For Google warnings, display the returned attribution/advisory link and explain
possible false positives/negatives before users enable protection. Respect
`sources[].details.valid_until` at display time; expired/historical results must
not be presented as a current Google warning. Re-analysis requests actual fresh
information. Other sources keep their own attribution.

## History and deletion

`GET /api/v1/investigations?limit=20&offset=0` → `200` with `items`, `limit`,
`offset`, `has_more`. Limit 1–100; offset 0–10,000. No records gives `items: []`.
`GET /api/v1/investigations/{investigation_id}` → the stored response or `404`.
`DELETE` on the same route → `204`, empty body. Evidence and linked per-case
records are deleted; audit metadata is retained under policy. Other-user IDs
return `404` without revealing their existence. Expired records are hidden
before maintenance physically removes them.

## Errors and unavailable routes

Errors use `{"error":{"code":...,"message":...,"details":[],"request_id":...}}`.
Values above are schema notation, not a returned investigation. Details identify
safe field names, never raw content or credentials.

| HTTP | Common code/action |
| --- | --- |
| 400 | `invalid_host`, `https_required`, `invalid_content_length` |
| 401 | `authentication_required`, `invalid_token`: sign in/refresh through Supabase. |
| 404 | `investigation_not_found`, `device_not_found`, `not_found` |
| 408 | `request_timeout` |
| 409 | `storage_constraint_error`, `model_version_conflict` |
| 413 | `request_too_large`, `file_too_large`: reduce encoded payload/file. |
| 415 | `json_required`, `unsupported_encoding`, `unsupported_image_type`, `unsupported_apk_type` |
| 422 | `sensitive_input`, `validation_error`, `invalid_image`, `invalid_upi_uri`, `invalid_apk_archive`: fix/redact input. |
| 429 | `rate_limited`: honor Retry-After. |
| 500 | `internal_error`: preserve request ID for support. |
| 503 | `auth_not_configured`, `auth_provider_unavailable`, `database_unavailable`, `apk_parser_unavailable`: availability/configuration failure. |

QR decoding, caller-format analysis, the guarded APK upload and optional Gemini
selection are described below. GET /api/v1/system/status reports actual
configuration/capability states; configured_not_verified does not establish
successful external communication.

## Correlation

POST /api/v1/investigations/{investigation_id}/correlate?limit=20 requires bearer authentication and no body; limit 1–100. Returns 200 CorrelationResponse with graph nodes/edges, observation evidence/sources/timestamps and directly related investigation IDs. Status: matched, no_matches, no_identifiers. Missing, expired and other-user roots return 404. has_more indicates additional direct matches. Do not interpret shared identifiers as campaign ownership. Existing risk and analysis responses stay unchanged. See CORRELATION.md and OpenAPI.

## QR upload and caller format

POST /api/v1/analyze/qr uses multipart/form-data with file (PNG/JPEG), source,
and use_threat_intelligence as literal form string true/false (default false).
Do not manually create the multipart boundary. Default file limit 2 MiB plus
32 KiB request overhead; at most 10 million image pixels and 5000 decoded
characters. Media/signature/image parsing are validated in a bounded child
process. Original filenames are ignored and temporary files are cleaned.
201 returns a stored partial InvestigationResponse; no readable QR gives
no_qr_found with no invented payload/model. Multiple QR payloads, malformed
images or sensitive content give 422; unsupported media 415; excess size 413.
UPI fields describe supported syntax only, masked payee hint, amount/currency
when present and recipient_verified=false. Never display these as verified
payment identity or proof of fraud. See QR_ANALYSIS.md.

POST /api/v1/analyze/caller is JSON with phone_number and ordinary submission
metadata. Supported E.164/Indian mobile syntax is normalized, displayed/stored
masked and returned as a partial investigation. Caller-reputation data is
provider_not_configured; model and score are absent. Normalization does not
verify identity, allocation or reputation. See CALLER_ANALYSIS.md.

## APK guarded adapter — success unverified

POST /api/v1/analyze/apk accepts multipart file and source, requires a Bearer
token and validates archive/media/expansion bounds. Current missing parser
returns 503 apk_parser_unavailable; no fabricated metadata or investigation is
returned. Do not treat a guarded upload adapter as completed malware analysis.
Successful static parsing still needs installed Androguard and a legitimate
fixture. Accepted media: application/vnd.android.package-archive or
application/octet-stream. Default file cap is 20 MiB, with 32 KiB multipart
overhead. Filenames are ignored. Source uses the standard submission values;
device_id and threat-intelligence form fields are not supported on this route.
If the parser becomes available, 201 requires actual validated metadata and a
committed partial investigation. See [APK_ANALYSIS.md](APK_ANALYSIS.md).

## Optional evidence selection

POST /api/v1/investigations/{investigation_id}/interpret requires the owner's
Bearer token and Content-Type: application/json. Contract-only request:

```json
{
  "use_gemini": false
}
```

Change to true only after the user explicitly permits external interpretation.
The backend also needs GEMINI_API_KEY and an actually supported GEMINI_MODEL.
No raw SMS, phone number, URL query, APK bytes or report body is sent. The model
can select only existing finding UUIDs and recommendation indices from a bounded
list; the server returns their original validated content. It cannot add factual
claims, sources, relationships, risk scores or recommendations.

200 InterpretationResponse contains investigation_id, status, provider,
model_used, checked_at, selected_findings, recommended_actions, confidence and
limitations. Confidence is always null. Statuses: provider_not_configured,
not_requested, insufficient_evidence, available, provider_error,
invalid_response or rate_limited. Unavailable states have empty findings/actions
and null model_used; available means validated reference selection, not
independent evidence verification. No live Gemini success is claimed here.

Other-user, expired and unknown cases return 404. Non-JSON media returns
415 json_required; non-boolean opt-in and unknown request fields return 422.
The existing database-backed user quota applies. Provider 429 is represented by
status rate_limited in this optional result; API quota exhaustion returns HTTP
429 with Retry-After. Interpretation status/selected IDs are audited without
overwriting the original risk assessment or stored investigation response.

The Postman collection covers all current HTTP operations and contains no saved
investigation responses. Set its blank variables to your actual redacted inputs
and choose actual upload files. No backend API key belongs in the collection or
Android build.

Contract 1.5: correlation methodology observed-identifiers-v2 includes actual QR/parsed-APK URL observations. ModelResult.label additionally permits legitimate/phishing for a genuinely trained raw-URL model; SMS remains ham/spam. Actual URL weights/evaluation are currently unavailable. Numeric model/risk confidence remains null. Original analysis request fields and response field names are preserved. See URL_ML_PIPELINE.md.

Contract 1.6: subject.value is nullable when no actual subject content is available. A readable image with no QR payload returns null rather than placeholder content; decode_status remains no_qr_found. Android/web clients must preserve this null. Existing supplied SMS/URL/caller/APK subject values remain actual redacted strings.
