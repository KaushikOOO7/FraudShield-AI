# Reports, watchlists and alerts

All routes require a verified Supabase bearer token and owner-scoped SQL storage.
JSON writes are validated, limited and sanitized; no reports are seeded.

POST /api/v1/reports accepts subject_type (sms/url/domain/phone/apk_sha256),
subject and description (1–5,000 characters). Returns 201 with an actual ID,
redacted values, created_at, moderation_status=unreviewed and verified_at=null.
GET /api/v1/reports and GET /api/v1/reports/{id} return owned unexpired reports.
User requests cannot forge approval. No moderation/admin workflow or public
reputation aggregation is claimed; unreviewed reports never increase risk.
Reports expire after COMMUNITY_REPORT_RETENTION_DAYS (default 30), are hidden
immediately and physically removed by scheduled retention.

POST /api/v1/watchlist accepts indicator_type (url/domain/phone/apk_sha256) and
value. Inputs use documented structural validation. Phone values use E.164 or
ten-digit Indian mobile syntax and are stored masked; URL query values are
redacted. SHA-256 of normalized values provides deduplication, not reputation.
201 creates a record; 200 returns an existing duplicate. GET /api/v1/watchlist
lists owned entries; DELETE /api/v1/watchlist/{id} returns 204. Watchlist entries
remain until removed. No automatic background monitoring is claimed.

PATCH /api/v1/alerts/preferences requires {"high_risk_alerts": true or false}.
The response states delivery=in_app_history. Default is disabled. When enabled,
an actual HIGH_RISK investigation creates an owned alert in the same transaction
as its evidence. GET /api/v1/alerts lists alerts linked to unexpired owned cases.
Deletion/retention cascade them. No push/email delivery is implemented.

List pagination: limit 1–100/default 20, offset 0–10,000/default 0; responses
contain items/limit/offset/has_more. Empty results are empty. Other-owner IDs
return 404. Recognizable secrets and forged fields return sanitized 422.
See OpenAPI for executable request/response fields and Android documentation.
