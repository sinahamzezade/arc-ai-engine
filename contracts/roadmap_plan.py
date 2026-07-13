from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ExplanationTrace(BaseModel):
    skill_node: str
    chosen_lesson_version: str | None = None
    reason: str
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    alternatives_considered: int = 0


class SelectedLesson(BaseModel):
    source_template_id: str
    source_version_id: str | None = None
    skill_node_id: str
    title: str
    mission_name: str | None = None
    lesson_type: str
    estimated_minutes: int
    difficulty: str = "beginner"
    xp_reward: int = 20
    reward_class: str = "standard"
    resource_id: str | None = None
    status: Literal["locked", "available", "completed"] = "locked"
    content_outline: dict[str, Any] = Field(default_factory=dict)
    week_index: int | None = None
    explanation: ExplanationTrace | None = None


class SelectedMilestone(BaseModel):
    skill_node_id: str
    title: str
    type: str = "skill"
    compress: bool = False
    order_index: int = 0
    xp_reward: int = 50
    lessons: list[SelectedLesson] = Field(default_factory=list)


class SelectedPhase(BaseModel):
    key: str
    title: str
    tech_stack_id: str | None = None
    tech_stack_slug: str | None = None
    order_index: int = 0
    locked: bool = True
    week_type: Literal["learning", "review", "assessment", "project", "buffer"] = "learning"
    milestones: list[SelectedMilestone] = Field(default_factory=list)


class FeasibilityResult(BaseModel):
    feasible: bool
    code: str | None = None
    message: str | None = None
    earliest_realistic_weeks: int | None = None
    earliest_realistic_date: str | None = None


class RoadmapPlan(BaseModel):
    title: str
    description: str
    primary_role_slug: str
    recipe_id: str
    timeline_weeks: int
    weekly_hours_target: float
    estimated_weeks: int
    estimated_completion_date: str | None = None
    engine_version: int
    seed: int
    content_version: str
    phases: list[SelectedPhase] = Field(default_factory=list)
    skipped_known: list[str] = Field(default_factory=list)
    explanations: list[ExplanationTrace] = Field(default_factory=list)
    schedule_meta: dict[str, Any] = Field(default_factory=dict)


class PlanResponse(BaseModel):
    ok: bool = True
    plan: RoadmapPlan | None = None
    feasibility: FeasibilityResult | None = None
    error_code: str | None = None
    error_message: str | None = None
