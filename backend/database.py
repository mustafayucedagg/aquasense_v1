import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

DB_PATH = os.environ.get(
    "AQUASENSE_DB_PATH",
    os.path.join(os.path.dirname(__file__), "aquasense.db"),
)

VALID_STATUSES = {"created", "assigned", "in_progress", "resolved", "closed"}
VALID_TRANSITIONS = {
    "created": {"assigned", "closed"},
    "assigned": {"in_progress", "created"},
    "in_progress": {"resolved"},
    "resolved": {"closed"},
    "closed": set(),
}


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS work_orders (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                municipality TEXT NOT NULL,
                node_id INTEGER NOT NULL,
                zone TEXT,
                severity TEXT NOT NULL,
                probability REAL,
                pressure REAL,
                address TEXT,
                ai_recommendation TEXT,
                assigned_team TEXT,
                status TEXT NOT NULL DEFAULT 'created',
                source TEXT NOT NULL DEFAULT 'auto'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS work_order_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                event_type TEXT NOT NULL,
                detail TEXT
            )
        """)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    if d.get("ai_recommendation"):
        try:
            d["ai_recommendation"] = json.loads(d["ai_recommendation"])
        except (json.JSONDecodeError, TypeError):
            pass
    return d


def _next_wo_id(conn: sqlite3.Connection) -> str:
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"WO-{today}-"
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM work_orders WHERE id LIKE ?", (prefix + "%",)
    ).fetchone()
    return f"{prefix}{row['n'] + 1:03d}"


def add_event(wo_id: str, event_type: str, detail: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO work_order_events (work_order_id, ts, event_type, detail) VALUES (?, ?, ?, ?)",
            (wo_id, _now(), event_type, detail),
        )


def create_work_order(data: dict) -> dict:
    now = _now()
    rec = data.get("ai_recommendation")
    with get_conn() as conn:
        wo_id = _next_wo_id(conn)
        conn.execute(
            """INSERT INTO work_orders
               (id, created_at, updated_at, municipality, node_id, zone, severity,
                probability, pressure, address, ai_recommendation, assigned_team, status, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'created', ?)""",
            (
                wo_id, now, now,
                data["municipality"], data["node_id"], data.get("zone"),
                data["severity"], data.get("probability"), data.get("pressure"),
                data.get("address"),
                json.dumps(rec) if rec is not None else None,
                data.get("assigned_team"),
                data.get("source", "auto"),
            ),
        )
        conn.execute(
            "INSERT INTO work_order_events (work_order_id, ts, event_type, detail) VALUES (?, ?, 'created', ?)",
            (wo_id, now, f"Work order created ({data.get('source', 'auto')}) for Node {data['node_id']}"),
        )
        if rec is not None:
            conn.execute(
                "INSERT INTO work_order_events (work_order_id, ts, event_type, detail) VALUES (?, ?, 'ai_recommendation', 'AI recommendation attached')",
                (wo_id, now),
            )
    return get_work_order(wo_id)


def list_work_orders(status: Optional[str] = None, municipality: Optional[str] = None) -> list:
    query = "SELECT * FROM work_orders WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if municipality:
        query += " AND municipality = ?"
        params.append(municipality)
    query += " ORDER BY created_at DESC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_work_order(wo_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM work_orders WHERE id = ?", (wo_id,)).fetchone()
        if row is None:
            return None
        events = conn.execute(
            "SELECT ts, event_type, detail FROM work_order_events WHERE work_order_id = ? ORDER BY id ASC",
            (wo_id,),
        ).fetchall()
    wo = _row_to_dict(row)
    wo["events"] = [dict(e) for e in events]
    return wo


def update_work_order(wo_id: str, status: Optional[str] = None,
                      assigned_team: Optional[str] = None) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM work_orders WHERE id = ?", (wo_id,)).fetchone()
        if row is None:
            raise KeyError(wo_id)
        now = _now()
        if status is not None:
            current = row["status"]
            if status not in VALID_STATUSES:
                raise ValueError(f"Unknown status '{status}'")
            if status != current and status not in VALID_TRANSITIONS[current]:
                raise ValueError(f"Invalid transition {current} -> {status}")
            conn.execute(
                "UPDATE work_orders SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, wo_id),
            )
            conn.execute(
                "INSERT INTO work_order_events (work_order_id, ts, event_type, detail) VALUES (?, ?, 'status_change', ?)",
                (wo_id, now, f"{row['status']} -> {status}"),
            )
        if assigned_team is not None:
            conn.execute(
                "UPDATE work_orders SET assigned_team = ?, updated_at = ? WHERE id = ?",
                (assigned_team, now, wo_id),
            )
            conn.execute(
                "INSERT INTO work_order_events (work_order_id, ts, event_type, detail) VALUES (?, ?, 'assigned', ?)",
                (wo_id, now, f"Assigned to {assigned_team}"),
            )
    return get_work_order(wo_id)


def work_order_stats(municipality: Optional[str] = None) -> dict:
    orders = list_work_orders(municipality=municipality)
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    return {
        "total": len(orders),
        "open": sum(1 for o in orders if o["status"] in ("created", "assigned")),
        "in_progress": sum(1 for o in orders if o["status"] == "in_progress"),
        "resolved_7d": sum(
            1 for o in orders
            if o["status"] in ("resolved", "closed") and o["updated_at"] >= week_ago
        ),
        "open_critical": sum(
            1 for o in orders
            if o["status"] not in ("resolved", "closed") and o["severity"] == "critical"
        ),
    }


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


class WorkOrderCreate(BaseModel):
    municipality: str
    node_id: int
    zone: Optional[str] = None
    severity: str
    probability: Optional[float] = None
    pressure: Optional[float] = None
    address: Optional[str] = None
    ai_recommendation: Optional[dict] = None
    assigned_team: Optional[str] = None
    source: str = "auto"


class WorkOrderUpdate(BaseModel):
    status: Optional[str] = None
    assigned_team: Optional[str] = None


class EventCreate(BaseModel):
    event_type: str
    detail: str = ""


@router.post("/workorders", status_code=201)
def create_wo(body: WorkOrderCreate):
    return create_work_order(body.model_dump())


@router.get("/workorders")
def list_wo(status: Optional[str] = None, municipality: Optional[str] = None):
    return list_work_orders(status=status, municipality=municipality)


@router.get("/workorders/stats")
def wo_stats(municipality: Optional[str] = None):
    return work_order_stats(municipality=municipality)


@router.get("/workorders/{wo_id}")
def get_wo(wo_id: str):
    wo = get_work_order(wo_id)
    if wo is None:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    return wo


@router.patch("/workorders/{wo_id}")
def update_wo(wo_id: str, body: WorkOrderUpdate):
    try:
        return update_work_order(wo_id, status=body.status, assigned_team=body.assigned_team)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/workorders/{wo_id}/events", status_code=201)
def add_wo_event(wo_id: str, body: EventCreate):
    if get_work_order(wo_id) is None:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    add_event(wo_id, body.event_type, body.detail)
    return get_work_order(wo_id)
