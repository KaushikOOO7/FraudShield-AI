"""Acquire the original CC BY 4.0 UCI PhiUSIIL archive; never substitute data."""
import hashlib
import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset"
DOWNLOAD = "https://archive.ics.uci.edu/static/public/967/phiusiil%2Bphishing%2Burl%2Bdataset.zip"
FILENAME = "PhiUSIIL_Phishing_URL_Dataset.csv"


def acquire(destination: Path, transport=None):
    content = bytearray()
    with httpx.Client(timeout=20, follow_redirects=False, trust_env=False, transport=transport) as client:
        with client.stream("GET", DOWNLOAD, headers={"Accept-Encoding": "identity"}) as response:
            if response.status_code != 200 or response.headers.get("content-encoding", "identity") != "identity":
                raise ValueError("Original dataset download did not succeed")
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > 20 * 1024 * 1024:
                    raise ValueError("Original dataset archive exceeds the supported size")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        matches = [item for item in archive.infolist() if Path(item.filename).name == FILENAME]
        if len(matches) != 1 or matches[0].file_size > 100 * 1024 * 1024:
            raise ValueError("Original archive member is missing or exceeds the size limit")
        data = archive.read(matches[0])
    frame = pd.read_csv(io.BytesIO(data), usecols=["URL", "label"])
    if len(frame) != 235795 or frame.isna().any().any() or set(frame["label"].unique()) != {0, 1}:
        raise ValueError("Downloaded source does not match documented release structure")
    actual = frame["label"].value_counts().to_dict()
    if actual != {1: 134850, 0: 100945}:
        raise ValueError("Downloaded release class distribution differs from original documentation")
    manifest = {
        "dataset_name": "UCI PhiUSIIL Phishing URL (Website)", "original_source": SOURCE,
        "original_download_url": DOWNLOAD, "version": "2024 UCI release, byte version identified by SHA-256",
        "source_doi": "10.1016/j.cose.2023.103545", "license": "CC-BY-4.0", "license_source": SOURCE,
        "attribution": "Prasad, A. and Chandra, S. (2024). PhiUSIIL Phishing URL (Website). UCI Machine Learning Repository.",
        "acquired_at": datetime.now(timezone.utc).isoformat(), "file": FILENAME,
        "archive_sha256": hashlib.sha256(content).hexdigest(), "file_sha256": hashlib.sha256(data).hexdigest(),
        "record_count": len(frame), "class_distribution": {"legitimate": int(actual[1]), "phishing": int(actual[0])},
        "label_definitions": {"0": "phishing", "1": "legitimate"},
        "acquisition_method": "Original UCI ZIP download, selected CSV retained byte-identically",
        "limitations": ["Historical benchmark, not a live malicious URL feed", "Only URL-text features can be reproduced without fetching pages", "Published page/content-derived and corpus-wide features must not be reused as reproducible online features", "No current Indian fraud, chronological or external performance is established"],
    }
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / FILENAME
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != manifest["file_sha256"]:
        raise ValueError("A different local dataset exists; preserve it and choose a new destination")
    target.write_bytes(data)
    target.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    try:
        result = acquire(PROJECT_ROOT / "data/datasets/phiusiil")
        print("Acquired actual source records:", result["record_count"])
        print("CSV SHA-256:", result["file_sha256"])
    except Exception as exc:
        # No raw provider/connection strings or substituted source.
        print(f"Dataset acquisition failed ({type(exc).__name__}); no replacement dataset was generated.", file=sys.stderr)
        raise SystemExit(1) from None
