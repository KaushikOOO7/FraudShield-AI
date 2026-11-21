"""Genuine UCI SMS + reserved example domains in disposable API databases.

Example URLs are explicitly non-production validation fixtures, never real
threat reports. Tests use actual inference and signed isolated JWTs. No URL
is fetched or passed to reputation services.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from backend.app.core.errors import APIError
from backend.app.database.correlation import CorrelationRepository
from backend.app.database.migrate import MIGRATIONS_ROOT, apply_migrations
from backend.app.database.models import (
    AuditLog, Evidence, EvidenceSource, GraphEdge, GraphNode, Investigation, URLIndicator,
)
from backend.app.database.retention import purge_expired
from backend.app.schemas.correlation import CorrelationResponse
from backend.app.utils.urls import extract_urls, parse_public_url


def auth_headers(token_factory, **claims):
    return {"Authorization": f"Bearer {token_factory(**claims)}"}


def submit_url(client, headers, url="https://example.com/", source="web_share"):
    response = client.post("/api/v1/analyze/url", headers=headers, json={"url": url, "source": source})
    assert response.status_code == 201, response.text
    return response.json(), response.headers["Location"]


def correlate(client, headers, result, **params):
    response = client.post(f"/api/v1/investigations/{result['investigation_id']}/correlate", headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.model
def test_actual_sms_and_url_match_is_evidence_backed_and_preserves_assessment(api_factory, corpus_message, token_factory):
    client, app, calls = api_factory()
    headers = auth_headers(token_factory)
    sms = client.post("/api/v1/analyze/sms", headers=headers, json={"content": corpus_message(12), "source": "android_share"})
    assert sms.status_code == 201
    original_sms = sms.json()
    observed_url = parse_public_url(extract_urls(corpus_message(12))[0][0]).normalized
    url_result, url_path = submit_url(client, headers, observed_url)
    result = correlate(client, headers, original_sms)
    parsed = CorrelationResponse.model_validate(result)
    assert parsed.status == "matched"
    assert len(parsed.related_investigations) == 1
    related = parsed.related_investigations[0]
    assert str(related.investigation_id) == url_result["investigation_id"]
    assert len(related.shared_url_node_ids) == len(related.shared_domain_node_ids) == 1
    assert len(parsed.observations) == 2
    assert len(parsed.nodes) == 4
    assert len(parsed.edges) == 4
    assert all(item.observed_at.tzinfo is not None for item in parsed.observations)
    assert client.get(sms.headers["Location"], headers=headers).json() == original_sms
    assert client.get(url_path, headers=headers).json() == url_result
    assert all(request.url.path.endswith("jwks.json") for request in calls)
    with Session(app.state.database.engine) as session:
        for edge in parsed.edges:
            stored = session.get(GraphEdge, edge.id)
            assert stored is not None
            assert stored.investigation_id == edge.investigation_id
            evidence = session.get(Evidence, edge.evidence_id)
            assert evidence.investigation_id == stored.investigation_id
            assert evidence.verification_status == "documented_rule"
            assert evidence.severity == "info"
            assert session.get(EvidenceSource, evidence.source_id) is not None
        assert session.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "investigation.correlated")) == 1


def test_exact_hostname_match_is_not_an_exact_url_match(api_factory, token_factory):
    client, _, _ = api_factory()
    headers = auth_headers(token_factory)
    root, _ = submit_url(client, headers, "https://example.com/first")
    other, _ = submit_url(client, headers, "https://example.com/second")
    subdomain, _ = submit_url(client, headers, "https://sub.example.com/first")
    result = correlate(client, headers, root)
    assert [item["investigation_id"] for item in result["related_investigations"]] == [other["investigation_id"]]
    assert result["related_investigations"][0]["shared_url_node_ids"] == []
    assert len(result["related_investigations"][0]["shared_domain_node_ids"]) == 1
    assert subdomain["investigation_id"] not in str(result)


def test_equal_redacted_urls_do_not_create_false_exact_matches(api_factory, token_factory):
    client, _, _ = api_factory()
    headers = auth_headers(token_factory)
    root, _ = submit_url(client, headers, "https://example.com/?reference=isolated-alpha")
    other, _ = submit_url(client, headers, "https://example.com/?reference=isolated-beta")
    assert root["subject"]["value"] == other["subject"]["value"]
    result = correlate(client, headers, root)
    assert result["status"] == "matched"
    assert result["related_investigations"][0]["shared_url_node_ids"] == []
    assert len([node for node in result["nodes"] if node["type"] == "url"]) == 2
    assert "isolated-alpha" not in str(result) and "isolated-beta" not in str(result)


def test_correlation_never_searches_another_owner(api_factory, token_factory):
    client, app, _ = api_factory()
    owner = auth_headers(token_factory)
    another = auth_headers(token_factory, sub=str(uuid4()))
    root, _ = submit_url(client, owner)
    other, _ = submit_url(client, another)
    result = correlate(client, owner, root)
    assert result["status"] == "no_matches"
    assert result["related_investigations"] == []
    assert other["investigation_id"] not in str(result)
    path = f"/api/v1/investigations/{root['investigation_id']}/correlate"
    assert client.post(path, headers=another).status_code == 404
    assert client.post(path).status_code == 401
    with Session(app.state.database.engine) as session:
        assert session.scalar(select(func.count()).select_from(GraphEdge)) == 2


@pytest.mark.model
def test_no_identifiers_returns_actual_empty_graph(api_factory, corpus_message, token_factory):
    client, _, _ = api_factory()
    headers = auth_headers(token_factory)
    response = client.post("/api/v1/analyze/sms", headers=headers, json={"content": corpus_message(0)})
    result = correlate(client, headers, response.json())
    assert result["status"] == "no_identifiers"
    for key in ("related_investigations", "nodes", "edges", "observations", "sources"):
        assert result[key] == []
    assert result["has_more"] is False


def test_repeated_correlation_does_not_duplicate_graph_or_evidence(api_factory, token_factory):
    client, app, _ = api_factory()
    headers = auth_headers(token_factory)
    root, _ = submit_url(client, headers)
    submit_url(client, headers)
    first = correlate(client, headers, root)
    second = correlate(client, headers, root)
    for key in ("nodes", "edges", "observations", "sources", "related_investigations"):
        assert first[key] == second[key]
    with Session(app.state.database.engine) as session:
        assert session.scalar(select(func.count()).select_from(GraphNode)) == 4
        assert session.scalar(select(func.count()).select_from(GraphEdge)) == 4
        assert session.scalar(select(func.count()).select_from(Evidence).where(Evidence.code == "STORED_URL_OBSERVATION")) == 2


def test_deletion_removes_supported_edges_and_orphan_nodes(api_factory, token_factory):
    client, app, _ = api_factory()
    headers = auth_headers(token_factory)
    root, root_path = submit_url(client, headers)
    other, other_path = submit_url(client, headers)
    correlate(client, headers, root)
    assert client.delete(other_path, headers=headers).status_code == 204
    with Session(app.state.database.engine) as session:
        assert session.scalar(select(func.count()).select_from(GraphEdge)) == 2
        assert session.scalar(select(func.count()).select_from(GraphNode)) == 3
        assert session.scalar(select(func.count()).select_from(Evidence).where(Evidence.investigation_id == UUID(other["investigation_id"]))) == 0
    result = correlate(client, headers, root)
    assert result["status"] == "no_matches"
    assert other["investigation_id"] not in str(result)
    assert client.delete(root_path, headers=headers).status_code == 204
    with Session(app.state.database.engine) as session:
        for table in (GraphEdge, GraphNode, URLIndicator):
            assert session.scalar(select(func.count()).select_from(table)) == 0


def test_expired_records_hidden_and_retention_removes_graph(api_factory, token_factory):
    client, app, _ = api_factory()
    headers = auth_headers(token_factory)
    root, _ = submit_url(client, headers)
    other, _ = submit_url(client, headers)
    correlate(client, headers, root)
    with Session(app.state.database.engine) as session, session.begin():
        session.get(Investigation, UUID(other["investigation_id"])).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    result = correlate(client, headers, root)
    assert result["status"] == "no_matches"
    path = f"/api/v1/investigations/{other['investigation_id']}/correlate"
    assert client.post(path, headers=headers).status_code == 404
    counts = purge_expired(app.state.database)
    assert counts["investigations_deleted"] == 1
    assert counts["orphan_graph_nodes_deleted"] == 1
    with Session(app.state.database.engine) as session:
        assert session.scalar(select(func.count()).select_from(GraphEdge)) == 2
        assert session.scalar(select(func.count()).select_from(GraphNode)) == 3


def test_direct_matches_do_not_expand_transitive_campaigns(api_factory, corpus_message, token_factory):
    client, _, _ = api_factory()
    headers = auth_headers(token_factory)
    root, _ = submit_url(client, headers, "https://example.com/first")
    # Clearly labelled isolated multi-URL fixture appended to a genuine corpus
    # message; not a fabricated dataset or verified fraud incident.
    bridge = client.post("/api/v1/analyze/sms", headers=headers, json={
        "content": corpus_message(0) + "\nISOLATED TEST LINKS: https://example.com/second https://example.org/bridge",
    })
    assert bridge.status_code == 201
    distant, _ = submit_url(client, headers, "https://example.org/bridge")
    result = correlate(client, headers, root)
    assert [item["investigation_id"] for item in result["related_investigations"]] == [bridge.json()["investigation_id"]]
    assert distant["investigation_id"] not in str(result)
    assert "example.org" not in str(result)


def test_bounded_results_and_query_validation(api_factory, token_factory):
    client, _, _ = api_factory()
    headers = auth_headers(token_factory)
    root, _ = submit_url(client, headers)
    submit_url(client, headers, "https://example.com/second")
    recent, _ = submit_url(client, headers, "https://example.com/third")
    result = correlate(client, headers, root, limit=1)
    assert result["has_more"] is True
    assert len(result["related_investigations"]) == 1
    assert result["related_investigations"][0]["investigation_id"] == recent["investigation_id"]
    path = f"/api/v1/investigations/{root['investigation_id']}/correlate"
    for limit in (0, 101, "invalid"):
        assert client.post(path, headers=headers, params={"limit": limit}).status_code == 422
    assert client.post("/api/v1/investigations/not-a-uuid/correlate", headers=headers).status_code == 422
    assert client.post(f"/api/v1/investigations/{uuid4()}/correlate", headers=headers).status_code == 404


def test_output_validation_rejects_absent_or_wrong_evidence(api_factory, token_factory):
    client, _, _ = api_factory()
    headers = auth_headers(token_factory)
    root, _ = submit_url(client, headers)
    result = correlate(client, headers, root)
    result["edges"][0]["evidence_id"] = str(uuid4())
    with pytest.raises(ValidationError, match="evidence"):
        CorrelationResponse.model_validate(result)
    result = correlate(client, headers, root)
    result["edges"][0]["investigation_id"] = str(uuid4())
    with pytest.raises(ValidationError, match="evidence"):
        CorrelationResponse.model_validate(result)


def test_correlation_failure_rolls_back_graph(api_factory, token_factory, monkeypatch):
    client, app, _ = api_factory()
    headers = auth_headers(token_factory)
    root, _ = submit_url(client, headers)
    original = CorrelationRepository._node
    def fail_after_node(self, *args):
        original(self, *args)
        raise APIError(503, "database_unavailable", "Isolated failure fixture")
    monkeypatch.setattr(CorrelationRepository, "_node", fail_after_node)
    response = client.post(f"/api/v1/investigations/{root['investigation_id']}/correlate", headers=headers)
    assert response.status_code == 503
    with Session(app.state.database.engine) as session:
        assert session.scalar(select(func.count()).select_from(GraphNode)) == 0
        assert session.scalar(select(func.count()).select_from(Evidence).where(Evidence.code == "STORED_URL_OBSERVATION")) == 0


def test_forward_migration_preserves_preexisting_data(api_factory, token_factory, auth_material, tmp_path):
    client, app, _ = api_factory()
    root, _ = submit_url(client, auth_headers(token_factory))
    # Copy a real API-produced record to a disposable old-revision database,
    # then verify an upgrade preserves it and adds the correlation indexes.
    from backend.app.core.config import Settings
    from backend.app.database.connection import Database
    old_root = tmp_path / "old" / "sqlite"
    old_root.mkdir(parents=True)
    (old_root / "0001_core.sql").write_bytes((MIGRATIONS_ROOT / "sqlite/0001_core.sql").read_bytes())
    database = Database(Settings(database_url=f"sqlite:///{tmp_path / 'upgrade.sqlite3'}", _env_file=None))
    try:
        assert apply_migrations(database.engine, old_root.parent) == ["0001_core"]
        from backend.app.database.models import User
        with Session(database.engine) as session, session.begin():
            session.add(User(id=auth_material["user_id"]))
            session.flush()
            session.add(Investigation(
                id=UUID(root["investigation_id"]), owner_id=auth_material["user_id"],
                subject_type=root["subject"]["type"], subject_value=root["subject"]["value"],
                source="web_share", status=root["status"], result=root,
                created_at=datetime.fromisoformat(root["created_at"]),
                expires_at=datetime.fromisoformat(root["expires_at"]),
            ))
        assert apply_migrations(database.engine) == ["0002_correlation_indexes"]
        indexes = {item["name"] for item in inspect(database.engine).get_indexes("urls")}
        assert "ix_urls_owner_sha256_investigation" in indexes
        assert "ix_urls_owner_domain_investigation" in indexes
        assert apply_migrations(database.engine) == []
        with Session(database.engine) as session:
            assert session.get(Investigation, UUID(root["investigation_id"])).result == root
    finally:
        database.dispose()
    with Session(app.state.database.engine) as session:
        assert session.get(Investigation, UUID(root["investigation_id"])) is not None
