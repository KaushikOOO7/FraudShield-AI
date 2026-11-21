"""Download the licensed original UCI corpus; fail explicitly without networking.

No data is generated or substituted. Network acquisition is separate from API
startup and requires successful HTTPS communication with the original source.
"""
import argparse
import hashlib
import io
import json
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from backend.app.core.config import PROJECT_ROOT
from backend.app.ml.datasets import UCI_SMS_DOI, UCI_SMS_DOWNLOAD, UCI_SMS_SOURCE


def parse_sms_source(text: str) -> list[dict]:
    records = []
    for index, line in enumerate(text.splitlines()):
        if line.startswith(("ham\t", "spam\t")):
            label, content = line.split("\t", 1)
            records.append({"label": label, "content": content, "source_line": index})
        elif records:
            records[-1]["content"] += "\n" + line
        elif line.strip():
            raise ValueError("Source contains an orphan continuation")
    if not records or any(not record["content"].strip() for record in records):
        raise ValueError("Source contains no usable labeled records")
    return records


def download(output: Path) -> dict:
    endpoint = UCI_SMS_DOWNLOAD
    with httpx.Client(timeout=20, follow_redirects=False, trust_env=False, headers={"Accept-Encoding": "identity"}) as client:
        for _ in range(4):
            with client.stream("GET", endpoint) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    next_url = urljoin(endpoint, response.headers.get("location", ""))
                    parsed = urlsplit(next_url)
                    if parsed.scheme != "https" or parsed.hostname != "archive.ics.uci.edu" or parsed.username or parsed.port not in (None, 443):
                        raise ValueError("Dataset redirect leaves the verified source")
                    endpoint = next_url
                    continue
                response.raise_for_status()
                archive_bytes = bytearray()
                for chunk in response.iter_bytes():
                    archive_bytes.extend(chunk)
                    if len(archive_bytes) > 2097152:
                        raise ValueError("Dataset archive exceeds its size limit")
                break
        else:
            raise ValueError("Dataset redirect limit exceeded")
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        member = archive.getinfo("SMSSpamCollection")
        if member.file_size > 1048576 or member.file_size / max(member.compress_size, 1) > 50:
            raise ValueError("Dataset archive member exceeds its limits")
        source_bytes = archive.read(member)
    records = parse_sms_source(source_bytes.decode("utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    manifest = {
        "dataset_name": "UCI SMS Spam Collection (official ZIP acquisition)",
        "original_source": UCI_SMS_SOURCE, "original_download_url": UCI_SMS_DOWNLOAD,
        "source_doi": UCI_SMS_DOI, "acquired_at": datetime.now(timezone.utc).isoformat(),
        "version": "2011 collection; acquisition identified by source and prepared-file SHA-256",
        "license": "CC-BY-4.0", "license_source": UCI_SMS_SOURCE,
        "attribution": "Almeida, T. & Hidalgo, J. (2011). SMS Spam Collection. UCI Machine Learning Repository. DOI: 10.24432/C5CC84.",
        "acquisition_method": "Successful HTTPS download of the original UCI ZIP; read the named SMS member without extracting paths",
        "record_count": len(records), "class_distribution": dict(Counter(record["label"] for record in records)),
        "label_definitions": {"ham": "non-spam", "spam": "spam; not a verified fraud label"},
        "file": output.name, "file_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        "archive_sha256": hashlib.sha256(archive_bytes).hexdigest(),
        "original_sms_file_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "byte_identical_to_original": False,
        "acquisition_transformations": ["Parse real tab-labeled records", "Join source continuation lines", "Serialize prepared UTF-8 JSONL; original source checksum retained"],
        "limitations": ["Historical general SMS spam task, not Indian banking fraud", "Corpus URLs are not live threat intelligence", "Prepared JSONL is a transformed copy of the original corpus"],
    }
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(encoded)
    temporary.replace(output)
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    raw_path = PROJECT_ROOT / "data/raw/SMSSpamCollection.official"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(source_bytes)
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Acquire the original licensed UCI SMS corpus")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/datasets/uci_sms_official.jsonl")
    args = parser.parse_args()
    try:
        manifest = download(args.output)
    except (httpx.HTTPError, ValueError, OSError, zipfile.BadZipFile, KeyError, UnicodeDecodeError) as exc:
        raise SystemExit(f"Dataset acquisition failed ({type(exc).__name__}); no substitute corpus was created") from None
    print(json.dumps({"file": manifest["file"], "records": manifest["record_count"], "class_distribution": manifest["class_distribution"], "sha256": manifest["file_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
