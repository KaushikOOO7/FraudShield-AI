# APK static adapter — parser verification pending

POST /api/v1/analyze/apk requires bearer auth and multipart file/source fields.
Accepted media: application/vnd.android.package-archive or application/octet-stream.
Default upload cap 20 MiB (APK_MAX_UPLOAD_BYTES); multipart overhead cap adds
32 KiB. Filenames are ignored. No APK is installed or executed.

Structural guards reject malformed ZIPs, missing manifests, duplicate/traversal/
encrypted entries, >5,000 entries, >40 MiB per entry, >128 MiB expanded total and
>100 expansion ratio. Androguard parsing uses private temporary files, a child
process, resource limits and a 15-second timeout; files are cleaned afterwards.
This requires additional container/egress hardening for production.

The Androguard 4.1.4 adapter extracts actual package/name/version, requested
permissions, explicit exported=true declarations, signing-certificate metadata,
SHA-256 and bounded DEX URL strings. Permissions alone cannot establish malware.
Only SMS+contacts requests raise caution; no dynamic execution, malicious-hash
lookup or APK ML is fabricated. Signature/publisher authenticity is not verified.
Analysis would use the common persisted partial InvestigationResponse/history.

Androguard is not installed or cached in this environment. Actual metadata parsing
and an end-to-end genuine APK investigation are **not verified**. The endpoint
currently returns 503 apk_parser_unavailable without a fake record. Install
backend/requirements-apk.txt when package/network access is available, then test
against an identifiable legitimate APK fixture before declaring this feature
complete. Version/Python support source: https://pypi.org/project/androguard/4.1.4/ .
Current tests verify upload, archive expansion/path controls and missing-parser
behavior with explicitly non-installable security fixtures, never malware data.
