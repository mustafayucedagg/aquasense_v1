"""
Automated Reports: assembles a PDF operational summary from data already present
in the system (work orders + their events, efficiency score payload supplied by
the caller). Does not introduce any new simulated data — every number in the
report is either read from the SQLite work-order store or passed in by the
frontend (which computes the efficiency score client-side, same as the
Efficiency Score page does today).
"""

import io
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

import database

NAVY = colors.HexColor("#0B1C36")
MUTED = colors.HexColor("#64748B")
LIGHT_BG = colors.HexColor("#F1F4F8")
OK = colors.HexColor("#15803D")
WARN = colors.HexColor("#B45309")
ALARM = colors.HexColor("#DC2626")


def _severity_color(sev: str):
    return {"critical": ALARM, "high": WARN, "medium": WARN, "low": OK}.get(sev, MUTED)


def build_report_pdf(municipality: str, efficiency: dict | None, period_days: int = 7) -> bytes:
    """Builds the PDF and returns raw bytes. `efficiency` is optional and, if given,
    is rendered as-is (it comes from compute_efficiency_score on the frontend —
    this function does not compute or invent efficiency numbers itself)."""
    orders = database.list_work_orders(municipality=municipality)
    stats = database.work_order_stats(municipality=municipality)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=20 * mm, bottomMargin=18 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("LydiaTitle", parent=styles["Title"], textColor=NAVY, fontSize=20)
    h2 = ParagraphStyle("LydiaH2", parent=styles["Heading2"], textColor=NAVY, spaceBefore=14, spaceAfter=6)
    body = ParagraphStyle("LydiaBody", parent=styles["Normal"], textColor=colors.HexColor("#0F1A2E"), fontSize=9.5, leading=14)
    muted = ParagraphStyle("LydiaMuted", parent=styles["Normal"], textColor=MUTED, fontSize=8.5, leading=12)

    story = []
    story.append(Paragraph("LYDIA — Operational Summary", title_style))
    story.append(Paragraph(f"{municipality}", body))
    story.append(Paragraph(
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · covering the last {period_days} days",
        muted,
    ))
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", color=NAVY, thickness=1.2))
    story.append(Spacer(1, 4 * mm))

    # --- Work order summary (real data, read from SQLite) ---
    story.append(Paragraph("Work Order Summary", h2))
    wo_table_data = [
        ["Open", "In Progress", "Resolved (7d)", "Open Critical", "Total"],
        [
            str(stats["open"]), str(stats["in_progress"]), str(stats["resolved_7d"]),
            str(stats["open_critical"]), str(stats["total"]),
        ],
    ]
    t = Table(wo_table_data, colWidths=[32 * mm] * 5)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 1), (-1, 1), LIGHT_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
    ]))
    story.append(t)
    story.append(Paragraph(
        "Figures reflect the live SQLite work-order store for this organization at report time.",
        muted,
    ))

    # --- Incident list (real data) ---
    story.append(Paragraph("Recent Incidents", h2))
    if not orders:
        story.append(Paragraph("No work orders recorded for this organization yet.", body))
    else:
        rows = [["ID", "Node", "Severity", "Status", "Created"]]
        for o in orders[:15]:
            rows.append([
                o["id"], f"Node {o['node_id']}", o["severity"].upper(),
                o["status"].replace("_", " ").title(), o["created_at"][:16].replace("T", " "),
            ])
        it = Table(rows, colWidths=[32 * mm, 24 * mm, 26 * mm, 30 * mm, 40 * mm])
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]
        for i, o in enumerate(orders[:15], start=1):
            style_cmds.append(("TEXTCOLOR", (2, i), (2, i), _severity_color(o["severity"])))
        it.setStyle(TableStyle(style_cmds))
        story.append(it)
        if len(orders) > 15:
            story.append(Paragraph(f"...and {len(orders) - 15} more, not shown in this summary.", muted))

    # --- Efficiency score (only if supplied by caller; otherwise explicitly noted) ---
    story.append(Paragraph("Water Efficiency Score", h2))
    if efficiency:
        story.append(Paragraph(
            f"Overall score: <b>{efficiency['total']}/100 (Grade {efficiency['grade']})</b>", body
        ))
        comp_rows = [["Component", "Score", "Weight", "Detail"]]
        for name, c in efficiency.get("components", {}).items():
            comp_rows.append([name, f"{c['score']}/100", f"{c['weight']}%", c.get("sub", "")])
        ct = Table(comp_rows, colWidths=[38 * mm, 20 * mm, 18 * mm, 76 * mm])
        ct.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(ct)
        story.append(Paragraph(
            "Component weights are an initial, unvalidated assumption pending calibration "
            "against an independent dataset — see project README for details.",
            muted,
        ))
    else:
        story.append(Paragraph(
            "Efficiency score was not supplied to this report run (backend-only report generation "
            "does not compute it independently — see README for why).", body
        ))

    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#E2E8F0"), thickness=0.8))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "Generated by LYDIA. Live sensor readings driving leak detection are currently simulated "
        "(EPANET/LeakDB-based); work order and event data shown above are real records from this "
        "deployment's database.",
        muted,
    ))

    doc.build(story)
    return buf.getvalue()


router = APIRouter()


class ReportRequest(BaseModel):
    municipality: str
    efficiency: dict | None = None
    period_days: int = 7


@router.post("/reports/generate")
def generate_report(body: ReportRequest):
    pdf_bytes = build_report_pdf(body.municipality, body.efficiency, body.period_days)
    filename = f"lydia-report-{body.municipality.replace(' ', '_')}-{datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
