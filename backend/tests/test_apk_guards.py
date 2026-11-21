"""Clearly labelled ZIP security fixtures; these are NOT installable APK datasets."""
import io
import zipfile

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.errors import APIError
from backend.app.database.models import Investigation
from backend.app.services.apk_service import validate_apk_archive


def archive(entries):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as apk:
        for name, value in entries:
            apk.writestr(name, value)
    return output.getvalue()


@pytest.mark.parametrize("data", [b"not an apk", archive([("other.txt", b"ISOLATED")]), archive([("AndroidManifest.xml", b"ISOLATED"), ("../escape", b"ISOLATED")]), archive([("AndroidManifest.xml", b"ISOLATED"), ("bomb", b"0" * 100000)])])
def test_archive_structural_guards(data):
    with pytest.raises(APIError):
        validate_apk_archive(data)


def test_missing_parser_explicit_without_fake_apk_result(api_factory, token_factory, monkeypatch):
    import backend.app.services.apk_service as module
    monkeypatch.setattr(module, "parser_available", lambda: False)
    client, app, _ = api_factory()
    response = client.post("/api/v1/analyze/apk", headers={"Authorization": f"Bearer {token_factory()}"}, files={"file": ("../../guard-fixture.apk", archive([("AndroidManifest.xml", b"ISOLATED NON-INSTALLABLE GUARD FIXTURE")]), "application/vnd.android.package-archive")})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "apk_parser_unavailable"
    with Session(app.state.database.engine) as session:
        assert session.scalar(select(func.count()).select_from(Investigation)) == 0


def test_apk_upload_size_media_and_auth(api_factory, token_factory):
    client, _, _ = api_factory(apk_max_upload_bytes=1024)
    auth = {"Authorization": f"Bearer {token_factory()}"}
    assert client.post("/api/v1/analyze/apk", files={"file": ("test.apk", b"PK", "application/octet-stream")}).status_code == 401
    assert client.post("/api/v1/analyze/apk", headers=auth, files={"file": ("test.apk", b"x" * 1100, "application/octet-stream")}).status_code == 413
    assert client.post("/api/v1/analyze/apk", headers=auth, files={"file": ("test.exe", b"MZ", "application/x-msdownload")}).status_code == 415
