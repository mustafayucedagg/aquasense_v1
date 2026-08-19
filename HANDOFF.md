# AquaSense (LYDIA) — Handoff Notes

For whichever Claude picks this up next. Written 2026-08-18, right after adding 5 new features on top of the original leak-detection MVP.

## What this project is

Water-leak-detection demo: FastAPI backend (`backend/`) running an XGBoost model over a Hanoi EPANET topology, single-file Streamlit frontend (`frontend/aquasense_app.py`, ~2700 lines). App name in the UI is **LYDIA**. Deployed on Render; frontend and backend are separate services talking over HTTP (`API_URL` env var on the frontend).

## What was added (commit `2c02103`, "new features")

Five features, on top of the existing `/predict` leak-detection flow (untouched):

1. **AI Recommendations** — after a leak alarm, a button on Live Monitoring calls the backend for a structured intervention plan: priority, which field team to dispatch, which valves to close, estimated water loss now vs. after a 24h delay, immediate steps.
2. **Work Order Management** — incidents become tracked work orders (SQLite-backed) with a lifecycle: `created → assigned → in_progress → resolved → closed`. Full CRUD + event timeline.
3. **Water Efficiency Score** — single 0–100 score (+ letter grade) combining leak management (35%), pressure balance (25%), energy efficiency (20%), operational efficiency (20%).
4. **AI Water Advisor** — chat page; sends a compressed live-system snapshot as context to Claude on every question.
5. **Consumption Analytics** — expected-vs-actual daily consumption with seeded anomaly windows (a "leak" window and a "meter under-registration" window), zone breakdown, hourly profile.

### New/changed files

- `backend/database.py` — **new**. SQLite work-order store (`aquasense.db`, path overridable via `AQUASENSE_DB_PATH`). Has its own `APIRouter` mounted in `main.py`. Endpoints: `POST/GET /workorders`, `GET /workorders/{id}`, `PATCH /workorders/{id}`, `GET /workorders/stats`, `POST /workorders/{id}/events`. Lifecycle transitions are validated server-side — illegal jumps return `409`.
- `backend/ai.py` — **new**. Wraps the `anthropic` SDK (model `claude-opus-5`). `generate_recommendation()` uses structured JSON-schema output; `chat_advisor()` uses `effort: low`. **Both gracefully fall back when `ANTHROPIC_API_KEY` is unset**: recommendations degrade to a deterministic rule-based plan (still `200 OK`, with `"ai_generated": false"`), chat returns `503`.
- `backend/main.py` — now imports and mounts both new routers, calls `database.init_db()` in the `lifespan` context. `/predict`, `/health`, `/reset_buffer` unchanged.
- `backend/requirements.txt` — added `anthropic`.
- `frontend/aquasense_app.py` — added 4 sidebar pages (Work Orders, Consumption Analytics, Efficiency Score, AI Advisor) and extended Live Monitoring with the recommendation button + "Create Work Order" button. Still one file, same CSS/design-token conventions as before — search for `PAGE: WORK ORDERS`, `PAGE: CONSUMPTION ANALYTICS`, `PAGE: EFFICIENCY SCORE`, `PAGE: AI ADVISOR` section banners.
- `.gitignore` — added (ignores `__pycache__`, the sqlite db files, `.env`).

## How to run locally

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
pip install -r requirements.txt
API_URL=http://localhost:8000 streamlit run aquasense_app.py
```

**macOS gotcha:** `xgboost` needs `libomp` (OpenMP runtime), which isn't bundled. If you see `Library not loaded: @rpath/libomp.dylib` on import, run `brew install libomp`.

## Env vars

| Var | Where | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | backend | Enables real Claude calls. Unset → rule-based fallback + advisor disabled (no crash either way). |
| `AQUASENSE_DB_PATH` | backend | Optional. SQLite path, defaults to `backend/aquasense.db`. |
| `API_URL` | frontend | Backend base URL. Defaults to `http://localhost:8000`. |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | frontend | Pre-existing, unrelated to this work — dispatch notifications. |

On Render's free tier the backend disk is **ephemeral** — the SQLite DB resets on every redeploy/restart. Acceptable for demo purposes; `AQUASENSE_DB_PATH` is there so a Persistent Disk mount can fix it later without code changes.

## What's verified vs. not

- ✅ Full work-order lifecycle (HTTP + through the Streamlit UI), invalid-transition 409, note/timeline events, Telegram integration on auto-created orders.
- ✅ All 10 pages render cleanly — tested headlessly via `streamlit.testing.v1.AppTest` (no browser needed; good tool for regressions here, see snippet below).
- ✅ AI fallback path (no key set): recommendation endpoint returns a sane rule-based plan, chat returns 503, UI shows clear "not configured" states.
- ✅ `/predict` regression — unchanged, still returns correct shape.
- ❌ **The live Claude path (with a real `ANTHROPIC_API_KEY`) was never exercised** — no credentials were available in that session. If something's broken there, start by hitting `/ai/recommendation` and `/ai/chat` directly with `curl` once a key is set, before touching the frontend.

### Quick headless smoke test pattern (no browser)

```python
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("frontend/aquasense_app.py", default_timeout=60)
at.run()
at.sidebar.radio[0].set_value("AI Advisor").run()
assert not at.exception
```
Backend must be running on `localhost:8000` for pages that call it (Work Orders, Efficiency Score, AI Advisor all hit the API on load).

## If something's broken — where to look first

- **Work order stuck / weird status:** check `VALID_TRANSITIONS` in `backend/database.py` — the state machine is intentionally strict (e.g. `assigned` can only go to `in_progress` or back to `created`, not straight to `resolved`).
- **AI recommendation missing/blank fields:** the JSON schema is `RECOMMENDATION_SCHEMA` in `backend/ai.py`; if Claude's response doesn't validate against it the API call raises and you silently get the rule-based fallback instead (check backend logs for the exception type — swallowed into the `reason` field, but not the traceback).
- **Chat not working:** `GET /ai/status` tells you `anthropic_configured` — the frontend caches this in `st.session_state.ai_status` and only refetches on "Refresh Connection" in the sidebar, so a stale cache after setting the key mid-session is a common false alarm.
- **Frontend session-state weirdness (chat losing messages, recommendation re-fetching every rerun):** all AI-related state is cached in `st.session_state` (`advisor_messages`, `ai_recommendations` keyed by node id) specifically to survive Streamlit's rerun-on-every-interaction model. If you add new interactive elements near these, make sure you're not accidentally clearing that state.
- **SQLite locking under concurrent requests:** WAL mode is on, connections are short-lived per-request. Fine for single-worker `uvicorn`; don't add `--workers > 1` without revisiting `backend/database.py`'s connection handling.

## Original plan file

Full original design doc (architecture rationale, prompt design, sequencing) is at `/Users/erenzeytun/.claude/plans/piped-chasing-cocke.md` if you need the "why" behind a decision, not just the "what."
