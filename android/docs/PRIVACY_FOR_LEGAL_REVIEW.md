# FOR-LEGAL-REVIEW · FraudShield AI privacy and DPDP notice draft

This is a draft, not an approved policy or compliance certification. Insert the operator/data-fiduciary identity, service address, grievance contact, applicable legal basis, processors, retention schedule and effective date before public release.

FraudShield AI is intended to analyze supported notifications you allow, identify suspicious incoming callers by reputation, and check links, QR codes and screenshots you share. It does not listen to calls, read all WhatsApp messages or guarantee detection of all fraud or deepfakes.

Protection is optional. You may use manual check mode without notification, SMS, caller or contact access. Before cloud analysis is enabled, a consent screen must explain what selected content will be sent to the investigation service and why. You can withdraw monitoring consent and revoke permissions at any time. QR camera access occurs only in the active scanner. A contact picker must transmit only the member explicitly chosen, never the full address book.

On-device filtering is intended to reduce unnecessary transfers; it is not a local fraud verdict. Only consented, relevant content should be sent. Do not submit passwords, OTPs, UPI PINs or full bank credentials. Reports should use redacted evidence and account last-four digits only. Family warnings require opt-in member consent and omit original messages and financial details.

The client cache may contain case explanations, extracted entities and pending user reports. Backups are disabled. Cloud retention and on-device expiry must be finalized and disclosed. No analytics SDK or advertising identifier is included. Logs must omit evidence and anonymous bearer tokens.

Provide accessible request flows for information/access, correction, erasure, consent withdrawal and grievance redressal as applicable under the DPDP Act and effective rules. The backend deletion and correction endpoints, identity verification and offline-request handling must be confirmed before claiming these flows work. “Delete all my data” must distinguish local deletion from confirmed remote deletion.

Children's data processing, language quality, international transfers, subprocessors and emergency guidance require counsel review. Guidance is informational and not legal or financial advice. Users should confirm suspicious requests via official bank/government channels.

**Phase 2 client behavior:** manual checks require per-check consent; background checking requires separate opt-in, enabled source permissions and selected notification apps. Live requests remain disabled until the teammate URL/contract is configured. Original pending signals are encrypted with an Android Keystore AES-GCM key; WorkManager receives an opaque ID, and completed/discarded jobs delete their signal. Expired queued files are cleaned on app startup and subsequent intake; force-stopping the app may delay cleanup. Demo substitutes synthetic content and persists separately labeled fixture cases. Investigation cache/token encryption, finalized retention, family enrollment, export and remote deletion still require Phase 3/4 implementation and legal review.
