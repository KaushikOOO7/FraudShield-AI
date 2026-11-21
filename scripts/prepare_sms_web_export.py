"""Reproduce the registered browser-export corpus without inventing any rows."""
import argparse
import hashlib
import html
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.core.config import PROJECT_ROOT
from backend.app.ml.datasets import UCI_SMS_DOI, UCI_SMS_DOWNLOAD, UCI_SMS_SOURCE


def prepare(source: Path, output: Path) -> dict:
    acquisition = json.loads(source.with_name("uci_sms_acquisition.json").read_text())
    if acquisition.get("official_source") != UCI_SMS_SOURCE or not acquisition.get("retrieved_at"):
        raise ValueError("The original export acquisition record is required")
    lines = json.loads(source.read_text())["lines"]
    if [item["index"] for item in lines] != list(range(5579)):
        raise ValueError("The registered web export requires all 5579 displayed source lines in order")
    records = []
    for item in lines:
        line = html.unescape(item["text"])
        if line.startswith(("ham\t", "spam\t")):
            label, content = line.split("\t", 1)
            records.append({"label": label, "content": content, "source_line": item["index"]})
        elif records:
            records[-1]["content"] += "\n" + line
        elif line.strip():
            raise ValueError("Orphan source continuation")
    counts = dict(Counter(record["label"] for record in records))
    if len(records) != 5574 or counts != {"ham": 4827, "spam": 747}:
        raise ValueError("The export does not match the registered corpus counts")
    encoded = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded)
    manifest = {
        "dataset_name": "UCI SMS Spam Collection (web-exported mirror copy)",
        "original_source": UCI_SMS_SOURCE, "original_download_url": UCI_SMS_DOWNLOAD, "source_doi": UCI_SMS_DOI,
        "mirror_url": "https://raw.githubusercontent.com/veermshah/cs6350-sms-spam-dataset/main/SMSSpamCollection",
        "acquired_at": acquisition["retrieved_at"], "prepared_at": datetime.now(timezone.utc).isoformat(),
        "version": "2011 collection; web-export copy identified by SHA-256", "license": "CC-BY-4.0", "license_source": UCI_SMS_SOURCE,
        "attribution": "Almeida, T. & Hidalgo, J. (2011). SMS Spam Collection. UCI Machine Learning Repository. DOI: 10.24432/C5CC84.",
        "acquisition_method": "Connected web tool text export, not an original ZIP download",
        "record_count": len(records), "class_distribution": counts,
        "label_definitions": {"ham": "non-spam", "spam": "spam; not a verified fraud label"},
        "file": output.name, "file_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        "source_export_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "mirror_original_sha256": "7d039a24a6083ed9ef0f806ebad56bbb976e3aeb8de05669173bfdc4996c239d",
        "byte_identical_to_original": False,
        "acquisition_transformations": ["Decode web HTML entities once", "Rejoin five source continuation lines", "Preserve source-line identifiers", "Serialize real labeled records as UTF-8 JSONL"],
        "limitations": ["Historical general SMS spam/ham, not Indian banking fraud", "Mirror main URL is mutable; this export is frozen by checksum", "Web export may normalize source whitespace and controls; not byte-identical to original", "Corpus URLs are not live threat intelligence"],
    }
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Prepare a complete, provenance-tracked SMS web export")
    parser.add_argument("--source", type=Path, default=PROJECT_ROOT / "data/raw/uci_sms_web_export.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/datasets/uci_sms_web_export.jsonl")
    args = parser.parse_args()
    result = prepare(args.source, args.output)
    print(json.dumps({"records": result["record_count"], "sha256": result["file_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
