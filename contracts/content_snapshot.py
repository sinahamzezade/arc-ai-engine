from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PhaseBlueprint(BaseModel):
    key: str
    title: str
    tech_stack_slugs: list[str] = Field(default_factory=list)
    required: bool = True
    include_if_confidence_gte: str | None = None


class RoleRecipeSnapshot(BaseModel):
    id: str
    target_role_slug: str
    title: str
    default_timeline_weeks: int = 24
    content_version: str = "1"
    required_skill_node_ids: list[str] = Field(default_factory=list)
    optional_skill_node_ids: list[str] = Field(default_factory=list)
    phase_blueprint: list[PhaseBlueprint] = Field(default_factory=list)
    minimum_assessment_rules: dict[str, Any] = Field(default_factory=dict)


class SkillNodeSnapshot(BaseModel):
    id: str
    slug: str
    title: str
    tech_stack_id: str | None = None
    tech_stack_slug: str | None = None
    tags: list[str] = Field(default_factory=list)
    prerequisite_skill_ids: list[str] = Field(default_factory=list)
    estimated_mastery_minutes: int = 60
    difficulty: str = "beginner"
    order_hint: int = 0
    content_version: str = "1"


class LessonCandidate(BaseModel):
    id: str
    skill_node_id: str
    slug: str
    title: str
    mission_name_template: str | None = None
    lesson_type: str
    estimated_minutes: int = 20
    difficulty: str = "beginner"
    xp_reward: int = 20
    reward_class: str = "standard"
    learning_style_tags: list[str] = Field(default_factory=list)
    scheduling_tags: list[str] = Field(default_factory=list)
    language: str = "en"
    order_hint: int = 0
    default_resource_id: str | None = None
    published_version_id: str | None = None
    content_outline: dict[str, Any] = Field(default_factory=dict)
    status: str = "published"
    quality_score: float = 0.8
    content_version: str = "1"


class TechStackSnapshot(BaseModel):
    id: str
    slug: str
    title: str


class ResourceSnapshot(BaseModel):
    id: str
    title: str | None = None


class ContentSnapshot(BaseModel):
    content_version: str
    recipe: RoleRecipeSnapshot
    stacks: list[TechStackSnapshot] = Field(default_factory=list)
    skills: list[SkillNodeSnapshot] = Field(default_factory=list)
    lessons: list[LessonCandidate] = Field(default_factory=list)
    resources: list[ResourceSnapshot] = Field(default_factory=list)
    assessments: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
