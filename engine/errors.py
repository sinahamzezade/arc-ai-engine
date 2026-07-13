from __future__ import annotations


class ErrorCodes:
    ROADMAP_ROLE_NOT_FOUND = "ROADMAP_ROLE_NOT_FOUND"
    ROADMAP_GRAPH_INVALID = "ROADMAP_GRAPH_INVALID"
    ROADMAP_PREREQUISITE_FAILED = "ROADMAP_PREREQUISITE_FAILED"
    ROADMAP_CONTENT_NOT_FOUND = "ROADMAP_CONTENT_NOT_FOUND"
    ROADMAP_DEADLINE_UNREALISTIC = "ROADMAP_DEADLINE_UNREALISTIC"
    ROADMAP_GENERATION_FAILED = "ROADMAP_GENERATION_FAILED"
    ROADMAP_ENGINE_VERSION_CONFLICT = "ROADMAP_ENGINE_VERSION_CONFLICT"
    ROADMAP_REPLAN_CONFLICT = "ROADMAP_REPLAN_CONFLICT"


class EngineError(Exception):
    def __init__(self, code: str, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
