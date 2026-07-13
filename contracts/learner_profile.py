from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LearnerProfile(BaseModel):
    user_id: str
    goal_id: str
    goal_revision: str
    target_roles: list[str] = Field(default_factory=list)
    motivation: list[str] = Field(default_factory=list)
    current_profession: str | None = None
    known_skills: list[str] = Field(default_factory=list)
    confidence: str | None = None
    weekly_hours_token: str | None = None
    availability_days: list[str] = Field(default_factory=list)
    availability_times: list[str] = Field(default_factory=list)
    target_deadline_token: str | None = None
    learning_styles: list[str] = Field(default_factory=list)
    quit_reasons: list[str] = Field(default_factory=list)
    language: str = "en"
    interview_signals: dict[str, Any] = Field(default_factory=dict)
    # Proven mastered skill node IDs (diagnostic or prior roadmap history)
    proven_mastered_skill_ids: list[str] = Field(default_factory=list)


class PlanRequest(BaseModel):
    profile: LearnerProfile
    snapshot: dict[str, Any]  # validated as ContentSnapshot in handler
    seed: int


class ReplanCurrentState(BaseModel):
    roadmap_id: str
    completed_lesson_template_ids: list[str] = Field(default_factory=list)
    completed_skill_node_ids: list[str] = Field(default_factory=list)
    completed_phase_keys: list[str] = Field(default_factory=list)
    current_week: int = 1
    trigger: str = "manual"
    prior_plan: dict[str, Any] | None = None


class ReplanRequest(BaseModel):
    profile: LearnerProfile
    snapshot: dict[str, Any]
    seed: int
    current_state: ReplanCurrentState
