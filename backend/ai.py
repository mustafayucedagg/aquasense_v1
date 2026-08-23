import os
import json
import math
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from google import genai
    from google.genai import types as genai_types
    GEMINI_SDK_AVAILABLE = True
except ImportError:
    GEMINI_SDK_AVAILABLE = False

# Model alias, not a pinned version - Google points this at whatever their current
# "Flash" tier model is, so this deployment doesn't need a code change every time
# Google retires a dated model name (e.g. gemini-2.5-flash is being retired
# October 2026; gemini-flash-latest avoids that churn).
MODEL = "gemini-3.5-flash-lite"

FIELD_TEAMS = [
    "Team Alpha - Pipe Repair",
    "Team Bravo - Valve & Isolation Ops",
    "Team Charlie - Metering & Detection",
]

_client = None


def gemini_configured() -> bool:
    """True if the Gemini SDK is installed and an API key is present.
    Accepts either GEMINI_API_KEY or GOOGLE_API_KEY (the SDK's own default env var),
    checked in that order so a Render deploy only needs to set one of them."""
    if not GEMINI_SDK_AVAILABLE:
        return False
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


def anthropic_configured() -> bool:
    """Kept for backward compatibility with any older caller still expecting this
    name - it now reflects whichever AI provider is actually configured (Gemini)."""
    return gemini_configured()


def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        _client = genai.Client(api_key=api_key)
    return _client


class AIUnavailableError(Exception):
    pass


RECOMMENDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
        "summary": {"type": "string"},
        "recommended_team": {"type": "string", "enum": FIELD_TEAMS},
        "team_rationale": {"type": "string"},
        "valves_to_close": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "link_id": {"type": "integer"},
                    "reason": {"type": "string"},
                },
                "required": ["link_id", "reason"],
            },
        },
        "estimated_loss_m3_per_hour": {"type": "number"},
        "estimated_loss_24h_delay_m3": {"type": "number"},
        "immediate_steps": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "priority", "summary", "recommended_team", "team_rationale",
        "valves_to_close", "estimated_loss_m3_per_hour",
        "estimated_loss_24h_delay_m3", "immediate_steps",
    ],
}

RECOMMENDATION_SYSTEM = """You are the senior water-network operations advisor for LYDIA, \
a municipal leak-detection platform. When a leak alarm is raised, you produce a concrete \
intervention plan as JSON.

Field teams available (choose exactly one):
- Team Alpha - Pipe Repair: excavation and pipe replacement; best for confirmed single-point bursts.
- Team Bravo - Valve & Isolation Ops: valve operations and zone isolation; best when multiple \
pipe links must be closed or the leak point is uncertain.
- Team Charlie - Metering & Detection: acoustic detection and metering; best for low-probability \
or ambiguous signals.

Isolation rule: to isolate node N, close the valves on every pipe link incident to N. \
The incident links for the alarmed node are provided in the request as connected_links - \
only recommend closing links from that list.

Water-loss estimation: leak outflow scales roughly with the square root of line pressure. \
A typical service-line leak loses 1-6 m3/h; a main burst can lose considerably more. \
Estimate the current loss rate from pressure and leak probability, and multiply by 24 for \
the volume lost if intervention is delayed a full day. Be conservative and round sensibly.

Write 3-6 immediate_steps as short imperative sentences. Respond in English."""

ADVISOR_SYSTEM = """You are the LYDIA Water Advisor, a natural-language assistant embedded in \
a municipal water-network monitoring platform. You explain what is happening in the network, \
interpret anomalies (pressure drops, elevated night flow, demand deviations, zone losses), \
and recommend operational actions.

Background you may rely on: the platform's leak detector is an XGBoost classifier over 161 \
features - 31 node pressures, 34 link flows, 32 node demands, hour-of-day and a night flag \
(02:00-04:00), plus 3-sample rolling means and first differences of each pressure. Elevated \
flow during the night window is a strong leak indicator because legitimate demand is minimal then. \
Normal operating pressure is 3.0-5.6 bar.

A LIVE SYSTEM CONTEXT block with the current network snapshot (alarms, zone summaries, open \
work orders, efficiency score) is provided in this conversation. Base factual claims only on \
that context; when something is not in the context, say the data is not available. Answer in \
concise English and keep responses focused."""

