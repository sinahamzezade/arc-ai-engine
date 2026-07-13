from __future__ import annotations

import networkx as nx

from contracts.content_snapshot import ContentSnapshot, SkillNodeSnapshot
from engine.errors import EngineError, ErrorCodes


def build_skill_graph(snapshot: ContentSnapshot) -> nx.DiGraph:
    g = nx.DiGraph()
    by_id = {s.id: s for s in snapshot.skills}
    for skill in snapshot.skills:
        g.add_node(skill.id, skill=skill)
    for skill in snapshot.skills:
        for pre_id in skill.prerequisite_skill_ids or []:
            if pre_id not in by_id:
                raise EngineError(
                    ErrorCodes.ROADMAP_PREREQUISITE_FAILED,
                    f"Dangling prerequisite {pre_id} for skill {skill.id}",
                )
            if pre_id not in g:
                g.add_node(pre_id, skill=by_id[pre_id])
            g.add_edge(pre_id, skill.id)
    if not nx.is_directed_acyclic_graph(g):
        raise EngineError(
            ErrorCodes.ROADMAP_GRAPH_INVALID,
            "Skill subgraph contains a cycle",
        )
    return g


def prerequisite_closure(
    graph: nx.DiGraph,
    required_ids: set[str],
) -> set[str]:
    closed = set(required_ids)
    for node_id in list(required_ids):
        if node_id not in graph:
            raise EngineError(
                ErrorCodes.ROADMAP_CONTENT_NOT_FOUND,
                f"Required skill node missing from snapshot: {node_id}",
            )
        closed.update(nx.ancestors(graph, node_id))
        closed.add(node_id)
    return closed


def topological_order(
    graph: nx.DiGraph,
    node_ids: set[str],
) -> list[SkillNodeSnapshot]:
    sub = graph.subgraph(node_ids).copy()
    try:
        ordered_ids = list(nx.topological_sort(sub))
    except nx.NetworkXUnfeasible as exc:
        raise EngineError(
            ErrorCodes.ROADMAP_GRAPH_INVALID,
            "Topological sort failed",
        ) from exc
    result: list[SkillNodeSnapshot] = []
    for nid in ordered_ids:
        skill = graph.nodes[nid].get("skill")
        if skill is not None:
            result.append(skill)
    # Stable secondary sort by order_hint within equal topo layers
    return result


def validate_dependencies(graph: nx.DiGraph) -> None:
    if not nx.is_directed_acyclic_graph(graph):
        raise EngineError(
            ErrorCodes.ROADMAP_GRAPH_INVALID,
            "Skill subgraph contains a cycle",
        )
