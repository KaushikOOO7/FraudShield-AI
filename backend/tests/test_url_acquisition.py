"""Failure tests only; no fabricated URL training corpus is created."""
import httpx
import pytest

from scripts.download_url_dataset import acquire


def test_url_source_download_failure_creates_no_fake_dataset(tmp_path):
    destination = tmp_path / "not-acquired"
    with pytest.raises(ValueError, match="did not succeed"):
        acquire(destination, httpx.MockTransport(lambda request: httpx.Response(503)))
    assert not destination.exists()


def test_invalid_url_archive_is_not_substituted(tmp_path):
    destination = tmp_path / "not-acquired"
    with pytest.raises(Exception):
        acquire(destination, httpx.MockTransport(lambda request: httpx.Response(200, content=b"ISOLATED NON-ARCHIVE SECURITY FIXTURE")))
    assert not destination.exists()
