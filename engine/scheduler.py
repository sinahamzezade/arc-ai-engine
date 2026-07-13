from __future__ import annotations

from config import MAX_LESSONS
from contracts.roadmap_plan import SelectedPhase
from engine.study_budget import StudyBudget


def sum_minutes(phases: list[SelectedPhase]) -> int:
    total = 0
    for p in phases:
        for m in p.milestones:
            for lesson in m.lessons:
                total += lesson.estimated_minutes
    return total


def count_lessons(phases: list[SelectedPhase]) -> int:
    return sum(len(m.lessons) for p in phases for m in p.milestones)


def size_to_budget(
    phases: list[SelectedPhase], budget: StudyBudget
) -> list[SelectedPhase]:
    result = list(phases)
    while sum_minutes(result) > budget.budget_minutes and len(result) > 1:
        # Prefer dropping optional trailing phases
        result = result[:-1]
    while count_lessons(result) > MAX_LESSONS and len(result) > 1:
        result = result[:-1]
    return _reindex(result)


def _reindex(phases: list[SelectedPhase]) -> list[SelectedPhase]:
    out: list[SelectedPhase] = []
    for i, phase in enumerate(phases):
        milestones = []
        for mi, m in enumerate(phase.milestones):
            lessons = []
            for li, lesson in enumerate(m.lessons):
                status = (
                    "available"
                    if i == 0 and mi == 0 and li == 0
                    else "locked"
                )
                lessons.append(lesson.model_copy(update={"status": status}))
            milestones.append(
                m.model_copy(update={"order_index": mi, "lessons": lessons})
            )
        out.append(
            phase.model_copy(
                update={
                    "order_index": i,
                    "locked": i > 0,
                    "milestones": milestones,
                }
            )
        )
    return out


def insert_special_weeks(
    phases: list[SelectedPhase],
    budget: StudyBudget,
) -> tuple[list[SelectedPhase], int]:
    """Insert review / buffer marker phases; return (phases, special_week_count)."""
    if not phases:
        return phases, 0

    result: list[SelectedPhase] = []
    special = 0
    n = budget.review_every_n_phases

    for i, phase in enumerate(phases):
        result.append(phase)
        if n > 0 and (i + 1) % n == 0 and i < len(phases) - 1:
            result.append(
                SelectedPhase(
                    key=f"review-after-{phase.key}",
                    title=f"Review: {phase.title}",
                    tech_stack_id=phase.tech_stack_id,
                    tech_stack_slug=phase.tech_stack_slug,
                    order_index=0,
                    locked=True,
                    week_type="review",
                    milestones=[],
                )
            )
            special += 1

    for bi in range(budget.buffer_weeks):
        result.append(
            SelectedPhase(
                key=f"buffer-{bi + 1}",
                title=f"Recovery buffer {bi + 1}",
                order_index=0,
                locked=True,
                week_type="buffer",
                milestones=[],
            )
        )
        special += 1

    return _reindex(result), special


def assign_weeks(
    phases: list[SelectedPhase], budget: StudyBudget
) -> list[SelectedPhase]:
    """Bin-pack lessons into week indexes under target_weekly_load."""
    week = 1
    load = 0.0
    target = budget.target_weekly_load
    updated: list[SelectedPhase] = []

    for phase in phases:
        if phase.week_type != "learning":
            # Special weeks consume one week slot
            updated.append(phase)
            week += 1
            load = 0.0
            continue
        new_milestones = []
        for m in phase.milestones:
            new_lessons = []
            for lesson in m.lessons:
                mins = lesson.estimated_minutes
                if load + mins > target and load > 0:
                    week += 1
                    load = 0.0
                new_lessons.append(lesson.model_copy(update={"week_index": week}))
                load += mins
            new_milestones.append(m.model_copy(update={"lessons": new_lessons}))
        updated.append(phase.model_copy(update={"milestones": new_milestones}))

    return updated
