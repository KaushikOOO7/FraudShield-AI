# Caller analysis

POST /api/v1/analyze/caller accepts phone_number plus normal submission metadata.
Requires bearer authentication, JSON, existing limits and optional owned device
validation. Phone formats: E.164, or a ten-digit Indian mobile number beginning
6–9 (normalized with +91); whitespace/parentheses/hyphens are removed.
These rules check syntax only, not allocation, validity, caller identity or
reputation. Do not treat a normalized number as an authenticated caller.

201 returns/stores a partial standard InvestigationResponse, information-level
format finding, masked subject and provider_not_configured reputation source.
No reputation request, fabricated reports, ML label or score is substituted.
Classification remains EXERCISE_CAUTION for missing identity/reputation evidence.
Full phone numbers are not persisted in an indicator index. History/ownership,
redaction, device checks, audit and deletion use the common workflow.

No permitted caller provider, caller dataset or verified report aggregation is
available. Caller-ID spoofing remains a limitation. Reports are separately
owner-scoped and unreviewed, never inferred to be genuine reputation evidence.
