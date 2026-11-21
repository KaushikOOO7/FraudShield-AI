# Phase 1 verification evidence

Phase 2 changes and verification attempts are recorded separately in [phase2](phase2/README.md). The user explicitly requested Phase 2; the Phase 1 failures below remain historical evidence and are not rewritten as a passing build.

The environment is Windows PowerShell at `C:\Users\abhis\fraud`. `JAVA_HOME` and `ANDROID_HOME` are unset; `java`, `gradle` and `adb` were not found, and the standard SDK/JDK locations are absent. Gradle, GitHub wrapper and Google's Android repository URLs fail to connect. No escalation was attempted or needed for project edits.

`assembleDebug.txt` and `test.txt` preserve actual Windows-equivalent Gradle command output. Both exit with status 1 before Gradle starts: JDK 17 is missing. `wrapper-bootstrap.txt` records the failed official wrapper download (unreachable remote server). The source audit output lives in `source-audit.txt` and passes: 34 Kotlin sources inspected, 14 destinations, 157 matching resources per language, five verdict fixtures. These logs are not evidence of APK compilation, JUnit execution or app launch.

The required phase gate remains blocked until JDK 17, SDK 34 and dependency network access are available. On a prepared machine, run the README quickstart, commit the official generated wrapper/checksum, then repeat assembleDebug and test. Do not mark Phase 1 DONE until both the debug build and navigation launch are verified.