# Gemini 3.5 Flash-Lite already runs with thinking disabled by default for speed/cost,
# so no explicit thinking_config is needed here (and passing an unsupported config
# shape is a common source of 400/500 errors across Gemini model tiers - simplest to
# just not send it and let the model's own default behavior apply).


def rule_based_recommendation(ctx: dict, reason: str) -> dict:
    probability = float(ctx.get("leak_probability") or 0.5)
    pressure = float(ctx.get("pressure_bar") or 3.0)
    links = ctx.get("connected_links") or []
    node_id = ctx.get("node_id")

    if probability >= 0.9:
        priority = "critical"
    elif probability >= 0.75:
        priority = "high"
    elif probability >= 0.5:
        priority = "medium"
    else:
        priority = "low"

    team = FIELD_TEAMS[1] if len(links) > 2 else FIELD_TEAMS[0]
    loss_per_hour = round(2.2 * math.sqrt(max(pressure, 0.5)) * probability, 1)

    return {
        "available": False,
        "ai_generated": False,
        "reason": reason,
        "recommendation": {
            "priority": priority,
            "summary": (
                f"Suspected leak at Node {node_id} (probability {probability:.0%}). "
                f"Isolate the node and dispatch a field team for inspection."
            ),
            "recommended_team": team,
            "team_rationale": (
                "Multiple incident pipe links require coordinated valve isolation."
                if len(links) > 2
                else "Single-point intervention; pipe repair crew can isolate and fix directly."
            ),
            "valves_to_close": [
                {"link_id": l["link_id"], "reason": f"Isolates Node {node_id}"} for l in links
            ],
            "estimated_loss_m3_per_hour": loss_per_hour,
            "estimated_loss_24h_delay_m3": round(loss_per_hour * 24, 0),
            "immediate_steps": [
                f"Notify {team} and share the node location and address.",
                f"Close the {len(links)} valve(s) on the pipe links incident to Node {node_id}.",
                "Verify pressure recovery in neighboring nodes after isolation.",
                "Inspect the isolated segment acoustically to pinpoint the leak.",
                "Log findings and update the work order status.",
            ],
        },
    }


def generate_recommendation(ctx: dict) -> dict:
    if not gemini_configured():
        return rule_based_recommendation(
            ctx, "GEMINI_API_KEY not set - showing rule-based fallback"
        )
    try:
        response = get_client().models.generate_content(
            model=MODEL,
            contents=json.dumps(ctx),
            config=genai_types.GenerateContentConfig(
                system_instruction=RECOMMENDATION_SYSTEM,
                max_output_tokens=700,
                response_mime_type="application/json",
                response_json_schema=RECOMMENDATION_SCHEMA,
            ),
        )
        return {
            "available": True,
            "ai_generated": True,
            "model": MODEL,
            "recommendation": json.loads(response.text),
        }
    except Exception as exc:
        return rule_based_recommendation(
            ctx, f"AI call failed ({type(exc).__name__}: {exc}) - showing rule-based fallback"
        )


PRIORITY_SCHEMA = {
    "type": "object",
    "properties": {
        "ranking": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string"},
                    "rank": {"type": "integer"},
                    "urgency_score": {"type": "number"},
                    "rationale": {"type": "string"},
                },
                "required": ["incident_id", "rank", "urgency_score", "rationale"],
            },
        },
    },
    "required": ["ranking"],
}

PRIORITY_SYSTEM = """You are the incident triage advisor for LYDIA, a water-network monitoring \
platform. You receive a list of concurrent open incidents (leak alarms / work orders) and must \
rank them by urgency, most urgent first.

Weigh these factors: leak probability (higher = more urgent), current severity label, estimated \
water-loss rate if known, how long the incident has been open (older unresolved incidents should \
generally rise in priority), and whether it is still unassigned. An incident already 'in_progress' \
is being handled and should rank below untouched 'created' incidents of similar severity, unless \
its own severity is critical.

Return a full ranking of every incident_id given, each with a 0-100 urgency_score and a short \
rationale (max ~20 words). Respond in English."""


