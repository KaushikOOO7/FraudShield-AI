import hashlib
import json
import platform
from datetime import datetime, timezone

import joblib
import numpy as np
import sklearn
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier

from backend.app.ml.url.features import FEATURE_NAMES, FEATURE_VERSION, URLFeatures
from backend.app.schemas.investigation import ModelResult


class URLInference:
    def __init__(self, directory):
        self.pipeline, self.manifest, self.status = None, None, "model_not_trained"
        artifact, manifest = directory / "url_pipeline.joblib", directory / "url_manifest.json"
        if not artifact.is_file() or not manifest.is_file():
            return
        try:
            record = json.loads(manifest.read_text())
            if record["name"] != "url-classifier" or record["task"] != "phishing_url_detection" or record["feature_version"] != FEATURE_VERSION or record["feature_names"] != FEATURE_NAMES or record["dataset"]["license"] != "CC-BY-4.0" or record["dataset"]["original_source"] != "https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset" or not record["dataset"]["file_sha256"] or not record["evaluation"]["test"] or not record["version"] or not isinstance(record["limitations"], list) or not record["trained_at"]:
                self.status = "invalid_manifest"
                return
            if record["dependencies"]["scikit-learn"] != sklearn.__version__ or record["dependencies"]["numpy"] != np.__version__ or record["python_version"].split(".")[:2] != platform.python_version().split(".")[:2]:
                self.status = "model_incompatible"
                return
            if hashlib.sha256(artifact.read_bytes()).hexdigest() != record["artifact_sha256"]:
                self.status = "model_integrity_error"
                return
            # Only deployment-owned trusted artifacts are accepted. Checksums
            # detect corruption; they are not authenticity/signature proofs.
            pipeline = joblib.load(artifact)
            if not isinstance(pipeline, Pipeline) or list(pipeline.named_steps) != ["features", "classifier"] or type(pipeline.named_steps.get("features")) is not URLFeatures or list(pipeline.named_steps["classifier"].classes_) != [0, 1]:
                self.status = "model_incompatible"
                return
            classifier = pipeline.named_steps["classifier"]
            if type(classifier) is not RandomForestClassifier:
                from xgboost import XGBClassifier, __version__ as xgb_version
                if type(classifier) is not XGBClassifier or record["dependencies"]["xgboost"] != xgb_version:
                    self.status = "model_incompatible"
                    return
            self.pipeline, self.manifest, self.status = pipeline, record, "available"
        except (ValueError, KeyError, TypeError, OSError):
            self.status = "invalid_manifest"
        except Exception:
            self.status = "model_incompatible"

    def predict(self, value):
        status, label = self.status, None
        if status == "available":
            try:
                predicted = int(self.pipeline.predict([value])[0])
                if predicted not in (0, 1):
                    raise ValueError
                label = "phishing" if predicted == 1 else "legitimate"
            except Exception:
                status = "inference_error"
        return ModelResult(name="url-classifier", task="phishing_url_detection", status=status, version=self.manifest["version"] if self.manifest else None, label=label, observed_at=datetime.now(timezone.utc), limitations=self.manifest["limitations"] if self.manifest else ["No trained raw-URL classifier is available; no prediction was substituted."])

    def system_status(self):
        return {"status": self.status, "version": self.manifest["version"] if self.manifest else None}
