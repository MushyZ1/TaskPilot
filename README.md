# TaskPilot

TaskPilot is an AI-powered task manager. Use it two ways:

* **Natural language** - "add buy groceries for tomorrow", "mark the report as done".
* **REST API** - conventional CRUD endpoints for tasks.

The language model never touches your data directly. It only proposes a
*structured decision* (`create_task`, `update_task`, ...), which the agent
validates before executing against the task store.

## Architecture

```
 CLI (main.py) ──┐
                 ├──> agent.py ──> llm_provider.py ──> Ollama / OpenAI-compatible API
 FastAPI (api.py)┘       │
                         └──> task_store.py (in-memory)
```

| File | Responsibility |
|------|----------------|
| `api.py` | FastAPI app: task CRUD + `/api/agent/execute` |
| `agent.py` | Prompt building, LLM call, decision validation, execution |
| `llm_provider.py` | Provider abstraction (Ollama, OpenAI-compatible) |
| `task_store.py` | Thread-safe in-memory store |
| `models.py` | Pydantic models (tasks, requests, LLM decision schema) |
| `main.py` | Interactive CLI |

### Safeguards around the LLM

1. **Schema-constrained output** - the model must return JSON matching `AgentDecision`; anything else becomes a clean `502`.
2. **Weekday check** - if the user says "Friday" and the model returns a Monday date, the agent retries once with corrective feedback, then asks the user instead of guessing.
3. **ID check** - `update`/`delete`/`complete` with an unknown (hallucinated) task ID results in a clarification question, never a silent no-op.
4. **Past-date and missing-field checks** - e.g. a create with no title, or an update that changes nothing.
5. **Clarification loop** - ambiguous requests return `needs_clarification: true`; the client sends the earlier turns back via `history`.

## Getting started

Requires Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

**Option A - local model (default):**

```bash
ollama pull qwen3:4b
```

**Option B - hosted model:** set `LLM_PROVIDER=openai`, `LLM_API_KEY`, `LLM_MODEL` (and optionally `LLM_BASE_URL`) in `.env`.

Run the API (docs at <http://localhost:8000/docs>) or the CLI:

```bash
uvicorn api:app --reload
python main.py
```

### Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_PROVIDER` | `ollama` | `ollama` or `openai` |
| `OLLAMA_MODEL` | `qwen3:4b` | Ollama model name |
| `LLM_API_KEY` / `LLM_MODEL` | - | Required for `openai` |
| `LLM_BASE_URL` | OpenAI | Any OpenAI-compatible endpoint |
| `LLM_TIMEOUT` | `60` | Seconds, `openai` provider |

## API reference

| Method | Path | Description | Success |
|--------|------|-------------|---------|
| GET | `/health` | Liveness check | 200 |
| GET | `/api/tasks` | List tasks | 200 |
| GET | `/api/tasks/{id}` | Get one task | 200 / 404 |
| POST | `/api/tasks` | Create task | 201 / 422 |
| PATCH | `/api/tasks/{id}` | Partial update | 200 / 400 / 404 / 422 |
| DELETE | `/api/tasks/{id}` | Delete task | 204 / 404 |
| POST | `/api/agent/execute` | Natural-language request | 200 / 422 / 502 |

Full request/response samples are in [EXAMPLES.md](EXAMPLES.md).

Quick try:

```bash
curl -X POST localhost:8000/api/agent/execute \
  -H 'Content-Type: application/json' \
  -d '{"user_request": "Add buy groceries for tomorrow"}'
```

## Testing

```bash
pytest                          # 35 tests, no LLM or network required

pip install pytest-cov          # only needed for the coverage report
pytest --cov=. --cov-report=term-missing

pip install pyright             # optional static type check
pyright .
```

The LLM is replaced by a scripted fake (`tests/conftest.py`), so tests are
fast and deterministic. They cover the store, API (success, 404, 422, 400,
502), weekday-retry logic, hallucinated IDs, past dates, malformed LLM
output and the clarification flow. Current coverage is ~87%; the uncovered
code is the real provider clients and the CLI loop.

## Deployment (Render)

`render.yaml` is preconfigured. Set `LLM_API_KEY` and `LLM_MODEL` in the
dashboard. The free tier cannot host Ollama, so deployment uses the hosted provider.

## Known limitations

* **Storage is in-memory** - tasks are lost on restart, and with multiple workers each would have its own list. Replace `task_store.py` with a database for production.
* **No authentication or per-user tasks.**
* `PATCH` cannot *clear* a due date (`null` means "unchanged").
* The agent handles one action per message ("add X and delete Y" is not supported).
* Small local models can misjudge dates; the weekday check covers named weekdays but not every relative phrase ("in three weeks").

## License

See [LICENSE](LICENSE).
