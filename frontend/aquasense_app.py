import streamlit as st
import pandas as pd
import numpy as np
import math
import random
import os
from datetime import datetime, timedelta

# streamlit-folium is optional
try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

import requests

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LYDIA — Water Network Intelligence",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN TOKENS
# ─────────────────────────────────────────────────────────────────────────────
COLORS_LIGHT = {
    "navy": "#0B1C36",
    "navy_light": "#16315C",
    "accent": "#2563EB",
    "bg": "#FAFBFC",
    "panel": "#FFFFFF",
    "panel_alt": "#F1F4F8",
    "border": "#E2E8F0",
    "border_strong": "#CBD5E1",
    "text": "#0F1A2E",
    "text_muted": "#64748B",
    "text_faint": "#94A3B8",
    "ok": "#0F766E",
    "ok_bg": "#ECFDF8",
    "warning": "#B45309",
    "warning_bg": "#FFFBEB",
    "alarm": "#DC2626",
    "alarm_bg": "#FEF2F2",
    "sidebar_bg": "#0B1C36",
    "sidebar_text": "#E8EDF5",
    "sidebar_muted": "#8FA3C2",
    "sidebar_dim": "#B9C6DC",
    "input_bg": "#FFFFFF",
}

COLORS_DARK = {
    "navy": "#4A90D9",
    "navy_light": "#60A8F0",
    "accent": "#60A5FA",
    "bg": "#0D1117",
    "panel": "#161B22",
    "panel_alt": "#1C2333",
    "border": "#30363D",
    "border_strong": "#484F58",
    "text": "#E6EDF3",
    "text_muted": "#8B949E",
    "text_faint": "#6E7681",
    "ok": "#3FB950",
    "ok_bg": "#0F2B17",
    "warning": "#D29922",
    "warning_bg": "#2B1D09",
    "alarm": "#F85149",
    "alarm_bg": "#2B0E0E",
    "sidebar_bg": "#010409",
    "sidebar_text": "#E6EDF3",
    "sidebar_muted": "#6E7681",
    "sidebar_dim": "#8B949E",
    "input_bg": "#0D1117",
}

API_URL = os.environ.get("API_URL", "http://localhost:8000")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

APP_NAME = "LYDIA"
APP_FULL_NAME = "Leak Yield Detection Integrated AI"

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "municipality": "Merzifon Municipality",
        "dark_mode": False,
        "alarm_log": [],
        "team_dispatch_log": [],
        "manual_test_log": [],
        "selected_node": None,
        "api_status_checked": False,
        "api_online": False,
        "last_telegram_message": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# Active color palette
COLORS = COLORS_DARK if st.session_state.dark_mode else COLORS_LIGHT

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

* {{
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}}

html, body, [data-testid="stAppViewContainer"], .main {{
    background-color: {COLORS['bg']} !important;
    color: {COLORS['text']};
    font-family: 'Inter', -apple-system, sans-serif;
}}

p, span, div, label {{
    font-family: 'Inter', -apple-system, sans-serif;
}}

/* Sidebar */
[data-testid="stSidebar"] {{
    background-color: {COLORS['sidebar_bg']} !important;
    border-right: 1px solid {COLORS['border']};
}}
[data-testid="stSidebar"] * {{ color: {COLORS['sidebar_text']} !important; }}
[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.12) !important; }}
[data-testid="stSidebar"] [role="radiogroup"] label {{
    background: transparent;
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 3px;
    transition: background 0.15s ease;
    font-size: 14.5px !important;
    font-weight: 500 !important;
}}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {{
    background: rgba(255,255,255,0.08);
}}

/* Main content area */
[data-testid="stMain"] {{
    background-color: {COLORS['bg']} !important;
}}
section[data-testid="stMain"] > div {{
    background-color: {COLORS['bg']} !important;
}}

/* Headings */
h1, h2, h3, h4 {{
    font-family: 'Inter', -apple-system, sans-serif;
    font-weight: 800;
    color: {COLORS['text']} !important;
    letter-spacing: -0.01em;
}}

/* Guide box - top (short summary) */
.guide-box-top {{
    background: {COLORS['panel_alt']};
    border-left: 4px solid {COLORS['navy']};
    border-radius: 0 10px 10px 0;
    padding: 14px 20px;
    margin-bottom: 20px;
    font-size: 14px;
    color: {COLORS['text']};
    font-weight: 600;
    line-height: 1.55;
}}

/* Guide box - bottom (detailed explanation) */
.guide-box-bottom {{
    background: {COLORS['panel_alt']};
    border: 1px solid {COLORS['border']};
    border-top: 3px solid {COLORS['navy']};
    border-radius: 10px;
    padding: 20px 24px;
    margin-top: 32px;
    font-size: 13px;
    color: {COLORS['text_muted']};
    line-height: 1.8;
}}
.guide-box-bottom h4 {{
    font-size: 12.5px !important;
    font-weight: 800 !important;
    color: {COLORS['text']} !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 10px !important;
}}
.guide-box-bottom b {{ color: {COLORS['text']} !important; font-weight: 700; }}

