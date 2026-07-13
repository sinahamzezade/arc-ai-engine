from __future__ import annotations

from contracts.learner_profile import LearnerProfile
from engine.errors import EngineError, ErrorCodes


def load_profile(profile: LearnerProfile) -> LearnerProfile:
    roles = [r for r in (profile.target_roles or []) if r]
    if not roles:
        raise EngineError(
            ErrorCodes.ROADMAP_ROLE_NOT_FOUND,
            "Goal has no target role",
        )
    known = [s for s in (profile.known_skills or []) if s and s != "none"]
    return profile.model_copy(
        update={
            "target_roles": roles,
            "known_skills": known,
        }
    )