def rule_based_priority(incidents: list, reason: str) -> dict:
    """Deterministic scoring: weights probability, severity, status and age."""
    severity_weight = {"critical": 40, "high": 28, "medium": 16, "low": 6}
    status_penalty = {"created": 0, "assigned": -3, "in_progress": -10,
                       "resolved": -100, "closed": -100}

    scored = []
    now = datetime.now()
    for inc in incidents:
        probability = float(inc.get("probability") or 0.5)
        severity = inc.get("severity", "medium")
        status = inc.get("status", "created")
        created_at = inc.get("created_at")
        age_hours = 0.0
        if created_at:
            try:
                age_hours = (now - datetime.fromisoformat(created_at)).total_seconds() / 3600
            except ValueError:
                pass
        age_bonus = min(age_hours * 1.5, 15)
        score = (
            probability * 45
            + severity_weight.get(severity, 16)
            + status_penalty.get(status, 0)
            + age_bonus
        )
        score = max(0.0, min(100.0, score))
        scored.append((inc["id"], score, severity, status, age_hours))

    scored.sort(key=lambda t: t[1], reverse=True)

    ranking = []
    for rank, (inc_id, score, severity, status, age_hours) in enumerate(scored, start=1):
        ranking.append({
            "incident_id": inc_id,
            "rank": rank,
            "urgency_score": round(score, 1),
            "rationale": (
                f"{severity} severity, status '{status}', open {age_hours:.1f}h - "
                f"scored on probability + severity + status + age."
            ),
        })

    return {
        "available": False,
        "ai_generated": False,
        "reason": reason,
        "ranking": ranking,
    }


def generate_priority_ranking(incidents: list) -> dict:
    if not incidents:
        return {"available": True, "ai_generated": False, "reason": "No open incidents", "ranking": []}
    if not gemini_configured():
        return rule_based_priority(incidents, "GEMINI_API_KEY not set - showing rule-based fallback")
    try:
        payload = {"incidents": incidents}
        response = get_client().models.generate_content(
            model=MODEL,
            contents=json.dumps(payload),
            config=genai_types.GenerateContentConfig(
                system_instruction=PRIORITY_SYSTEM,
                max_output_tokens=700,
                response_mime_type="application/json",
                response_json_schema=PRIORITY_SCHEMA,
            ),
        )
        parsed = json.loads(response.text)
        return {
            "available": True,
            "ai_generated": True,
            "model": MODEL,
            "ranking": parsed["ranking"],
        }
    except Exception as exc:
        return rule_based_priority(
            incidents, f"AI call failed ({type(exc).__name__}) - showing rule-based fallback"
        )


def _to_gemini_contents(messages: list) -> list:
    """Converts the Anthropic-shaped {role, content} messages this API has always
    accepted from the frontend into Gemini's {role, parts: [{text}]} contents format.
    Gemini uses 'model' instead of 'assistant' for the assistant role."""
    contents = []
    for m in messages:
        role = "model" if m.get("role") == "assistant" else "user"
        text = m.get("content", "")
        contents.append(genai_types.Content(role=role, parts=[genai_types.Part(text=text)]))
    return contents


def chat_advisor(messages: list, context: dict) -> str:
    if not gemini_configured():
        raise AIUnavailableError(
            "AI Advisor requires GEMINI_API_KEY (or GOOGLE_API_KEY) on the backend service."
        )
    response = get_client().models.generate_content(
        model=MODEL,
        contents=_to_gemini_contents(messages[-20:]),
        config=genai_types.GenerateContentConfig(
            system_instruction=ADVISOR_SYSTEM + "\n\nLIVE SYSTEM CONTEXT:\n" + json.dumps(context),
            max_output_tokens=600,
        ),
    )
    return response.text or ""


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


class ChatRequest(BaseModel):
    messages: list
    context: dict = {}


@router.get("/ai/status")
def ai_status():
    configured = gemini_configured()
    return {
        "anthropic_configured": configured,
        "ai_configured": configured,
        "provider": "gemini",
        "model": MODEL,
        "field_teams": FIELD_TEAMS,
    }


@router.post("/ai/recommendation")
def ai_recommendation(ctx: dict):
    return generate_recommendation(ctx)


@router.post("/ai/priority")
def ai_priority(body: dict):
    incidents = body.get("incidents", [])
    return generate_priority_ranking(incidents)


@router.post("/ai/chat")
def ai_chat(body: ChatRequest):
    try:
        reply = chat_advisor(body.messages, body.context)
    except AIUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI call failed: {type(exc).__name__}")
    return {"reply": reply, "model": MODEL}
