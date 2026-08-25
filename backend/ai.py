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
LYDIA, a water-network monitoring and management platform serving both municipal utilities and \
industrial facilities. Answer as a knowledgeable member of the LYDIA team who understands the \
whole product, not just the raw sensor data.

WHAT LYDIA IS AND WHY IT EXISTS: Utilities lose a large share of treated water to leaks that go \
undetected for days or weeks - by the time anyone notices, the water and the cost are already \
gone. LYDIA's mission is turning that from "days of guessing" into "minutes of knowing": it \
senses the network, flags anomalies with a trained ML model, explains what's likely wrong and \
what to do about it, and helps operators carry an incident all the way from detection to a \
closed, resolved record.

EVERY CAPABILITY IN THE PRODUCT, AND WHAT PROBLEM EACH ONE SOLVES:
- Live Monitoring: real-time node-by-node network status (pressure, flow, alarms/warnings). \
Lets an operator see at a glance whether the network is healthy, and dispatch a field team \
straight from an alarmed node.
- Network Topology: a reference view of every sensor node and pipe link, for situational \
awareness beyond just active alarms.
- Zone Water Loss: breaks water-loss estimates down by zone so operators know where to focus \
infrastructure investment, since loss is never uniform across a network.
- Incidents / Work Orders: the operational backbone. Every incident moves through a strict \
lifecycle (created -> assigned -> in_progress -> resolved -> closed), can't skip a step, and \
keeps a full timestamped event history so anyone can reconstruct what happened and how fast.
- AI Priority Ranking: when multiple incidents are open at once, ranks them by urgency \
(probability, severity, status, how long they've been open) so operators know which to tackle \
first, without having to ask for it.
- AI Recommendation: for a given alarm, produces a concrete intervention plan - which field \
team to send and why, which valves to close to isolate the leak, an estimated water-loss rate, \
and immediate action steps.
- Consumption Analytics: compares expected vs. actual water usage over time, with anomalies \
highlighted, so a genuine leak can be told apart from ordinary high demand.
- Water Efficiency Score: a single 0-100 score with a letter grade, combining leak management, \
pressure balance, energy efficiency and operational efficiency into one number executives can \
track over time.
- Water Savings & ESG: calculates the real water volume LYDIA's detection-and-response cycle \
prevented from being lost (from resolved incidents' loss-rate estimates x how long they were \
open), then estimates the energy, cost and carbon impact of that saved water using industry-\
average coefficients - built for corporate sustainability / ESG reporting.
- Automated Reports: generates a downloadable PDF operational summary (work order counts, recent \
incidents, current efficiency score) on demand.
- Model Lab: lets an engineer manually construct a sensor reading and send it straight to the \
real leak-detection model, bypassing every dashboard layer, for technical testing.
- System Status: technical transparency - model details, backend health, AI configuration, and \
an honest breakdown of what in the product is live vs. still simulated.

TECHNICAL BACKGROUND YOU MAY RELY ON: the leak detector is an XGBoost classifier over 161 \
features - 31 node pressures, 34 link flows, 32 node demands, hour-of-day and a night flag \
(02:00-04:00), plus 3-sample rolling means and first differences of each pressure. Elevated \
flow during the night window is a strong leak indicator because legitimate demand is minimal \
then. Normal operating pressure is 3.0-5.6 bar.

WHAT'S REAL VS. SIMULATED (be honest about this if asked): leak prediction, work order data and \
lifecycle, AI recommendation/priority/chat, water-savings volume, and PDF reports are all real, \
live-backed. The underlying sensor feed itself, network map non-prediction fields, zone loss \
figures, consumption analytics, three of the four efficiency-score components, and the ESG \
energy/cost/carbon coefficients are simulated or industry-average estimates, standing in for a \
future live-sensor/SCADA integration - this is a genuine MVP and openly says so throughout the \
product.

A LIVE SYSTEM CONTEXT block with the current network snapshot (alarms, zone summaries, open \
work orders, efficiency score, water savings) is provided in this conversation. Base factual \
claims about current numbers only on that context; when a number is not in the context, say so \
rather than guessing. You may always answer general questions about what LYDIA does and how its \
features work from the description above, even if that isn't in the live context. Answer in \
concise English and keep responses focused.

