# Phase 2 verification

This directory records actual command results after the Phase 2 changes. `assembleDebug.txt` and `test.txt` capture Windows-equivalent Gradle attempts. `source-audit.txt` records offline structural checks; `toolchain.txt` records Java/SDK/network availability.

The source audit is not Kotlin compilation, Android resource compilation, JUnit execution or a device proof. The real notification→case checkpoint, calls, denial/revocation, TalkBack, font scale and runtime latency must be executed using the [device checklist](../../PHASE_2_DEVICE_CHECKLIST.md).

No backend URL or payload confirmation has been received. Live checks remain gated by explicit local configuration. Demo is default off, debug-only, and never replaces a live network error.

The required Gradle commands both exit before compilation because JDK 17 is not configured. The offline audit passes (51 main Kotlin files, 14 destinations, 230 string resources per language, all five verdict fixtures and structural Phase 2 guards). During work, Android Studio 2026.2.2 became available with bundled JBR 25, a separate JBR 21 installation and SDK 37/Build Tools 36; the required JDK 17/SDK 34/Build Tools 34 are absent. The new local.properties contains sdk.dir only and was preserved. A Gradle 8.7 download lock/.part file exists, both zero bytes, with no complete distribution or official wrapper JAR. Gradle downloads remain unreachable from this session. No newer SDK/JDK was substituted for the pinned stack.
