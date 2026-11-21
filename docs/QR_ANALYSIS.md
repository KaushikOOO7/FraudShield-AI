# QR analysis

POST /api/v1/analyze/qr uses multipart/form-data: file (PNG/JPEG), source
(existing submission enum, default api), use_threat_intelligence (literal form
true/false, default false). Supabase bearer required. Device registration is not
supported for this upload yet. Success 201 stores the usual InvestigationResponse
and QRAnalysis metadata; Location supports existing history/deletion APIs.

Default file cap: 2 MiB (QR_MAX_UPLOAD_BYTES), maximum decoded image 10 million
pixels, payload 5,000 characters. The request body cap adds 32 KiB for multipart
overhead. Original filenames are ignored. Signatures/media types and Pillow
image validation are checked. Parsing occurs in a disposable child process with
CPU/address-space/file-size limits and a ten-second deadline, single OpenCV
thread, no downloaded-content execution. Private temporary files are cleaned
on success/failure. This is process isolation, not a hardened container sandbox.
No original image is retained or uploaded to an intelligence/LLM provider.

OpenCV decodes actual payloads. No readable QR returns a stored partial analysis,
no_qr_found and empty findings/models; no content is invented. Multiple readable
QR payloads, malformed files or oversized content return sanitized 422. Unsupported
media returns 415; excessive file/body returns 413. Recognizable credentials in
decoded content return 422 sensitive_input with no investigation persisted.

HTTP(S) payloads use existing safe URL parsing and opted-in provider adapters;
private/invalid URLs are not fetched/forwarded. URL ML remains unavailable.
UPI payment URIs support payee-address syntax, unique query fields, positive
decimal amount if present and INR currency. Returned payee is masked; actual
amount/currency remain available. Validation is supported_syntax_only and
recipient_verified=false. This subset does not implement every NPCI extension.
It never verifies recipient identity or labels ordinary payment QR codes high
risk. Text QR content is redacted and treated with appropriate uncertainty.

Results always state partial: decoding and syntax are real, fraud verification
remains incomplete. No QR fraud dataset/model is invented. Automated tests use
clearly identified generated non-production QR images to exercise real decoding,
API persistence, permissions, redaction, UPI validation and file security.

A no_qr_found result has subject.value=null. SQL retains an empty content string alongside the explicit absence status; no placeholder QR content is invented.
