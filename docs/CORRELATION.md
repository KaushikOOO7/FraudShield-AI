# Observed URL correlation across channels

`POST /api/v1/investigations/{investigation_id}/correlate` requires a verified
Supabase bearer token and no body. Query limit: default 20, range 1–100.
Returns 200 after graph/evidence commit. Missing, expired and other-owner root
IDs return 404. Executable response type: `CorrelationResponse` in OpenAPI.

Methodology `observed-identifiers-v2` searches owned unexpired SMS/URL/QR/parsed-APK records
for directly shared URL hashes or exact IDNA hostnames. Hashes are stored by
original analysis before redaction. Equal-looking redacted URLs do not produce
exact URL matches; different subdomains are not merged into registrable domains.

Information-level `STORED_URL_OBSERVATION` evidence references the original
investigation, parsed URL record, rule source and original observation time.
Persisted paths: investigation → observed_url → URL → url_host → domain.
Both edges reference their investigation's evidence. NetworkX finds shared
identifier nodes; no LLM creates relationships.

Response: investigation_id, status, methodology_version, generated_at,
related_investigations, nodes, edges, observations, sources, limit, has_more,
limitations. Related records cite node IDs supported by both investigations.
Newest-first bounded results; has_more means additional direct matches exist.
No cursor is implemented. Status matched means observed reuse; no_matches
means root observations only; no_identifiers returns empty graph/evidence lists.

Repeated calls reuse graph/evidence identities and record actual audit/events.
Original investigation and risk JSON remain unchanged. Identifier reuse does
not prove ownership, fraud or a campaign. No transitive, redirect, caller-number, APK-hash,
UPI or brand links are inferred. Deletion cascades supporting edges/evidence and
prunes orphan nodes, retaining shared nodes with surviving support. Expired
records are immediately hidden and physically removed by scheduled retention.

Index migrations: sqlite/0002_correlation_indexes.sql and
postgresql/0003_correlation_indexes.sql. Prior revisions are unchanged.
PostgreSQL RLS is retained; live PostgreSQL/RLS execution remains unverified.

Tests cover genuine SMS/URL reuse, hostname versus URL identity, redaction
collisions, ownership, empty results, repeat calls, deletion, expiration,
retention, direct versus transitive links, limits, output validation, rollback,
and an old-schema upgrade preserving a real API-produced investigation.

2026-11-21 methodology v2 expands candidate channels to actual QR and parsed-APK URL observations. Observation-edge rules/identities remain unchanged. Genuine APK parsing is still unavailable locally; no APK relationships are manufactured.
