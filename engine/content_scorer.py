from __future__ import annotations

import random
from dataclasses import dataclass

from config import SCORE_WEIGHTS
from contracts.content_snapshot import LessonCandidate
from contracts.learner_profile import LearnerProfile
from contracts.roadmap_plan import ExplanationTrace


@dataclass
class ScoredLesson:
    lesson: LessonCandidate
    score: float
    breakdown: dict[str, float]


def _style_fit(lesson: LessonCandidate, styles: list[str]) -> float:
    if not styles:
        return 0.5
    hits = sum(1 for t in lesson.learning_style_tags if t in styles)
    return min(1.0, hits / max(1, len(styles))) if hits else 0.2


def _time_fit(lesson: LessonCandidate, weekly_minutes: float) -> float:
    if weekly_minutes <= 0:
        return 0.5
    ratio = lesson.estimated_minutes / weekly_minutes
    if ratio <= 0.25:
        return 1.0
    if ratio <= 0.5:
        return 0.8
    if ratio <= 1.0:
        return 0.5
    return 0.2


def score_lesson(
    lesson: LessonCandidate,
    *,
    profile: LearnerProfile,
    is_required_gap: bool,
    prereq_ready: bool,
    weekly_minutes: float,
) -> ScoredLesson:
    breakdown = {
        "role_fit": 1.0 if is_required_gap else 0.6,
        "skill_gap_fit": 1.0 if is_required_gap else 0.4,
        "prerequisite_readiness": 1.0 if prereq_ready else 0.3,
        "learning_style_fit": _style_fit(lesson, profile.learning_styles or []),
        "time_fit": _time_fit(lesson, weekly_minutes),
        "quality_score": float(lesson.quality_score or 0.8),
    }
    score = sum(breakdown[k] * SCORE_WEIGHTS[k] for k in SCORE_WEIGHTS)
    return ScoredLesson(lesson=lesson, score=score, breakdown=breakdown)


def select_best_lessons(
    candidates: list[LessonCandidate],
    *,
    profile: LearnerProfile,
    is_required_gap: bool,
    prereq_ready: bool,
    weekly_minutes: float,
    seed: int,
    max_count: int,
    compress: bool,
) -> tuple[list[ScoredLesson], ExplanationTrace | None]:
    rng = random.Random(seed)
    published = [
        c
        for c in candidates
        if c.status in ("published", "Published", "active")
        and (c.language == profile.language or not profile.language)
    ]
    if not published:
        published = list(candidates)
    if not published:
        return [], None

    scored = [
        score_lesson(
            c,
            profile=profile,
            is_required_gap=is_required_gap,
            prereq_ready=prereq_ready,
            weekly_minutes=weekly_minutes,
        )
        for c in published
    ]
    # Seeded tie-break: shuffle equal scores
    scored.sort(key=lambda s: (-s.score, rng.random(), s.lesson.order_hint))

    if compress:
        practice = next(
            (s for s in scored if s.lesson.lesson_type == "practice"),
            scored[0],
        )
        chosen = [practice]
    else:
        chosen = scored[:max_count]
        practice = next(
            (s for s in scored if s.lesson.lesson_type == "practice"), None
        )
        if practice and all(c.lesson.id != practice.lesson.id for c in chosen):
            chosen[-1] = practice
        chosen.sort(key=lambda s: s.lesson.order_hint)

    top = chosen[0]
    reason = "candidate_refresh" if compress else (
        "required_gap" if is_required_gap else "optional_fill"
    )
    trace = ExplanationTrace(
        skill_node=top.lesson.skill_node_id,
        chosen_lesson_version=top.lesson.published_version_id or top.lesson.id,
        reason=reason,
        score_breakdown={k: round(v * SCORE_WEIGHTS[k], 4) for k, v in top.breakdown.items()},
        alternatives_considered=max(0, len(scored) - 1),
    )
    return chosen, trace
