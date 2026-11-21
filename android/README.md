# FraudShield AI · Android client

Android client with all 14 destinations implemented for an India-focused fraud-protection companion. Kotlin, Compose Material 3, MVVM, StateFlow, Hilt, Retrofit/OkHttp/kotlinx.serialization and Room. The AI and investigation backend belong to a separate teammate.

**Current status:** the core Welcome → consent/permissions → Home → text/caller check → shared Alert Detail → History loop is implemented, including notification/SMS/caller intake, encrypted queued signals, warning actions, permission-revocation handling and persistent Demo cases. QR camera, screenshot selection/upload, Canvas graph/PNG export, assistant, trends, opt-in family, reports/outbox and privacy export/deletion are now implemented. Unconfirmed backend extensions stay gated; local operations remain available. **No APK, passing Gradle build, device demonstration, TalkBack pass or performance measurement is claimed.** Android Studio/tooling appeared during Phase 2, with JBR 21 and SDK 37; the required JDK 17, SDK 34 and Build Tools 34 are still missing, and Gradle downloads are unreachable from this session. No teammate URL or confirmed payload schema has been supplied. See [verification evidence](docs/verification/README.md).

## Quickstart · 8 steps

1. Clone/copy this repository onto a network-enabled development machine. Prerequisites: **Android Studio Koala or newer, JDK 17, Android SDK Platform 34, Build Tools 34.0.0**, and platform tools. Set `JAVA_HOME` and Android Studio's **Gradle JDK** to JDK 17; newer Studio installations may default to a newer incompatible runtime. Use SDK Manager for the Android components.
2. Copy `local.properties.example` to `local.properties`; set `sdk.dir` to your SDK directory.
3. Set `BACKEND_BASE_URL` in `local.properties` to the teammate's URL, with a trailing `/`. Emulator host: `http://10.0.2.2:8000/`; a phone needs a reachable LAN address. Set `BACKEND_CONTRACT_CONFIRMED=true` only after confirming anonymous registration `{}`, SMS `{text}`, URL `{url}`, caller `{phone}`, and history items matching the investigation model. Until then, live requests stay disabled. Set `FEEDBACK_CONTRACT_CONFIRMED=true` separately only after accepting the proposed feedback API. HTTPS is required in release; debug alone permits HTTP. Never place credentials in the URL.
4. For an offline Demo walkthrough, set `DEMO_MODE=true` in `local.properties`. Default is `false`; release forces `false` and excludes fake code/assets. Demo never replaces a failed live request.
5. Run `./gradlew assembleDebug` (`.\gradlew.bat assembleDebug` in Windows PowerShell). The launchers bootstrap the official Gradle **8.7** wrapper JAR if missing, checking it against Gradle's published SHA-256 and pinning the distribution checksum. Network access is required. Commit the verified generated JAR and updated properties once obtained. On Unix, use `sh gradlew assembleDebug` until the launcher executable bit is recorded in Git.
6. Run `./gradlew test` (`.\gradlew.bat test` on Windows). These commands have **not passed in the supplied environment**.
7. Install with `adb install -r app/build/outputs/apk/debug/app-debug.apk`, or run from Android Studio.
8. Walk through Welcome → Detect/Investigate/Protect → rationale cards → Skip for now → Home. In Scan, paste `Urgent KYC: share your OTP to avoid account blocked` and select consent, then Check. Demo shows a synthetic result; live mode uses only the backend verdict. Expand agent signals, copy an entity and open the 1930 dialer. Use the [device checkpoint](docs/PHASE_2_DEVICE_CHECKLIST.md) for notification/SMS tests. **Do not place a test call to the real emergency helpline.**

The repository starts without `local.properties` and without a permission prompt. Manual text/caller checks require an explicit per-check consent choice and no protection permission. Background checking requires separate opt-in, enabled sources and live OS grants; notifications additionally require selected apps. Demo validates input, then returns fixed synthetic cases instead of investigating it. Use it only as a labeled demonstration. Returning users skip onboarding; warning taps open the saved case.

## Architecture

```text
FraudShieldApplication (Hilt) + AppCompatActivity (per-app locales)
  └── Compose / Material 3 / Navigation (14 stable destinations)
       └── feature/*Route                 one public UI entry per feature
            └── ViewModel                 lifecycle + immutable StateFlow UI
                 └── FraudRepository       single interface for investigations
                      ├── BackendRepository → Retrofit → OkHttp → device token
                      │                    └→ Room history cache (IO dispatcher)
                      └── FakeRepository    debug fixtures → isolated Room demo rows

NotificationListener / SMS receiver / CallScreeningService (immediate allow)
  └── consent + allowed-app gate → on-device keyword prefilter / OTP redaction
       └── encrypted pending signal (Android Keystore AES-GCM; opaque work ID)
            └── Hilt CoroutineWorker → Repository → Room → warning → Alert Detail

core/designsystem  colors, typography, cards, states, single VerdictBadge
core/model         exact verdict/status enums and serialized API models
core/network       dispatchers, structured failure mapping
core/db            history_case, report_outbox, entity_cache, settings
data/api           Retrofit contract
data/repository    backend, session, UI preferences; fake only in debug
data/di            Hilt network/cache bindings + variant repository selection
```

