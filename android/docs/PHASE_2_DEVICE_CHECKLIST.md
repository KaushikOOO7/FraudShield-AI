# Phase 2 device checkpoint · pending execution

This is a test plan, not a recorded result. There is no built APK, connected Android device/emulator or configured teammate backend in the current environment. Do not present Demo verdicts as real backend responses.

1. Build/install using the README. Use debug Demo for a reproducible offline pipeline, or a confirmed real backend and an approved flagged sample from the teammate.
2. Fresh install: Welcome shows no OS prompt. Visit each onboarding page. On Permissions, enable background-check consent, the desired source and warning notifications only after reading their rationale. For notification access, select the SMS app (or another supported app) explicitly.
3. Deny every permission on a separate fresh install. In Demo, a consented manual text/caller check should open Alert Detail. With a real backend, manual checks must need no notification/SMS/call/camera/contact grant. With an unreachable backend, show a retryable error; no invented verdict. Emergency and saved history must remain usable.
4. Test notification-listener route with direct SMS disabled. Generate a supported text notification containing the approved sample. On an emulator, use the synthetic example below; ensure the default SMS app itself is permitted to show notifications and selected in FraudShield. A Demo HIGH_RISK result should produce a `DEMO` warning with View.
5. Test the direct RECEIVE_SMS route separately with SMS and warnings enabled. The default SMS app notification should be skipped while this route is active; one message should not create duplicate investigations through both routes.
6. Tap the warning from a stopped activity/process. Confirm the correct case ID, shared VerdictBadge, backend/fixture score, explanations, expanded agent signals and saved/Demo provenance. Test the View action as well as the notification body.
7. Tap Call 1930; confirm the dialer shows 1930, then exit **without placing a call**. Check NCRP opens its official URL. Bank actions must open an installed supported bank app or show clear manual instructions; never claim an account was frozen. Share must omit original evidence and include DEMO when applicable.
8. Revoke an enabled permission in Android settings while the app is running. Within the resume/foreground health refresh, confirm the persistent re-enable banner and Attention state. Future jobs must not send data for the revoked source. Re-enable from its rationale card.
9. Disable monitoring or withdraw background-check consent while a check runs. Confirm cancellation and no subsequent warning. Incoming calls must always be allowed, including offline and backend failure. API 26–28 must show the caller role unavailable and offer manual number checks.
10. Airplane mode: Demo manual checks still work; real mode shows an honest connection error. Saved cases remain available and explicitly labeled saved. Unexpired cached caller findings may warn with a saved-reputation label; an unknown caller must not get a fabricated score. Repeat the same source within ten minutes and after the debounce window.

For **emulators only**, inject a synthetic SMS without contacting a real phone:

```powershell
adb emu sms send +911234567890 "Urgent KYC: account blocked. Share your OTP for a refund. https://kyc-check.example.invalid"
```

The sender/domain are synthetic. In live mode this text has no promised verdict: use teammate-approved samples and preserve the returned result. A synthetic Demo warning is proof of client plumbing only.

Capture screenshots/video following [the capture checklist](screenshots/README.md). Record Android API/device, build flags, locale and granted sources. Redact evidence and credentials; check Home, Scan, Alert Detail and Emergency with TalkBack and 200% font scale. Fill in actual results only after executing on a device.
