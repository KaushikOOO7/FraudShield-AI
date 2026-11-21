# Optional Gemini evidence prioritization

POST /api/v1/investigations/{id}/interpret requires owner authentication and JSON
use_gemini, a strict boolean default false. Configure actual GEMINI_API_KEY and
an account-supported GEMINI_MODEL; no model ID is guessed. Source contract:
https://ai.google.dev/gemini-api/docs/structured-output .

The adapter sends bounded, application-generated finding descriptions/IDs and
known recommendation indices. No raw SMS, URL queries, phone numbers, APK bytes
or user-report text is sent. The model can return only reference-selection JSON.
Unknown evidence IDs, indices, extra fields or malformed output are rejected.
Returned descriptions/actions are the original server content; no generated
factual prose, threat intelligence, new relationships or numeric scores enter
the result. Critical risk assessment remains deterministic and unchanged.

Output statuses: provider_not_configured, not_requested, insufficient_evidence,
available, invalid_response, provider_error, rate_limited. Unavailable states
have empty selections and null model_used/confidence. Available names the
provider-returned model version after a validated response; it is interpretation,
not independent verification. HTTP/provider response limits/retries/timeouts
and sanitized logging use the shared transport. No long SQL write transaction
is held during network work. The actual status/reference IDs are audited.

Offline tests exercise selection, rejection of invented evidence/scores, opt-in,
ownership, input media, persistence and unchanged risk. No live Gemini success
is claimed: real keys/model communication is still required. LangGraph and the
full multi-agent coordinator are not implemented and require separate work.
