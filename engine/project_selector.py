from __future__ import annotations

from contracts.roadmap_plan import SelectedMilestone, SelectedPhase


def place_projects_and_assessments(
    phases: list[SelectedPhase],
    *,
    assessments: list[dict] | None = None,
    projects: list[dict] | None = None,
) -> list[SelectedPhase]:
    """Place assessment/project milestone markers at phase boundaries when available."""
    assessments = assessments or []
    projects = projects or []
    if not assessments and not projects:
        return phases

    out: list[SelectedPhase] = []
    for i, phase in enumerate(phases):
        if phase.week_type != "learning":
            out.append(phase)
            continue
        milestones = list(phase.milestones)
        # Attach assessment at end of phase if recipe provides one
        if assessments and i < len(assessments):
            a = assessments[i]
            milestones.append(
                SelectedMilestone(
                    skill_node_id=str(a.get("skill_node_id") or phase.milestones[-1].skill_node_id if phase.milestones else ""),
                    title=str(a.get("title") or f"Assessment: {phase.title}"),
                    type="assessment",
                    compress=False,
                    order_index=len(milestones),
                    xp_reward=int(a.get("xp_reward") or 75),
                    lessons=[],
                )
            )
        if projects and i == len([p for p in phases if p.week_type == "learning"]) - 1:
            p = projects[0]
            milestones.append(
                SelectedMilestone(
                    skill_node_id=str(p.get("skill_node_id") or ""),
                    title=str(p.get("title") or f"Project: {phase.title}"),
                    type="project",
                    compress=False,
                    order_index=len(milestones),
                    xp_reward=int(p.get("xp_reward") or 100),
                    lessons=[],
                )
            )
        out.append(phase.model_copy(update={"milestones": milestones}))
    return out
