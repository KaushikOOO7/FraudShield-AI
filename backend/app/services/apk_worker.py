"""Static Androguard parser in a bounded child process. Never installs/runs an APK."""
import json
import re
import resource
import sys
import zipfile


def analyze(path):
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 * 1024, 1536 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 * 1024, 8 * 1024 * 1024))
    from androguard.core.apk import APK
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from importlib.metadata import version

    apk = APK(path)
    if not apk.is_valid_APK():
        raise ValueError("Invalid APK manifest")
    manifest = apk.get_android_manifest_xml()
    namespace = "{http://schemas.android.com/apk/res/android}"
    exported = []
    for element in manifest.iter():
        if element.tag in ("activity", "activity-alias", "service", "receiver", "provider") and element.get(namespace + "exported") == "true":
            exported.append({"type": element.tag, "name": element.get(namespace + "name")})
    certificates = []
    certificate_status = "parsed"
    try:
        for certificate in apk.get_certificates():
            parsed = x509.load_der_x509_certificate(certificate.dump())
            certificates.append({"sha256": parsed.fingerprint(hashes.SHA256()).hex(), "subject": parsed.subject.rfc4514_string()[:500], "issuer": parsed.issuer.rfc4514_string()[:500], "not_before": parsed.not_valid_before_utc.isoformat(), "not_after": parsed.not_valid_after_utc.isoformat()})
    except (ValueError, TypeError):
        certificate_status = "unavailable"
        certificates = []
    candidates = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if re.fullmatch(r"classes\d*\.dex", name):
                # Explicit scan bound. Do not interpret missing strings as clean.
                with archive.open(name) as handle:
                    data = handle.read(2 * 1024 * 1024)
                for match in re.finditer(rb"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]{1,2000}", data):
                    value = match.group().decode("ascii")
                    if value not in candidates:
                        candidates.append(value)
                    if len(candidates) >= 20:
                        break
            if len(candidates) >= 20:
                break
    return {"status": "parsed", "metadata": {
        "parser": "androguard", "parser_version": version("androguard"),
        "package_name": apk.get_package(), "application_name": apk.get_app_name() or None,
        "version_name": apk.get_androidversion_name() or None, "version_code": apk.get_androidversion_code() or None,
        "requested_permissions": apk.get_permissions(), "explicitly_exported_components": exported,
        "certificates": certificates, "certificate_status": certificate_status,
        "embedded_url_candidates": candidates,
    }}


if __name__ == "__main__":
    try:
        print(json.dumps(analyze(sys.argv[1]), ensure_ascii=True))
    except ImportError:
        print(json.dumps({"status": "parser_unavailable", "metadata": None}))
    except Exception:
        print(json.dumps({"status": "invalid_apk", "metadata": None}))
