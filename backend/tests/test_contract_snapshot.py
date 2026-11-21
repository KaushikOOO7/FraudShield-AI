import json
import re
from urllib.parse import urlsplit

from backend.app.core.config import PROJECT_ROOT, Settings
from backend.app.main import create_app


def test_documented_openapi_matches_executable_contract():
    stored = json.loads((PROJECT_ROOT / "docs/openapi.json").read_text())
    actual = create_app(Settings(app_env="test", _env_file=None)).openapi()
    assert stored == actual
    sms = actual["paths"]["/api/v1/analyze/sms"]["post"]
    assert "201" in sms["responses"]
    assert sms["security"] == [{"SupabaseAccessToken": []}]
    assert "security" not in actual["paths"]["/health"]["get"]


def test_postman_covers_current_contract_without_saved_fake_responses():
    collection = json.loads((PROJECT_ROOT / "docs/postman/FraudShield_AI.postman_collection.json").read_text())
    actual = create_app(Settings(app_env="test", _env_file=None)).openapi()
    expected = {(method.upper(), re.sub(r"\{[^}]+\}", "_", path)) for path, operations in actual["paths"].items() for method in operations if method in ("get", "post", "patch", "delete")}
    declared = set()
    for item in collection["item"]:
        request = item["request"]
        path = urlsplit(request["url"].replace("{{base_url}}", "https://example.com")).path
        declared.add((request["method"], re.sub(r"\{\{[^}]+\}\}", "_", path)))
        assert not item.get("response")
    assert expected <= declared
    assert next(value["value"] for value in collection["variable"] if value["key"] == "access_token") == ""