One Gradle application module supplies the required package boundaries. Features never call Retrofit/Room directly. Network and file processing use IO dispatchers; cache and operation state combine into lifecycle-collected StateFlows. First launch performs no network request. Returning users who previously consented may sync history after configuring the backend. Background work checks consent again before sending and before warning; consent withdrawal cancels its request. QR uses CameraX and bundled ML Kit only on the active screen. Graph rendering uses native Canvas with cached fallback, avoiding a CDN/WebView. Offline reports are labeled locally queued; automatic replay requires confirmed server idempotency.

## Screen catalog

Device captures are pending; [screenshot checklist](docs/screenshots/README.md) records exactly what remains. No rendered design mockup is presented as a device screenshot.

| Destination | Current Phase 2 behavior | Next phase |
| --- | --- | --- |
| Welcome | Shield vector, calm promise, language picker, saved completion | Device/accessibility verification |
| Onboarding | Detect → Investigate → Protect, separate background opt-in | Device/accessibility verification |
| Permissions | Source switches, selected notification apps, lazy OS requests/settings, safe skip | Human/legal review |
| Home | Paused/attention/protected status, real cache counts, quick actions, Demo cases | Period statistics after contract clarification |
| Alert Detail | Shared badge/gauge, findings/signals, copy entities, source/freshness banner, real external actions, gated correction | Family sends in Phase 3 |
| History | Local flow, live cursor pagination, search/filter, retry and saved-mode fallback | Swipe report/delete/mark safe in Phase 3 |
| Scan / Check | Consented text/URL classification and caller number with country code; same detail destination | CameraX/ML Kit QR and consented screenshot upload are wired; upload contract must be confirmed |
| Investigation Graph | Canvas graph, legend, entity sheet, cached fallback, PNG export | Device verification |
| AI Assistant | Backend/Fake chat, suggested questions, markdown-lite, actions and disclaimer | Device verification |
| Trends | Backend/Fake weekly chart, categories and vectors | Device verification |
| Emergency | 1930 dialer, official portals, evidence and harassment guidance | Bank category sheets |
| Family Protection | Local opt-in members/contact picker, sharing switches, guarded redacted alerts | Confirm enrollment contract |
| Settings / Privacy | Monitoring pause, consent withdrawal, permission health, language/methodology | Counts/export, local deletion and guarded remote deletion implemented |
| Report / Submit | Evidence/consent, upload guard, receipt or explicitly local queue | Confirm upload/idempotency contract |

Home, Scan, History and Settings are the four bottom tabs. Other screens are pushed destinations with a back affordance. Static screens do not manufacture async failures; data-driven screens and placeholders use the common loading/error/retry/empty state renderer.

## Permission matrix

The Phase 2 manifest includes INTERNET, ACCESS_NETWORK_STATE, RECEIVE_SMS, POST_NOTIFICATIONS, CAMERA and optional READ_CONTACTS, plus system-permission-protected listener/screening/receiver components. Runtime grants are requested only from the rationale flow. Camera/contacts can be skipped and are not accessed automatically; their user-facing capture/member flows are Phase 3. No full address book is read or uploaded.

| Capability | Planned request | Why | If denied/revoked |
| --- | --- | --- | --- |
| Notification analysis | Notification Access settings after rationale | Prefilter notification title/text the user allows | Disable listener submission; manual checks remain; re-enable banner |
| Incoming caller reputation | `ROLE_CALL_SCREENING`; API 26–28 limitations documented in decisions | Caller metadata/reputation only; no audio or auto-blocking | Disable reputation warnings; manual number check |
| New SMS | `RECEIVE_SMS` after rationale and consent | Newly received message only | Notification/manual paths remain; no SMS history read |
| Local warnings | Android 13+ `POST_NOTIFICATIONS` after rationale | Show high-importance fraud alert channel | In-app alerts and permission-health banner |
| QR camera | `CAMERA` only when opening scanner after rationale | CameraX + bundled ML Kit on active screen | Paste a link instead; stop camera on revoke |
| Family contact | Optional `READ_CONTACTS` only after rationale; no reading in Phase 2 | Reserved for the explicitly opt-in family flow | Manual member entry/contact picker in Phase 3; never upload address book |

No READ_SMS, READ_CALL_LOG, microphone, background location or default SMS-handler role is declared. The client does not start a foreground service or call setForeground; it uses ordinary WorkManager work, which may be delayed by Android/Doze. Callback work stays lightweight, but the 300ms callback budget has not been measured. Calls are allowed before reputation lookup; cached caller findings have a 24-hour TTL and a saved-reputation label. Android 8/9 has manual number checks because role requests require API 29. Revoked permissions stop processing and show a re-enable banner; denying all permissions preserves manual checks, saved history and emergency actions.

## Demo mode

