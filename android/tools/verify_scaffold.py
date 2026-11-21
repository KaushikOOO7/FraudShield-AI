"""Offline source checks. These do NOT compile Kotlin or replace Gradle/device tests."""
from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "app/src/main"
JAVA = MAIN / "java/com/fraudshield/app"

def check(condition, message):
    if not condition:
        raise AssertionError(message)

strings = {}
for directory in ("values", "values-hi", "values-kn"):
    xml = ET.parse(MAIN / "res" / directory / "strings.xml")
    entries = {s.attrib["name"]: s.text or "" for s in xml.getroot()}
    check(len(entries) == len(xml.getroot()), f"Duplicate resource in {directory}")
    strings[directory] = entries
for directory, entries in strings.items():
    check(set(entries) == set(strings["values"]), f"Translation key mismatch: {directory}")
    for key, value in entries.items():
        fmt = re.findall(r"%\d+\$[ds]", value)
        check(sorted(fmt) == sorted(re.findall(r"%\d+\$[ds]", strings["values"][key])), f"Format mismatch: {key}/{directory}")

for xml_path in MAIN.rglob("*.xml"):
    ET.parse(xml_path)

sources = list(JAVA.rglob("*.kt"))
combined = "\n".join(path.read_text(encoding="utf-8") for path in sources)
references = set(re.findall(r"R\.string\.(\w+)", combined))
check(references <= set(strings["values"]), f"Missing string resources: {references - set(strings['values'])}")
check("!!" not in combined, "Found non-null assertion")
check("GlobalScope" not in combined, "Found GlobalScope")
check("fun VerdictBadge(" in combined, "Missing shared badge")
check(combined.count("fun VerdictBadge(") == 1, "Duplicate verdict badge")

destinations = (JAVA / "navigation/Destinations.kt").read_text(encoding="utf-8")
routes = re.findall(r'^    (\w+)\("([^\"]+)"', destinations, re.M)
check(len(routes) == 14, f"Expected 14 destinations, found {len(routes)}")
nav = (JAVA.parent / "app/FraudShieldApp.kt").read_text(encoding="utf-8")
for name, route in routes:
    check(f"composable(Destination.{name}.route" in nav, f"Missing navigation body: {name}")

for feature in (JAVA / "feature").iterdir():
    texts = "\n".join(p.read_text(encoding="utf-8") for p in feature.glob("*.kt"))
    entries = re.findall(r"^fun (\w+Route)\(", texts, re.M)
    check(len(entries) == 1, f"Feature needs one public entry: {feature.name}: {entries}")
    check(not re.search(r"riskScore\s*=\s*\d|risk_score\s*=\s*\d", texts), f"Hardcoded risk in {feature}")
    check("FraudShieldApi" not in texts and "HistoryDao" not in texts, f"UI bypasses repository: {feature}")

manifest = (MAIN / "AndroidManifest.xml").read_text(encoding="utf-8")
check("READ_SMS" not in manifest and "READ_CALL_LOG" not in manifest, "Prohibited broad permissions")
check("FOREGROUND_SERVICE" not in manifest, "Phase 1 does not run a foreground service")
check(not list((MAIN / "assets").rglob("cases.json")) if (MAIN / "assets").exists() else True, "Demo fixtures in release assets")
check("local.properties" in (ROOT / ".gitignore").read_text(), "local.properties must be ignored")

cases = json.loads((ROOT / "app/src/debug/assets/demo/cases.json").read_text(encoding="utf-8"))
verdicts = {"VERIFIED", "SAFE", "CAUTION", "HIGH_RISK", "CONFIRMED_FRAUD"}
check({item["verdict"] for item in cases} == verdicts, "Fixtures must cover all five verdicts")
for item in cases:
    check(item["case_id"].startswith("DEMO-"), "Unlabeled synthetic case")
    check(0 <= item["risk_score"] <= 100 and 0 <= item["confidence"] <= 1, "Invalid risk or confidence")
    check(item["created_at"].endswith("Z"), "Timestamp is not UTC")
    for finding in item["agent_findings"]:
        check(finding["agent"] in {"Message", "Call", "Link", "Behavior"}, "Unknown agent")
        check(finding["status"] in {"OK", "LOW", "SUSPICIOUS", "HIGH"}, "Unknown agent status")
for fixture in (ROOT / "app/src/debug/assets/demo").glob("*.json"):
    json.loads(fixture.read_text(encoding="utf-8"))

release = (ROOT / "app/src/release/java/com/fraudshield/app/data/di/RepositoryModule.kt").read_text(encoding="utf-8")
check("FakeRepository" not in release, "Fake repository in release binding")

# Phase 2 source boundaries; these checks do not execute Android services.
android_ns = "{http://schemas.android.com/apk/res/android}"
manifest_root = ET.parse(MAIN / "AndroidManifest.xml").getroot()
app = manifest_root.find("application")
expected_services = {
    ".core.service.FraudShieldListener": "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE",
    ".core.service.FraudShieldCallScreeningService": "android.permission.BIND_SCREENING_SERVICE",
}
for name, permission in expected_services.items():
    service = next((s for s in app.findall("service") if s.get(android_ns + "name") == name), None)
    check(service is not None and service.get(android_ns + "permission") == permission, f"Unprotected service: {name}")
receiver = app.find("receiver")
check(receiver is not None and receiver.get(android_ns + "permission") == "android.permission.BROADCAST_SMS", "Unprotected SMS receiver")
check("RECEIVE_SMS" in manifest and "POST_NOTIFICATIONS" in manifest, "Missing supported permission routes")
worker = (JAVA / "data/monitoring/AnalyzeSignalWorker.kt").read_text(encoding="utf-8")
coordinator = (JAVA / "data/monitoring/SignalCoordinator.kt").read_text(encoding="utf-8")
check('workDataOf("signal_id" to id)' in coordinator, "WorkManager must receive opaque references")
check("consentWatcher" in worker and "if (allowed(signal)) publisher.publish(case)" in worker, "Missing consent checks around background processing")
check("Result.retry()" not in worker, "Do not replay non-idempotent analyze POSTs")
crypto = (JAVA / "data/monitoring/PendingSignalStore.kt").read_text(encoding="utf-8")
check("AndroidKeyStore" in crypto and "AES/GCM/NoPadding" in crypto, "Missing encrypted signal storage")
backend = (JAVA / "data/repository/BackendRepository.kt").read_text(encoding="utf-8")
check("!BuildConfig.BACKEND_READY" in backend and "!preferences.protection.value.cloudConsent" in backend, "Missing live request consent/configuration gate")
call_service = (JAVA / "core/service/FraudShieldCallScreeningService.kt").read_text(encoding="utf-8")
check("setDisallowCall(false)" in call_service and "setRejectCall(false)" in call_service, "V1 must allow calls")
check("setForeground(" not in combined and "startForegroundService(" not in combined, "Unexpected foreground service path")
print(f"PASS: {len(sources)} Kotlin source files checked; 14 destinations; {len(strings['values'])} resources in each of en/hi/kn; five verdict fixtures.")
print("PASS: Phase 2 service guards, opaque encrypted queue, consent boundaries and non-blocking caller policy inspected.")
print("Source invariants only. Kotlin compilation, Android resource compilation and device behavior remain unverified.")
