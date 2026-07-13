from __future__ import annotations

from contracts.content_snapshot import (
    ContentSnapshot,
    LessonCandidate,
    PhaseBlueprint,
    RoleRecipeSnapshot,
    SkillNodeSnapshot,
    TechStackSnapshot,
)
from contracts.learner_profile import LearnerProfile, ReplanCurrentState
from engine.dependency_resolver import build_skill_graph, prerequisite_closure
from engine.errors import EngineError, ErrorCodes
from engine.generator import generate_roadmap
from engine.replanner import replan_roadmap
from engine.study_budget import calculate_study_budget


def _snapshot(*, many_lessons: bool = False) -> ContentSnapshot:
    skills = [
        SkillNodeSnapshot(
            id="skill-a",
            slug="a",
            title="Skill A",
            tech_stack_slug="stack-1",
            tags=["html"],
            prerequisite_skill_ids=[],
            order_hint=1,
        ),
        SkillNodeSnapshot(
            id="skill-b",
            slug="b",
            title="Skill B",
            tech_stack_slug="stack-1",
            tags=["css"],
            prerequisite_skill_ids=["skill-a"],
            order_hint=2,
        ),
        SkillNodeSnapshot(
            id="skill-c",
            slug="c",
            title="Skill C",
            tech_stack_slug="stack-2",
            tags=["js"],
            prerequisite_skill_ids=["skill-b"],
            order_hint=1,
        ),
    ]
    lessons = []
    for skill in skills:
        for i in range(3 if many_lessons else 2):
            lessons.append(
                LessonCandidate(
                    id=f"lesson-{skill.id}-{i}",
                    skill_node_id=skill.id,
                    slug=f"{skill.slug}-l{i}",
                    title=f"{skill.title} L{i}",
                    mission_name_template=f"Mission {skill.slug}",
                    lesson_type="practice" if i == 0 else "reading",
                    estimated_minutes=30,
                    learning_style_tags=["doing"],
                    published_version_id=f"ver-{skill.id}-{i}",
                    order_hint=i,
                )
            )
    return ContentSnapshot(
        content_version="test-v1",
        recipe=RoleRecipeSnapshot(
            id="recipe-1",
            target_role_slug="frontend-dev",
            title="Frontend Dev",
            default_timeline_weeks=12,
            required_skill_node_ids=["skill-a", "skill-b", "skill-c"],
            optional_skill_node_ids=[],
            phase_blueprint=[
                PhaseBlueprint(
                    key="fundamentals",
                    title="Fundamentals",
                    tech_stack_slugs=["stack-1"],
                    required=True,
                ),
                PhaseBlueprint(
                    key="js",
                    title="JavaScript",
                    tech_stack_slugs=["stack-2"],
                    required=True,
                ),
            ],
        ),
        stacks=[
            TechStackSnapshot(id="ts-1", slug="stack-1", title="Web"),
            TechStackSnapshot(id="ts-2", slug="stack-2", title="JS"),
        ],
        skills=skills,
        lessons=lessons,
    )


def _profile(**overrides) -> LearnerProfile:
    base = dict(
        user_id="user-1",
        goal_id="goal-1",
        goal_revision="goal-1:2020-01-01",
        target_roles=["frontend-dev"],
        known_skills=[],
        confidence="somewhat",
        weekly_hours_token="5-8",
        target_deadline_token="3-6",
        learning_styles=["doing"],
        quit_reasons=[],
    )
    base.update(overrides)
    return LearnerProfile(**base)


def test_dag_and_closure():
    snap = _snapshot()
    g = build_skill_graph(snap)
    closed = prerequisite_closure(g, {"skill-c"})
    assert closed == {"skill-a", "skill-b", "skill-c"}


def test_cycle_raises():
    snap = _snapshot()
    snap.skills[0].prerequisite_skill_ids = ["skill-b"]
    try:
        build_skill_graph(snap)
        assert False, "expected cycle error"
    except EngineError as err:
        assert err.code == ErrorCodes.ROADMAP_GRAPH_INVALID


def test_generate_plan_ok():
    result = generate_roadmap(_profile(), _snapshot(), seed=42)
    assert result.ok is True
    assert result.plan is not None
    assert result.plan.engine_version >= 1
    assert len(result.plan.phases) >= 1
    assert result.plan.explanations or any(
        m.lessons for p in result.plan.phases for m in p.milestones
    )


def test_seeded_divergence():
    snap = _snapshot(many_lessons=True)
    a = generate_roadmap(_profile(), snap, seed=1)
    b = generate_roadmap(_profile(), snap, seed=999)
    assert a.ok and b.ok
    # Titles may match but seed stored differs
    assert a.plan.seed != b.plan.seed


def test_known_skill_refresh_not_silent_skip():
    result = generate_roadmap(
        _profile(known_skills=["html"]),
        _snapshot(),
        seed=7,
    )
    assert result.ok
    titles = [
        m.title
        for p in result.plan.phases
        for m in p.milestones
    ]
    assert any("refresh" in t for t in titles)


def test_proven_skip():
    result = generate_roadmap(
        _profile(proven_mastered_skill_ids=["skill-a"]),
        _snapshot(),
        seed=3,
    )
    assert result.ok
    skill_ids = {
        m.skill_node_id
        for p in result.plan.phases
        for m in p.milestones
        if m.type == "skill"
    }
    assert "skill-a" not in skill_ids
    assert "skill-a" in result.plan.skipped_known


def test_feasibility_unrealistic():
    # Tiny budget via very low hours + short deadline vs large content
    snap = _snapshot(many_lessons=True)
    for lesson in snap.lessons:
        lesson.estimated_minutes = 500
    result = generate_roadmap(
        _profile(weekly_hours_token="lt-3", target_deadline_token="1-3"),
        snap,
        seed=1,
    )
    assert result.ok is False
    assert result.error_code == ErrorCodes.ROADMAP_DEADLINE_UNREALISTIC
    assert result.feasibility is not None
    assert result.feasibility.earliest_realistic_weeks is not None


def test_replan_preserves_completed():
    snap = _snapshot()
    first = generate_roadmap(_profile(), snap, seed=11)
    assert first.ok and first.plan
    prior = first.plan.model_dump()
    completed_phase = first.plan.phases[0].key
    completed_skills = [
        m.skill_node_id for m in first.plan.phases[0].milestones
    ]
    state = ReplanCurrentState(
        roadmap_id="rm-1",
        completed_skill_node_ids=completed_skills,
        completed_phase_keys=[completed_phase],
        trigger="pace",
        prior_plan=prior,
    )
    replanned = replan_roadmap(_profile(), snap, seed=11, current_state=state)
    assert replanned.ok and replanned.plan
    preserved = [
        p for p in replanned.plan.phases if p.key == completed_phase
    ]
    assert preserved
    assert all(
        lesson.status == "completed"
        for m in preserved[0].milestones
        for lesson in m.lessons
    )


def test_budget_math():
    budget = calculate_study_budget(_profile(), 12)
    assert budget.weekly_hours == 6.5
    assert budget.budget_minutes > 0
    assert budget.target_weekly_load < budget.weekly_minutes
