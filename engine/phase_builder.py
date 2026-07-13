from __future__ import annotations

from config import CONFIDENCE_RANK, MAX_LESSONS_PER_SKILL
from contracts.content_snapshot import (
    ContentSnapshot,
    LessonCandidate,
    PhaseBlueprint,
    SkillNodeSnapshot,
)
from contracts.learner_profile import LearnerProfile
from contracts.roadmap_plan import (
    SelectedLesson,
    SelectedMilestone,
    SelectedPhase,
)
from engine.content_scorer import select_best_lessons
from engine.skill_gap import SkillGap
from engine.study_budget import StudyBudget


def confidence_meets(user_confidence: str | None, required: str | None) -> bool:
    if not required:
        return True
    user_rank = CONFIDENCE_RANK.get(user_confidence or "starting", 0)
    need_rank = CONFIDENCE_RANK.get(required, 0)
    return user_rank >= need_rank


def _lessons_for_skill(
    snapshot: ContentSnapshot, skill_id: str
) -> list[LessonCandidate]:
    return [l for l in snapshot.lessons if l.skill_node_id == skill_id]


def _to_selected(
    scored_list,
    skill_id: str,
    status: str = "locked",
) -> list[SelectedLesson]:
    out: list[SelectedLesson] = []
    for scored in scored_list:
        lesson = scored.lesson
        out.append(
            SelectedLesson(
                source_template_id=lesson.id,
                source_version_id=lesson.published_version_id,
                skill_node_id=skill_id,
                title=lesson.title,
                mission_name=lesson.mission_name_template,
                lesson_type=lesson.lesson_type,
                estimated_minutes=lesson.estimated_minutes,
                difficulty=lesson.difficulty,
                xp_reward=lesson.xp_reward,
                reward_class=lesson.reward_class,
                resource_id=lesson.default_resource_id,
                status=status,  # type: ignore[arg-type]
                content_outline=lesson.content_outline or {},
            )
        )
    return out


def build_learning_phases(
    *,
    snapshot: ContentSnapshot,
    profile: LearnerProfile,
    gap: SkillGap,
    ordered_skills: list[SkillNodeSnapshot],
    budget: StudyBudget,
    seed: int,
) -> tuple[list[SelectedPhase], list]:
    stacks_by_slug = {s.slug: s for s in snapshot.stacks}
    skills_by_stack: dict[str, list[SkillNodeSnapshot]] = {}
    for skill in ordered_skills:
        if skill.id not in gap.active_ids:
            continue
        slug = skill.tech_stack_slug or ""
        skills_by_stack.setdefault(slug, []).append(skill)

    blueprints: list[PhaseBlueprint] = list(snapshot.recipe.phase_blueprint)
    phases: list[SelectedPhase] = []
    explanations = []
    order_index = 0

    for bp in blueprints:
        if not bp.required and not confidence_meets(
            profile.confidence, bp.include_if_confidence_gte
        ):
            continue

        stack_slug = bp.tech_stack_slugs[0] if bp.tech_stack_slugs else None
        stack = stacks_by_slug.get(stack_slug) if stack_slug else None
        milestones: list[SelectedMilestone] = []
        seen: set[str] = set()
        mi = 0

        for slug in bp.tech_stack_slugs:
            for skill in skills_by_stack.get(slug, []):
                if skill.id in seen:
                    continue
                seen.add(skill.id)
                compress = skill.id in gap.candidate_refresh_ids
                candidates = _lessons_for_skill(snapshot, skill.id)
                scored, trace = select_best_lessons(
                    candidates,
                    profile=profile,
                    is_required_gap=skill.id in gap.required_ids,
                    prereq_ready=True,
                    weekly_minutes=budget.weekly_minutes,
                    seed=seed + hash(skill.id) % 10_000,
                    max_count=MAX_LESSONS_PER_SKILL,
                    compress=compress,
                )
                if not scored:
                    continue
                lessons = _to_selected(scored, skill.id)
                if trace:
                    explanations.append(trace)
                    if lessons:
                        lessons[0].explanation = trace
                milestones.append(
                    SelectedMilestone(
                        skill_node_id=skill.id,
                        title=f"{skill.title} (refresh)" if compress else skill.title,
                        type="skill",
                        compress=compress,
                        order_index=mi,
                        xp_reward=25 if compress else 50,
                        lessons=lessons,
                    )
                )
                mi += 1

        if not milestones:
            continue

        phases.append(
            SelectedPhase(
                key=bp.key,
                title=bp.title,
                tech_stack_id=stack.id if stack else None,
                tech_stack_slug=stack_slug,
                order_index=order_index,
                locked=order_index > 0,
                week_type="learning",
                milestones=milestones,
            )
        )
        order_index += 1

    return phases, explanations