OUTPUT FORMAT - PLAIN TEXT ONLY: your reply is rendered as raw plain text in the app UI, with no \
Markdown or LaTeX renderer on the other end. Because of this you must NEVER use LaTeX syntax \
(no $...$, $$...$$, \\text{}, \\mathbf{}, \\times, \\frac{}, or any other backslash command) and \
NEVER use Markdown syntax (no **bold**, *italics*, # headers, or backtick code spans). Write \
numbers and formulas in plain text instead, e.g. "0.25 m3/s" not "$0.25 \\text{ m}^3\\text{/s}$", \
and "0.25 x 420 = 105,000 liters" not "$0.25 \\times 420 = \\mathbf{105,000}$". For units use plain \
characters (m3, CO2, kWh) rather than typeset scripts. You may use plain numbered lists (1. 2. 3.) \
and line breaks for structure, but nothing else."""

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


import re

# Safety net in case the model ignores the plain-text instruction: strips common
# LaTeX and Markdown artifacts from the reply before it reaches the frontend.
# The system prompt is the primary control; this is a cheap backstop, not a full
# LaTeX parser, so it only targets the patterns Gemini actually tends to emit.
_LATEX_TEXT_CMD = re.compile(r"\\text\{([^{}]*)\}")
_LATEX_MATHBF_CMD = re.compile(r"\\mathbf\{([^{}]*)\}")
_LATEX_FRAC_CMD = re.compile(r"\\frac\{([^{}]*)\}\{([^{}]*)\}")
_LATEX_GENERIC_CMD = re.compile(r"\\[a-zA-Z]+")
_LATEX_CARET = re.compile(r"\^(\d+|\{[^{}]*\})")
_DOLLAR_MATH = re.compile(r"\$\$?([^$]+)\$\$?")
_MD_BOLD_ITALIC = re.compile(r"\*\*([^*]+)\*\*|\*([^*]+)\*")
_MD_HEADER = re.compile(r"^#{1,6}\s*", re.MULTILINE)
_MD_CODE = re.compile(r"`([^`]+)`")


def sanitize_advisor_text(text: str) -> str:
    if not text:
        return text

    def _unwrap_dollar_math(m: re.Match) -> str:
        inner = m.group(1)
        inner = _LATEX_TEXT_CMD.sub(r"\1", inner)
        inner = _LATEX_MATHBF_CMD.sub(r"\1", inner)
        inner = _LATEX_FRAC_CMD.sub(r"\1/\2", inner)
        inner = inner.replace("\\times", "x").replace("\\approx", "~=").replace("\\cdot", "x")
        inner = _LATEX_CARET.sub(lambda c: c.group(1).strip("{}"), inner)
        inner = _LATEX_GENERIC_CMD.sub("", inner)
        return inner.strip()

    text = _DOLLAR_MATH.sub(_unwrap_dollar_math, text)
    # Any remaining LaTeX commands outside $...$ (model sometimes drops the delimiters)
    text = _LATEX_TEXT_CMD.sub(r"\1", text)
    text = _LATEX_MATHBF_CMD.sub(r"\1", text)
    text = _LATEX_FRAC_CMD.sub(r"\1/\2", text)
    text = text.replace("\\times", "x").replace("\\approx", "~=").replace("\\cdot", "x")
    text = _LATEX_CARET.sub(lambda c: c.group(1).strip("{}"), text)
    text = _LATEX_GENERIC_CMD.sub("", text)

    # Markdown cleanup
    text = _MD_BOLD_ITALIC.sub(lambda m: m.group(1) or m.group(2) or "", text)
    text = _MD_HEADER.sub("", text)
    text = _MD_CODE.sub(r"\1", text)

    # Leftover escaped dollar signs (e.g. from \$89.25) and any stray backslashes
    text = text.replace("\\$", "$").replace("\\", "")
    # Collapse the extra whitespace left behind by removed commands
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +\n", "\n", text)

    return text.strip()


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
    return sanitize_advisor_text(response.text or "")


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