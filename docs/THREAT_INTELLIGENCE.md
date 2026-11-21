# Threat intelligence

Implemented adapters: Google Safe Browsing v4, VirusTotal v3 URL report,
URLhaus, PhishTank, AbuseIPDB public-IP checks, fixed-registry RDAP and crt.sh.
They are connected to submitted/extracted URL investigation services.
**No live success is claimed in this session:** no provider keys were configured.
Offline tests use explicitly synthetic HTTP contract fixtures in disposable
contexts, never as real reports.

| Provider | Environment | Behavior/reference |
| --- | --- | --- |
| Google Safe Browsing | GOOGLE_SAFE_BROWSING_API_KEY | POST threatMatches lookup at fixed HTTPS origin. Validates match type and requested URL. https://developers.google.com/safe-browsing/v4/reference/rest/v4/threatMatches/find |
| VirusTotal | VIRUSTOTAL_API_KEY | GET an existing URL report using URL-safe base64 identifier. Never submits/rescans a URL. Validates URL, detector counts and report timestamp. https://docs.virustotal.com/reference/url-info |
| URLhaus | URLHAUS_API_KEY | Fixed HTTPS malware-URL lookup. https://urlhaus.abuse.ch/api/ |
| PhishTank | PHISHTANK_API_KEY | Fixed HTTPS URL lookup. https://www.phishtank.org/api_info.php |
| AbuseIPDB | ABUSEIPDB_API_KEY | Public IP literals only; no domain-to-IP inference. https://docs.abuseipdb.com/#check-endpoint |
| Registry RDAP | ENABLE_RDAP=false by default | Supported fixed registry origins; dates do not establish fraud. https://data.iana.org/rdap/dns.json |
| crt.sh | ENABLE_CRTSH=false by default | Actual CT observations; not live TLS validity or safety. https://crt.sh/ |

Requests need explicit per-submission `use_threat_intelligence: true`. Missing
keys produce `provider_not_configured`, with null verdict and no request. A key
present but never exercised is `configured_not_verified` in system status.
Configured but unrequested lookups yield `not_requested`.

Outcome statuses: `matched`, `no_match`, `not_found`, `stale`, `invalid_response`,
`provider_error`, `rate_limited`, `not_requested`, `provider_not_configured`.
Unavailable/invalid results never carry a clean verdict. `no_match` means
`no_known_match`, not guaranteed safety. Empty-but-valid Safe Browsing `{}` is
distinguished from malformed/unknown JSON. VirusTotal requires real nonzero
detector totals; reports older than 30 days are marked stale.

Contradictory no-match responses are rejected. URLhaus no_results cannot also
carry a malware listing/status/date; PhishTank in_database=false cannot also
claim verified/valid=true. These cases return invalid_response with no verdict,
and are tested using explicitly non-production HTTP fixtures.

Fixed provider HTTPS origins, certificate verification, no redirects, no proxy
environment trust, bounded connections, a five-second default total deadline
per attempt, two attempts maximum, and a 256 KiB JSON response limit apply.
HTTP 429 is not retried immediately and carries parsed Retry-After seconds.
Transient network failures and 5xx get one bounded retry. Compressed provider
responses are rejected after requesting identity encoding. Errors never include
raw provider responses, credentials or request URLs.

Per-user URL/provider cache: at most 256 entries/process, at most five minutes
for validated outcomes. Google matches use the shorter provider cacheDuration;
absent/invalid duration prevents a validated warning, and zero duration is stale.
No-match Google responses without a duration are not cached. Cache hits retain
the earlier real check timestamp and
set `cached: true`. They do not fabricate a fresh observation. Failed/missing
providers are not cached as clean. Persistence records status, selected validated
details, source ID and timestamps; no raw keys or unbounded provider payloads.

VirusTotal votes are not confirmation of fraud. Three or more malicious votes
in a non-stale report give a high warning under the documented qualitative rule;
other positive/stale reports give caution. Safe Browsing matches give high risk,
with no automatic confirmed-fraud classification.

Check the provider's account permissions, quota, data disclosure rules and terms
for the actual deployment. Safe Browsing's non-commercial-use terms and
VirusTotal public API restrictions may require a different commercial service
tier. Configuration does not itself prove permitted access or successful use.

Google warnings include qualifying language, the required Google attribution and
the official advisory URL. Clients must show the protection limitation before
opt-in and must not display Google warnings after `sources[].details.valid_until`.
Stored history is a historical assessment, not a refreshed warning. References:
https://developers.google.com/safe-browsing/v4/usage-limits and
https://docs.virustotal.com/reference/public-vs-premium-api .

To verify live operation later, use a permitted, non-sensitive input and actual
key, enable the request opt-in, then inspect the persisted source status and
timestamp. A successful no-match remains uncertainty. API keys stay backend-only.

Additional observed/unsupported_input outcomes describe neutral registry/CT
facts or unsupported scope. They are not clean verdicts. All seven adapters
have isolated contract validation; actual external success remains unverified.
