from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from config import ENGINE_VERSION
from contracts.content_snapshot import ContentSnapshot
from contracts.learner_profile import PlanRequest, ReplanRequest
from contracts.roadmap_plan import PlanResponse
from engine.generator import generate_roadmap
from engine.replanner import replan_roadmap

app = FastAPI(title="Arc Roadmap Engine", version=str(ENGINE_VERSION))


@app.get("/v1/health")
def health() -> dict:
    return {"status": "ok", "engineVersion": ENGINE_VERSION}


@app.post("/v1/plan", response_model=PlanResponse)
def plan(body: PlanRequest) -> PlanResponse:
    try:
        snapshot = ContentSnapshot.model_validate(body.snapshot)
    except ValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "ROADMAP_GENERATION_FAILED",
                "message": f"Invalid snapshot: {exc.errors()[0]}",
            },
        ) from exc

    result = generate_roadmap(body.profile, snapshot, body.seed)
    if not result.ok and result.error_code == "ROADMAP_DEADLINE_UNREALISTIC":
        # Feasibility is a first-class 200 result (not a crash)
        return result
    return result


@app.post("/v1/replan", response_model=PlanResponse)
def replan(body: ReplanRequest) -> PlanResponse:
    try:
        snapshot = ContentSnapshot.model_validate(body.snapshot)
    except ValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "ROADMAP_GENERATION_FAILED",
                "message": f"Invalid snapshot: {exc.errors()[0]}",
            },
        ) from exc

    return replan_roadmap(
        body.profile, snapshot, body.seed, body.current_state
    )
