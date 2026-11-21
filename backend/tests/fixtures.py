import json

from backend.app.core.config import PROJECT_ROOT


def registered_sms_path():
    manifest = json.loads((PROJECT_ROOT / "backend/app/ml/models/sms_manifest.json").read_text())
    filename = manifest["dataset"]["file"]
    if "/" in filename or "\\" in filename:
        raise ValueError("Fixture dataset filename must be a basename")
    return PROJECT_ROOT / "data/datasets" / filename
