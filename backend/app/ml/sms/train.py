import argparse
import hashlib
import json
import os
import platform
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

from backend.app.core.config import PROJECT_ROOT
from backend.app.ml.datasets import load_sms_dataset
from backend.app.ml.preprocessing.text import (
    PREPROCESSING_VERSION, normalize_messages, normalize_text, template_group,
)

MODEL_NAME = "sms-spam-tfidf-logistic-regression"
RANDOM_STATE = 42
LIMITATIONS = [
    "Historical general SMS spam/ham classification; spam is not equivalent to fraud.",
    "Not evaluated on Indian banking fraud, current scams, Hindi or other Indian languages.",
    "Group-separated random holdout is not a chronological or independent external test set.",
    "Exact URL/number template grouping mitigates, but does not eliminate, near-duplicate campaign leakage.",
    "Decision-function values are uncalibrated margins, not fraud probabilities or confidence.",
]
PARAMETERS = {
    "tfidf": {"ngram_range": [1, 2], "min_df": 2, "sublinear_tf": True, "lowercase": False},
    "logistic_regression": {"C": 1.0, "class_weight": "balanced", "solver": "liblinear", "max_iter": 1000, "random_state": RANDOM_STATE},
}


def evaluation(y_true, y_pred) -> dict:
    matrix = confusion_matrix(y_true, y_pred, labels=["ham", "spam"])
    tn, fp, fn, tp = matrix.ravel().tolist()
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, pos_label="spam", zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, pos_label="spam", zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, pos_label="spam", zero_division=0)),
        "confusion_matrix": matrix.tolist(), "confusion_matrix_labels": ["ham", "spam"],
        "false_positive_rate": fp / (tn + fp) if tn + fp else None,
        "false_negative_rate": fn / (fn + tp) if fn + tp else None,
        "dataset_size": len(y_true), "class_distribution": dict(Counter(y_true)),
    }


def atomic_json(path: Path, payload: dict):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    os.replace(temporary, path)


