from __future__ import annotations

from config import ENGINE_VERSION
from contracts.content_snapshot import ContentSnapshot
from contracts.learner_profile import LearnerProfile
from contracts.roadmap_plan import FeasibilityResult, PlanResponse, RoadmapPlan
from engine.dependency_resolver import (
    build_skill_graph,
    prerequisite_closure,
    topological_order,
)
from engine.errors import EngineError, ErrorCodes
from engine.explainer import collect_explanations
from engine.phase_builder import build_learning_phases
from engine.profile_loader import load_profile
from engine.project_selector import place_projects_and_assessments
from engine.scheduler import (
    assign_weeks,
    insert_special_weeks,
    size_to_budget,
    sum_minutes,
)
from engine.skill_gap import calculate_skill_gap
from engine.study_budget import calculate_study_budget, estimate_completion


def generate_roadmap(
    profile: LearnerProfile,
    snapshot: ContentSnapshot,
    seed: int,
) -> PlanResponse:
    try:
        profile = load_profile(profile)
        recipe = snapshot.recipe
        if not recipe or not recipe.id:
            raise EngineError(
                ErrorCodes.ROADMAP_ROLE_NOT_FOUND,
                "Role recipe missing from snapshot",
            )

        graph = build_skill_graph(snapshot)

        required = set(recipe.required_skill_node_ids or [])
        optional = set(recipe.optional_skill_node_ids or [])

        # If recipe lists no explicit skill IDs, take all skills in blueprint stacks
        if not required:
            blueprint_slugs = {
                slug
                for bp in recipe.phase_blueprint
                for slug in bp.tech_stack_slugs
            }
            required = {
                s.id
                for s in snapshot.skills
                if s.tech_stack_slug in blueprint_slugs
            }

        try:
            closed = prerequisite_closure(graph, required | optional)
        except EngineError:
            raise
        except Exception as exc:
            raise EngineError(
                ErrorCodes.ROADMAP_PREREQUISITE_FAILED,
                str(exc),
            ) from exc

        # Ensure all closed nodes exist
        skill_ids = {s.id for s in snapshot.skills}
        missing = closed - skill_ids
        if missing:
            raise EngineError(
                ErrorCodes.ROADMAP_CONTENT_NOT_FOUND,
                f"Snapshot missing skill nodes: {', '.join(sorted(missing)[:5])}",
            )

        gap = calculate_skill_gap(profile, snapshot.skills, closed)
        ordered = topological_order(graph, gap.active_ids)
        budget = calculate_study_budget(profile, recipe.default_timeline_weeks)

        phases, _ = build_learning_phases(
            snapshot=snapshot,
            profile=profile,
            gap=gap,
            ordered_skills=ordered,
            budget=budget,
            seed=seed,
        )

        if not phases:
            raise EngineError(
                ErrorCodes.ROADMAP_CONTENT_NOT_FOUND,
                "Skill graph returned no phases for recipe",
            )

        phases = size_to_budget(phases, budget)
        required_minutes = sum_minutes(phases)

        # Feasibility: required content must fit before deadline horizon
        if required_minutes > budget.budget_minutes:
            earliest, earliest_date = estimate_completion(
                required_minutes, budget, special_weeks=0
            )
            return PlanResponse(
                ok=False,
                feasibility=FeasibilityResult(
                    feasible=False,
                    code=ErrorCodes.ROADMAP_DEADLINE_UNREALISTIC,
                    message=(
                        f"Required content ({required_minutes}m) exceeds "
                        f"budget ({budget.budget_minutes}m)"
                    ),
                    earliest_realistic_weeks=earliest,
                    earliest_realistic_date=earliest_date,
                ),
                error_code=ErrorCodes.ROADMAP_DEADLINE_UNREALISTIC,
                error_message="Required content cannot fit before deadline",
            )

        phases = place_projects_and_assessments(
            phases,
            assessments=snapshot.assessments,
            projects=snapshot.projects,
        )
        phases, special = insert_special_weeks(phases, budget)
        phases = assign_weeks(phases, budget)

        estimated_weeks, completion_date = estimate_completion(
            sum_minutes(phases), budget, special
        )
        explanations = collect_explanations(phases)

        plan = RoadmapPlan(
            title=f"{recipe.title} Path",
            description=f"Personalized path for {recipe.title}",
            primary_role_slug=recipe.target_role_slug,
            recipe_id=recipe.id,
            timeline_weeks=budget.horizon_weeks,
            weekly_hours_target=budget.weekly_hours,
            estimated_weeks=estimated_weeks,
            estimated_completion_date=completion_date,
            engine_version=ENGINE_VERSION,
            seed=seed,
            content_version=snapshot.content_version,
            phases=phases,
            skipped_known=gap.skipped_known_ids,
            explanations=explanations,
            schedule_meta={
                "budget_minutes": budget.budget_minutes,
                "target_weekly_load": budget.target_weekly_load,
                "pace_factor": budget.pace_factor,
                "buffer_weeks": budget.buffer_weeks,
                "special_weeks": special,
                "required_minutes": required_minutes,
            },
        )
        return PlanResponse(
            ok=True,
            plan=plan,
            feasibility=FeasibilityResult(feasible=True),
        )
    except EngineError as err:
        return PlanResponse(
            ok=False,
            error_code=err.code,
            error_message=err.message,
            feasibility=FeasibilityResult(
                feasible=False,
                code=err.code,
                message=err.message,
                **(
                    {
                        "earliest_realistic_weeks": err.details.get(
                            "earliest_realistic_weeks"
                        ),
                        "earliest_realistic_date": err.details.get(
                            "earliest_realistic_date"
                        ),
                    }
                    if err.details
                    else {}
                ),
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return PlanResponse(
            ok=False,
            error_code=ErrorCodes.ROADMAP_GENERATION_FAILED,
            error_message=str(exc),
        )
