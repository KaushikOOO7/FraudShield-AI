# Security and privacy

Implemented/tested: verified JWT signatures/issuer/audience/expiry/role/UUID,
owner-scoped access, composite owner foreign keys, sanitized errors, body/input
limits, strict provider opt-in, redaction, audit metadata, quota enforcement,
cascade deletion and retention. Supabase/PostgreSQL RLS and deployed HTTPS have
not been exercised against a live project in this session.

Authentication uses configured Supabase signing keys, never a token-supplied
URL. ES256/RS256 JWKS are bounded/cached; unknown key IDs cannot trigger unlimited
refreshes. Legacy HS256 requires an explicit backend secret. Anonymous/service
role/unsigned tokens are rejected. Local validation does not instantly revoke
an otherwise unexpired signed token; review session revocation requirements.

Production configuration requires PostgreSQL verify-full TLS, a Supabase origin
and explicit host names. Runtime rejects unsafe/bypass database roles. RLS is
enabled/forced by the Supabase-specific migration with client writes revoked;
application ownership filters remain mandatory. Run migrations/maintenance with
a separate credential. Keep service-role/provider/DB/JWT secrets out of clients,
logs and source control. Secrets use SecretStr and validation errors hide inputs.

Clients must redact passwords, OTP values, UPI PINs and banking/card credentials
before transmission. Server recognition rejects sensitive input before inference
or storage and never reflects values or unknown sensitive field names. Redaction
is best effort, not proof that all personal data is removed. Phones/emails/UPI
handles and query values/fragments are redacted for storage; names/context may
remain. URL hashes identify observations and are not strong anonymization.

External URL lookups require explicit JSON-boolean opt-in. No raw SMS is sent to
an LLM. Arbitrary URLs/pages/redirects are not fetched. URL validation rejects
private/local literals/hosts, credential-bearing inputs, controls, ambiguous
numeric hosts and unsupported ports/schemes. Hostname DNS rebinding defenses and
every-hop redirect validation are prerequisites for a future page fetcher, not
claimed current functionality. Fixed provider HTTPS endpoints never follow
redirects, ignore proxy environment settings and cap time/response size.

JSON requests are limited to 32768 encoded bytes including streaming requests
with dishonest Content-Length. Body deadlines, IP ingress limits and database
user quotas apply. Production needs a gateway for shared ingress limits and
slow-client/egress controls. API errors, provider errors and request metadata do
not expose raw text, keys or database URLs. Disable Uvicorn access logging;
HTTPX/httpcore URL logging is suppressed. Configure log storage deliberately.

Analysis uses short authorization/quota and persistence transactions, with no
open write transaction during model/network work. Success is sent only after
persistence commits. Partial results explicitly list missing evidence. Model
artifacts are loaded only from a trusted operator-controlled directory after
hash/version checks. A hash alone cannot protect against malicious replacement
of both model and manifest; restrict filesystem/mount access. No model-artifact
upload endpoint exists. APK uploads use byte/archive/expansion/path controls and
an optional bounded static child parser. Genuine parsing remains unverified;
uploaded applications are never installed or executed.
QR image upload validates PNG/JPEG media/signatures, bytes/pixels and decoded
payload bounds, uses a private disposable resource-limited child parser, cleans
temporary data, and never retains the raw image. This is bounded process parsing,
not a hardened malware sandbox. Caller displays remain masked and reputation
unknown; no unverified user report is treated as authoritative evidence.

Optional Gemini interpretation requires an owner's explicit strict-boolean opt-in
and backend configuration. It sends bounded existing finding descriptions and
application recommendations without raw submissions. Structured responses can
select existing references only; unsupported IDs/actions and extra fields are
rejected with empty outputs. Original evidence and risk assessments are preserved.
The JSON media-type requirement is enforced before external processing. Live
model communication and deployment data-handling controls remain unverified.

User deletion covers individual investigations and associated evidence. Expired
cases are hidden immediately; scheduled maintenance physically deletes them.
Defaults: investigation/report retention 30 days, audit metadata 180 days.
Watchlists persist until owner deletion. Full account erasure, backups/legal
holds and storage-object controls need their own workflow.
Audit metadata excludes message bodies. It is not a complete incident logging
or legal compliance implementation.

Indian obligations require qualified review for the actual business/deployment.
The DPDP Act 2023 and Rules 2025 use staged commencement; verify applicable
provisions, amendments, notice/consent/withdrawal, purpose limitation, safeguards,
breach notification, erasure/access/grievance rights, children, processors and
cross-border arrangements. Official notification and rules:
https://www.meity.gov.in/static/uploads/2025/11/c56ceae6c383460ca69577428d36828b.pdf
and https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf .

Where applicable, CERT-In directions include reporting specified incidents within
six hours and securely maintaining ICT logs for 180 days in Indian jurisdiction.
Verify scope, point of contact, time synchronization, preservation and hosting
region/backup jurisdiction. Source:
https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf .
The code's retention default alone does not satisfy these obligations. No legal
compliance, production readiness or unverified provider success is claimed.


Correlation searches owned unexpired investigations only. It matches hashes before URL redaction, bounds results and validates evidence for every edge. Graph nodes never copy raw SMS. Deletion/retention remove unsupported graph support. Live PostgreSQL RLS, HTTPS termination and provider access remain deployment checks.
