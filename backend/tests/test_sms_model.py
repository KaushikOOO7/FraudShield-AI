"""All model text fixtures come from the registered real UCI corpus."""
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from backend.app.core.config import PROJECT_ROOT
from backend.app.ml.datasets import DatasetValidationError, load_sms_dataset
from backend.app.ml.inference.sms import SMSInference
from backend.app.ml.preprocessing.text import normalize_text, template_group
from backend.app.ml.sms.train import evaluation
from backend.tests.fixtures import registered_sms_path

MODEL_DIR = PROJECT_ROOT / "backend/app/ml/models"
DATASET_PATH = registered_sms_path()


@pytest.fixture(scope="module")
def genuine_corpus():
    assert DATASET_PATH.exists(), "Acquire the documented real UCI dataset before model tests"
    return load_sms_dataset(DATASET_PATH)


@pytest.fixture(scope="module")
def actual_model():
    model = SMSInference(MODEL_DIR)
    assert model.load_status == "available", "Train the genuine baseline before model tests"
    return model


@pytest.mark.model
def test_real_model_predicts_both_labels(actual_model, genuine_corpus):
    data, _ = genuine_corpus
    # Public UCI source rows 0 and 2. These are not invented scam incidents.
    outputs = [actual_model.predict(data[data["source_line"] == line].iloc[0]["content"]) for line in (0, 2)]
    assert [output.label for output in outputs] == ["ham", "spam"]
    assert all(output.status == "available" for output in outputs)
    assert all(output.confidence is None for output in outputs)
    assert all(output.score_type == "uncalibrated_decision_function" for output in outputs)


@pytest.mark.model
def test_saved_holdout_metrics_reproduce_and_no_split_leakage(actual_model, genuine_corpus):
    data, manifest = genuine_corpus
    splits = json.loads((MODEL_DIR / "sms_splits.json").read_text())
    assert splits["dataset_sha256"] == manifest["file_sha256"]
    lookup = data.set_index("source_line")
    groups = {partition: set() for partition in ("train", "validation", "test")}
    content_ids = {partition: set() for partition in groups}
    test_text, test_labels = [], []
    train_text = []
    for row in splits["rows"]:
        source = lookup.loc[row["source_line"]]
        normalized = normalize_text(source["content"])
        assert hashlib.sha256(normalized.encode()).hexdigest() == row["content_sha256"]
        group = template_group(source["content"])
        assert hashlib.sha256(group.encode()).hexdigest() == row["group_sha256"]
        groups[row["partition"]].add(group)
        content_ids[row["partition"]].add(normalized)
        if row["partition"] == "test":
            test_text.append(source["content"])
            test_labels.append(source["label"])
        if row["partition"] == "train":
            train_text.append(normalized)
    for first, second in (("train", "validation"), ("train", "test"), ("validation", "test")):
        assert not groups[first] & groups[second]
        assert not content_ids[first] & content_ids[second]
    observed = evaluation(test_labels, actual_model.pipeline.predict(test_text))
    assert observed == actual_model.manifest["evaluation"]["test"]
    analyzer = actual_model.pipeline.named_steps["tfidf"].build_analyzer()
    train_tokens = {token for content in train_text for token in analyzer(content)}
    assert set(actual_model.pipeline.named_steps["tfidf"].vocabulary_).issubset(train_tokens)


def test_unavailable_model_never_invents_a_prediction(tmp_path):
    output = SMSInference(tmp_path).predict("ISOLATED NON-PRODUCTION UNAVAILABLE-STATE FIXTURE")
    assert output.status == "model_not_trained"
    assert output.label is None
    assert output.decision_score is None
    assert output.version is None


def test_corrupt_model_is_rejected_before_deserialization(tmp_path):
    shutil.copyfile(MODEL_DIR / "sms_manifest.json", tmp_path / "sms_manifest.json")
    (tmp_path / "sms_pipeline.joblib").write_bytes(b"ISOLATED INVALID FILE; NOT A MODEL")
    model = SMSInference(tmp_path)
    assert model.load_status == "model_integrity_error"
    assert model.predict("isolated fixture").label is None


def test_incompatible_model_is_explicit(tmp_path):
    manifest = json.loads((MODEL_DIR / "sms_manifest.json").read_text())
    manifest["dependencies"]["scikit-learn"] = "incompatible-test-version"
    (tmp_path / "sms_manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "sms_pipeline.joblib").write_bytes(b"ISOLATED INVALID MODEL FILE")
    assert SMSInference(tmp_path).load_status == "model_incompatible"


def test_dataset_tampering_is_rejected(genuine_corpus, tmp_path):
    _, manifest = genuine_corpus
    destination = tmp_path / "corpus.jsonl"
    destination.write_text("ISOLATED INVALID DATA; NOT A DATASET\n")
    destination.with_suffix(".manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(DatasetValidationError, match="checksum"):
        load_sms_dataset(destination)


@pytest.mark.model
def test_out_of_vocabulary_content_has_no_intercept_only_prediction(actual_model):
    output = actual_model.predict("\U0001f6e1\U0001f680\U0001f9ec")
    assert output.status == "insufficient_features"
    assert output.label is None
    assert output.decision_score is None
