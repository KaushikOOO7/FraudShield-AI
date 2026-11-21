import hashlib
import json
from collections import Counter
from pathlib import Path

import pandas as pd

UCI_SMS_SOURCE = "https://archive.ics.uci.edu/dataset/228/sms+spam+collection"
UCI_SMS_DOWNLOAD = "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip"
UCI_SMS_DOI = "10.24432/C5CC84"


class DatasetValidationError(ValueError):
    pass


def load_sms_dataset(path: Path, manifest_path: Path | None = None) -> tuple[pd.DataFrame, dict]:
    manifest_path = manifest_path or path.with_suffix(".manifest.json")
    if not path.is_file() or not manifest_path.is_file():
        raise DatasetValidationError("Dataset or provenance manifest is unavailable")
    manifest = json.loads(manifest_path.read_text())
    if (
        manifest.get("original_source") != UCI_SMS_SOURCE
        or manifest.get("source_doi") != UCI_SMS_DOI
        or manifest.get("license") != "CC-BY-4.0"
        or not manifest.get("acquired_at")
        or not manifest.get("label_definitions")
        or not manifest.get("acquisition_method")
    ):
        raise DatasetValidationError("Dataset provenance or supported license is incomplete")
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest.get("file_sha256"):
        raise DatasetValidationError("Dataset checksum does not match its provenance manifest")
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    for record in records:
        if (
            record.get("label") not in ("ham", "spam")
            or not isinstance(record.get("content"), str)
            or not record["content"].strip()
            or not isinstance(record.get("source_line"), int)
        ):
            raise DatasetValidationError("Dataset contains invalid labeled records")
    if len(records) != manifest.get("record_count"):
        raise DatasetValidationError("Dataset record count differs from its manifest")
    counts = dict(Counter(record["label"] for record in records))
    if counts != manifest.get("class_distribution") or set(counts) != {"ham", "spam"}:
        raise DatasetValidationError("Dataset class distribution differs from its manifest")
    if len(records) < 500:
        raise DatasetValidationError("A demonstration-sized corpus is not an approved production baseline")
    return pd.DataFrame.from_records(records), manifest