Set `DEMO_MODE=true` locally and rebuild **debug**. A persistent `DEMO` banner appears even on Welcome and pushed screens. All fixture case IDs start `DEMO-`; domains used for suspicious links end `.invalid`. Cases cover VERIFIED, SAFE, CAUTION, HIGH_RISK and CONFIRMED_FRAUD. These examples are **not supplied by the backend teammate** and are never used to assess real evidence. Scores exist only in JSON assets; ViewModels and Composables do not invent them.

The release source set binds only BackendRepository and cannot package debug fixtures. Demo uses the same consented intake/worker/warning/deep-link path with encrypted `{demo:true}` input, so it does not retain original notification/SMS content. It persists cases in separately filtered Room rows and labels warning/share/correction output DEMO. SMS and notification-listener device checkpoints are implemented but remain **unverified**, with no fabricated recording. When direct SMS is enabled, the default SMS app notification is skipped to avoid analyzing one SMS twice. A source is debounced for ten minutes.

## Testing and verification

```powershell
# Windows; JDK 17 + Android SDK 34 + dependency network required
.\gradlew.bat assembleDebug
.\gradlew.bat test
.\gradlew.bat connectedDebugAndroidTest  # emulator/real device required
.\gradlew.bat assembleRelease            # unsigned release; supply signing separately

# Optional source invariants only; no Android toolchain required
python tools/verify_scaffold.py
```

Auth/Retrofit tests check anonymous registration, Bearer headers, payload keys and UTC timestamps. Parsing tests cover URL-vs-SMS input, country codes, input rejection and OTP redaction. Signal policy tests cover consent/grants, source debounce, warning enums and status on denial/offline/unavailable service. Existing JUnit/Turbine tests check contracts and local-history error/retry/filter flows; one Compose test checks the 1930 action semantics. **Gradle and instrumentation tests remain unexecuted because the toolchain is missing.** R8 configuration exists but no release APK is claimed.

The source audit checks resource parity and placeholders in all languages, JSON and XML structure, route/entry coverage, demo isolation and prohibited UI data access. **It is not a Kotlin compiler or Android test.** TalkBack, 200% font scaling, API 26/28/29/33/34 behavior, revoked permissions and the cold-start target require device verification in Phase 4.

## Privacy and Play Store notes

[Draft privacy notice](docs/PRIVACY_FOR_LEGAL_REVIEW.md) is explicitly **FOR-LEGAL-REVIEW**. DPDP readiness is a design requirement, not a claim of legal certification. No analytics SDK, third-party keys or background audio capture is included. Backups are disabled for cached investigation evidence. Device token persistence is private app storage; production key-backed encryption and retention policy are tracked in decisions.

SMS permissions are restricted by Google Play. The planned direct-SMS route is for approved/disclosed distribution only; Play deployment needs a notification-access/manual variant or an accepted permissions declaration. Default SMS handling and call logs are later, separately scoped milestones. This app's current targetSdk 34 is fixed by the supplied brief; current Play target requirements must be checked before submission. Release networking rejects cleartext HTTP, release signing keys are external, and no store publication is performed.

See [DECISIONS.md](DECISIONS.md) for backend contract questions, implementation choices, deferred checkpoints and build limitations.

## Final source handoff

All 14 routes have functional client screens. Native QR decoding never submits automatically; screenshot/APK evidence is selected explicitly and upload is capped at 10 MB. Family contacts stay local, phone numbers are never substituted for enrolled member IDs, and live alerts need confirmed enrollment. History supports swipe report/local deletion plus correction requests; original backend verdicts are retained. Graph exports carry a DEMO watermark when appropriate. Privacy erasure stops monitoring, cancels work, wipes Room/session/pending/private cache data and clears navigation state; local-only deletion explicitly preserves remote records.

The following additional local flags default false and represent **unaccepted contract extensions**: `EVIDENCE_CONTRACT_CONFIRMED` (multipart /evidence and screenshot reference), `DELETION_CONTRACT_CONFIRMED` (DELETE /me with confirmed success/token invalidation), `FAMILY_ENROLLMENT_CONFIRMED` (valid enrolled IDs/recipient consent), and `REPORT_IDEMPOTENCY_CONFIRMED` (stable Idempotency-Key deduplication). Upload, deletion and enrollment must be confirmed with the teammate before enabling live writes. Reports may be saved on-device without claiming submission; replay is gated until idempotency is accepted.

Final checks: offline source audit passes, and the installed IDE Kotlin parser found zero syntax errors across 71 Kotlin files. This is **not typechecking or a build with Kotlin 1.9.24**. assembleDebug, test and assembleRelease were attempted and stopped before compilation because JDK 17 is not configured. Required SDK 34/Build Tools 34 are absent; only SDK 37/Build Tools 36 are installed, and Gradle download is incomplete/unreachable. No APK, real-device recording, screenshot pack, TalkBack pass, cold-start measurement or passing Gradle test suite is claimed. See [final evidence](docs/verification/final).

A five-minute judge walkthrough is in [DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md). Legal copy remains FOR-LEGAL-REVIEW. The final acceptance gate still needs a prepared toolchain, confirmed backend schemas and device execution.
