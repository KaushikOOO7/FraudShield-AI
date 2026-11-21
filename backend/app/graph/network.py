"""Build a bounded evidence graph. Shared identifiers never imply a fraud campaign."""
from datetime import datetime, timezone
from uuid import UUID

import networkx as nx

from backend.app.schemas.correlation import CorrelationResponse, RelatedInvestigation

LIMITATIONS = [
    "Shared URLs or hostnames show observed reuse, not common ownership or a coordinated fraud campaign.",
    "Only this user's unexpired SMS, URL, QR and parsed-APK URL observations are considered; no other user's records are searched.",
    "URL matches use stored SHA-256 of normalized URLs before redaction; host matches use exact IDNA hostnames, not registrable domains.",
    "Only direct shared URL/hostname identifiers are returned; redirects, caller numbers, APK hashes, UPI identifiers and brand identity are not correlated.",
    "Correlation does not change the original risk assessment or run new model/provider analysis.",
]


def build_correlation(root_id: UUID, cases, nodes, edges, observations, sources, limit, has_more):
    graph = nx.MultiDiGraph()
    for node in nodes:
        graph.add_node(node.id, type=node.type, value=node.value)
    for edge in edges:
        graph.add_edge(edge.from_node_id, edge.to_node_id, key=edge.id, evidence_id=edge.evidence_id)
    investigation_nodes = {UUID(node.value): node.id for node in nodes if node.type == "investigation"}

    def observed_identifiers(investigation_id):
        node_id = investigation_nodes.get(investigation_id)
        return nx.descendants(graph, node_id) if node_id is not None else set()

    root_identifiers = observed_identifiers(root_id)
    related = []
    for case in cases:
        if case.id == root_id:
            continue
        shared = root_identifiers & observed_identifiers(case.id)
        urls = sorted((item for item in shared if graph.nodes[item]["type"] == "url"), key=str)
        domains = sorted((item for item in shared if graph.nodes[item]["type"] == "domain"), key=str)
        if urls or domains:
            related.append(RelatedInvestigation(
                investigation_id=case.id, subject_type=case.subject_type, source=case.source,
                created_at=case.created_at.replace(tzinfo=timezone.utc) if case.created_at.tzinfo is None else case.created_at,
                shared_url_node_ids=urls, shared_domain_node_ids=domains,
            ))
    return CorrelationResponse(
        investigation_id=root_id,
        status="matched" if related else "no_matches" if observations else "no_identifiers",
        generated_at=datetime.now(timezone.utc), related_investigations=related,
        nodes=nodes, edges=edges, observations=observations, sources=sources,
        limit=limit, has_more=has_more, limitations=LIMITATIONS,
    )
