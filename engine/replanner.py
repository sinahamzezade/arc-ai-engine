from __future__ import annotations

from contracts.content_snapshot import ContentSnapshot
from contracts.learner_profile import LearnerProfile, ReplanCurrentState
from contracts.roadmap_plan import PlanResponse, RoadmapPlan, SelectedPhase
from engine.generator import generate_roadmap


def replan_roadmap(
    profile: LearnerProfile,
    snapshot: ContentSnapshot,
    seed: int,
    current_state: ReplanCurrentState,
) -> PlanResponse:
    """
    Re-run planning for the future path only.
    Completed skill nodes / phase keys are treated as proven mastered.
    """
    proven = set(profile.proven_mastered_skill_ids or [])
    proven.update(current_state.completed_skill_node_ids or [])
    proven.update(current_state.completed_phase_keys or [])  # harmless if keys

    # Also treat completed lesson template skills as proven via snapshot lookup
    completed_templates = set(current_state.completed_lesson_template_ids or [])
    for lesson in snapshot.lessons:
        if lesson.id in completed_templates:
            proven.add(lesson.skill_node_id)

    profile = profile.model_copy(
        update={"proven_mastered_skill_ids": list(proven)}
    )

    response = generate_roadmap(profile, snapshot, seed)
    if not response.ok or not response.plan:
        return response

    plan = response.plan

    # Preserve completed phases from prior plan if provided
    preserved: list[SelectedPhase] = []
    if current_state.prior_plan:
        try:
            prior = RoadmapPlan.model_validate(current_state.prior_plan)
            for phase in prior.phases:
                if phase.key in (current_state.completed_phase_keys or []):
                    # Freeze completed lessons as completed
                    frozen_milestones = []
                    for m in phase.milestones:
                        lessons = [
                            lesson.model_copy(update={"status": "completed"})
                            for lesson in m.lessons
                        ]
                        frozen_milestones.append(
                            m.model_copy(update={"lessons": lessons})
                        )
                    preserved.append(
                        phase.model_copy(
                            update={
                                "locked": False,
                                "milestones": frozen_milestones,
                            }
                        )
                    )
        except Exception:  # noqa: BLE001
            preserved = []

    # Drop future phases that duplicate preserved keys
    preserved_keys = {p.key for p in preserved}
    future = [p for p in plan.phases if p.key not in preserved_keys]

    # Trigger-specific tweaks
    trigger = current_state.trigger or "manual"
    if trigger in ("stuck", "assessment") and future:
        # Leave remedial content from gap calc; mark schedule meta
        meta = dict(plan.schedule_meta)
        meta["replan_trigger"] = trigger
        meta["weeks_shifted"] = len(preserved)
        plan = plan.model_copy(update={"schedule_meta": meta})

    merged = preserved + future
    for i, phase in enumerate(merged):
        locked = i > 0 and phase.week_type == "learning"
        # First incomplete lesson available
        milestones = []
        unlocked = False
        for mi, m in enumerate(phase.milestones):
            lessons = []
            for li, lesson in enumerate(m.lessons):
                if lesson.status == "completed":
                    lessons.append(lesson)
                    continue
                if not unlocked and i == len(preserved):
                    lessons.append(
                        lesson.model_copy(update={"status": "available"})
                    )
                    unlocked = True
                else:
                    lessons.append(
                        lesson.model_copy(update={"status": "locked"})
                    )
            milestones.append(
                m.model_copy(update={"order_index": mi, "lessons": lessons})
            )
        merged[i] = phase.model_copy(
            update={"order_index": i, "locked": locked, "milestones": milestones}
        )

    plan = plan.model_copy(
        update={
            "phases": merged,
            "schedule_meta": {
                **plan.schedule_meta,
                "replan_trigger": trigger,
                "preserved_phase_count": len(preserved),
                "source_roadmap_id": current_state.roadmap_id,
            },
        }
    )
    return PlanResponse(ok=True, plan=plan, feasibility=response.feasibility)
