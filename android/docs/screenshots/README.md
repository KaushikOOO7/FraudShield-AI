# Device capture checklist · pending

No Android device/emulator or built APK is available in the current environment. This folder intentionally contains no fabricated device captures.

After the build and real-device gates pass, capture Welcome, Hindi Home, Kannada Home, permission rationale/denial, Home paused/enabled/revoked, manual check, history empty/error, each verdict via the shared badge, agent signals expanded, graph, assistant disclaimer, trends, family opt-in, privacy deletion confirmation, report outbox and Emergency's visible 1930 dialer action.

For each screen, check default and 200% font scale. Record device model, Android API, build variant, demo flag and locale. A stage demo recording must carry the persistent DEMO label when using fixtures. A real flagged-test-SMS recording must use a reachable teammate backend; it must not present a synthetic case as a real backend result.

```powershell
adb shell screencap -p /sdcard/fraudshield-home.png
adb pull /sdcard/fraudshield-home.png docs/screenshots/
adb shell screenrecord /sdcard/fraudshield-demo.mp4
adb pull /sdcard/fraudshield-demo.mp4 docs/screenshots/
```

Do not include real phone numbers, OTPs, family names or bank credentials in the captures. Never place a demonstration call to the real 1930 emergency helpline.
