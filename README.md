# Arc Roadmap Engine

Stateless Python planner (FastAPI + NetworkX + NumPy). NestJS owns persistence/queue.

## Endpoints

- `GET /v1/health` → `{ status, engineVersion }`
- `POST /v1/plan` → `{ profile, snapshot, seed }` → `PlanResponse`
- `POST /v1/replan` → `{ profile, snapshot, seed, current_state }` → `PlanResponse`

## Local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8080
pytest
```

## Docker

Built from monorepo via `arc-backend/docker-compose.dev.yml` service `roadmap-engine`.
