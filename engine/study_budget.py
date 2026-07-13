from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

from config import (
    CONFIDENCE_RANK,
    DEADLINE_WEEKS,
    SAFETY_FACTOR,
    STUDY_HOURS,
    WEEKLY_SLACK,
)
from contracts.learner_profile import LearnerProfile


@dataclass
class StudyBudget:
    weekly_hours: float
    weekly_minutes: float
    horizon_weeks: int
    budget_minutes: int
    target_weekly_load: float
    pace_factor: float
    buffer_weeks: int
    review_every_n_phases: int


def decode_weekly_hours(token: str | None) -> float:
    if not token:
        return 6.5
    return STUDY_HOURS.get(token, 6.5)


def decode_timeline_weeks(token: str | None, recipe_default: int) -> int:
    if not token:
        return recipe_default
    mapped = DEADLINE_WEEKS.get(token)
    if mapped is None:
        return recipe_default
    return min(mapped, recipe_default * 2)


def pace_factor(profile: LearnerProfile) -> float:
    conf = CONFIDENCE_RANK.get(profile.confidence or "starting", 0)
    obstacles = len(profile.quit_reasons or [])
    # Low confidence / many quit reasons → slower (more weeks / buffer)
    factor = 1.0
    if conf <= 1:
        factor += 0.15
    if obstacles >= 2:
        factor += 0.1 * min(obstacles, 4)
    return factor


def calculate_study_budget(
    profile: LearnerProfile,
    recipe_default_weeks: int,
) -> StudyBudget:
    hours = decode_weekly_hours(profile.weekly_hours_token)
    deadline_weeks = decode_timeline_weeks(
        profile.target_deadline_token, recipe_default_weeks
    )
    pf = pace_factor(profile)
    horizon = max(1, int(math.ceil(min(deadline_weeks, recipe_default_weeks * pf))))
    weekly_minutes = hours * 60
    budget = int(round(weekly_minutes * horizon * SAFETY_FACTOR))
    target_load = max(15.0, weekly_minutes * (1.0 - WEEKLY_SLACK))
    buffer_weeks = min(4, len(profile.quit_reasons or []) // 2 + (1 if pf > 1.1 else 0))
    review_n = 3 if pf > 1.15 else 2
    return StudyBudget(
        weekly_hours=hours,
        weekly_minutes=weekly_minutes,
        horizon_weeks=horizon,
        budget_minutes=budget,
        target_weekly_load=target_load,
        pace_factor=pf,
        buffer_weeks=buffer_weeks,
        review_every_n_phases=review_n,
    )


def estimate_completion(
    total_selected_minutes: int,
    budget: StudyBudget,
    special_weeks: int,
    start: date | None = None,
) -> tuple[int, str | None]:
    load = max(budget.target_weekly_load, 1.0)
    learning_weeks = int(math.ceil(total_selected_minutes / load))
    estimated = learning_weeks + special_weeks
    start_date = start or date.today()
    completion = start_date + timedelta(weeks=estimated)
    return estimated, completion.isoformat()