def train(dataset_path: Path, output_dir: Path) -> dict:
    started = time.monotonic()
    data, dataset_manifest = load_sms_dataset(dataset_path)
    data["normalized"] = data["content"].map(normalize_text)
    conflicting = data.groupby("normalized")["label"].nunique()
    conflicting_texts = set(conflicting[conflicting > 1].index)
    conflicts_removed = int(data["normalized"].isin(conflicting_texts).sum())
    data = data[~data["normalized"].isin(conflicting_texts)].copy()
    before_dedup = len(data)
    data = data.drop_duplicates(subset="normalized", keep="first").reset_index(drop=True)
    duplicates_removed = before_dedup - len(data)
    data["group"] = data["normalized"].map(template_group)
    data["content_sha256"] = data["normalized"].map(lambda x: hashlib.sha256(x.encode()).hexdigest())
    groups = data["group"].to_numpy()
    labels = data["label"].to_numpy()
    development, test_indices = next(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE).split(data["content"], labels, groups))
    inner_train, inner_validation = next(StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE + 1).split(data.iloc[development]["content"], labels[development], groups[development]))
    train_indices, validation_indices = development[inner_train], development[inner_validation]
    partitions = {"train": train_indices, "validation": validation_indices, "test": test_indices}
    group_sets = {key: set(groups[indices]) for key, indices in partitions.items()}
    for first, second in (("train", "validation"), ("train", "test"), ("validation", "test")):
        if group_sets[first] & group_sets[second]:
            raise ValueError("Leakage: split groups overlap")
    if any(set(labels[indices]) != {"ham", "spam"} for indices in partitions.values()):
        raise ValueError("Every evaluation partition must contain both labels")
    pipeline = Pipeline([
        ("normalize", FunctionTransformer(normalize_messages, validate=False)),
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, lowercase=False)),
        ("classifier", LogisticRegression(**PARAMETERS["logistic_regression"])),
    ])
    # Vectorizer and classifier see TRAIN only. No holdout-based tuning or refit.
    pipeline.fit(data.iloc[train_indices]["content"].tolist(), labels[train_indices])
    metrics = {
        partition: evaluation(labels[indices], pipeline.predict(data.iloc[indices]["content"].tolist()))
        for partition, indices in (("validation", validation_indices), ("test", test_indices))
    }
    dependencies = {name: version(name) for name in ("scikit-learn", "numpy", "pandas", "scipy", "joblib")}
    identity = json.dumps({"dataset": dataset_manifest["file_sha256"], "parameters": PARAMETERS, "preprocessing": PREPROCESSING_VERSION, "sklearn": dependencies["scikit-learn"]}, sort_keys=True)
    model_version = "sms-uci-tfidf-lr-v1-" + hashlib.sha256(identity.encode()).hexdigest()[:12]
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / "sms_pipeline.joblib"
    with tempfile.NamedTemporaryFile(dir=output_dir, suffix=".joblib", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        joblib.dump(pipeline, temporary_path, compress=3)
        os.replace(temporary_path, artifact_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    artifact_sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    split_rows = []
    for partition, indices in partitions.items():
        for index in indices:
            row = data.iloc[index]
            split_rows.append({"partition": partition, "source_line": int(row["source_line"]), "content_sha256": row["content_sha256"], "group_sha256": hashlib.sha256(row["group"].encode()).hexdigest(), "label": row["label"]})
    splits = {"dataset_sha256": dataset_manifest["file_sha256"], "rows": split_rows}
    atomic_json(output_dir / "sms_splits.json", splits)
    manifest = {
        "schema_version": 1, "name": MODEL_NAME, "version": model_version, "task": "sms_spam_detection",
        "artifact_file": artifact_path.name, "artifact_sha256": artifact_sha256,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_duration_seconds": round(time.monotonic() - started, 3),
        "python_version": platform.python_version(), "dependencies": dependencies,
        "dataset": dataset_manifest, "preprocessing_version": PREPROCESSING_VERSION,
        "parameters": PARAMETERS,
        "preprocessing": {
            "raw_records": dataset_manifest["record_count"], "conflicting_label_records_removed": conflicts_removed,
            "normalized_duplicates_removed": duplicates_removed, "usable_records": len(data),
            "usable_class_distribution": dict(Counter(data["label"])),
            "operations": ["NFKC Unicode normalization", "casefold", "collapse whitespace", "remove conflicting normalized labels", "deduplicate normalized content before splitting"],
        },
        "split": {
            "method": "StratifiedGroupKFold 5-way outer test fold and 4-way inner validation fold; first folds fixed in advance",
            "random_state": RANDOM_STATE, "inner_random_state": RANDOM_STATE + 1,
            "grouping": "exact normalized text template after replacing URLs and digit sequences",
            "training_records": len(train_indices), "validation_records": len(validation_indices), "test_records": len(test_indices),
            "training_class_distribution": dict(Counter(labels[train_indices])),
            "disjoint_groups": True, "disjoint_normalized_content": True,
            "test_usage": "Untouched holdout; evaluated once after a fixed baseline fit; no tuning or final refit",
            "splits_file": "sms_splits.json", "splits_sha256": hashlib.sha256((output_dir / "sms_splits.json").read_bytes()).hexdigest(),
        },
        "evaluation": metrics, "limitations": LIMITATIONS + dataset_manifest.get("limitations", []),
    }
    atomic_json(output_dir / "sms_manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Train the genuine UCI SMS spam baseline")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "data/datasets/uci_sms_web_export.jsonl")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "backend/app/ml/models")
    args = parser.parse_args()
    manifest = train(args.dataset, args.output)
    print(json.dumps({"name": manifest["name"], "version": manifest["version"], "preprocessing": manifest["preprocessing"], "split": manifest["split"], "test_evaluation": manifest["evaluation"]["test"]}, indent=2))


if __name__ == "__main__":
    main()
