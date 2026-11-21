"""Structure/unavailable-state tests only; no fabricated URL model/dataset."""
import json

import numpy as np
import pytest

from backend.app.ml.datasets import DatasetValidationError
from backend.app.ml.inference.urls import URLInference
from backend.app.ml.url.features import FEATURE_NAMES, URLFeatures, domain_group
from backend.app.ml.url.train import train
from backend.app.utils.urls import URLValidationError


def test_reproducible_url_features_without_page_or_provider_access():
    values = ["https://example.com/path?reference=example", "http://8.8.8.8/"]
    matrix = URLFeatures().fit_transform(values)
    assert matrix.shape == (2, len(FEATURE_NAMES))
    assert np.isfinite(matrix).all()
    assert matrix[0, FEATURE_NAMES.index("url_length")] == len(values[0])
    assert matrix[0, FEATURE_NAMES.index("https_scheme")] == 1
    assert matrix[1, FEATURE_NAMES.index("is_ip")] == 1


def test_private_urls_rejected_by_training_inference_feature_parser():
    with pytest.raises(URLValidationError):
        URLFeatures().transform(["http://127.0.0.1/"])


def test_conservative_domain_grouping_prevents_subdomain_split_overlap():
    assert domain_group("https://a.example.com/") == domain_group("https://b.example.com/")
    assert domain_group("https://a.example.co.in/") == domain_group("https://b.other.co.in/")
    assert domain_group("https://example.com/") != domain_group("https://example.org/")


def test_missing_url_model_returns_no_substitute(tmp_path):
    model = URLInference(tmp_path)
    prediction = model.predict("https://example.com/")
    assert prediction.status == "model_not_trained"
    assert prediction.label is prediction.decision_score is prediction.confidence is None


def test_invalid_url_manifest_never_loads_a_fake_model(tmp_path):
    (tmp_path / "url_pipeline.joblib").write_bytes(b"ISOLATED NEGATIVE NON-MODEL FIXTURE")
    (tmp_path / "url_manifest.json").write_text(json.dumps({"invalid": "not training metadata"}))
    prediction = URLInference(tmp_path).predict("https://example.com/")
    assert prediction.status == "invalid_manifest"
    assert prediction.label is None


def test_training_missing_real_source_creates_no_artifacts(tmp_path):
    output = tmp_path / "no-model"
    with pytest.raises(DatasetValidationError, match="unavailable"):
        train(tmp_path / "no-real-dataset.csv", output)
    assert not output.exists()
