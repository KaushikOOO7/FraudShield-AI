"""Real decoder exercised with generated, explicitly non-production QR images.

These fixtures encode reserved example URLs/UPI test identifiers; they are not
datasets, real payments or threat incidents. No reputation verdict is simulated.
"""
import hashlib
import io
from uuid import UUID, uuid4

import cv2
import numpy as np
import pytest
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database.models import Investigation, QRAnalysis
from backend.app.services.qr_decoder import decode_image
from backend.app.utils.upi import parse_upi_uri


def qr_image(content):
    encoded = cv2.QRCodeEncoder_create().encode(content)
    encoded = cv2.copyMakeBorder(encoded, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255)
    encoded = cv2.resize(encoded, None, fx=10, fy=10, interpolation=cv2.INTER_NEAREST)
    valid, png = cv2.imencode(".png", encoded)
    assert valid
    return png.tobytes()


def headers(token_factory, **claims):
    return {"Authorization": f"Bearer {token_factory(**claims)}"}


def upload(client, token_factory, data, **kwargs):
    return client.post("/api/v1/analyze/qr", headers=headers(token_factory), files={"file": ("../../isolated-test.png", data, "image/png")}, data={"source": "android_share", "use_threat_intelligence": "false"}, **kwargs)


def test_actual_decoder_reads_generated_reserved_url():
    result = decode_image(qr_image("https://example.com/"))
    assert result.status == "decoded"
    assert result.content == "https://example.com/"
    assert result.image_format == "PNG"


def test_qr_url_android_api_persists_and_routes_url_analysis(api_factory, token_factory):
    client, app, calls = api_factory()
    data = qr_image("https://example.com/?reference=isolated-private-value")
    response = upload(client, token_factory, data)
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["subject"]["type"] == "qr"
    assert result["subject"]["attributes"]["content_type"] == "url"
    assert result["subject"]["attributes"]["image_sha256"] == hashlib.sha256(data).hexdigest()
    assert result["models"][0]["status"] == "model_not_trained"
    assert result["assessment"]["risk_score"] is None
    assert "isolated-private-value" not in response.text
    assert all(call.url.path.endswith("jwks.json") for call in calls)
    owner = headers(token_factory)
    assert client.get(response.headers["Location"], headers=owner).json() == result
    assert client.get(response.headers["Location"], headers=headers(token_factory, sub=str(uuid4()))).status_code == 404
    with Session(app.state.database.engine) as session:
        row = session.scalar(select(QRAnalysis))
        assert row.investigation_id == UUID(result["investigation_id"])
        assert row.decoded_attributes["image_sha256"] == hashlib.sha256(data).hexdigest()
    assert client.delete(response.headers["Location"], headers=owner).status_code == 204
    with Session(app.state.database.engine) as session:
        assert session.scalar(select(func.count()).select_from(QRAnalysis)) == 0


def test_upi_qr_is_syntax_only_not_automatically_high_risk(api_factory, token_factory):
    client, _, calls = api_factory()
    response = upload(client, token_factory, qr_image("upi://pay?pa=isolatedfixture@upi&pn=Isolated%20Fixture&am=10.25&cu=INR"))
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["subject"]["attributes"]["content_type"] == "upi_payment"
    assert result["subject"]["attributes"]["recipient_verified"] is False
    assert result["subject"]["attributes"]["amount"] == "10.25"
    assert result["assessment"]["classification"] == "EXERCISE_CAUTION"
    assert result["models"] == []
    assert "isolatedfixture@upi" not in response.text
    assert len(calls) == 1


def test_no_qr_returns_explicit_no_payload_not_a_clean_verdict(api_factory, token_factory):
    client, _, _ = api_factory()
    output = io.BytesIO()
    Image.new("RGB", (200, 200), "white").save(output, format="PNG")
    response = upload(client, token_factory, output.getvalue())
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["subject"]["attributes"]["decode_status"] == "no_qr_found"
    assert result["subject"]["value"] is None
    assert result["findings"] == []
    assert result["models"] == []
    assert result["status"] == "partial"


@pytest.mark.parametrize("content", ["upi://pay?pa=invalid", "upi://pay?pa=fixture@upi&am=-1", "upi://pay?pa=fixture@upi&am=NaN", "upi://pay?pa=fixture@upi&pa=other@upi", "upi://pay?pa=fixture@upi&cu=USD"])
def test_invalid_upi_syntax(content):
    with pytest.raises(ValueError):
        parse_upi_uri(content)


def test_sensitive_qr_is_rejected_without_storage_or_reflection(api_factory, token_factory):
    client, app, _ = api_factory()
    response = upload(client, token_factory, qr_image("ISOLATED TEST OTP is 123456"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "sensitive_input"
    assert "123456" not in response.text
    with Session(app.state.database.engine) as session:
        assert session.scalar(select(func.count()).select_from(Investigation)) == 0


def test_file_type_size_and_corruption_validation(api_factory, token_factory):
    client, _, _ = api_factory(qr_max_upload_bytes=1024)
    assert upload(client, token_factory, b"not an image").status_code == 422
    assert upload(client, token_factory, b"\x89PNG\r\n\x1a\n" + b"x" * 1100).status_code == 413
    response = client.post("/api/v1/analyze/qr", headers=headers(token_factory), files={"file": ("test.svg", b"<svg/>", "image/svg+xml")})
    assert response.status_code == 415
    assert upload(client, token_factory, b"\x89PNG\r\n\x1a\ninvalid").status_code == 422


def test_upload_auth_and_form_validation(api_factory, token_factory):
    client, _, _ = api_factory()
    image = qr_image("https://example.com/")
    assert client.post("/api/v1/analyze/qr", files={"file": ("qr.png", image, "image/png")}).status_code == 401
    assert client.post("/api/v1/analyze/qr", headers=headers(token_factory), files={"file": ("qr.png", image, "image/png")}, data={"source": "invalid"}).status_code == 422


def test_private_decoded_url_is_not_forwarded(api_factory, token_factory):
    client, _, calls = api_factory()
    response = upload(client, token_factory, qr_image("http://127.0.0.1/"))
    assert response.status_code == 201
    assert response.json()["models"] == []
    assert any("failed validation" in text for text in response.json()["limitations"])
    assert len(calls) == 1


def test_real_decoded_qr_and_url_share_evidence_backed_graph(api_factory, token_factory):
    client, _, _ = api_factory()
    qr = upload(client, token_factory, qr_image("https://example.com/"))
    assert qr.status_code == 201
    owner = headers(token_factory)
    url = client.post("/api/v1/analyze/url", headers=owner, json={"url": "https://example.com/", "source": "web_share"})
    assert url.status_code == 201
    linked = client.post(url.headers["Location"] + "/correlate", headers=owner)
    assert linked.status_code == 200, linked.text
    result = linked.json()
    assert result["methodology_version"] == "observed-identifiers-v2"
    assert result["related_investigations"][0]["subject_type"] == "qr"
    assert result["related_investigations"][0]["investigation_id"] == qr.json()["investigation_id"]
    assert len(result["observations"]) == 2
    assert all(edge["evidence_id"] in {item["evidence_id"] for item in result["observations"]} for edge in result["edges"])
