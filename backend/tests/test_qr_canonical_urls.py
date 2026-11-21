"""Generated non-production QR fixture; no real payment or threat claim."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database.models import URLIndicator
from backend.tests.test_qr import qr_image, upload


def test_equivalent_urls_in_one_qr_do_not_duplicate_storage(api_factory, token_factory):
    client, app, _ = api_factory()
    payload = "ISOLATED URL NORMALIZATION TEST: https://EXAMPLE.com https://example.com/"
    response = upload(client, token_factory, qr_image(payload))
    assert response.status_code == 201, response.text
    with Session(app.state.database.engine) as session:
        assert session.scalar(select(func.count()).select_from(URLIndicator)) == 1
