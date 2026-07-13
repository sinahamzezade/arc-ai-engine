from __future__ import annotations

from dataclasses import dataclass, field

from contracts.content_snapshot import SkillNodeSnapshot
from contracts.learner_profile import LearnerProfile


@dataclass
class SkillGap:
    required_ids: set[str]
    active_ids: set[str]
    candidate_refresh_ids: set[str] = field(default_factory=set)
    skipped_known_ids: list[str] = field(default_factory=list)
    skills_by_id: dict[str, SkillNodeSnapshot] = field(default_factory=dict)


def calculate_skill_gap(
    profile: LearnerProfile,
    skills: list[SkillNodeSnapshot],
    required_ids: set[str],
) -> SkillGap:
    by_id = {s.id: s for s in skills}
    known_tokens = set(profile.known_skills or [])
    proven = set(profile.proven_mastered_skill_ids or [])

    candidate_refresh: set[str] = set()
    skipped: list[str] = []
    active = set(required_ids)

    for skill_id in list(required_ids):
        skill = by_id.get(skill_id)
        if not skill:
            continue
        tag_hit = any(t in known_tokens for t in (skill.tags or []))
        if skill_id in proven:
            active.discard(skill_id)
            skipped.append(skill_id)
            continue
        if tag_hit:
            # Known but not proven → keep as compressed refresh (Content Pool §7.1)
            candidate_refresh.add(skill_id)

    return SkillGap(
        required_ids=required_ids,
        active_ids=active,
        candidate_refresh_ids=candidate_refresh,
        skipped_known_ids=skipped,
        skills_by_id=by_id,
    )
