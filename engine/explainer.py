from __future__ import annotations

from contracts.roadmap_plan import ExplanationTrace, SelectedPhase


def collect_explanations(phases: list[SelectedPhase]) -> list[ExplanationTrace]:
    traces: list[ExplanationTrace] = []
    for phase in phases:
        for m in phase.milestones:
            for lesson in m.lessons:
                if lesson.explanation:
                    traces.append(lesson.explanation)
    return traces
