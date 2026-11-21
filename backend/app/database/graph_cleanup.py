from sqlalchemy import delete, exists, or_, select

from backend.app.database.models import GraphEdge, GraphNode


def prune_orphan_graph_nodes(session, owner_id=None) -> int:
    statement = delete(GraphNode).where(~exists(select(GraphEdge.id).where(or_(
        GraphEdge.from_node_id == GraphNode.id, GraphEdge.to_node_id == GraphNode.id,
    ))))
    if owner_id is not None:
        statement = statement.where(GraphNode.owner_id == owner_id)
    return session.execute(statement).rowcount