/* Hint pill */
.hint {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 11.5px;
    font-weight: 600;
    color: {COLORS['text_faint']};
    background: {COLORS['panel_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: 20px;
    padding: 3px 11px;
    margin-left: 8px;
}}

/* Metric cards */
.metric-card {{
    background: {COLORS['panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    transition: box-shadow 0.2s ease;
}}
.metric-card.alarm {{ border-color: {COLORS['alarm']}; background: {COLORS['alarm_bg']}; border-width: 2px; }}
.metric-card.warning {{ border-color: {COLORS['warning']}; background: {COLORS['warning_bg']}; border-width: 2px; }}
.metric-card.ok {{ border-color: {COLORS['ok']}; background: {COLORS['ok_bg']}; }}
.metric-label {{
    font-size: 10.5px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase;
    color: {COLORS['text_faint']}; margin-bottom: 7px;
}}
.metric-value {{
    font-family: 'JetBrains Mono', monospace; font-size: 30px; font-weight: 700; color: {COLORS['text']};
    letter-spacing: -0.01em;
}}
.metric-sub {{ font-size: 12px; color: {COLORS['text_muted']}; margin-top: 5px; font-weight: 500; }}

/* Status badge */
.badge {{
    font-family: 'JetBrains Mono', monospace; font-size: 10.5px; padding: 5px 11px;
    border-radius: 6px; font-weight: 700; letter-spacing: 0.04em;
}}
.badge-alarm {{ background: {COLORS['alarm']}; color: #fff; }}
.badge-warning {{ background: {COLORS['warning']}; color: #fff; }}
.badge-ok {{ background: {COLORS['ok']}; color: #fff; }}

/* Measurement node row */
.node-row {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 13px 17px; border-radius: 9px; margin-bottom: 7px;
    background: {COLORS['panel']}; border: 1px solid {COLORS['border']}; font-size: 13.5px;
    color: {COLORS['text']};
}}
.node-row.alarm {{ background: {COLORS['alarm_bg']}; border-color: {COLORS['alarm']}; border-width: 2px; }}
.node-row.warning {{ background: {COLORS['warning_bg']}; border-color: {COLORS['warning']}; }}

/* Status pill */
.status-pill {{
    display: inline-flex; align-items: center; gap: 7px; font-size: 12.5px; font-weight: 700;
    padding: 7px 15px; border-radius: 20px; background: {COLORS['ok_bg']}; color: {COLORS['ok']};
    border: 1px solid {COLORS['ok']};
}}
.status-pill.offline {{ background: {COLORS['alarm_bg']}; color: {COLORS['alarm']}; border-color: {COLORS['alarm']}; }}
.status-dot {{
    width: 7px; height: 7px; border-radius: 50%; background: currentColor;
    animation: pulse-dot 2s infinite;
}}
@keyframes pulse-dot {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.35; }} }}

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background: transparent; border-bottom: 2px solid {COLORS['border']}; gap: 6px;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    background: transparent; color: {COLORS['text_muted']} !important; font-size: 14px;
    font-weight: 600; padding: 11px 22px;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    color: {COLORS['navy']} !important; border-bottom: 2px solid {COLORS['navy']} !important;
    font-weight: 700 !important;
}}

/* Table */
.stDataFrame {{ border: 1px solid {COLORS['border']} !important; border-radius: 10px !important; overflow: hidden; }}
[data-testid="stDataFrameResizable"] {{ background: {COLORS['panel']} !important; }}

/* Divider */
.divider {{ border: none; border-top: 1px solid {COLORS['border']}; margin: 26px 0; }}

/* Inputs */
.stNumberInput input, .stSelectbox > div, .stTextInput input, .stSlider {{
    background: {COLORS['input_bg']} !important; color: {COLORS['text']} !important;
    border: 1px solid {COLORS['border_strong']} !important; border-radius: 9px !important;
    font-weight: 500 !important;
}}
.stNumberInput input:focus, .stTextInput input:focus {{
    border-color: {COLORS['accent']} !important;
    box-shadow: 0 0 0 3px {COLORS['accent']}22 !important;
}}

/* BUTTONS — large and vivid */
.stButton button {{
    background: {COLORS['navy']} !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 15px 30px !important;
    font-size: 15.5px !important;
    transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1) !important;
    letter-spacing: 0.01em !important;
    min-height: 52px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08) !important;
}}
.stButton button:hover {{
    background: {COLORS['navy_light']} !important;
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(11,28,54,0.28) !important;
}}
.stButton button:active {{
    transform: translateY(0px);
}}
.stButton button:disabled {{
    background: {COLORS['border']} !important;
    color: {COLORS['text_faint']} !important;
    transform: none !important;
    box-shadow: none !important;
}}
.stButton button p {{
    font-size: 15.5px !important;
    font-weight: 700 !important;
}}

/* Dispatch Team button — red, large, alive */
.action-btn-active button {{
    background: linear-gradient(135deg, {COLORS['alarm']} 0%, #B91C1C 100%) !important;
    font-size: 17px !important;
    padding: 18px 34px !important;
    min-height: 60px !important;
    box-shadow: 0 4px 18px rgba(220,38,38,0.42) !important;
    animation: pulse-btn 2.2s infinite;
    letter-spacing: 0.02em !important;
}}
.action-btn-active button:hover {{
    background: linear-gradient(135deg, #EF4444 0%, #B91C1C 100%) !important;
    box-shadow: 0 10px 28px rgba(220,38,38,0.5) !important;
    transform: translateY(-2px);
}}
@keyframes pulse-btn {{
    0%, 100% {{ box-shadow: 0 4px 18px rgba(220,38,38,0.42); }}
    50% {{ box-shadow: 0 4px 30px rgba(220,38,38,0.75); }}
}}

/* Close ("X") button used inside dialogs */
.close-btn-wrap button {{
    background: {COLORS['panel_alt']} !important;
    color: {COLORS['text']} !important;
    border: 1px solid {COLORS['border_strong']} !important;
    min-height: 44px !important;
    font-size: 14px !important;
    box-shadow: none !important;
}}
.close-btn-wrap button:hover {{
    background: {COLORS['alarm_bg']} !important;
    border-color: {COLORS['alarm']} !important;
    color: {COLORS['alarm']} !important;
    transform: none;
    box-shadow: none !important;
}}

/* Telegram message preview inside dialog */
.telegram-msg-box {{
    background: {COLORS['panel_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    padding: 16px 18px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12.5px;
    color: {COLORS['text']};
    line-height: 1.95;
    white-space: pre-wrap;
    margin: 14px 0 4px 0;
}}
.dialog-status-ok {{
    display: flex; align-items: center; gap: 10px;
    font-size: 17px; font-weight: 800; color: {COLORS['ok']};
    margin-bottom: 6px;
}}
.dialog-status-error {{
    display: flex; align-items: center; gap: 10px;
    font-size: 17px; font-weight: 800; color: {COLORS['warning']};
    margin-bottom: 6px;
}}
.dialog-sub {{
    font-size: 13px; color: {COLORS['text_muted']}; line-height: 1.6; margin-bottom: 4px;
}}

/* Brand header */
.brand-header {{
    display: flex; align-items: center; gap: 10px; padding: 6px 4px 4px 4px;
}}
.brand-title {{
    font-size: 21px; font-weight: 900; color: #fff; letter-spacing: -0.02em;
    font-family: 'Inter', sans-serif;
}}
.brand-full-name {{
    font-size: 10px; color: {COLORS['sidebar_muted']}; margin-top: 1px; font-weight: 600;
    letter-spacing: 0.02em;
}}
.brand-sub {{ font-size: 11px; color: {COLORS['sidebar_muted']}; margin-top: 6px; margin-bottom: 4px; font-weight: 500; }}

/* Scrollbar */
::-webkit-scrollbar {{ width: 7px; height: 7px; }}
::-webkit-scrollbar-track {{ background: {COLORS['bg']}; }}
::-webkit-scrollbar-thumb {{ background: {COLORS['border_strong']}; border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: {COLORS['text_faint']}; }}

/* MVP warning banner */
.mvp-banner {{
    background: {COLORS['warning_bg']};
    border: 2px solid {COLORS['warning']};
    border-radius: 12px;
    padding: 18px 22px;
    color: {COLORS['warning']};
    font-size: 13.5px;
    font-weight: 600;
    margin-bottom: 22px;
    line-height: 1.7;
}}

/* Guide page — clean documentation styling */
.guide-section-title {{
    font-size: 15px;
    font-weight: 800;
    color: {COLORS['text']};
    margin: 8px 0 14px 0;
    display: flex;
    align-items: center;
    gap: 10px;
}}
.guide-section-number {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 7px;
    background: {COLORS['navy']};
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    flex-shrink: 0;
}}
.guide-card {{
    background: {COLORS['panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 22px 26px;
    margin-bottom: 18px;
    line-height: 1.85;
    font-size: 13.5px;
    color: {COLORS['text_muted']};
}}
.guide-card b {{ color: {COLORS['text']}; font-weight: 700; }}
.guide-card code {{
    background: {COLORS['panel_alt']};
    padding: 2px 7px;
    border-radius: 5px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: {COLORS['navy']};
}}
.formula-box {{
    background: {COLORS['panel_alt']};
    border: 1px solid {COLORS['border']};
    border-left: 3px solid {COLORS['accent']};
    border-radius: 0 10px 10px 0;
    padding: 14px 18px;
    margin: 12px 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12.5px;
    color: {COLORS['text']};
    line-height: 1.9;
}}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# EPANET TOPOLOGY (Hanoi benchmark network)
# ─────────────────────────────────────────────────────────────────────────────
LOCAL_COORDS = {
    1: (5251.17, 4485.98), 2: (5251.17, 5268.69), 3: (5227.80, 5969.63),
    4: (6068.93, 5969.63), 5: (6676.40, 5969.63), 6: (7260.51, 5969.63),
    7: (7260.51, 6600.47), 8: (7260.51, 7301.40), 9: (7260.51, 7990.65),
    10: (6793.22, 7990.65), 11: (6793.22, 8551.40), 12: (6793.22, 8960.28),
    13: (6150.70, 8960.28), 14: (6302.57, 7990.65), 15: (5683.41, 7990.65),
    16: (5216.12, 7990.65), 17: (5216.12, 7535.05), 18: (5227.80, 7137.85),
    19: (5227.80, 6542.06), 20: (4550.23, 5969.63), 21: (4550.23, 5303.74),
    22: (4550.23, 4591.12), 23: (3977.80, 5969.63), 24: (3977.80, 7172.90),
    25: (3954.44, 7990.65), 26: (4410.05, 7990.65), 27: (4818.93, 7990.65),
    28: (3405.37, 5969.63), 29: (2716.12, 6004.67), 30: (2716.12, 6904.21),
    31: (2716.12, 7990.65), 32: (3405.37, 7990.65),
}
RESERVOIR_ID = 1
PIPES = [
    (1,1,2),(2,2,3),(3,3,4),(4,4,5),(5,5,6),(6,6,7),(7,7,8),(8,8,9),
    (9,9,10),(10,10,11),(11,11,12),(12,12,13),(13,10,14),(14,14,15),
    (15,15,16),(16,17,16),(17,17,18),(18,18,19),(19,19,3),(20,3,20),
    (21,20,21),(22,21,22),(23,20,23),(24,23,24),(25,24,25),(26,26,25),
    (27,27,26),(28,16,27),(29,23,28),(30,28,29),(31,29,30),(32,30,31),
    (33,32,31),(34,25,32),
]
PRESSURE_NODE_IDS = list(range(2, 33))
FLOW_LINK_IDS = list(range(1, 35))
DEMAND_NODE_IDS = list(range(1, 33))

# ─────────────────────────────────────────────────────────────────────────────
# MUNICIPALITY DATA
# ─────────────────────────────────────────────────────────────────────────────
MUNICIPALITIES = {
    "Merzifon Municipality": {
        "province": "Amasya",
        "population": 42000,
        "center": (40.8706, 35.4636),
        "span_km": 1.8,
        "isolated_zones": [
            "IMZ-MRZ-1 (Center)", "IMZ-MRZ-2 (Industrial)",
            "IMZ-MRZ-3 (New District)", "IMZ-MRZ-4 (Kışla)",
        ],
        "sample_addresses": [
            "Alparslan District, 110th St. No:14, Merzifon/Amasya",
            "Gazi District, Cumhuriyet Ave. No:7, Merzifon/Amasya",
            "Industrial District, 3rd St. No:22, Merzifon/Amasya",
            "New District, Atatürk Blvd. No:45, Merzifon/Amasya",
        ],
    },
    "Uluborlu Municipality": {
        "province": "Isparta",
        "population": 8500,
        "center": (38.0758, 30.4647),
        "span_km": 1.2,
        "isolated_zones": [
            "IMZ-ULB-1 (Center)", "IMZ-ULB-2 (Surrounding)", "IMZ-ULB-3 (Elevated Zone)",
        ],
        "sample_addresses": [
            "Cumhuriyet District, Station Ave. No:9, Uluborlu/Isparta",
            "Yeşilköy District, 2nd St. No:18, Uluborlu/Isparta",
            "Kemer District, Atatürk Ave. No:31, Uluborlu/Isparta",
        ],
    },
    "Bolu Municipality": {
        "province": "Bolu",
        "population": 98000,
        "center": (40.7360, 31.6069),
        "span_km": 2.4,
        "isolated_zones": [
            "IMZ-BLU-1 (Center)", "IMZ-BLU-2 (North)",
            "IMZ-BLU-3 (Industrial)", "IMZ-BLU-4 (South)", "IMZ-BLU-5 (Karaçayır)",
        ],
        "sample_addresses": [
            "Tabaklar District, Cumhuriyet Ave. No:12, Bolu",
            "Çaydurt District, İzzet Baysal Ave. No:34, Bolu",
            "Sanayi District, Seben Road No:8, Bolu",
            "Karaçayır District, Abant Ave. No:21, Bolu",
            "Türkali District, Atatürk Blvd. No:55, Bolu",
        ],
    },
}


@st.cache_data
def local_to_latlon(center_lat, center_lon, span_km=1.8):
    xs = [c[0] for c in LOCAL_COORDS.values()]
    ys = [c[1] for c in LOCAL_COORDS.values()]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    max_range = max(x_max - x_min, y_max - y_min)
    km_per_deg_lat = 111.0
    km_per_deg_lon = 111.0 * math.cos(math.radians(center_lat))
    lat_span_deg = span_km / km_per_deg_lat
    lon_span_deg = span_km / km_per_deg_lon
    latlon = {}
    for node_id, (x, y) in LOCAL_COORDS.items():
        nx = (x - x_min) / max_range - 0.5
        ny = (y - y_min) / max_range - 0.5
        lat = center_lat + ny * lat_span_deg
        lon = center_lon + nx * lon_span_deg
        latlon[node_id] = (round(lat, 6), round(lon, 6))
    return latlon


def get_node_assignments(mun_key, n_zones):
    node_ids = PRESSURE_NODE_IDS
    chunk = len(node_ids) // n_zones
    assignments = {}
    for i, nid in enumerate(node_ids):
        zone_idx = min(i // max(chunk, 1), n_zones - 1)
        assignments[nid] = zone_idx
    return assignments


def get_node_states(mun_key, alarm_node_ids=None, seed_offset=0):
    rnd = random.Random(hash(mun_key) + seed_offset)
    alarm_node_ids = alarm_node_ids or []
    states = {}
    for nid in PRESSURE_NODE_IDS:
        if nid in alarm_node_ids:
            status = "alarm"
            pressure = round(rnd.uniform(1.0, 2.3), 2)
            probability = round(rnd.uniform(0.78, 0.99), 3)
        else:
            r = rnd.random()
            if r < 0.08:
                status = "warning"
                pressure = round(rnd.uniform(2.4, 2.9), 2)
                probability = round(rnd.uniform(0.35, 0.55), 3)
            else:
                status = "ok"
                pressure = round(rnd.uniform(3.0, 5.6), 2)
                probability = round(rnd.uniform(0.0, 0.15), 3)
        states[nid] = {
            "status": status,
            "pressure": pressure,
            "flow": round(rnd.uniform(0.8, 4.2), 2),
            "demand": round(rnd.uniform(0.5, 3.0), 2),
            "probability": probability,
        }
    return states


def check_api_health():
    try:
        resp = requests.get(f"{API_URL}/health", timeout=3)
        return resp.status_code == 200 and resp.json().get("model_loaded", False)
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# TELEGRAM DISPATCH FUNCTION
# ─────────────────────────────────────────────────────────────────────────────
def send_telegram_alert(node_id, address, pressure, probability, municipality_name):
    """
    Sends a leak alert to the field team via the Telegram Bot API.
    TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set as Environment Variables on Onrender.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False, "Telegram bot configuration is missing (BOT_TOKEN or CHAT_ID not set)"

    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    message = (
        f"🚨 *LEAK ALERT — LYDIA*\n\n"
        f"📍 *Address:* {address}\n"
        f"📊 *Measurement Node:* {node_id}\n"
        f"💧 *Current Pressure:* {pressure} bar\n"
        f"⚠️ *Leak Probability:* {probability*100:.1f}%\n"
        f"🏛️ *Municipality:* {municipality_name}\n"
        f"🕐 *Detection Time:* {timestamp}\n\n"
        f"Please dispatch a field team to the address above as soon as possible."
    )

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        }
        resp = requests.post(url, json=payload, timeout=6)
        if resp.status_code == 200:
            return True, message
        else:
            err = resp.json().get("description", "Unknown error")
            return False, f"Telegram API error: {err}"
    except Exception as e:
        return False, f"Connection error: {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# FOLIUM MAP
# ─────────────────────────────────────────────────────────────────────────────
STATUS_COLOR = {"alarm": "#DC2626", "warning": "#B45309", "ok": "#0F766E"}
STATUS_LABEL = {"alarm": "Alarm", "warning": "Warning", "ok": "Normal"}


def build_network_map(mun_key, node_states, detail_level="summary", highlight_node=None):
    mun = MUNICIPALITIES[mun_key]
    latlon = local_to_latlon(*mun["center"], span_km=mun["span_km"])
    center = mun["center"]
    tile = "CartoDB dark_matter" if st.session_state.dark_mode else "CartoDB positron"
    m = folium.Map(location=center, zoom_start=15, tiles=tile, control_scale=True)

    for pipe_id, n1, n2 in PIPES:
        if n1 in latlon and n2 in latlon:
            s1 = node_states.get(n1, {}).get("status", "ok") if n1 != RESERVOIR_ID else "ok"
            s2 = node_states.get(n2, {}).get("status", "ok") if n2 != RESERVOIR_ID else "ok"
            is_alarm_line = (s1 == "alarm" or s2 == "alarm")
            folium.PolyLine(
                locations=[latlon[n1], latlon[n2]],
                color="#F85149" if is_alarm_line else ("#6E7681" if st.session_state.dark_mode else "#94A3B8"),
                weight=4.2 if is_alarm_line else 2.6,
                opacity=0.92 if is_alarm_line else 0.65,
            ).add_to(m)

    if RESERVOIR_ID in latlon:
        folium.CircleMarker(
            location=latlon[RESERVOIR_ID], radius=10,
            color="#FFFFFF" if st.session_state.dark_mode else "#0B1C36",
            fill=True,
            fill_color="#4A90D9" if st.session_state.dark_mode else "#0B1C36",
            fill_opacity=1, weight=2.5,
            popup=folium.Popup("Reservoir (Main Water Source)", max_width=200),
            tooltip="Reservoir",
        ).add_to(m)

    for nid, (lat, lon) in latlon.items():
        if nid == RESERVOIR_ID:
            continue
        state = node_states.get(nid, {"status": "ok", "pressure": 0, "flow": 0, "probability": 0})
        status = state["status"]
        color = STATUS_COLOR[status]
        is_highlighted = (highlight_node == nid)
        radius = 12 if status == "alarm" else (8.5 if detail_level == "detail" else 7.5)
        if is_highlighted:
            radius += 4

        popup_html = f"""
        <div style="font-family:Inter,sans-serif;font-size:12.5px;min-width:175px">
            <b>Measurement Node {nid}</b><br>
            <span style="color:{color};font-weight:700">{STATUS_LABEL[status]}</span><br>
            Pressure: {state['pressure']} bar<br>
            Flow: {state.get('flow', 0)} m³/h<br>
            Leak probability: {state.get('probability', 0):.3f}
        </div>
        """
        folium.CircleMarker(
            location=(lat, lon), radius=radius, color="#FFFFFF",
            fill=True, fill_color=color, fill_opacity=0.94, weight=2.2,
            popup=folium.Popup(popup_html, max_width=225),
            tooltip=f"Node {nid} — {STATUS_LABEL[status]}",
        ).add_to(m)

        if status == "alarm":
            folium.Circle(
                location=(lat, lon), radius=48, color="#DC2626",
                fill=True, fill_opacity=0.13, weight=1, opacity=0.55,
            ).add_to(m)

    return m, latlon


# ─────────────────────────────────────────────────────────────────────────────
# TELEGRAM DISPATCH RESULT DIALOG — native Streamlit dialog, closable via X
# ─────────────────────────────────────────────────────────────────────────────
@st.dialog("Dispatch Result")
def show_dispatch_dialog():
    tg = st.session_state.last_telegram_message
    if not tg:
        st.write("No dispatch data available.")
        if st.button("Close", use_container_width=True):
            st.session_state.last_telegram_message = None
            st.rerun()
        return

    if tg["ok"]:
        st.markdown(f"""<div class="dialog-status-ok">✅ Field Team Notified</div>""", unsafe_allow_html=True)
        st.markdown(f"""<div class="dialog-sub">The following message was delivered to the field team via Telegram.</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="dialog-status-error">⚠️ Telegram Delivery Failed</div>""", unsafe_allow_html=True)
        st.markdown(f"""<div class="dialog-sub">{tg['mesaj'] if 'mesaj' in tg else tg.get('message','')}</div>""", unsafe_allow_html=True)
        st.markdown(f"""<div class="dialog-sub" style="font-size:11.5px">Are TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID set on Onrender?</div>""", unsafe_allow_html=True)

    if tg["ok"]:
        clean_message = tg["message"].replace("*", "")
        st.markdown(f"""<div class="telegram-msg-box">{clean_message}</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="close-btn-wrap">', unsafe_allow_html=True)
    if st.button("✕  Close", use_container_width=True, key="dialog_close_btn"):
        st.session_state.last_telegram_message = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div class="brand-header">
        <div>
            <div class="brand-title">{APP_NAME}</div>
            <div class="brand-full-name">{APP_FULL_NAME}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f'<div class="brand-sub">Water Network Leak Detection System</div>', unsafe_allow_html=True)

    page = st.radio(
        label="Navigation",
        options=[
            "Live Monitoring",
            "Network Map",
            "Isolated Measurement Zones",
            "Data Analysis",
            "Guide",
            "System & Model",
        ],
        label_visibility="collapsed",
    )

    st.markdown('<hr>', unsafe_allow_html=True)

    # Dark/Light mode toggle
    mode_label = "Light Mode" if st.session_state.dark_mode else "Dark Mode"
    if st.button(f"{'☀️' if st.session_state.dark_mode else '🌙'} {mode_label}", use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    st.markdown('<hr>', unsafe_allow_html=True)

    st.markdown(f'<div style="font-size:10.5px;font-weight:800;letter-spacing:0.07em;text-transform:uppercase;color:{COLORS["sidebar_muted"]};margin-bottom:9px">Municipality</div>', unsafe_allow_html=True)
    municipality_choice = st.selectbox("Municipality", list(MUNICIPALITIES.keys()), label_visibility="collapsed")
    st.session_state.municipality = municipality_choice
    mun = MUNICIPALITIES[municipality_choice]

    st.markdown('<hr>', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="font-size:12.5px;line-height:2.1;color:{COLORS['sidebar_dim']}">
        <b style="color:{COLORS['sidebar_text']}">Province:</b> {mun['province']}<br>
        <b style="color:{COLORS['sidebar_text']}">Population:</b> {mun['population']:,}<br>
        <b style="color:{COLORS['sidebar_text']}">Isolated Zones:</b> {len(mun['isolated_zones'])}<br>
        <b style="color:{COLORS['sidebar_text']}">Measurement Nodes:</b> {len(PRESSURE_NODE_IDS)}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr>', unsafe_allow_html=True)

    if not st.session_state.api_status_checked:
        st.session_state.api_online = check_api_health()
        st.session_state.api_status_checked = True

    if st.session_state.api_online:
        st.markdown('<div class="status-pill"><span class="status-dot"></span>System Online</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-pill offline"><span class="status-dot"></span>Awaiting Data</div>', unsafe_allow_html=True)

    if st.button("Refresh Connection", use_container_width=True):
        st.session_state.api_status_checked = False
        st.rerun()

    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:10.5px;color:{COLORS["sidebar_muted"]};">Last updated<br><span style="font-family:JetBrains Mono;color:{COLORS["sidebar_dim"]}">{datetime.now().strftime("%d.%m.%Y %H:%M")}</span></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED PAGE HEADER
# ─────────────────────────────────────────────────────────────────────────────
def render_page_header(title, subtitle=None):
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
        <div>
            <div style="font-size:24px;font-weight:800;color:{COLORS['text']}">{title}</div>
            <div style="font-size:13px;color:{COLORS['text_muted']};margin-top:3px;font-weight:500">{subtitle or f"{municipality_choice} — {mun['province']} Province"}</div>
        </div>
        <div style="font-family:JetBrains Mono;font-size:12.5px;color:{COLORS['text_muted']};text-align:right">
            {datetime.now().strftime("%B %d, %Y")}<br>
            <span style="color:{COLORS['navy']};font-weight:700">{datetime.now().strftime("%H:%M:%S")}</span>
        </div>
    </div>
    <hr style="border-color:{COLORS['border']};margin:16px 0 22px 0">
    """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: LIVE MONITORING
# ═════════════════════════════════════════════════════════════════════════════
if page == "Live Monitoring":
    render_page_header("Live Monitoring")

    st.markdown("""<div class="guide-box-top">
    Real-time status across the network. Measurement nodes suspected of leaking are flagged in red;
    once an alarm is detected, the <b>Dispatch Team</b> button activates and sends a Telegram notification to the field team.
    </div>""", unsafe_allow_html=True)

    # Demo state generation
    demo_alarm_nodes = [PRESSURE_NODE_IDS[3]]
    node_states = get_node_states(municipality_choice, demo_alarm_nodes)

    alarm_count = sum(1 for s in node_states.values() if s["status"] == "alarm")
    warning_count = sum(1 for s in node_states.values() if s["status"] == "warning")
    ok_count = sum(1 for s in node_states.values() if s["status"] == "ok")

    # Top metric row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        cls = "alarm" if alarm_count > 0 else "ok"
        st.markdown(f'<div class="metric-card {cls}"><div class="metric-label">Active Alarms</div><div class="metric-value">{alarm_count}</div><div class="metric-sub">Nodes with suspected leaks</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card warning"><div class="metric-label">Warnings</div><div class="metric-value">{warning_count}</div><div class="metric-sub">Nodes needing follow-up</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card ok"><div class="metric-label">Normal</div><div class="metric-value">{ok_count}</div><div class="metric-sub">Operating nodes</div></div>', unsafe_allow_html=True)
    with c4:
        avg_p = np.mean([s["pressure"] for s in node_states.values()])
        st.markdown(f'<div class="metric-card"><div class="metric-label">Avg. Pressure</div><div class="metric-value">{avg_p:.2f}</div><div class="metric-sub">bar — network-wide</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Map + Dynamic list
    col_map, col_list = st.columns([2, 1])

    with col_map:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px">Network Map — Live Status</div>', unsafe_allow_html=True)
        if FOLIUM_AVAILABLE:
            m, latlon = build_network_map(municipality_choice, node_states, detail_level="summary", highlight_node=st.session_state.selected_node)
            map_data = st_folium(m, height=420, width=None, returned_objects=["last_object_clicked_tooltip"])
        else:
            st.markdown(f'<div class="metric-card" style="text-align:center;padding:60px 20px;color:{COLORS["text_faint"]}">The map module (streamlit-folium) failed to load.<br>Please check requirements.txt.</div>', unsafe_allow_html=True)

    with col_list:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px">Measurement Nodes <span class="hint">Alarms first</span></div>', unsafe_allow_html=True)
        order = {"alarm": 0, "warning": 1, "ok": 2}
        sorted_nodes = sorted(node_states.items(), key=lambda x: (order[x[1]["status"]], x[0]))
        list_container = st.container(height=420)
        with list_container:
            for nid, state in sorted_nodes:
                status = state["status"]
                badge_cls = f"badge-{status}"
                badge_text = STATUS_LABEL[status].upper()
                row_cls = f"node-row {status}" if status != "ok" else "node-row"
                st.markdown(f"""
                <div class="{row_cls}">
                    <div>
                        <div style="font-weight:700;font-size:13.5px;color:{COLORS['text']}">Node {nid}</div>
                        <div style="font-family:JetBrains Mono;font-size:11.5px;color:{COLORS['text_muted']}">{state['pressure']} bar · {state['flow']} m³/h</div>
                    </div>
                    <span class="badge {badge_cls}">{badge_text}</span>
                </div>
                """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Detail panel + Dispatch Team
    alarm_nodes_list = [nid for nid, s in node_states.items() if s["status"] == "alarm"]
    has_alarm = len(alarm_nodes_list) > 0

    col_detail, col_action = st.columns([2, 1])

    with col_detail:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px">Detection Detail</div>', unsafe_allow_html=True)
        if has_alarm:
            primary = alarm_nodes_list[0]
            st_data = node_states[primary]
            st.markdown(f"""
            <div class="metric-card alarm">
                <div class="metric-label">Detected Anomaly</div>
                <div style="font-size:17px;font-weight:800;color:{COLORS['alarm']};margin-bottom:9px">
                    Node {primary} — Suspected Leak
                </div>
                <div style="font-size:13.5px;color:{COLORS['text']};line-height:1.8">
                    Current pressure: <span style="font-family:JetBrains Mono;font-weight:700;color:{COLORS['alarm']}">{st_data['pressure']} bar</span>
                    (expected: &gt;3.0 bar)<br>
                    Model leak probability: <span style="font-family:JetBrains Mono;font-weight:700;color:{COLORS['alarm']}">{st_data['probability']*100:.1f}%</span><br>
                    Affected pipe segments: <span style="font-family:JetBrains Mono;font-weight:700">{len([p for p in PIPES if primary in (p[1], p[2])])}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="metric-card ok">
                <div class="metric-label">Overall Status</div>
                <div style="font-size:16px;font-weight:700;color:{COLORS['ok']};margin-bottom:7px">Network Operating Normally</div>
                <div style="font-size:13.5px;color:{COLORS['text_muted']};line-height:1.75">
                    No measurement node currently shows a suspected leak.
                    All pressure and flow values are within expected ranges.
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_action:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px">Field Operations</div>', unsafe_allow_html=True)

        if has_alarm:
            primary = alarm_nodes_list[0]
            st_data = node_states[primary]
            address = random.choice(mun["sample_addresses"])

            # Preview of what will be sent
            st.markdown(f"""
            <div style="background:{COLORS['alarm_bg']};border:2px solid {COLORS['alarm']};border-radius:12px;padding:15px 17px;margin-bottom:18px">
                <div style="font-size:11px;font-weight:800;color:{COLORS['alarm']};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:7px">Information To Be Sent</div>
                <div style="font-size:12.5px;color:{COLORS['text']};line-height:1.9;font-family:JetBrains Mono">
                    Node: {primary}<br>
                    Pressure: {st_data['pressure']} bar<br>
                    Probability: {st_data['probability']*100:.1f}%<br>
                    Address: {address[:32]}...
                </div>
            </div>
            """, unsafe_allow_html=True)

            btn_container = st.container()
            with btn_container:
                st.markdown('<div class="action-btn-active">', unsafe_allow_html=True)
                dispatch_clicked = st.button(
                    "🚨  DISPATCH TEAM",
                    use_container_width=True,
                    key="dispatch_team_btn",
                )
                st.markdown('</div>', unsafe_allow_html=True)

            if dispatch_clicked:
                tg_ok, tg_message = send_telegram_alert(
                    node_id=primary,
                    address=address,
                    pressure=st_data["pressure"],
                    probability=st_data["probability"],
                    municipality_name=municipality_choice,
                )
                st.session_state.team_dispatch_log.append({
                    "Time": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    "Node": f"Node {primary}",
                    "Address": address,
                    "Municipality": municipality_choice,
                    "Telegram": "Delivered" if tg_ok else "Failed",
                })
                st.session_state.last_telegram_message = {"ok": tg_ok, "message": tg_message, "address": address}
                show_dispatch_dialog()

            # If a dialog result exists but wasn't shown this run (e.g. after other reruns), offer to reopen it
            if st.session_state.last_telegram_message and not dispatch_clicked:
                if st.button("View Last Dispatch Result", use_container_width=True, key="reopen_dispatch_dialog"):
                    show_dispatch_dialog()
        else:
            st.button(
                "Dispatch Team (No Alarm)",
                disabled=True,
                use_container_width=True,
                key="dispatch_team_btn_disabled",
            )
            st.markdown(f'<div style="font-size:12.5px;color:{COLORS["text_faint"]};margin-top:11px;line-height:1.75;text-align:center">This button activates automatically when a leak is detected and sends a Telegram notification to the field team.</div>', unsafe_allow_html=True)

        # Dispatch history
        if st.session_state.team_dispatch_log:
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:11px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:9px">Dispatch History</div>', unsafe_allow_html=True)
            with st.expander(f"{len(st.session_state.team_dispatch_log)} record(s)", expanded=False):
                st.dataframe(pd.DataFrame(st.session_state.team_dispatch_log), use_container_width=True, hide_index=True)

    # Bottom detailed explanation
    st.markdown(f"""<div class="guide-box-bottom">
    <h4>About This Page</h4>
    <b>Live Monitoring</b> shows the current pressure and flow readings for every measurement node
    in the water network. The XGBoost model evaluates each node independently; when an anomaly
    is detected, that node turns red and the alarm counter increases.<br><br>
    The <b>Dispatch Team</b> button is only active while there is a live alarm. When clicked, it sends
    a notification containing the measurement node, address, pressure reading and leak probability
    to the field team through a pre-configured Telegram bot. To enable this feature, set
    <span style="font-family:JetBrains Mono">TELEGRAM_BOT_TOKEN</span> and
    <span style="font-family:JetBrains Mono">TELEGRAM_CHAT_ID</span> as environment variables on Onrender.<br><br>
    <b>Demo note:</b> the data shown here is currently simulated. Once connected to the live API,
    these values will update automatically from the model's <code>/predict</code> output.
    </div>""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: NETWORK MAP
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Network Map":
    render_page_header("Network Map")

    st.markdown("""<div class="guide-box-top">
    All measurement nodes and pipe segments plotted on their real geographic locations. Click a node
    to view pressure, flow and leak probability details.
    </div>""", unsafe_allow_html=True)

    demo_alarm_nodes = [PRESSURE_NODE_IDS[3]]
    node_states = get_node_states(municipality_choice, demo_alarm_nodes, seed_offset=1)

    col_map, col_info = st.columns([2.2, 1])

    with col_map:
        if FOLIUM_AVAILABLE:
            m, latlon = build_network_map(municipality_choice, node_states, detail_level="detail")
            map_data = st_folium(m, height=520, width=None, returned_objects=["last_object_clicked_tooltip"])
        else:
            st.markdown(f'<div class="metric-card" style="text-align:center;padding:60px 20px;color:{COLORS["text_faint"]}">The map module failed to load.</div>', unsafe_allow_html=True)

    with col_info:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px">Network Summary</div>', unsafe_allow_html=True)
        info_items = [
            ("Total Measurement Nodes", str(len(PRESSURE_NODE_IDS))),
            ("Total Pipe Segments", str(len(PIPES))),
            ("Main Water Source", "1 Reservoir"),
            ("Active Alarms", str(sum(1 for s in node_states.values() if s["status"] == "alarm"))),
            ("Data Source", "EPANET / Hanoi"),
        ]
        for label, val in info_items:
            st.markdown(f"""<div class="node-row" style="margin-bottom:6px">
                <div class="metric-label" style="margin:0">{label}</div>
                <div style="font-family:JetBrains Mono;font-size:12px;color:{COLORS['text']}">{val}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="font-size:12.5px;color:{COLORS['text_muted']};line-height:2.1">
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{COLORS['alarm']};margin-right:7px"></span>Alarm<br>
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{COLORS['warning']};margin-right:7px"></span>Warning<br>
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{COLORS['ok']};margin-right:7px"></span>Normal<br>
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{COLORS['navy']};margin-right:7px"></span>Reservoir
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px">Node Detail Table</div>', unsafe_allow_html=True)

    node_table = []
    order = {"alarm": 0, "warning": 1, "ok": 2}
    for nid, state in sorted(node_states.items(), key=lambda x: (order[x[1]["status"]], x[0])):
        node_table.append({
            "Node": f"Node {nid}",
            "Status": STATUS_LABEL[state["status"]],
            "Pressure (bar)": state["pressure"],
            "Flow (m³/h)": state["flow"],
            "Demand (m³/h)": state["demand"],
            "Leak Probability": f"{state['probability']:.3f}",
        })
    st.dataframe(pd.DataFrame(node_table), use_container_width=True, hide_index=True)

    st.markdown(f"""<div class="guide-box-bottom">
    <h4>About This Page</h4>
    The map data is derived from the <b>Hanoi water network</b> EPANET model used in the LeakDB
    project. This topology of 32 measurement nodes and 34 pipe segments represents a real network
    structure; the geographic coordinates, however, have been mathematically scaled and repositioned
    around the selected municipality's center.<br><br>
    <b>Map color coding:</b> red nodes indicate an active alarm (suspected leak), amber/yellow
    indicates a warning state, and green indicates normal operation. Red pipe segments mark
    connections where at least one endpoint is in alarm.
    </div>""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: ISOLATED MEASUREMENT ZONES
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Isolated Measurement Zones":
    render_page_header("Isolated Measurement Zones")

    st.markdown("""<div class="guide-box-top">
    Zone-level water balance and loss analysis. The riskiest zones are shown first; each zone
    tracks an estimated loss rate and its number of active alarms.
    </div>""", unsafe_allow_html=True)

    isolated_zones = mun["isolated_zones"]
    node_assignments = get_node_assignments(municipality_choice, len(isolated_zones))
    demo_alarm_nodes = [PRESSURE_NODE_IDS[3]]
    node_states = get_node_states(municipality_choice, demo_alarm_nodes, seed_offset=2)

    zone_data = []
    for idx, zone in enumerate(isolated_zones):
        zone_nodes = [nid for nid, z in node_assignments.items() if z == idx]
        zone_node_states = [node_states[nid] for nid in zone_nodes if nid in node_states]
        alarm_in_zone = sum(1 for s in zone_node_states if s["status"] == "alarm")
        avg_pressure = np.mean([s["pressure"] for s in zone_node_states]) if zone_node_states else 0
        avg_flow = sum(s["flow"] for s in zone_node_states) if zone_node_states else 0
        risk = "High" if alarm_in_zone > 0 else ("Medium" if any(s["status"] == "warning" for s in zone_node_states) else "Low")
        risk_order = {"High": 0, "Medium": 1, "Low": 2}
        loss = round(random.Random(idx + hash(municipality_choice)).uniform(8, 18), 1) if risk == "High" else round(random.Random(idx + hash(municipality_choice)).uniform(1, 5), 1)
        zone_data.append({
            "_risk_order": risk_order[risk],
            "Zone": zone,
            "Risk": risk,
            "Avg. Pressure (bar)": round(avg_pressure, 2),
            "Total Flow (m³/h)": round(avg_flow, 1),
            "Estimated Loss (%)": loss,
            "Node Count": len(zone_nodes),
            "Active Alarms": alarm_in_zone,
        })
    zone_data.sort(key=lambda x: x["_risk_order"])

    cols = st.columns(len(zone_data))
    for col, row in zip(cols, zone_data):
        with col:
            cls = "alarm" if row["Risk"] == "High" else ("warning" if row["Risk"] == "Medium" else "ok")
            st.markdown(f"""<div class="metric-card {cls}">
                <div class="metric-label">{row['Zone']}</div>
                <div class="metric-value">{row['Estimated Loss (%)']:.1f}%</div>
                <div class="metric-sub">Estimated water loss</div>
                <div style="margin-top:11px;font-size:12.5px;color:{COLORS['text_muted']}">
                    Pressure: <span style="font-family:JetBrains Mono">{row['Avg. Pressure (bar)']} bar</span><br>
                    Active Alarms: <span style="font-family:JetBrains Mono;color:{COLORS['alarm'] if row['Active Alarms']>0 else COLORS['ok']}">{row['Active Alarms']}</span>
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px">Zone Comparison Table</div>', unsafe_allow_html=True)
    display_df = pd.DataFrame([{k: v for k, v in d.items() if k != "_risk_order"} for d in zone_data])
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px">24-Hour Pressure Trend by Zone</div>', unsafe_allow_html=True)
    hours = list(range(24))
    trend_data = {}
    for row in zone_data:
        base = row["Avg. Pressure (bar)"] or 4.0
        rnd = random.Random(hash(row["Zone"]))
        series = [round(base + math.sin(h / 3) * 0.3 + rnd.gauss(0, 0.1), 2) for h in hours]
        if row["Risk"] == "High":
            series[18:] = [round(s - rnd.uniform(0.5, 0.9), 2) for s in series[18:]]
        trend_data[row["Zone"].split(" ")[0]] = series
    df_trend = pd.DataFrame(trend_data, index=[f"{h:02d}:00" for h in hours])
    st.line_chart(df_trend, height=240)

    st.markdown(f"""<div class="guide-box-bottom">
    <h4>About This Page</h4>
    An <b>Isolated Measurement Zone (IMZ)</b> is an independently metered sub-area of the network,
    created so that water balance and leak risk can be monitored zone by zone. Inflow and outflow
    are measured at each IMZ boundary to compute a zone-specific estimated loss rate.<br><br>
    <b>Color coding:</b> red zones currently have an active alarm and require priority response.
    Amber/yellow zones show abnormal readings that warrant close monitoring. Green zones are within
    normal operating range.<br><br>
    The <b>24-hour trend chart</b> shows pressure changes by zone. Pressure drops detected during
    overnight low-demand hours (22:00–06:00) are particularly meaningful, since legitimate
    consumption is at its minimum during that window.
    </div>""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: DATA ANALYSIS (Manual Test + Live Feed)
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Data Analysis":
    render_page_header("Data Analysis")

    st.markdown("""<div class="guide-box-top">
    Two analysis modes: <b>Manual Test</b> lets you enter sensor values yourself to see how the
    detection logic responds. <b>Live Feed</b> shows the real-time prediction stream coming from the API.
    </div>""", unsafe_allow_html=True)

    tab_manual, tab_live = st.tabs(["Manual Test", "Live Feed"])

    # ── Tab 1: Manual Test (independent of API) ─────────────────────────────────
    with tab_manual:
        st.markdown(f"""
        <div style="margin:16px 0 20px 0;padding:15px 19px;background:{COLORS['panel_alt']};border-radius:10px;font-size:13.5px;color:{COLORS['text_muted']};border:1px solid {COLORS['border']}">
            This tab runs <b>completely independently of the API</b>. Enter sensor values manually;
            leak detection is performed using a simple rule-based evaluation that mimics the model's logic.
            To test the real model, use the <b>Live Feed</b> tab.
        </div>
        """, unsafe_allow_html=True)

        col_form, col_result = st.columns([1, 1])

        with col_form:
            st.markdown(f'<div style="font-size:14px;font-weight:700;color:{COLORS["text"]};margin-bottom:17px">Sensor Value Input</div>', unsafe_allow_html=True)

            hour_val = st.slider("Measurement Hour (0–23)", 0, 23, datetime.now().hour)

            st.markdown(f'<div style="font-size:12.5px;color:{COLORS["text_muted"]};margin:17px 0 11px;font-weight:700">Pressure Values (bar) — Sample Nodes</div>', unsafe_allow_html=True)
            node_cols = st.columns(3)
            p_values = {}
            sample_nodes = [2, 5, 10, 15, 20, 25]
            for idx, n in enumerate(sample_nodes):
                with node_cols[idx % 3]:
                    p_values[f"P_Node_{n}"] = st.number_input(
                        f"Node {n}", value=4.0, step=0.1, key=f"mt_p{n}",
                        min_value=0.0, max_value=10.0
                    )

            st.markdown(f'<div style="font-size:12.5px;color:{COLORS["text_muted"]};margin:17px 0 11px;font-weight:700">Flow Values (m³/h) — Sample Links</div>', unsafe_allow_html=True)
            link_cols = st.columns(3)
            f_values = {}
            sample_links = [1, 5, 10, 15, 20, 25]
            for idx, n in enumerate(sample_links):
                with link_cols[idx % 3]:
                    f_values[f"F_Link_{n}"] = st.number_input(
                        f"Link {n}", value=2.0, step=0.1, key=f"mt_f{n}",
                        min_value=0.0, max_value=20.0
                    )

            manual_test_btn = st.button("Run Analysis", use_container_width=True, key="manual_test_btn")

        with col_result:
            st.markdown(f'<div style="font-size:14px;font-weight:700;color:{COLORS["text"]};margin-bottom:17px">Analysis Result</div>', unsafe_allow_html=True)

            if manual_test_btn:
                # Rule-based evaluation, independent of the API
                avg_pressure = np.mean(list(p_values.values()))
                min_pressure = min(p_values.values())
                avg_flow = np.mean(list(f_values.values()))

                leak_score = 0.0
                reasons = []

                if min_pressure < 2.0:
                    leak_score += 0.45
                    reasons.append(f"Critically low pressure: {min_pressure:.2f} bar")
                elif min_pressure < 3.0:
                    leak_score += 0.25
                    reasons.append(f"Low pressure: {min_pressure:.2f} bar")

                if avg_pressure < 2.5:
                    leak_score += 0.30
                    reasons.append(f"Low average pressure: {avg_pressure:.2f} bar")

                if 0 <= hour_val <= 5 and avg_flow > 3.5:
                    leak_score += 0.30
                    reasons.append(f"High overnight flow: {avg_flow:.2f} m³/h")

                if avg_flow > 5.0:
                    leak_score += 0.20
                    reasons.append(f"Abnormally high flow: {avg_flow:.2f} m³/h")

                leak_score = min(leak_score, 0.99)
                pred = 1 if leak_score >= 0.45 else 0

                cls = "alarm" if pred == 1 else "ok"
                verdict = "SUSPECTED LEAK" if pred == 1 else "NORMAL"
                verdict_color = COLORS["alarm"] if pred == 1 else COLORS["ok"]

                st.markdown(f"""<div class="metric-card {cls}" style="margin-bottom:18px">
                    <div class="metric-label">Manual Test Result</div>
                    <div style="font-size:27px;font-weight:800;color:{verdict_color};font-family:JetBrains Mono">{verdict}</div>
                    <div class="metric-sub">Computed risk score: <span style="font-family:JetBrains Mono;color:{verdict_color};font-weight:700">{leak_score:.3f}</span></div>
                </div>""", unsafe_allow_html=True)

                if reasons:
                    st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:9px">Detection Reasons</div>', unsafe_allow_html=True)
                    for s in reasons:
                        icon = "🔴" if pred == 1 else "⚠️"
                        st.markdown(f'<div style="font-size:13px;padding:9px 13px;background:{COLORS["panel_alt"]};border-radius:8px;margin-bottom:7px;color:{COLORS["text"]};border:1px solid {COLORS["border"]}">{icon} {s}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="font-size:13px;padding:13px;background:{COLORS["ok_bg"]};border-radius:8px;color:{COLORS["ok"]};border:1px solid {COLORS["ok"]}">✓ All values within normal range.</div>', unsafe_allow_html=True)

                st.session_state.manual_test_log.append({
                    "Time": datetime.now().strftime("%H:%M:%S"),
                    "Result": verdict,
                    "Risk Score": f"{leak_score:.3f}",
                    "Min. Pressure": f"{min_pressure:.2f} bar",
                    "Avg. Flow": f"{avg_flow:.2f} m³/h",
                    "Hour": hour_val,
                })
            else:
                st.markdown(f'<div style="color:{COLORS["text_faint"]};font-size:13.5px;padding:55px 0;text-align:center">Enter values and click "Run Analysis".</div>', unsafe_allow_html=True)

            if st.session_state.manual_test_log:
                st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:9px">Session History</div>', unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(st.session_state.manual_test_log[-10:]), use_container_width=True, hide_index=True)

    # ── Tab 2: Live Feed (from the API) ─────────────────────────────────────────
    with tab_live:
        st.markdown(f"""
        <div style="margin:16px 0 20px 0;padding:15px 19px;background:{COLORS['panel_alt']};border-radius:10px;font-size:13.5px;color:{COLORS['text_muted']};border:1px solid {COLORS['border']}">
            This tab sends a real <code>/predict</code> request to the FastAPI backend and shows the
            model's raw prediction output. <b>Connection status:</b>
            {"<span style='color:" + COLORS['ok'] + ";font-weight:700'> Online</span>" if st.session_state.api_online else "<span style='color:" + COLORS['alarm'] + ";font-weight:700'> Offline</span>"}
        </div>
        """, unsafe_allow_html=True)

        col_live_form, col_live_result = st.columns([1, 1])

        with col_live_form:
            st.markdown(f'<div style="font-size:14px;font-weight:700;color:{COLORS["text"]};margin-bottom:17px">API Request Parameters</div>', unsafe_allow_html=True)

            hour_live = st.slider("Measurement Hour (0–23)", 0, 23, datetime.now().hour, key="live_hour")

            st.markdown(f'<div style="font-size:12.5px;color:{COLORS["text_muted"]};margin:17px 0 11px;font-weight:700">Pressure Values (bar)</div>', unsafe_allow_html=True)
            live_cols = st.columns(3)
            lp_values = {}
            for idx, n in enumerate(sample_nodes):
                with live_cols[idx % 3]:
                    lp_values[f"P_Node_{n}"] = st.number_input(
                        f"Node {n}", value=4.0, step=0.1, key=f"lp{n}",
                        min_value=0.0, max_value=10.0
                    )

            st.markdown(f'<div style="font-size:12.5px;color:{COLORS["text_muted"]};margin:17px 0 11px;font-weight:700">Flow Values (m³/h)</div>', unsafe_allow_html=True)
            live_link_cols = st.columns(3)
            lf_values = {}
            for idx, n in enumerate(sample_links):
                with live_link_cols[idx % 3]:
                    lf_values[f"F_Link_{n}"] = st.number_input(
                        f"Link {n}", value=2.0, step=0.1, key=f"lf{n}",
                        min_value=0.0, max_value=20.0
                    )

            live_btn = st.button("Send to API", use_container_width=True, key="live_btn")

        with col_live_result:
            st.markdown(f'<div style="font-size:14px;font-weight:700;color:{COLORS["text"]};margin-bottom:17px">API Response</div>', unsafe_allow_html=True)

            if live_btn:
                payload = {}
                for i in PRESSURE_NODE_IDS:
                    payload[f"P_Node_{i}"] = lp_values.get(f"P_Node_{i}", 4.0)
                for i in FLOW_LINK_IDS:
                    payload[f"F_Link_{i}"] = lf_values.get(f"F_Link_{i}", 2.0)
                for i in DEMAND_NODE_IDS:
                    payload[f"D_Node_{i}"] = 1.5
                payload["hour"] = hour_live
                payload["timestamp"] = datetime.now().isoformat()

                with st.spinner("Sending request to API..."):
                    try:
                        resp = requests.post(f"{API_URL}/predict", json=payload, timeout=8)
                        data = resp.json()
                        pred = data.get("prediction", 0)
                        proba = data.get("leak_probability", 0.0)
                        suspicious = data.get("suspicious_nodes", [])
                        api_ok = True
                    except Exception as e:
                        api_ok = False
                        pred, proba, suspicious = 0, 0.0, []
                        api_err = str(e)

                if not api_ok:
                    st.markdown(f"""
                    <div class="metric-card alarm">
                        <div class="metric-label">Connection Error</div>
                        <div style="font-size:14.5px;color:{COLORS['alarm']};font-weight:700">Could not reach the API</div>
                        <div class="metric-sub">{api_err}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    cls = "alarm" if pred == 1 else "ok"
                    verdict = "LEAK DETECTED" if pred == 1 else "NORMAL"
                    verdict_color = COLORS["alarm"] if pred == 1 else COLORS["ok"]

                    st.markdown(f"""<div class="metric-card {cls}" style="margin-bottom:18px">
                        <div class="metric-label">API Prediction Result</div>
                        <div style="font-size:25px;font-weight:800;color:{verdict_color};font-family:JetBrains Mono">{verdict}</div>
                        <div class="metric-sub">Leak probability: <span style="font-family:JetBrains Mono;color:{verdict_color};font-weight:700">{proba:.4f}</span></div>
                    </div>""", unsafe_allow_html=True)

                    if suspicious:
                        st.markdown(f"""
                        <div class="metric-card alarm">
                            <div class="metric-label">Suspicious Measurement Nodes</div>
                            <div style="font-family:JetBrains Mono;font-size:13.5px;color:{COLORS['text']}">{", ".join(suspicious)}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with st.expander("Raw API Response (JSON)", expanded=False):
                        st.json(data)
            else:
                st.markdown(f'<div style="color:{COLORS["text_faint"]};font-size:13.5px;padding:55px 0;text-align:center">Enter parameters and click "Send to API".</div>', unsafe_allow_html=True)

    st.markdown(f"""<div class="guide-box-bottom">
    <h4>About This Page</h4>
    <b>Manual Test</b> can be used to understand the leak detection logic even without an API
    connection. The pressure and flow values you enter are evaluated using a rule-based risk
    score: critical pressure drops and abnormal overnight flow are among the signals considered.
    This tab is designed for training, demos and offline environments.<br><br>
    <b>Live Feed</b> sends a request to the real XGBoost model on the FastAPI backend. The model
    evaluates 161 features (pressure, flow and demand values across all measurement nodes, plus
    the hour of day) to compute a leak probability and return any suspicious nodes. If the API is
    offline, this tab returns a connection error; you can check the connection using the
    "Refresh Connection" button in the sidebar.
    </div>""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: GUIDE
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Guide":
    render_page_header("Guide", subtitle="Project overview, methodology and how to use LYDIA")

    st.markdown("""<div class="guide-box-top">
    A complete walkthrough of why LYDIA exists, how each module works, and what the underlying
    calculations mean — written for anyone evaluating the project, not just engineers.
    </div>""", unsafe_allow_html=True)

    # ── 1. Purpose & Problem ─────────────────────────────────────────────────
    st.markdown(f"""<div class="guide-section-title"><span class="guide-section-number">1</span>Purpose &amp; Problem</div>""", unsafe_allow_html=True)
    st.markdown(f"""<div class="guide-card">
    Water utilities lose a significant share of treated water before it ever reaches a consumer —
    through undetected leaks, aging pipes and delayed fault response. This is known as
    <b>Non-Revenue Water (NRW)</b>: water that is produced and treated, but never billed because it
    escapes the network. In many municipal systems, especially older or under-instrumented ones,
    leaks are only discovered after they surface — long after the water, energy and treatment cost
    are already gone.<br><br>
    The core problem <b>LYDIA</b> ({APP_FULL_NAME}) addresses is detection speed and precision:
    turning raw pressure and flow readings into an early, localized, high-confidence leak alert —
    before a technician is dispatched, and ideally before the leak becomes visible on the surface.
    </div>""", unsafe_allow_html=True)

    # ── 2. How Detection Works ───────────────────────────────────────────────
    st.markdown(f"""<div class="guide-section-title"><span class="guide-section-number">2</span>How Leak Detection Works</div>""", unsafe_allow_html=True)
    st.markdown(f"""<div class="guide-card">
    LYDIA's detection engine is an <b>XGBoost</b> classification model — a gradient-boosted decision
    tree ensemble well suited to structured sensor data. The model was trained incrementally on the
    <b>LeakDB</b> dataset, using the Hanoi benchmark network topology (32 measurement nodes,
    34 pipe segments, 1 reservoir).<br><br>
    For every 30-minute reading cycle, the model receives <b>161 engineered features</b>: pressure
    at every node, flow through every pipe segment, demand at every node, and the hour of day.
    It outputs a probability that the current network state reflects a leak, rather than a simple
    yes/no — which lets the interface show a graded risk level (Normal / Warning / Alarm) instead
    of a binary flag.
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="formula-box">
    leak_probability = XGBoost(P_Node_1 ... P_Node_32, F_Link_1 ... F_Link_34, D_Node_1 ... D_Node_32, hour)<br>
    <br>
    if leak_probability ≥ threshold → status = ALARM<br>
    if leak_probability ≥ warning_threshold → status = WARNING<br>
    else → status = NORMAL
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="guide-card">
    <b>Training and evaluation:</b> the model was trained on 700 simulated scenarios (roughly
    12.3 million time steps) and evaluated on a held-out set of 150 scenarios (2,628,000 steps)
    that it never saw during training. On that independent test set, it reaches
    <b>82% overall accuracy</b>, with <b>59% precision</b> and <b>53% recall</b> specifically on the
    leak class. These numbers describe performance on simulated LeakDB data — see the
    <b>System &amp; Model</b> page for the full breakdown and honest limitations.
    </div>""", unsafe_allow_html=True)

    # ── 3. What the Numbers Mean ─────────────────────────────────────────────
    st.markdown(f"""<div class="guide-section-title"><span class="guide-section-number">3</span>What The Numbers On Screen Mean</div>""", unsafe_allow_html=True)
    st.markdown(f"""<div class="guide-card">
    <b>Pressure (bar):</b> water pressure measured at a node. A sustained drop below the expected
    range (roughly 3.0 bar or higher under normal conditions in this simulated network) is one of
    the strongest leak indicators, since a leak reduces downstream pressure.<br><br>
    <b>Flow (m³/h):</b> the rate of water moving through a pipe segment. Unusually high flow —
    especially overnight, when legitimate household demand is at its lowest — often signals water
    escaping the system rather than being consumed.<br><br>
    <b>Leak probability:</b> the model's confidence, from 0 to 1, that the current readings reflect
    a real leak rather than normal operating variation. This is the number the Alarm / Warning /
    Normal status is derived from.<br><br>
    <b>Estimated loss (%):</b> on the Isolated Measurement Zones page, this is a zone-level estimate
    of how much of the water entering that zone is not accounted for by legitimate demand —
    the practical, zone-scoped version of Non-Revenue Water.
    </div>""", unsafe_allow_html=True)

    # ── 4. Module-by-module guide ────────────────────────────────────────────
    st.markdown(f"""<div class="guide-section-title"><span class="guide-section-number">4</span>How Each Module Works</div>""", unsafe_allow_html=True)
    st.markdown(f"""<div class="guide-card">
    <b>Live Monitoring</b> — the operational front line. Shows every node's live status on a real
    map, ranks nodes by severity in the side list, and lets an operator trigger a field dispatch
    the moment an alarm appears.<br><br>
    <b>Network Map</b> — the same network at a more detailed, exploratory level: a full data table
    alongside the map, useful for reviewing every node's exact readings rather than just the
    active alarms.<br><br>
    <b>Isolated Measurement Zones</b> — aggregates nodes into sub-regions (IMZs) so that water loss
    can be reasoned about at the neighborhood level rather than the individual-node level, which is
    closer to how utilities actually plan interventions and budget repairs.<br><br>
    <b>Data Analysis → Manual Test</b> — a sandbox that runs a transparent, rule-based approximation
    of the detection logic locally, with no API required. Useful for demonstrating <i>why</i> a
    reading would be flagged, in plain rules rather than a black-box model call.<br><br>
    <b>Data Analysis → Live Feed</b> — sends the exact same kind of payload to the real, deployed
    XGBoost model via the FastAPI backend, and shows its raw response. This is the module that
    proves the model is live, not just described.<br><br>
    <b>System &amp; Model</b> — the technical appendix: architecture, training data, full performance
    metrics, and an explicit statement of what is implemented versus what remains future work.
    </div>""", unsafe_allow_html=True)

    # ── 5. MVP scope & honesty ────────────────────────────────────────────────
    st.markdown(f"""<div class="guide-section-title"><span class="guide-section-number">5</span>Using This MVP Responsibly</div>""", unsafe_allow_html=True)
    st.markdown(f"""<div class="guide-card">
    This is a <b>Minimum Viable Product</b>, not a finished utility platform. The prediction engine
    is real and evaluated on held-out data, but the sensor readings driving the demo are simulated,
    not pulled from physical hardware. The municipalities shown (Merzifon, Uluborlu, Bolu) are
    representative deployment targets used to demonstrate that the same network logic can be
    repositioned onto real geography — they are not confirmed operating pilots.<br><br>
    Before any real deployment, the model would need retraining on genuine local sensor data,
    field validation against known leak events, and a security review of the dispatch pipeline.
    Treat every number on this dashboard as a demonstration of capability, not a live operational
    guarantee — and see the <b>System &amp; Model</b> page for the complete, unfiltered breakdown.
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="guide-box-bottom">
    <h4>Where To Go Next</h4>
    If you want the live operational view, start on <b>Live Monitoring</b>. If you want to
    understand the model's real accuracy and what's implemented versus planned, go to
    <b>System &amp; Model</b>. If you want to test the detection logic yourself with your own
    numbers, use <b>Data Analysis → Manual Test</b>.
    </div>""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: SYSTEM & MODEL
# ═════════════════════════════════════════════════════════════════════════════
elif page == "System & Model":
    render_page_header("System & Model")

    st.markdown(f"""<div class="guide-box-top">
    {APP_NAME}'s technical infrastructure, model performance and MVP scope. A reference page for
    the jury and technical reviewers.
    </div>""", unsafe_allow_html=True)

    # MVP warning banner — prominent, at the top
    st.markdown(f"""
    <div class="mvp-banner">
        <b>⚠️ This Is An MVP Prototype — Not A Finished Product</b><br><br>
        {APP_NAME} is a <b>Minimum Viable Product (MVP)</b> developed for the AI for Sustainability
        competition. An MVP is an early-stage prototype built to validate a product's core
        functionality — it is not ready for full-scale deployment.<br><br>
        All data used in this system is derived from the <b>LeakDB simulation dataset</b>. Map
        coordinates, zone names and addresses represent a realistic but simulated topology, not a
        real municipality's infrastructure. Before use by any actual municipality, this system would
        need to be retrained on local network data, validated in the field, and subjected to a
        security review.
    </div>
    """, unsafe_allow_html=True)

    col_sys, col_model = st.columns(2)

    with col_sys:
        st.markdown(f'<div style="font-size:14px;font-weight:700;color:{COLORS["text"]};margin-bottom:15px">System Information</div>', unsafe_allow_html=True)
        sys_items = [
            ("Model Type", "XGBoost — Incremental Training"),
            ("Training Data", "LeakDB — Hanoi Network Topology"),
            ("Feature Count", "161"),
            ("Training Steps", "~12.3 million"),
            ("Evaluation Cycle", "Every 30 minutes"),
            ("API Infrastructure", "FastAPI (Cloud Server)"),
            ("Interface", "Streamlit (Cloud Server)"),
            ("Stage", "MVP / Prototype"),
        ]
        for label, val in sys_items:
            st.markdown(f"""<div class="node-row" style="margin-bottom:7px">
                <div class="metric-label" style="margin:0">{label}</div>
                <div style="font-family:JetBrains Mono;font-size:12.5px;color:{COLORS['text']}">{val}</div>
            </div>""", unsafe_allow_html=True)

    with col_model:
        st.markdown(f'<div style="font-size:14px;font-weight:700;color:{COLORS["text"]};margin-bottom:15px">Model Performance <span class="hint">Held-out test set</span></div>', unsafe_allow_html=True)
        perf_items = [
            ("Accuracy", "82%", "ok"),
            ("Leak Precision", "59%", "ok"),
            ("Leak Recall", "53%", ""),
            ("Leak F1 Score", "56%", ""),
            ("Train / Test Split", "700 / 150 Scenarios", ""),
            ("Test Steps", "2,628,000", ""),
        ]
        for item in perf_items:
            label, val = item[0], item[1]
            cls = item[2] if len(item) > 2 else ""
            row_cls = f"node-row {cls}" if cls else "node-row"
            st.markdown(f"""<div class="{row_cls}" style="margin-bottom:7px">
                <div class="metric-label" style="margin:0">{label}</div>
                <div style="font-family:JetBrains Mono;font-size:12.5px;color:{COLORS['text']}">{val}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # MVP explainer
    st.markdown(f'<div style="font-size:14px;font-weight:700;color:{COLORS["text"]};margin-bottom:15px">What Is An MVP? What Does This System Actually Prove?</div>', unsafe_allow_html=True)

    mvp_cols = st.columns(3)
    mvp_items = [
        ("Proven", "An XGBoost model trained on simulated water network data can detect leaks with 82% accuracy on data it has never seen."),
        ("Demonstrated", "A FastAPI + Streamlit architecture supports a real-time prediction pipeline end to end. The Folium map integration provides genuine topology visualization."),
        ("Not Yet Done", "Real sensor hardware integration, field validation against actual leak events, a security audit, and retraining on real local network data."),
    ]
    for col, (title, desc) in zip(mvp_cols, mvp_items):
        with col:
            st.markdown(f"""<div style="background:{COLORS['panel']};border-radius:12px;padding:19px;border:1px solid {COLORS['border']}">
                <div style="font-size:12px;font-weight:800;color:{COLORS['navy']};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:9px">{title}</div>
                <div style="font-size:13px;color:{COLORS['text_muted']};line-height:1.65">{desc}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:14px;font-weight:700;color:{COLORS["text"]};margin-bottom:15px">Data Pipeline</div>', unsafe_allow_html=True)

    pipeline_steps = [
        ("1", "LeakDB Dataset", "17,520 steps/scenario, 1,000 scenarios"),
        ("2", "Feature Engineering", "161 features: pressure, flow, demand, time"),
        ("3", "Incremental Training", "100 scenarios/batch × 7 batches, XGBoost"),
        ("4", "FastAPI Service", "/predict → 161 features → live prediction"),
        ("5", "Streamlit Interface", "Live monitoring, map, zone analysis"),
    ]
    p_cols = st.columns(5)
    for col, (num, title, desc) in zip(p_cols, pipeline_steps):
        with col:
            st.markdown(f"""<div style="background:{COLORS['panel']};border-radius:12px;padding:17px;border:1px solid {COLORS['border']};text-align:center">
                <div style="font-family:JetBrains Mono;font-size:21px;font-weight:700;color:{COLORS['navy']}">{num}</div>
                <div style="font-size:12.5px;font-weight:700;color:{COLORS['text']};margin:7px 0 4px">{title}</div>
                <div style="font-size:11px;color:{COLORS['text_muted']};line-height:1.45">{desc}</div>
            </div>""", unsafe_allow_html=True)

    # Telegram configuration note
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:14px;font-weight:700;color:{COLORS["text"]};margin-bottom:15px">Telegram Integration — Configuration</div>', unsafe_allow_html=True)

    tg_status_ok = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    tg_cls = "ok" if tg_status_ok else "warning"
    tg_msg = "Telegram configuration is active." if tg_status_ok else "Telegram configuration is missing — BOT_TOKEN or CHAT_ID is not set."

    st.markdown(f"""
    <div class="metric-card {tg_cls}">
        <div class="metric-label">Telegram Bot Status</div>
        <div style="font-size:14.5px;font-weight:700;color:{COLORS[tg_cls]};margin-bottom:9px">
            {"✅ Active" if tg_status_ok else "⚠️ Not Configured"}
        </div>
        <div style="font-size:13px;color:{COLORS['text_muted']};line-height:1.8">
            {tg_msg}<br><br>
            To enable it, set two environment variables on Onrender:<br>
            <span style="font-family:JetBrains Mono;background:{COLORS['panel_alt']};padding:2px 8px;border-radius:5px">TELEGRAM_BOT_TOKEN</span> — the bot token from BotFather<br>
            <span style="font-family:JetBrains Mono;background:{COLORS['panel_alt']};padding:2px 8px;border-radius:5px">TELEGRAM_CHAT_ID</span> — the field team group chat ID<br>
            <br>
            To find the group ID, add @userinfobot or @getidsbot to the group.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""<div class="guide-box-bottom">
    <h4>About This Page</h4>
    This page transparently documents {APP_NAME}'s technical infrastructure, model performance and
    MVP limitations. It is intended as a reference for the competition jury and technical
    reviewers.<br><br>
    <b>About the model:</b> the XGBoost model was trained incrementally on Hanoi network
    simulations from the LeakDB open dataset. The 82% accuracy figure was measured on an
    independent test set; performance under real network conditions may differ.<br><br>
    <b>About the Telegram integration:</b> when the <b>Dispatch Team</b> button is clicked, the
    system uses the Telegram Bot API to notify a pre-configured field team group — only two
    environment variables are required. A production implementation could extend this to multiple
    groups (field team, management) and an acknowledgement/confirmation workflow.
    </div>""", unsafe_allow_html=True)
