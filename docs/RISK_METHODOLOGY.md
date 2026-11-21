# Risk methodology

Version: `evidence-qualitative-v1`. Deterministic qualitative assessment;
**risk score, score type and confidence are null**. No LLM or arbitrary point
scale makes critical decisions.

| Classification | Current evidence requirement |
| --- | --- |
| HIGH_RISK | Validated Safe Browsing match; recent VirusTotal report with at least three malicious votes; or the actual secret-solicitation + KYC/payment-pressure rule combination. |
| EXERCISE_CAUTION | Caution rule, actual historical spam prediction, lower-count/stale provider warning, unverified URL or insufficient evidence. |
| SAFE_INDICATORS | SMS model predicts ham, no warning rule fires, and no URL-like substring needs unverified destination analysis. Explanation limits the conclusion. |
| CONFIRMED_FRAUD | Never returned automatically. Authoritative evidence and a human review workflow are required; that workflow is not implemented. Storage rejects this value without review time and an evidence reference. |

High warnings take priority over caution and limited ham indicators. A model
ham label cannot override a high provider warning. A spam label alone gives
caution. No-match is `no_known_match`, with no guarantee of legitimacy.

## SMS rules

Each finding references `sms-rules-v1` and an actual timestamp.

| Code | Observable trigger and limitation |
| --- | --- |
| SMS_REQUESTS_SECRET | Solicitation verb followed within four words by OTP/PIN/password/passcode/CVV/CVC. Immediate never/do-not/don't/not-to negations are excluded. Sender intent remains unverified. Recognizable actual secret values are rejected before inference. |
| SMS_KYC_PRESSURE_LINK | KYC wording + urgent/blocked/expired/suspended/deactivated wording + URL-like substring. Genuine messages may share language. |
| SMS_DIGITAL_ARREST_LANGUAGE | Phrase “digital arrest”; context and sender remain unverified. |
| SMS_PAYMENT_THREAT | Payment/transfer/deposit wording + police/arrest/jail/warrant wording. A co-occurrence is not a verified incident. |
| SMS_UNSUPPORTED_URL | URL-like substring fails validation; never fetched/forwarded. |
| SMS_SPAM_MODEL | Available trained historical baseline actually predicts spam. |

Secret solicitation combined with KYC-pressure-link or payment-threat raises a
documented high warning. Both may come from one message; no independent sources
or coordinated campaign are claimed. Sender/brand identity remains unknown.

## URL/provider rules

| Code/source | Rule |
| --- | --- |
| URL_IP_LITERAL | Public IP URL: caution with no inferred reputation. |
| URL_HTTP_SCHEME | HTTP spelling: information only; no certificate/page fetch. |
| URL_INTERNATIONAL_DOMAIN | IDNA/punycode host: information only, with no verified brand match. |
| URL_LONG_STRUCTURE | At least 200 characters: weak caution heuristic. |
| URL_MANY_HOST_LABELS | At least six hostname labels: weak caution heuristic. |
| SAFE_BROWSING_THREAT_MATCH | Validated match for the submitted URL: high warning. |
| VIRUSTOTAL_DETECTOR_REPORT | Actual counts and report date. At least three malicious votes with analysis at most 30 days old: high; other positive/stale reports: caution. |

URL ML, page/redirect fetches, domain age/ownership, caller reputation, verified
regulatory information and visual brand references are unavailable. A young
domain, HTTPS spelling or similarity cannot confirm fraud. None is fabricated.

Evidence includes source ID, verification status, time and attributes. Missing,
unrequested, invalid, stale and rate-limited sources stay explicit. Cache hits
preserve the earlier actual check time. Recommendations follow observed warnings
and advise independent verification. Messages are stored with redaction.


Stored URL-observation correlation is information-level evidence of identifier reuse, returned separately. It does not modify original classification, score or confidence. Hostname reuse is not confirmation of campaign ownership.

Additional provider rules: validated online URLhaus malware-download listings and PhishTank verified+valid listings raise a provider-attributed high warning. Offline URLhaus listings and AbuseIPDB IP-only indicators raise caution. RDAP dates and certificate-transparency observations are neutral metadata, never safety/fraud proof. A future actually trained URL phishing label raises caution only. Gemini selection only reorders existing observations/actions; it never changes scoring or adds facts.
