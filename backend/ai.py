import os
import json
import math

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    import anthropic
    ANTHROPIC_SDK_AVAILABLE = True
except ImportError:
    ANTHROPIC_SDK_AVAILABLE = False

MODEL = "claude-opus-5"

FIELD_TEAMS = [
    "Team Alpha — Pipe Repair",
    "Team Bravo — Valve & Isolation Ops",
    "Team Charlie — Metering & Detection",
]

_client = None


def anthropic_configured() -> bool:
    return ANTHROPIC_SDK_AVAILABLE and bool(os.environ.get("ANTHROPIC_API_KEY"))


def get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
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
                "additionalProperties": False,
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
    "additionalProperties": False,
}

RECOMMENDATION_SYSTEM = f"""You are the senior water-network operations advisor for LYDIA, \
a municipal leak-detection platform. When a leak alarm is raised, you produce a concrete \
intervention plan as JSON.

Field teams available (choose exactly one):
- {FIELD_TEAMS[0]}: excavation and pipe replacement; best for confirmed single-point bursts.
- {FIELD_TEAMS[1]}: valve operations and zone isolation; best when multiple pipe links must \
be closed or the leak point is uncertain.
- {FIELD_TEAMS[2]}: acoustic detection and metering; best for low-probability or ambiguous signals.

Isolation rule: to isolate node N, close the valves on every pipe link incident to N. \
The incident links for the alarmed node are provided in the request as `connected_links` — \
only recommend closing links from that list.

Water-loss estimation: leak outflow scales roughly with the square root of line pressure. \
A typical service-line leak loses 1–6 m³/h; a main burst can lose considerably more. \
Estimate the current loss rate from pressure and leak probability, and multiply by 24 for \
the volume lost if intervention is delayed a full day. Be conservative and round sensibly.

Write 3–6 immediate_steps as short imperative sentences. Respond in English."""

ADVISOR_SYSTEM = """You are the LYDIA Water Advisor, a natural-language assistant embedded in \
a municipal water-network monitoring platform. You explain what is happening in the network, \
interpret anomalies (pressure drops, elevated night flow, demand deviations, zone losses), \
and recommend operational actions.

Background you may rely on: the platform's leak detector is an XGBoost classifier over 161 \
features — 31 node pressures, 34 link flows, 32 node demands, hour-of-day and a night flag \
(02:00–04:00), plus 3-sample rolling means and first differences of each pressure. Elevated \
flow during the night window is a strong leak indicator because legitimate demand is minimal then. \
Normal operating pressure is 3.0–5.6 bar.

A LIVE SYSTEM CONTEXT block with the current network snapshot (alarms, zone summaries, open \
work orders, efficiency score) is provided in this conversation. Base factual claims only on \
that context; when something is not in the context, say the data is not available. Answer in \
concise English and keep responses focused."""


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
    if not anthropic_configured():
        return rule_based_recommendation(
            ctx, "ANTHROPIC_API_KEY not set — showing rule-based fallback"
        )
    try:
        response = get_client().messages.create(
            model=MODEL,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": RECOMMENDATION_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": json.dumps(ctx)}],
            output_config={"format": {"type": "json_schema", "schema": RECOMMENDATION_SCHEMA}},
        )
        text = next(b.text for b in response.content if b.type == "text")
        return {
            "available": True,
            "ai_generated": True,
            "model": MODEL,
            "recommendation": json.loads(text),
        }
    except Exception as exc:
        return rule_based_recommendation(
            ctx, f"AI call failed ({type(exc).__name__}) — showing rule-based fallback"
        )


def chat_advisor(messages: list, context: dict) -> str:
    if not anthropic_configured():
        raise AIUnavailableError(
            "AI Advisor requires ANTHROPIC_API_KEY on the backend service."
        )
    response = get_client().messages.create(
        model=MODEL,
        max_tokens=2048,
        output_config={"effort": "low"},
        system=[
            {
                "type": "text",
                "text": ADVISOR_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": "LIVE SYSTEM CONTEXT:\n" + json.dumps(context),
            },
        ],
        messages=messages[-20:],
    )
    return next(
        (b.text for b in reversed(response.content) if b.type == "text"),
        "",
    )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


class ChatRequest(BaseModel):
    messages: list
    context: dict = {}


@router.get("/ai/status")
def ai_status():
    return {"anthropic_configured": anthropic_configured(), "model": MODEL,
            "field_teams": FIELD_TEAMS}


@router.post("/ai/recommendation")
def ai_recommendation(ctx: dict):
    return generate_recommendation(ctx)


@router.post("/ai/chat")
def ai_chat(body: ChatRequest):
    try:
        reply = chat_advisor(body.messages, body.context)
    except AIUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI call failed: {type(exc).__name__}")
    return {"reply": reply, "model": MODEL}
