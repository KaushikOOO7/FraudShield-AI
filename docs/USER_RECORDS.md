# User records — additive API contract 1.2

These endpoints use verified Bearer authentication, owner-scoped transactions,
input/output schemas, sanitized errors, rate limits and actual SQL storage.
They do not seed user records or classify user allegations as verified threats.
Existing SMS/URL investigation schemas are preserved.

| Operation | Request | Response |
| --- | --- | --- |
| POST /api/v1/reports | subject_type, subject, description | 201, actual id, redacted_subject/description, moderation_status=unreviewed, verified_at=null, created_at and Location. |
| GET /api/v1/reports | limit 1–100/default 20, offset 0–10000/default 0 | 200, actual owner records in items/limit/offset/has_more. |
| GET /api/v1/reports/{record_id} | Actual UUID | 200 owner report or 404. |
| POST /api/v1/watchlist | indicator_type, value | 201 new entry or 200 existing exact normalized indicator; actual id/type/redacted_value/created_at. |
| GET /api/v1/watchlist | limit/offset as above | 200 actual owner records; no matches gives items: []. |
| DELETE /api/v1/watchlist/{record_id} | Actual UUID | 204 empty body; unknown/other-user record gives 404. |
| GET /api/v1/alerts | limit/offset as above | 200 actual owner alert history, filtered to unexpired investigations. |
| PATCH /api/v1/alerts/preferences | high_risk_alerts: strict JSON boolean | 200 saved preference and delivery=in_app_history. |

Reports support subject types sms/url/domain/phone/apk_sha256. Watchlists support
url/domain/phone/apk_sha256. URLs use the same public-URL/credential validation;
domains require exact ASCII public hostnames; phone values use E.164 or supported
Indian mobile normalization; hashes require 64 hex characters. These are format
checks, not reputation verdicts. Known secrets are rejected and displayed/stored
values are redacted. Unknown fields, including forged moderation state, are
rejected. SMS report/description fields are nonblank and at most 5000 characters.

Reports remain unreviewed with verified_at null; there is no moderation API.
They do not affect risk classifications or become cross-user reputation data.
Report retention is configurable, default 30 days; old reports are hidden before
maintenance removes them. Full account-erasure workflow remains pending.

Watchlists represent actual user selections only and are retained until user
deletion/account deletion. Repeated normalized indicators reuse the real row;
equal redacted display values with different raw hashes are not merged.

Alert creation requires an actual new investigation classified HIGH_RISK and an
explicit saved opt-in. An unconfigured/default preference produces no fabricated
alerts. Stored text comes from the actual assessment explanation and links to
its investigation. Deletion/expiration hides or removes associated alerts.
Delivery is in-app history only; no email, SMS or push transmission occurs.

Tests use clearly labeled non-production fixtures in disposable databases and
actual model inference for the warning workflow. No production database receives
fixture reports, fake users or predetermined threat predictions.
