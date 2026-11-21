"""Train only on acquired, provenance-validated PhiUSIIL data; no fallback corpus."""
import argparse
import hashlib
import json
import platform
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline

from backend.app.core.config import PROJECT_ROOT
from backend.app.ml.datasets import DatasetValidationError
from backend.app.ml.url.features import FEATURE_NAMES, FEATURE_VERSION, URLFeatures, domain_group
from backend.app.utils.urls import URLValidationError, parse_public_url

SOURCE = "https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset"


def metrics(y, prediction):
    matrix = confusion_matrix(y, prediction, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel().tolist()
    return {"accuracy": float(accuracy_score(y, prediction)), "precision": float(precision_score(y, prediction, zero_division=0)), "recall": float(recall_score(y, prediction, zero_division=0)), "f1": float(f1_score(y, prediction, zero_division=0)), "confusion_matrix": matrix.tolist(), "confusion_matrix_labels": ["legitimate", "phishing"], "false_positive_rate": fp / (tn + fp), "false_negative_rate": fn / (fn + tp), "dataset_size": len(y), "class_distribution": {"legitimate": int(sum(y == 0)), "phishing": int(sum(y == 1))}}


def load(path):
    manifest_path = path.with_suffix(".manifest.json")
    if not path.is_file() or not manifest_path.is_file():
        raise DatasetValidationError("Real URL dataset or provenance manifest is unavailable")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("original_source") != SOURCE or manifest.get("license") != "CC-BY-4.0" or manifest.get("label_definitions") != {"0": "phishing", "1": "legitimate"} or not manifest.get("acquired_at"):
        raise DatasetValidationError("URL source provenance is not approved")
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest.get("file_sha256"):
        raise DatasetValidationError("URL dataset checksum mismatch")
    frame = pd.read_csv(path, usecols=["URL", "label"])
    if len(frame) != manifest.get("record_count") or len(frame) != 235795 or frame.isna().any().any() or frame["label"].value_counts().to_dict() != {1: 134850, 0: 100945}:
        raise DatasetValidationError("URL source count/label distribution mismatch")
    return frame, manifest


def train(path: Path, output: Path):
    frame, provenance = load(path)
    try:
        from xgboost import XGBClassifier, __version__ as xgb_version
    except ImportError:
        raise DatasetValidationError("XGBoost comparator unavailable; install requirements-url-training.txt before training") from None
    def normalize(value):
        try:
            return parse_public_url(value).normalized
        except (URLValidationError, TypeError):
            return None
    frame["normalized"] = frame["URL"].map(normalize)
    invalid = int(frame["normalized"].isna().sum())
    frame = frame.dropna(subset=["normalized"])
    conflicts = frame.groupby("normalized")["label"].nunique()
    conflicting = set(conflicts[conflicts > 1].index)
    conflicting_count = int(frame["normalized"].isin(conflicting).sum())
    frame = frame[~frame["normalized"].isin(conflicting)]
    before = len(frame)
    frame = frame.drop_duplicates("normalized").reset_index(drop=True)
    duplicate_count = before - len(frame)
    values = frame["normalized"].to_numpy()
    # Source 0=phishing, 1=legitimate. Metrics use phishing as positive (1).
    labels = (1 - frame["label"]).to_numpy(dtype=int)
    groups = np.asarray([domain_group(value) for value in values])
    development, test = next(StratifiedGroupKFold(5, shuffle=True, random_state=42).split(values, labels, groups))
    inner_train, inner_validation = next(StratifiedGroupKFold(4, shuffle=True, random_state=43).split(values[development], labels[development], groups[development]))
    partitions = {"train": development[inner_train], "validation": development[inner_validation], "test": test}
    for first, second in (("train", "validation"), ("train", "test"), ("validation", "test")):
        if set(groups[partitions[first]]) & set(groups[partitions[second]]):
            raise DatasetValidationError("URL split group leakage")
    if any(set(labels[indices]) != {0, 1} for indices in partitions.values()):
        raise DatasetValidationError("Each URL partition must contain both classes")
    classifiers = {
        "random_forest": RandomForestClassifier(n_estimators=200, max_depth=20, min_samples_leaf=2, class_weight="balanced", random_state=42, n_jobs=2),
        "xgboost": XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1, subsample=0.8, colsample_bytree=0.8, objective="binary:logistic", eval_metric="logloss", tree_method="hist", random_state=42, n_jobs=2),
    }
    fitted, validation = {}, {}
    for name, classifier in classifiers.items():
        pipeline = Pipeline([("features", URLFeatures()), ("classifier", classifier)])
        pipeline.fit(values[partitions["train"]], labels[partitions["train"]])
        validation[name] = metrics(labels[partitions["validation"]], pipeline.predict(values[partitions["validation"]]))
        fitted[name] = pipeline
    # Fixed candidate comparison uses validation only. Test is evaluated once
    # for the chosen training-only fit, never for selection/refitting.
    chosen = max(classifiers, key=lambda name: validation[name]["f1"])
    test_result = metrics(labels[test], fitted[chosen].predict(values[test]))
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / "url_pipeline.joblib"
    joblib.dump(fitted[chosen], artifact)
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    version = "url-phiusiil-v1-" + digest[:12]
    records = [{"url_sha256": hashlib.sha256(values[index].encode()).hexdigest(), "group": groups[index], "partition": name} for name, indices in partitions.items() for index in indices]
    split_path = output / "url_splits.json"
    split_path.write_text(json.dumps(records) + "\n")
    manifest = {
        "schema_version": 1, "name": "url-classifier", "task": "phishing_url_detection", "version": version,
        "artifact_file": artifact.name, "artifact_sha256": digest, "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset": provenance, "feature_version": FEATURE_VERSION, "feature_names": FEATURE_NAMES,
        "dependencies": {"scikit-learn": sklearn.__version__, "numpy": np.__version__, "xgboost": xgb_version}, "python_version": platform.python_version(),
        "preprocessing": {"invalid_urls_removed": invalid, "conflicting_records_removed": conflicting_count, "duplicates_removed": duplicate_count, "usable_records": len(frame)},
        "split": {"method": "conservative hostname last-two-label grouping, 5-fold outer/4-fold inner; first folds predetermined, seeds 42/43", "counts": {name: len(indices) for name, indices in partitions.items()}, "splits_sha256": hashlib.sha256(split_path.read_bytes()).hexdigest()},
        "evaluation": {"validation_candidates": validation, "selected": chosen, "test": test_result},
        "limitations": ["Historical URL-text benchmark; not current Indian fraud performance", "No page/content or corpus-derived published features are reused", "Conservative suffix grouping can overgroup unrelated registrations on multi-label suffixes; it is not ownership evidence", "No chronological or independent external evaluation", "Classifier labels are predictions, not confirmed fraud; no calibrated probability/confidence is returned"],
    }
    (output / "url_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "data/datasets/phiusiil/PhiUSIIL_Phishing_URL_Dataset.csv")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "backend/app/ml/models")
    args = parser.parse_args()
    try:
        result = train(args.dataset, args.output)
        print("Actual trained URL model:", result["version"])
    except Exception as exc:
        raise SystemExit(f"URL training not completed ({type(exc).__name__}); no prediction or evaluation was substituted") from None
