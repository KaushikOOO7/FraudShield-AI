import hashlib
import json
import math
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted

from backend.app.ml.preprocessing.text import PREPROCESSING_VERSION
from backend.app.ml.sms.train import LIMITATIONS, MODEL_NAME
from backend.app.schemas.investigation import ModelResult


class SMSInference:
    def __init__(self, model_dir: Path):
        self.model_dir = model_dir
        self.pipeline: Pipeline | None = None
        self.manifest: dict | None = None
        self.load_status = "model_not_trained"
        self._load()

    def _load(self):
        artifact = self.model_dir / "sms_pipeline.joblib"
        manifest_path = self.model_dir / "sms_manifest.json"
        if not artifact.is_file() or not manifest_path.is_file():
            return
        try:
            if manifest_path.stat().st_size > 1048576 or artifact.stat().st_size > 67108864:
                self.load_status = "invalid_manifest"
                return
            manifest = json.loads(manifest_path.read_text())
            if (
                manifest.get("schema_version") != 1 or manifest.get("name") != MODEL_NAME
                or manifest.get("artifact_file") != "sms_pipeline.joblib"
                or manifest.get("preprocessing_version") != PREPROCESSING_VERSION
                or not manifest.get("version") or not manifest.get("dataset", {}).get("file_sha256")
                or not manifest.get("evaluation", {}).get("test")
            ):
                self.load_status = "invalid_manifest"
                return
            expected_dependencies = manifest.get("dependencies", {})
            if any(expected_dependencies.get(name) != version(name) for name in ("scikit-learn", "numpy", "pandas", "scipy", "joblib")):
                self.load_status = "model_incompatible"
                return
            if hashlib.sha256(artifact.read_bytes()).hexdigest() != manifest.get("artifact_sha256"):
                self.load_status = "model_integrity_error"
                return
            # Only trusted, locally trained artifacts may reside in this directory.
            # Hash verification detects corruption, not a malicious file+manifest replacement.
            pipeline = joblib.load(artifact)
            if not isinstance(pipeline, Pipeline) or not isinstance(pipeline.named_steps.get("classifier"), LogisticRegression):
                self.load_status = "invalid_manifest"
                return
            classifier = pipeline.named_steps["classifier"]
            check_is_fitted(classifier)
            if set(classifier.classes_) != {"ham", "spam"}:
                self.load_status = "invalid_manifest"
                return
            self.pipeline = pipeline
            self.manifest = manifest
            self.load_status = "available"
        except Exception:
            self.load_status = "invalid_manifest"
            self.pipeline = None
            self.manifest = None

    def predict(self, content: str) -> ModelResult:
        fields = {
            "name": MODEL_NAME, "version": self.manifest["version"] if self.manifest else None,
            "task": "sms_spam_detection", "status": self.load_status,
            "observed_at": datetime.now(timezone.utc), "limitations": self.manifest["limitations"] if self.manifest else LIMITATIONS,
        }
        if self.pipeline is None:
            return ModelResult(**fields)
        try:
            features = self.pipeline[:-1].transform([content])
            if features.nnz == 0:
                fields["status"] = "insufficient_features"
                return ModelResult(**fields)
            classifier = self.pipeline.named_steps["classifier"]
            label = str(classifier.predict(features)[0])
            margin = float(classifier.decision_function(features)[0])
            if not math.isfinite(margin):
                raise ValueError("Invalid model margin")
            return ModelResult(**fields, label=label, decision_score=margin, score_type="uncalibrated_decision_function")
        except Exception:
            fields["status"] = "inference_error"
            return ModelResult(**fields)

    def system_status(self) -> dict:
        return {
            "name": MODEL_NAME, "status": self.load_status,
            "version": self.manifest["version"] if self.manifest else None,
            "task": "sms_spam_detection",
            "evaluation": self.manifest["evaluation"]["test"] if self.manifest else None,
            "limitations": self.manifest["limitations"] if self.manifest else LIMITATIONS,
        }
