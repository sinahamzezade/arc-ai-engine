"""Engine version + scoring/scheduling knobs. Bump ENGINE_VERSION when output changes for same input."""

from __future__ import annotations

import os

ENGINE_VERSION = int(os.getenv("ROADMAP_ENGINE_VERSION", "2"))

SAFETY_FACTOR = float(os.getenv("ROADMAP_SAFETY_FACTOR", "0.85"))
WEEKLY_SLACK = float(os.getenv("ROADMAP_WEEKLY_SLACK", "0.10"))

SCORE_WEIGHTS = {
    "role_fit": 0.30,
    "skill_gap_fit": 0.25,
    "prerequisite_readiness": 0.15,
    "learning_style_fit": 0.10,
    "time_fit": 0.10,
    "quality_score": 0.10,
}

MAX_LESSONS = 80
MAX_LESSONS_PER_SKILL = 4
REVIEW_EVERY_N_PHASES = 2

STUDY_HOURS = {
    "lt-3": 2.0,
    "3-5": 4.0,
    "5-8": 6.5,
    "8-12": 10.0,
    "gt-12": 14.0,
}

DEADLINE_WEEKS: dict[str, int | None] = {
    "1-3": 8,
    "3-6": 16,
    "6-12": 24,
    "12+": 40,
    "none": None,
}

CONFIDENCE_RANK = {
    "starting": 0,
    "beginner": 1,
    "somewhat": 2,
    "confident": 3,
    "very": 4,
}
