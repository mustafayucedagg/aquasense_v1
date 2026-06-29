import streamlit as st
import pandas as pd
import numpy as np
import math
import random
import os
from datetime import datetime, timedelta

# streamlit-folium opsiyonel
try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

import requests

# ─────────────────────────────────────────────────────────────────────────────
# SAYFA AYARLARI
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AquaSense — Su Şebekesi İzleme Sistemi",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# TASARIM TOKEN'LARI
# ─────────────────────────────────────────────────────────────────────────────
COLORS_LIGHT = {
    "navy": "#0B1C36",
    "navy_light": "#16315C",
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

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "belediye": "Merzifon Belediyesi",
        "dark_mode": False,
        "alarm_log": [],
        "ekip_gonderildi": [],
        "manuel_tahmin_log": [],
        "secili_node": None,
        "api_durumu_kontrol_edildi": False,
        "api_aktif": False,
        "telegram_son_mesaj": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# Aktif renk paleti
COLORS = COLORS_DARK if st.session_state.dark_mode else COLORS_LIGHT

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [data-testid="stAppViewContainer"], .main {{
    background-color: {COLORS['bg']} !important;
    color: {COLORS['text']};
    font-family: 'Inter', sans-serif;
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
    padding: 9px 12px;
    margin-bottom: 2px;
    transition: background 0.15s ease;
    font-size: 14px !important;
}}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {{
    background: rgba(255,255,255,0.08);
}}

/* Ana içerik alanı */
[data-testid="stMain"] {{
    background-color: {COLORS['bg']} !important;
}}
section[data-testid="stMain"] > div {{
    background-color: {COLORS['bg']} !important;
}}

/* Başlıklar */
h1, h2, h3, h4 {{ font-family: 'Inter', sans-serif; font-weight: 700; color: {COLORS['text']} !important; }}

/* Rehber metin kutusu - üst (kısa) */
.guide-box-top {{
    background: {COLORS['panel_alt']};
    border-left: 4px solid {COLORS['navy']};
    border-radius: 0 8px 8px 0;
    padding: 12px 18px;
    margin-bottom: 18px;
    font-size: 13.5px;
    color: {COLORS['text']};
    font-weight: 600;
    line-height: 1.5;
}}

/* Rehber metin kutusu - alt (detaylı) */
.guide-box-bottom {{
    background: {COLORS['panel_alt']};
    border: 1px solid {COLORS['border']};
    border-top: 3px solid {COLORS['navy']};
    border-radius: 8px;
    padding: 18px 22px;
    margin-top: 30px;
    font-size: 12.5px;
    color: {COLORS['text_muted']};
    line-height: 1.75;
}}
.guide-box-bottom h4 {{
    font-size: 12px !important;
    font-weight: 700 !important;
    color: {COLORS['text']} !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 8px !important;
}}
.guide-box-bottom b {{ color: {COLORS['text']} !important; }}

/* İpucu balonu */
.hint {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 11.5px;
    color: {COLORS['text_faint']};
    background: {COLORS['panel_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: 20px;
    padding: 3px 10px;
    margin-left: 8px;
}}

/* Metrik kartlar */
.metric-card {{
    background: {COLORS['panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}}
.metric-card.alarm {{ border-color: {COLORS['alarm']}; background: {COLORS['alarm_bg']}; border-width: 2px; }}
.metric-card.warning {{ border-color: {COLORS['warning']}; background: {COLORS['warning_bg']}; border-width: 2px; }}
.metric-card.ok {{ border-color: {COLORS['ok']}; background: {COLORS['ok_bg']}; }}
.metric-label {{
    font-size: 10.5px; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase;
    color: {COLORS['text_faint']}; margin-bottom: 6px;
}}
.metric-value {{
    font-family: 'JetBrains Mono', monospace; font-size: 28px; font-weight: 600; color: {COLORS['text']};
}}
.metric-sub {{ font-size: 11.5px; color: {COLORS['text_muted']}; margin-top: 4px; }}

/* Durum rozeti */
.badge {{
    font-family: 'JetBrains Mono', monospace; font-size: 10.5px; padding: 4px 10px;
    border-radius: 5px; font-weight: 700; letter-spacing: 0.03em;
}}
.badge-alarm {{ background: {COLORS['alarm']}; color: #fff; }}
.badge-warning {{ background: {COLORS['warning']}; color: #fff; }}
.badge-ok {{ background: {COLORS['ok']}; color: #fff; }}

/* Ölçüm noktası satırı */
.node-row {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 16px; border-radius: 8px; margin-bottom: 6px;
    background: {COLORS['panel']}; border: 1px solid {COLORS['border']}; font-size: 13px;
    color: {COLORS['text']};
}}
.node-row.alarm {{ background: {COLORS['alarm_bg']}; border-color: {COLORS['alarm']}; border-width: 2px; }}
.node-row.warning {{ background: {COLORS['warning_bg']}; border-color: {COLORS['warning']}; }}

/* Durum göstergesi */
.status-pill {{
    display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 700;
    padding: 6px 14px; border-radius: 20px; background: {COLORS['ok_bg']}; color: {COLORS['ok']};
    border: 1px solid {COLORS['ok']};
}}
.status-pill.offline {{ background: {COLORS['alarm_bg']}; color: {COLORS['alarm']}; border-color: {COLORS['alarm']}; }}
.status-dot {{
    width: 7px; height: 7px; border-radius: 50%; background: currentColor;
    animation: pulse-dot 2s infinite;
}}
@keyframes pulse-dot {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.35; }} }}

/* Sekmeler */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background: transparent; border-bottom: 2px solid {COLORS['border']}; gap: 4px;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    background: transparent; color: {COLORS['text_muted']} !important; font-size: 13.5px;
    font-weight: 500; padding: 10px 20px;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    color: {COLORS['navy']} !important; border-bottom: 2px solid {COLORS['navy']} !important;
    font-weight: 700 !important;
}}

/* Tablo */
.stDataFrame {{ border: 1px solid {COLORS['border']} !important; border-radius: 8px !important; }}
[data-testid="stDataFrameResizable"] {{ background: {COLORS['panel']} !important; }}

/* Ayırıcı */
.divider {{ border: none; border-top: 1px solid {COLORS['border']}; margin: 24px 0; }}

/* Inputlar */
.stNumberInput input, .stSelectbox > div, .stTextInput input, .stSlider {{
    background: {COLORS['input_bg']} !important; color: {COLORS['text']} !important;
    border: 1px solid {COLORS['border_strong']} !important; border-radius: 8px !important;
}}

/* BUTONLAR — büyük ve canlı */
.stButton button {{
    background: {COLORS['navy']} !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 14px 28px !important;
    font-size: 15px !important;
    transition: all 0.15s ease !important;
    letter-spacing: 0.01em !important;
    min-height: 48px !important;
}}
.stButton button:hover {{
    background: {COLORS['navy_light']} !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
}}
.stButton button:disabled {{
    background: {COLORS['border']} !important;
    color: {COLORS['text_faint']} !important;
    transform: none !important;
    box-shadow: none !important;
}}

/* Ekibi Gönder butonu — kırmızı, büyük */
.action-btn-active button {{
    background: {COLORS['alarm']} !important;
    font-size: 16px !important;
    padding: 16px 32px !important;
    min-height: 56px !important;
    box-shadow: 0 4px 16px rgba(220,38,38,0.4) !important;
    animation: pulse-btn 2s infinite;
}}
.action-btn-active button:hover {{
    background: #B91C1C !important;
    box-shadow: 0 6px 20px rgba(220,38,38,0.5) !important;
}}
@keyframes pulse-btn {{
    0%, 100% {{ box-shadow: 0 4px 16px rgba(220,38,38,0.4); }}
    50% {{ box-shadow: 0 4px 24px rgba(220,38,38,0.7); }}
}}

/* Telegram onay kutusu */
.telegram-banner {{
    background: {COLORS['ok_bg']};
    border: 2px solid {COLORS['ok']};
    border-radius: 10px;
    padding: 18px 20px;
    color: {COLORS['ok']};
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 16px;
    line-height: 1.6;
}}
.telegram-banner .tg-title {{
    font-size: 16px;
    font-weight: 800;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.telegram-banner .tg-detail {{
    font-size: 12.5px;
    font-weight: 400;
    color: {COLORS['text_muted']};
    margin-top: 8px;
    font-family: 'JetBrains Mono', monospace;
    background: {COLORS['panel']};
    border-radius: 6px;
    padding: 10px 14px;
    line-height: 1.8;
}}
.telegram-banner.error {{
    background: {COLORS['warning_bg']};
    border-color: {COLORS['warning']};
    color: {COLORS['warning']};
}}

/* Logo başlığı */
.brand-header {{
    display: flex; align-items: center; gap: 10px; padding: 4px 4px 18px 4px;
}}
.brand-title {{ font-size: 18px; font-weight: 800; color: #fff; letter-spacing: -0.01em; }}
.brand-sub {{ font-size: 10.5px; color: {COLORS['sidebar_muted']}; margin-top: -2px; }}

/* Scrollbar */
::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-track {{ background: {COLORS['bg']}; }}
::-webkit-scrollbar-thumb {{ background: {COLORS['border_strong']}; border-radius: 3px; }}

/* MVP uyarı kutusu */
.mvp-banner {{
    background: {COLORS['warning_bg']};
    border: 2px solid {COLORS['warning']};
    border-radius: 10px;
    padding: 16px 20px;
    color: {COLORS['warning']};
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 20px;
    line-height: 1.6;
}}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# EPANET TOPOLOJİSİ
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
# BELEDİYE VERİSİ
# ─────────────────────────────────────────────────────────────────────────────
BELEDIYELER = {
    "Merzifon Belediyesi": {
        "il": "Amasya",
        "nufus": 42000,
        "merkez": (40.8706, 35.4636),
        "span_km": 1.8,
        "izole_bolgeler": [
            "İÖB-MRZ-1 (Merkez)", "İÖB-MRZ-2 (Sanayi)",
            "İÖB-MRZ-3 (Yeni Mahalle)", "İÖB-MRZ-4 (Kışla)",
        ],
        "ornek_adresler": [
            "Alparslan Mah. 110. Sk. No:14, Merzifon/Amasya",
            "Gazi Mah. Cumhuriyet Cad. No:7, Merzifon/Amasya",
            "Sanayi Mah. 3. Sk. No:22, Merzifon/Amasya",
            "Yeni Mah. Atatürk Bulvarı No:45, Merzifon/Amasya",
        ],
    },
    "Uluborlu Belediyesi": {
        "il": "Isparta",
        "nufus": 8500,
        "merkez": (38.0758, 30.4647),
        "span_km": 1.2,
        "izole_bolgeler": [
            "İÖB-ULB-1 (Merkez)", "İÖB-ULB-2 (Çevre)", "İÖB-ULB-3 (Yüksek Bölge)",
        ],
        "ornek_adresler": [
            "Cumhuriyet Mah. İstasyon Cad. No:9, Uluborlu/Isparta",
            "Yeşilköy Mah. 2. Sk. No:18, Uluborlu/Isparta",
            "Kemer Mah. Atatürk Cad. No:31, Uluborlu/Isparta",
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


def get_node_assignments(bel_key, n_zones):
    node_ids = PRESSURE_NODE_IDS
    chunk = len(node_ids) // n_zones
    assignments = {}
    for i, nid in enumerate(node_ids):
        zone_idx = min(i // max(chunk, 1), n_zones - 1)
        assignments[nid] = zone_idx
    return assignments


def get_node_states(bel_key, alarm_node_ids=None, seed_offset=0):
    rnd = random.Random(hash(bel_key) + seed_offset)
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
# TELEGRAM GÖNDERIM FONKSİYONU
# ─────────────────────────────────────────────────────────────────────────────
def send_telegram_alert(node_id, adres, pressure, probability, bel_adi):
    """
    Telegram Bot API aracılığıyla saha ekibine kaçak alarmı gönderir.
    TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID Onrender'da Environment Variable olarak tanımlanmalıdır.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False, "Telegram bot yapılandırması eksik (BOT_TOKEN veya CHAT_ID tanımlı değil)"

    zaman = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    mesaj = (
        f"🚨 *KAÇAK ALARMI — AquaSense*\n\n"
        f"📍 *Adres:* {adres}\n"
        f"📊 *Ölçüm Noktası:* {node_id}\n"
        f"💧 *Anlık Basınç:* {pressure} bar\n"
        f"⚠️ *Kaçak Olasılığı:* %{probability*100:.1f}\n"
        f"🏛️ *Belediye:* {bel_adi}\n"
        f"🕐 *Tespit Zamanı:* {zaman}\n\n"
        f"Lütfen belirtilen adrese en kısa sürede müdahale edin."
    )

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mesaj,
            "parse_mode": "Markdown",
        }
        resp = requests.post(url, json=payload, timeout=6)
        if resp.status_code == 200:
            return True, mesaj
        else:
            err = resp.json().get("description", "Bilinmeyen hata")
            return False, f"Telegram API hatası: {err}"
    except Exception as e:
        return False, f"Bağlantı hatası: {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# FOLIUM HARİTA
# ─────────────────────────────────────────────────────────────────────────────
STATUS_COLOR = {"alarm": "#DC2626", "warning": "#B45309", "ok": "#0F766E"}
STATUS_LABEL = {"alarm": "Alarm", "warning": "Uyarı", "ok": "Normal"}


def build_network_map(bel_key, node_states, detay_seviyesi="ozet", highlight_node=None):
    bel = BELEDIYELER[bel_key]
    latlon = local_to_latlon(*bel["merkez"], span_km=bel["span_km"])
    center = bel["merkez"]
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
                weight=4 if is_alarm_line else 2.4,
                opacity=0.9 if is_alarm_line else 0.6,
            ).add_to(m)

    if RESERVOIR_ID in latlon:
        folium.CircleMarker(
            location=latlon[RESERVOIR_ID], radius=9,
            color="#FFFFFF" if st.session_state.dark_mode else "#0B1C36",
            fill=True,
            fill_color="#4A90D9" if st.session_state.dark_mode else "#0B1C36",
            fill_opacity=1, weight=2,
            popup=folium.Popup("Rezervuar (Ana Su Kaynağı)", max_width=200),
            tooltip="Rezervuar",
        ).add_to(m)

    for nid, (lat, lon) in latlon.items():
        if nid == RESERVOIR_ID:
            continue
        state = node_states.get(nid, {"status": "ok", "pressure": 0, "flow": 0, "probability": 0})
        status = state["status"]
        color = STATUS_COLOR[status]
        is_highlighted = (highlight_node == nid)
        radius = 11 if status == "alarm" else (8 if detay_seviyesi == "detay" else 7)
        if is_highlighted:
            radius += 4

        popup_html = f"""
        <div style="font-family:Inter,sans-serif;font-size:12.5px;min-width:170px">
            <b>Ölçüm Noktası {nid}</b><br>
            <span style="color:{color};font-weight:600">{STATUS_LABEL[status]}</span><br>
            Basınç: {state['pressure']} bar<br>
            Debi: {state.get('flow', 0)} m³/h<br>
            Kaçak Olasılığı: {state.get('probability', 0):.3f}
        </div>
        """
        folium.CircleMarker(
            location=(lat, lon), radius=radius, color="#FFFFFF",
            fill=True, fill_color=color, fill_opacity=0.92, weight=2,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"Ölçüm Noktası {nid} — {STATUS_LABEL[status]}",
        ).add_to(m)

        if status == "alarm":
            folium.Circle(
                location=(lat, lon), radius=45, color="#DC2626",
                fill=True, fill_opacity=0.12, weight=1, opacity=0.5,
            ).add_to(m)

    return m, latlon


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="brand-header">
        <div class="brand-title">AquaSense</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f'<div class="brand-sub" style="margin-top:-14px;margin-bottom:18px">Su Şebekesi Kaçak Tespit Sistemi</div>', unsafe_allow_html=True)

    sayfa = st.radio(
        label="Navigasyon",
        options=[
            "Canlı İzleme",
            "Şebeke Haritası",
            "İzole Ölçüm Bölgeleri",
            "Veri Analizi",
            "Sistem & Model",
        ],
        label_visibility="collapsed",
    )

    st.markdown('<hr>', unsafe_allow_html=True)

    # Dark/Light mode toggle
    mode_label = "Açık Tema" if st.session_state.dark_mode else "Koyu Tema"
    if st.button(f"{'☀️' if st.session_state.dark_mode else '🌙'} {mode_label}", use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    st.markdown('<hr>', unsafe_allow_html=True)

    st.markdown(f'<div style="font-size:10.5px;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;color:{COLORS["sidebar_muted"]};margin-bottom:8px">Belediye Seçimi</div>', unsafe_allow_html=True)
    bel_secim = st.selectbox("Belediye", list(BELEDIYELER.keys()), label_visibility="collapsed")
    st.session_state.belediye = bel_secim
    bel = BELEDIYELER[bel_secim]

    st.markdown('<hr>', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="font-size:12px;line-height:2;color:{COLORS['sidebar_dim']}">
        <b style="color:{COLORS['sidebar_text']}">İl:</b> {bel['il']}<br>
        <b style="color:{COLORS['sidebar_text']}">Nüfus:</b> {bel['nufus']:,}<br>
        <b style="color:{COLORS['sidebar_text']}">İzole Bölge:</b> {len(bel['izole_bolgeler'])}<br>
        <b style="color:{COLORS['sidebar_text']}">Ölçüm Noktası:</b> {len(PRESSURE_NODE_IDS)}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr>', unsafe_allow_html=True)

    if not st.session_state.api_durumu_kontrol_edildi:
        st.session_state.api_aktif = check_api_health()
        st.session_state.api_durumu_kontrol_edildi = True

    if st.session_state.api_aktif:
        st.markdown('<div class="status-pill"><span class="status-dot"></span>Sistem Çevrimiçi</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-pill offline"><span class="status-dot"></span>Veri Bekleniyor</div>', unsafe_allow_html=True)

    if st.button("Bağlantıyı Yenile", use_container_width=True):
        st.session_state.api_durumu_kontrol_edildi = False
        st.rerun()

    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:10px;color:{COLORS["sidebar_muted"]};">Son güncelleme<br><span style="font-family:JetBrains Mono;color:{COLORS["sidebar_dim"]}">{datetime.now().strftime("%d.%m.%Y %H:%M")}</span></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SAYFA BAŞLIĞI (ortak)
# ─────────────────────────────────────────────────────────────────────────────
def render_page_header(title, subtitle=None):
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
        <div>
            <div style="font-size:22px;font-weight:800;color:{COLORS['text']}">{title}</div>
            <div style="font-size:12.5px;color:{COLORS['text_muted']};margin-top:2px">{subtitle or f"{bel_secim} — {bel['il']} İli"}</div>
        </div>
        <div style="font-family:JetBrains Mono;font-size:12px;color:{COLORS['text_muted']};text-align:right">
            {datetime.now().strftime("%d %B %Y")}<br>
            <span style="color:{COLORS['navy']};font-weight:600">{datetime.now().strftime("%H:%M:%S")}</span>
        </div>
    </div>
    <hr style="border-color:{COLORS['border']};margin:14px 0 20px 0">
    """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# SAYFA: CANLI İZLEME
# ═════════════════════════════════════════════════════════════════════════════
if sayfa == "Canlı İzleme":
    render_page_header("Canlı İzleme")

    st.markdown("""<div class="guide-box-top">
    Şebeke genelindeki anlık durum. Kaçak şüphesi taşıyan ölçüm noktaları kırmızı olarak işaretlenir;
    bir alarm tespit edildiğinde <b>Ekibi Gönder</b> butonu aktif hale gelir ve saha ekibine Telegram bildirimi iletilir.
    </div>""", unsafe_allow_html=True)

    # Demo durum üretimi
    demo_alarm_nodes = [PRESSURE_NODE_IDS[3]]
    node_states = get_node_states(bel_secim, demo_alarm_nodes)

    alarm_count = sum(1 for s in node_states.values() if s["status"] == "alarm")
    warning_count = sum(1 for s in node_states.values() if s["status"] == "warning")
    ok_count = sum(1 for s in node_states.values() if s["status"] == "ok")

    # Üst metrik satırı
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        cls = "alarm" if alarm_count > 0 else "ok"
        st.markdown(f'<div class="metric-card {cls}"><div class="metric-label">Aktif Alarm</div><div class="metric-value">{alarm_count}</div><div class="metric-sub">Kaçak şüphesi taşıyan nokta</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card warning"><div class="metric-label">Uyarı</div><div class="metric-value">{warning_count}</div><div class="metric-sub">Takip gerektiren nokta</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card ok"><div class="metric-label">Normal</div><div class="metric-value">{ok_count}</div><div class="metric-sub">Operasyonel nokta</div></div>', unsafe_allow_html=True)
    with c4:
        avg_p = np.mean([s["pressure"] for s in node_states.values()])
        st.markdown(f'<div class="metric-card"><div class="metric-label">Ort. Basınç</div><div class="metric-value">{avg_p:.2f}</div><div class="metric-sub">bar — şebeke geneli</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Harita + Dinamik Liste
    col_map, col_list = st.columns([2, 1])

    with col_map:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px">Şebeke Haritası — Anlık Durum</div>', unsafe_allow_html=True)
        if FOLIUM_AVAILABLE:
            m, latlon = build_network_map(bel_secim, node_states, detay_seviyesi="ozet", highlight_node=st.session_state.secili_node)
            map_data = st_folium(m, height=420, width=None, returned_objects=["last_object_clicked_tooltip"])
        else:
            st.markdown(f'<div class="metric-card" style="text-align:center;padding:60px 20px;color:{COLORS["text_faint"]}">Harita modülü (streamlit-folium) yüklenemedi.<br>requirements.txt dosyasını kontrol edin.</div>', unsafe_allow_html=True)

    with col_list:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px">Ölçüm Noktaları <span class="hint">Alarm önce</span></div>', unsafe_allow_html=True)
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
                        <div style="font-weight:600;font-size:13px;color:{COLORS['text']}">Ölçüm Noktası {nid}</div>
                        <div style="font-family:JetBrains Mono;font-size:11px;color:{COLORS['text_muted']}">{state['pressure']} bar · {state['flow']} m³/h</div>
                    </div>
                    <span class="badge {badge_cls}">{badge_text}</span>
                </div>
                """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Detay paneli + Ekibi Gönder
    alarm_nodes_list = [nid for nid, s in node_states.items() if s["status"] == "alarm"]
    has_alarm = len(alarm_nodes_list) > 0

    col_detail, col_action = st.columns([2, 1])

    with col_detail:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px">Tespit Detayı</div>', unsafe_allow_html=True)
        if has_alarm:
            primary = alarm_nodes_list[0]
            st_data = node_states[primary]
            st.markdown(f"""
            <div class="metric-card alarm">
                <div class="metric-label">Tespit Edilen Anomali</div>
                <div style="font-size:16px;font-weight:800;color:{COLORS['alarm']};margin-bottom:8px">
                    Ölçüm Noktası {primary} — Kaçak Şüphesi
                </div>
                <div style="font-size:13px;color:{COLORS['text']};line-height:1.75">
                    Anlık basınç: <span style="font-family:JetBrains Mono;font-weight:700;color:{COLORS['alarm']}">{st_data['pressure']} bar</span>
                    (beklenen: &gt;3.0 bar)<br>
                    Model kaçak olasılığı: <span style="font-family:JetBrains Mono;font-weight:700;color:{COLORS['alarm']}">%{st_data['probability']*100:.1f}</span><br>
                    Etkilenen boru hattı sayısı: <span style="font-family:JetBrains Mono;font-weight:700">{len([p for p in PIPES if primary in (p[1], p[2])])}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="metric-card ok">
                <div class="metric-label">Genel Durum</div>
                <div style="font-size:15px;font-weight:700;color:{COLORS['ok']};margin-bottom:6px">Şebeke Normal Çalışıyor</div>
                <div style="font-size:13px;color:{COLORS['text_muted']};line-height:1.7">
                    Şu anda hiçbir ölçüm noktasında kaçak şüphesi tespit edilmedi.
                    Tüm basınç ve debi değerleri beklenen aralıklar içinde.
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_action:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px">Saha Operasyonu</div>', unsafe_allow_html=True)

        if has_alarm:
            primary = alarm_nodes_list[0]
            st_data = node_states[primary]
            adres = random.choice(bel["ornek_adresler"])

            # Gönderilecek bilgileri önizle
            st.markdown(f"""
            <div style="background:{COLORS['alarm_bg']};border:2px solid {COLORS['alarm']};border-radius:10px;padding:14px 16px;margin-bottom:16px">
                <div style="font-size:11px;font-weight:700;color:{COLORS['alarm']};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px">Ekibe İletilecek Bilgi</div>
                <div style="font-size:12px;color:{COLORS['text']};line-height:1.8;font-family:JetBrains Mono">
                    Nokta: {primary}<br>
                    Basınç: {st_data['pressure']} bar<br>
                    Olasılık: %{st_data['probability']*100:.1f}<br>
                    Adres: {adres[:30]}...
                </div>
            </div>
            """, unsafe_allow_html=True)

            btn_container = st.container()
            with btn_container:
                st.markdown('<div class="action-btn-active">', unsafe_allow_html=True)
                ekip_gonder_clicked = st.button(
                    "🚨  EKİBİ GÖNDER",
                    use_container_width=True,
                    key="ekip_gonder_btn",
                )
                st.markdown('</div>', unsafe_allow_html=True)

            if ekip_gonder_clicked:
                # Telegram gönder
                tg_ok, tg_mesaj = send_telegram_alert(
                    node_id=primary,
                    adres=adres,
                    pressure=st_data["pressure"],
                    probability=st_data["probability"],
                    bel_adi=bel_secim,
                )

                # Kayıt
                st.session_state.ekip_gonderildi.append({
                    "Zaman": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    "Ölçüm Noktası": f"Node {primary}",
                    "Adres": adres,
                    "Belediye": bel_secim,
                    "Telegram": "Gönderildi" if tg_ok else "Başarısız",
                })
                st.session_state.telegram_son_mesaj = {"ok": tg_ok, "mesaj": tg_mesaj, "adres": adres}

            # Sonuç göster
            if st.session_state.telegram_son_mesaj:
                tg = st.session_state.telegram_son_mesaj
                if tg["ok"]:
                    st.markdown(f"""
                    <div class="telegram-banner">
                        <div class="tg-title">✅ Ekip Yönlendirildi</div>
                        Saha ekibine Telegram bildirimi iletildi.
                        <div class="tg-detail">Hedef: {tg['adres']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="telegram-banner error">
                        <div class="tg-title">⚠️ Telegram Gönderilemedi</div>
                        {tg['mesaj']}<br>
                        <span style="font-size:11px">Onrender'da BOT_TOKEN ve CHAT_ID tanımlı mı?</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.button(
                "Ekibi Gönder (Alarm Yok)",
                disabled=True,
                use_container_width=True,
                key="ekip_gonder_btn",
            )
            st.markdown(f'<div style="font-size:12px;color:{COLORS["text_faint"]};margin-top:10px;line-height:1.7;text-align:center">Kaçak tespit edildiğinde bu buton otomatik aktif hale gelir ve saha ekibine Telegram bildirimi gönderir.</div>', unsafe_allow_html=True)

        # Geçmiş müdahaleler
        if st.session_state.ekip_gonderildi:
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:11px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px">Müdahale Geçmişi</div>', unsafe_allow_html=True)
            with st.expander(f"{len(st.session_state.ekip_gonderildi)} kayıt", expanded=False):
                st.dataframe(pd.DataFrame(st.session_state.ekip_gonderildi), use_container_width=True, hide_index=True)

    # Alt detaylı açıklama
    st.markdown(f"""<div class="guide-box-bottom">
    <h4>Bu Sayfa Hakkında</h4>
    <b>Canlı İzleme</b> sayfası, su şebekesindeki tüm ölçüm noktalarının anlık basınç ve debi
    değerlerini gösterir. XGBoost modeli her noktayı bağımsız olarak değerlendirir; anormallik
    tespit edildiğinde ilgili nokta kırmızıya döner ve alarm sayacı artar.<br><br>
    <b>Ekibi Gönder</b> butonu yalnızca aktif alarm durumunda çalışır. Tıklandığında, önceden
    yapılandırılmış Telegram bot üzerinden saha ekibine ölçüm noktası, adres, basınç değeri
    ve kaçak olasılığı içeren bir bildirim mesajı iletilir. Bu özelliği kullanmak için
    Onrender'da <span style="font-family:JetBrains Mono">TELEGRAM_BOT_TOKEN</span> ve
    <span style="font-family:JetBrains Mono">TELEGRAM_CHAT_ID</span> environment variable olarak
    tanımlanmalıdır.<br><br>
    <b>Demo notu:</b> Şu anda gösterilen veriler simülasyon amaçlıdır. Gerçek API bağlantısı
    kurulduğunda, bu veriler modelin /predict çıktısıyla otomatik olarak güncellenecektir.
    </div>""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# SAYFA: ŞEBEKE HARİTASI
# ═════════════════════════════════════════════════════════════════════════════
elif sayfa == "Şebeke Haritası":
    render_page_header("Şebeke Haritası")

    st.markdown("""<div class="guide-box-top">
    Tüm ölçüm noktaları ve boru hatları gerçek coğrafi konumları üzerinde. Bir noktaya tıklayarak
    basınç, debi ve kaçak olasılığı detaylarını görebilirsiniz.
    </div>""", unsafe_allow_html=True)

    demo_alarm_nodes = [PRESSURE_NODE_IDS[3]]
    node_states = get_node_states(bel_secim, demo_alarm_nodes, seed_offset=1)

    col_map, col_info = st.columns([2.2, 1])

    with col_map:
        if FOLIUM_AVAILABLE:
            m, latlon = build_network_map(bel_secim, node_states, detay_seviyesi="detay")
            map_data = st_folium(m, height=520, width=None, returned_objects=["last_object_clicked_tooltip"])
        else:
            st.markdown(f'<div class="metric-card" style="text-align:center;padding:60px 20px;color:{COLORS["text_faint"]}">Harita modülü yüklenemedi.</div>', unsafe_allow_html=True)

    with col_info:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px">Şebeke Özeti</div>', unsafe_allow_html=True)
        info_items = [
            ("Toplam Ölçüm Noktası", str(len(PRESSURE_NODE_IDS))),
            ("Toplam Boru Hattı", str(len(PIPES))),
            ("Ana Su Kaynağı", "1 Rezervuar"),
            ("Aktif Alarm", str(sum(1 for s in node_states.values() if s["status"] == "alarm"))),
            ("Veri Kaynağı", "EPANET / Hanoi"),
        ]
        for label, val in info_items:
            st.markdown(f"""<div class="node-row" style="margin-bottom:6px">
                <div class="metric-label" style="margin:0">{label}</div>
                <div style="font-family:JetBrains Mono;font-size:12px;color:{COLORS['text']}">{val}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="font-size:12px;color:{COLORS['text_muted']};line-height:2">
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{COLORS['alarm']};margin-right:6px"></span>Alarm<br>
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{COLORS['warning']};margin-right:6px"></span>Uyarı<br>
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{COLORS['ok']};margin-right:6px"></span>Normal<br>
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{COLORS['navy']};margin-right:6px"></span>Rezervuar
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px">Ölçüm Noktası Detay Tablosu</div>', unsafe_allow_html=True)

    node_table = []
    order = {"alarm": 0, "warning": 1, "ok": 2}
    for nid, state in sorted(node_states.items(), key=lambda x: (order[x[1]["status"]], x[0])):
        node_table.append({
            "Ölçüm Noktası": f"Node {nid}",
            "Durum": STATUS_LABEL[state["status"]],
            "Basınç (bar)": state["pressure"],
            "Debi (m³/h)": state["flow"],
            "Talep (m³/h)": state["demand"],
            "Kaçak Olasılığı": f"{state['probability']:.3f}",
        })
    st.dataframe(pd.DataFrame(node_table), use_container_width=True, hide_index=True)

    st.markdown(f"""<div class="guide-box-bottom">
    <h4>Bu Sayfa Hakkında</h4>
    Harita verisi, LeakDB projesinde kullanılan <b>Hanoi su şebekesi</b> EPANET modelinden
    türetilmiştir. 32 ölçüm noktası ve 34 boru hattından oluşan bu topoloji, gerçek şebeke
    yapısını temsil eder; ancak coğrafi koordinatlar seçilen belediyenin merkezi etrafına
    matematiksel olarak ölçeklenerek yerleştirilmiştir.<br><br>
    <b>Haritada renk kodlaması:</b> Kırmızı noktalar aktif alarm (kaçak şüphesi), amber/sarı
    uyarı durumu, yeşil ise normal operasyonu ifade eder. Kırmızı boru hatları, her iki
    ucunda da alarm olan segmentleri gösterir.
    </div>""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# SAYFA: İZOLE ÖLÇÜM BÖLGELERİ
# ═════════════════════════════════════════════════════════════════════════════
elif sayfa == "İzole Ölçüm Bölgeleri":
    render_page_header("İzole Ölçüm Bölgeleri")

    st.markdown("""<div class="guide-box-top">
    Şebekenin bölge bazında su dengesi ve kayıp analizi. Riskli bölgeler listenin en üstünde
    gösterilir; her bölge için tahmini kayıp oranı ve aktif alarm sayısı izlenebilir.
    </div>""", unsafe_allow_html=True)

    izole_bolgeler = bel["izole_bolgeler"]
    node_assignments = get_node_assignments(bel_secim, len(izole_bolgeler))
    demo_alarm_nodes = [PRESSURE_NODE_IDS[3]]
    node_states = get_node_states(bel_secim, demo_alarm_nodes, seed_offset=2)

    bolge_data = []
    for idx, bolge in enumerate(izole_bolgeler):
        bolge_nodes = [nid for nid, z in node_assignments.items() if z == idx]
        bolge_node_states = [node_states[nid] for nid in bolge_nodes if nid in node_states]
        alarm_in_bolge = sum(1 for s in bolge_node_states if s["status"] == "alarm")
        avg_pressure = np.mean([s["pressure"] for s in bolge_node_states]) if bolge_node_states else 0
        avg_flow = sum(s["flow"] for s in bolge_node_states) if bolge_node_states else 0
        risk = "Yüksek" if alarm_in_bolge > 0 else ("Orta" if any(s["status"] == "warning" for s in bolge_node_states) else "Düşük")
        risk_order = {"Yüksek": 0, "Orta": 1, "Düşük": 2}
        kayip = round(random.Random(idx + hash(bel_secim)).uniform(8, 18), 1) if risk == "Yüksek" else round(random.Random(idx + hash(bel_secim)).uniform(1, 5), 1)
        bolge_data.append({
            "_risk_order": risk_order[risk],
            "Bölge": bolge,
            "Risk": risk,
            "Ort. Basınç (bar)": round(avg_pressure, 2),
            "Toplam Debi (m³/h)": round(avg_flow, 1),
            "Kayıp Tahmini (%)": kayip,
            "Ölçüm Noktası Sayısı": len(bolge_nodes),
            "Aktif Alarm": alarm_in_bolge,
        })
    bolge_data.sort(key=lambda x: x["_risk_order"])

    cols = st.columns(len(bolge_data))
    for col, row in zip(cols, bolge_data):
        with col:
            cls = "alarm" if row["Risk"] == "Yüksek" else ("warning" if row["Risk"] == "Orta" else "ok")
            st.markdown(f"""<div class="metric-card {cls}">
                <div class="metric-label">{row['Bölge']}</div>
                <div class="metric-value">{row['Kayıp Tahmini (%)']:.1f}%</div>
                <div class="metric-sub">Tahmini su kaybı</div>
                <div style="margin-top:10px;font-size:12px;color:{COLORS['text_muted']}">
                    Basınç: <span style="font-family:JetBrains Mono">{row['Ort. Basınç (bar)']} bar</span><br>
                    Aktif Alarm: <span style="font-family:JetBrains Mono;color:{COLORS['alarm'] if row['Aktif Alarm']>0 else COLORS['ok']}">{row['Aktif Alarm']}</span>
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px">Bölge Karşılaştırma Tablosu</div>', unsafe_allow_html=True)
    display_df = pd.DataFrame([{k: v for k, v in d.items() if k != "_risk_order"} for d in bolge_data])
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px">Bölge Bazında 24 Saatlik Basınç Trendi</div>', unsafe_allow_html=True)
    hours = list(range(24))
    trend_data = {}
    for row in bolge_data:
        base = row["Ort. Basınç (bar)"] or 4.0
        rnd = random.Random(hash(row["Bölge"]))
        series = [round(base + math.sin(h / 3) * 0.3 + rnd.gauss(0, 0.1), 2) for h in hours]
        if row["Risk"] == "Yüksek":
            series[18:] = [round(s - rnd.uniform(0.5, 0.9), 2) for s in series[18:]]
        trend_data[row["Bölge"].split(" ")[0]] = series
    df_trend = pd.DataFrame(trend_data, index=[f"{h:02d}:00" for h in hours])
    st.line_chart(df_trend, height=240)

    st.markdown(f"""<div class="guide-box-bottom">
    <h4>Bu Sayfa Hakkında</h4>
    <b>İzole Ölçüm Bölgesi (İÖB)</b>, şebekenin su dengesi ve kaçak riskinin alt bölgeler
    bazında izlenebilmesi amacıyla oluşturulan bağımsız ölçüm alanlarıdır. Her İÖB'de giriş
    ve çıkış debisi ölçülerek bölgeye özgü su kayıp oranı hesaplanır.<br><br>
    <b>Renk kodlaması:</b> Kırmızı bölgelerde aktif alarm mevcuttur ve öncelikli müdahale
    gerektirir. Amber/sarı bölgeler yakın takip gerektiren anormal değerler içermektedir.
    Yeşil bölgeler normal operasyon aralığındadır.<br><br>
    <b>24 saatlik trend grafiği</b> bölge bazında basınç değişimini gösterir. Gece saatlerinde
    (22:00–06:00) düşük talep döneminde tespit edilen basınç kayıpları özellikle anlamlıdır,
    zira bu saatlerde meşru tüketim minimumdadır.
    </div>""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# SAYFA: VERİ ANALİZİ (Manuel Tahmin + Yayın Verisi)
# ═════════════════════════════════════════════════════════════════════════════
elif sayfa == "Veri Analizi":
    render_page_header("Veri Analizi")

    st.markdown("""<div class="guide-box-top">
    İki farklı analiz modu: <b>Manuel Test</b> ile sensör değerlerini siz girerek modelin nasıl
    çalıştığını test edebilirsiniz. <b>Yayın Verisi</b> sekmesi ise API'den gelen gerçek zamanlı
    tahmin akışını gösterir.
    </div>""", unsafe_allow_html=True)

    tab_manuel, tab_yayin = st.tabs(["Manuel Test", "Yayın Verisi"])

    # ── Tab 1: Manuel Test (API'den bağımsız) ─────────────────────────────────
    with tab_manuel:
        st.markdown(f"""
        <div style="margin:16px 0 20px 0;padding:14px 18px;background:{COLORS['panel_alt']};border-radius:8px;font-size:13px;color:{COLORS['text_muted']};border:1px solid {COLORS['border']}">
            Bu sekme <b>API'den tamamen bağımsız</b> çalışır. Sensör değerlerini manuel olarak
            girin; kaçak tespiti model mantığını taklit eden basit kural tabanlı bir değerlendirme
            ile yapılır. Gerçek modeli test etmek için <b>Yayın Verisi</b> sekmesini kullanın.
        </div>
        """, unsafe_allow_html=True)

        col_form, col_result = st.columns([1, 1])

        with col_form:
            st.markdown(f'<div style="font-size:13.5px;font-weight:700;color:{COLORS["text"]};margin-bottom:16px">Sensör Değerleri Girişi</div>', unsafe_allow_html=True)

            hour_val = st.slider("Ölçüm Saati (0–23)", 0, 23, datetime.now().hour)

            st.markdown(f'<div style="font-size:12px;color:{COLORS["text_muted"]};margin:16px 0 10px;font-weight:700">Basınç Değerleri (bar) — Örnek Noktalar</div>', unsafe_allow_html=True)
            node_cols = st.columns(3)
            p_values = {}
            sample_nodes = [2, 5, 10, 15, 20, 25]
            for idx, n in enumerate(sample_nodes):
                with node_cols[idx % 3]:
                    p_values[f"P_Node_{n}"] = st.number_input(
                        f"Nokta {n}", value=4.0, step=0.1, key=f"mt_p{n}",
                        min_value=0.0, max_value=10.0
                    )

            st.markdown(f'<div style="font-size:12px;color:{COLORS["text_muted"]};margin:16px 0 10px;font-weight:700">Debi Değerleri (m³/h) — Örnek Hatlar</div>', unsafe_allow_html=True)
            link_cols = st.columns(3)
            f_values = {}
            sample_links = [1, 5, 10, 15, 20, 25]
            for idx, n in enumerate(sample_links):
                with link_cols[idx % 3]:
                    f_values[f"F_Link_{n}"] = st.number_input(
                        f"Hat {n}", value=2.0, step=0.1, key=f"mt_f{n}",
                        min_value=0.0, max_value=20.0
                    )

            manuel_test_btn = st.button("Analiz Et", use_container_width=True, key="manuel_test_btn")

        with col_result:
            st.markdown(f'<div style="font-size:13.5px;font-weight:700;color:{COLORS["text"]};margin-bottom:16px">Analiz Sonucu</div>', unsafe_allow_html=True)

            if manuel_test_btn:
                # API'den bağımsız kural tabanlı değerlendirme
                avg_pressure = np.mean(list(p_values.values()))
                min_pressure = min(p_values.values())
                avg_flow = np.mean(list(f_values.values()))

                # Basit kural motoru
                kaçak_skoru = 0.0
                sebep_listesi = []

                if min_pressure < 2.0:
                    kaçak_skoru += 0.45
                    sebep_listesi.append(f"Kritik düşük basınç: {min_pressure:.2f} bar")
                elif min_pressure < 3.0:
                    kaçak_skoru += 0.25
                    sebep_listesi.append(f"Düşük basınç: {min_pressure:.2f} bar")

                if avg_pressure < 2.5:
                    kaçak_skoru += 0.30
                    sebep_listesi.append(f"Ortalama basınç düşük: {avg_pressure:.2f} bar")

                if 0 <= hour_val <= 5 and avg_flow > 3.5:
                    kaçak_skoru += 0.30
                    sebep_listesi.append(f"Gece saatinde yüksek debi: {avg_flow:.2f} m³/h")

                if avg_flow > 5.0:
                    kaçak_skoru += 0.20
                    sebep_listesi.append(f"Anormal yüksek debi: {avg_flow:.2f} m³/h")

                kaçak_skoru = min(kaçak_skoru, 0.99)
                pred = 1 if kaçak_skoru >= 0.45 else 0

                cls = "alarm" if pred == 1 else "ok"
                verdict = "KAÇAK ŞÜPHESİ" if pred == 1 else "NORMAL"
                verdict_color = COLORS["alarm"] if pred == 1 else COLORS["ok"]

                st.markdown(f"""<div class="metric-card {cls}" style="margin-bottom:16px">
                    <div class="metric-label">Manuel Test Sonucu</div>
                    <div style="font-size:26px;font-weight:800;color:{verdict_color};font-family:JetBrains Mono">{verdict}</div>
                    <div class="metric-sub">Hesaplanan risk skoru: <span style="font-family:JetBrains Mono;color:{verdict_color};font-weight:700">{kaçak_skoru:.3f}</span></div>
                </div>""", unsafe_allow_html=True)

                if sebep_listesi:
                    st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px">Tespit Gerekçeleri</div>', unsafe_allow_html=True)
                    for s in sebep_listesi:
                        icon = "🔴" if pred == 1 else "⚠️"
                        st.markdown(f'<div style="font-size:13px;padding:8px 12px;background:{COLORS["panel_alt"]};border-radius:6px;margin-bottom:6px;color:{COLORS["text"]};border:1px solid {COLORS["border"]}">{icon} {s}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="font-size:13px;padding:12px;background:{COLORS["ok_bg"]};border-radius:6px;color:{COLORS["ok"]};border:1px solid {COLORS["ok"]}">✓ Tüm değerler normal aralıkta.</div>', unsafe_allow_html=True)

                st.session_state.manuel_tahmin_log.append({
                    "Zaman": datetime.now().strftime("%H:%M:%S"),
                    "Sonuç": verdict,
                    "Risk Skoru": f"{kaçak_skoru:.3f}",
                    "Min. Basınç": f"{min_pressure:.2f} bar",
                    "Ort. Debi": f"{avg_flow:.2f} m³/h",
                    "Saat": hour_val,
                })
            else:
                st.markdown(f'<div style="color:{COLORS["text_faint"]};font-size:13px;padding:50px 0;text-align:center">Değerleri girin ve "Analiz Et" butonuna basın.</div>', unsafe_allow_html=True)

            if st.session_state.manuel_tahmin_log:
                st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px">Oturum Geçmişi</div>', unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(st.session_state.manuel_tahmin_log[-10:]), use_container_width=True, hide_index=True)

    # ── Tab 2: Yayın Verisi (API'den) ─────────────────────────────────────────
    with tab_yayin:
        st.markdown(f"""
        <div style="margin:16px 0 20px 0;padding:14px 18px;background:{COLORS['panel_alt']};border-radius:8px;font-size:13px;color:{COLORS['text_muted']};border:1px solid {COLORS['border']}">
            Bu sekme, FastAPI backend'e gerçek bir /predict isteği gönderir ve modelin döndürdüğü
            ham tahmin verisini gösterir. <b>Bağlantı durumu:</b>
            {"<span style='color:" + COLORS['ok'] + ";font-weight:700'> Çevrimiçi</span>" if st.session_state.api_aktif else "<span style='color:" + COLORS['alarm'] + ";font-weight:700'> Çevrimdışı</span>"}
        </div>
        """, unsafe_allow_html=True)

        col_yayin_form, col_yayin_result = st.columns([1, 1])

        with col_yayin_form:
            st.markdown(f'<div style="font-size:13.5px;font-weight:700;color:{COLORS["text"]};margin-bottom:16px">API İsteği Parametreleri</div>', unsafe_allow_html=True)

            hour_yayin = st.slider("Ölçüm Saati (0–23)", 0, 23, datetime.now().hour, key="yayin_hour")

            st.markdown(f'<div style="font-size:12px;color:{COLORS["text_muted"]};margin:16px 0 10px;font-weight:700">Basınç Değerleri (bar)</div>', unsafe_allow_html=True)
            yayin_cols = st.columns(3)
            yp_values = {}
            for idx, n in enumerate(sample_nodes):
                with yayin_cols[idx % 3]:
                    yp_values[f"P_Node_{n}"] = st.number_input(
                        f"Nokta {n}", value=4.0, step=0.1, key=f"yp{n}",
                        min_value=0.0, max_value=10.0
                    )

            st.markdown(f'<div style="font-size:12px;color:{COLORS["text_muted"]};margin:16px 0 10px;font-weight:700">Debi Değerleri (m³/h)</div>', unsafe_allow_html=True)
            yayin_link_cols = st.columns(3)
            yf_values = {}
            for idx, n in enumerate(sample_links):
                with yayin_link_cols[idx % 3]:
                    yf_values[f"F_Link_{n}"] = st.number_input(
                        f"Hat {n}", value=2.0, step=0.1, key=f"yf{n}",
                        min_value=0.0, max_value=20.0
                    )

            yayin_btn = st.button("API'ye Gönder", use_container_width=True, key="yayin_btn")

        with col_yayin_result:
            st.markdown(f'<div style="font-size:13.5px;font-weight:700;color:{COLORS["text"]};margin-bottom:16px">API Yanıtı</div>', unsafe_allow_html=True)

            if yayin_btn:
                payload = {}
                for i in PRESSURE_NODE_IDS:
                    payload[f"P_Node_{i}"] = yp_values.get(f"P_Node_{i}", 4.0)
                for i in FLOW_LINK_IDS:
                    payload[f"F_Link_{i}"] = yf_values.get(f"F_Link_{i}", 2.0)
                for i in DEMAND_NODE_IDS:
                    payload[f"D_Node_{i}"] = 1.5
                payload["hour"] = hour_yayin
                payload["timestamp"] = datetime.now().isoformat()

                with st.spinner("API'ye istek gönderiliyor..."):
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
                        <div class="metric-label">Bağlantı Hatası</div>
                        <div style="font-size:14px;color:{COLORS['alarm']};font-weight:700">API'ye erişilemedi</div>
                        <div class="metric-sub">{api_err}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    cls = "alarm" if pred == 1 else "ok"
                    verdict = "KAÇAK TESPİT EDİLDİ" if pred == 1 else "NORMAL"
                    verdict_color = COLORS["alarm"] if pred == 1 else COLORS["ok"]

                    st.markdown(f"""<div class="metric-card {cls}" style="margin-bottom:16px">
                        <div class="metric-label">API Tahmin Sonucu</div>
                        <div style="font-size:24px;font-weight:800;color:{verdict_color};font-family:JetBrains Mono">{verdict}</div>
                        <div class="metric-sub">Kaçak olasılığı: <span style="font-family:JetBrains Mono;color:{verdict_color};font-weight:700">{proba:.4f}</span></div>
                    </div>""", unsafe_allow_html=True)

                    if suspicious:
                        st.markdown(f"""
                        <div class="metric-card alarm">
                            <div class="metric-label">Şüpheli Ölçüm Noktaları</div>
                            <div style="font-family:JetBrains Mono;font-size:13px;color:{COLORS['text']}">{", ".join(suspicious)}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    # Ham JSON
                    with st.expander("Ham API Yanıtı (JSON)", expanded=False):
                        st.json(data)
            else:
                st.markdown(f'<div style="color:{COLORS["text_faint"]};font-size:13px;padding:50px 0;text-align:center">Parametreleri girin ve "API\'ye Gönder" butonuna basın.</div>', unsafe_allow_html=True)

    st.markdown(f"""<div class="guide-box-bottom">
    <h4>Bu Sayfa Hakkında</h4>
    <b>Manuel Test</b> sekmesi, API bağlantısı olmadan bile kaçak tespit mantığını anlamak
    için kullanılabilir. Girilen basınç ve debi değerleri üzerinden kural tabanlı bir
    risk skorlaması yapılır: kritik basınç düşüşü, gece saatlerinde anormal debi gibi
    göstergeler değerlendirilir. Bu sekme eğitim, demo ve bağlantı olmayan ortamlar için
    tasarlanmıştır.<br><br>
    <b>Yayın Verisi</b> sekmesi ise FastAPI backend'deki gerçek XGBoost modeline istek
    gönderir. Model 161 özellik (tüm ölçüm noktalarının basınç, debi, talep değerleri +
    saat) üzerinden kaçak olasılığı hesaplar ve şüpheli noktaları döndürür. API çevrimdışıysa
    bu sekme bağlantı hatası verir; bağlantıyı sol menüdeki "Bağlantıyı Yenile" butonu
    ile kontrol edebilirsiniz.
    </div>""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# SAYFA: SİSTEM & MODEL
# ═════════════════════════════════════════════════════════════════════════════
elif sayfa == "Sistem & Model":
    render_page_header("Sistem & Model")

    st.markdown("""<div class="guide-box-top">
    AquaSense'in teknik altyapısı, model performansı ve MVP kapsamı. Jüri ve teknik
    değerlendirme için referans sayfası.
    </div>""", unsafe_allow_html=True)

    # MVP Uyarı Kutusu — en üstte, belirgin
    st.markdown(f"""
    <div class="mvp-banner">
        <b>⚠️ Bu bir MVP Prototipidir — Gerçek Bir Ürün Değildir</b><br><br>
        AquaSense, <b>AI for Sustainability</b> yarışması kapsamında geliştirilen bir
        <b>Minimum Viable Product (MVP)</b>'dir. MVP; bir ürünün temel işlevlerini
        doğrulamak amacıyla üretilen, tam ölçekli dağıtıma hazır olmayan erken aşama
        prototiptir.<br><br>
        Bu sistemde kullanılan tüm veriler <b>LeakDB simülasyon veri setinden</b> türetilmiştir.
        Harita koordinatları, bölge adları ve adresler gerçek şebeke altyapısını değil,
        temsili bir topolojiyi yansıtmaktadır. Gerçek bir belediye tarafından kullanılmadan
        önce sistemin yerel şebeke verileriyle yeniden eğitilmesi, saha doğrulamasından
        geçmesi ve güvenlik denetimine tabi tutulması gerekmektedir.
    </div>
    """, unsafe_allow_html=True)

    col_sys, col_model = st.columns(2)

    with col_sys:
        st.markdown(f'<div style="font-size:13px;font-weight:700;color:{COLORS["text"]};margin-bottom:14px">Sistem Bilgisi</div>', unsafe_allow_html=True)
        sys_items = [
            ("Model Türü", "XGBoost — Kademeli Eğitim"),
            ("Eğitim Verisi", "LeakDB — Hanoi Şebeke Topolojisi"),
            ("Özellik Sayısı", "161"),
            ("Eğitim Örneği", "~12,3 milyon adım"),
            ("Değerlendirme Sıklığı", "Her 30 dakika"),
            ("API Altyapısı", "FastAPI (Bulut Sunucu)"),
            ("Arayüz", "Streamlit (Bulut Sunucu)"),
            ("Aşama", "MVP / Prototip"),
        ]
        for label, val in sys_items:
            st.markdown(f"""<div class="node-row" style="margin-bottom:6px">
                <div class="metric-label" style="margin:0">{label}</div>
                <div style="font-family:JetBrains Mono;font-size:12px;color:{COLORS['text']}">{val}</div>
            </div>""", unsafe_allow_html=True)

    with col_model:
        st.markdown(f'<div style="font-size:13px;font-weight:700;color:{COLORS["text"]};margin-bottom:14px">Model Performansı <span class="hint">Bağımsız test seti</span></div>', unsafe_allow_html=True)
        perf_items = [
            ("Doğruluk (Accuracy)", "%82", "ok"),
            ("Kaçak Hassasiyeti (Precision)", "%59", "ok"),
            ("Kaçak Duyarlılığı (Recall)", "%53", ""),
            ("Kaçak F1 Skoru", "%56", ""),
            ("Eğitim / Test Bölünmesi", "700 / 150 Senaryo", ""),
            ("Test Adım Sayısı", "2.628.000", ""),
        ]
        for item in perf_items:
            label, val = item[0], item[1]
            cls = item[2] if len(item) > 2 else ""
            row_cls = f"node-row {cls}" if cls else "node-row"
            st.markdown(f"""<div class="{row_cls}" style="margin-bottom:6px">
                <div class="metric-label" style="margin:0">{label}</div>
                <div style="font-family:JetBrains Mono;font-size:12px;color:{COLORS['text']}">{val}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # MVP Ne Demek — genişletilmiş açıklama
    st.markdown(f'<div style="font-size:13px;font-weight:700;color:{COLORS["text"]};margin-bottom:14px">MVP Nedir? Bu Sistem Neyi Kanıtlamaktadır?</div>', unsafe_allow_html=True)

    mvp_cols = st.columns(3)
    mvp_items = [
        ("Kanıtlanan", "Su şebekesi simülasyon verisiyle eğitilen XGBoost modeli kaçakları %82 doğrulukla tespit edebilmektedir."),
        ("Gösterilen", "FastAPI + Streamlit mimarisi ile gerçek zamanlı tahmin akışı mümkündür. Folium harita entegrasyonu topoloji görselleştirmesini sağlar."),
        ("Yapılmayan", "Gerçek sensör donanımı entegrasyonu, sahada doğrulama, güvenlik denetimi ve yerel şebeke verileriyle yeniden eğitim."),
    ]
    for col, (baslik, aciklama) in zip(mvp_cols, mvp_items):
        with col:
            st.markdown(f"""<div style="background:{COLORS['panel']};border-radius:10px;padding:18px;border:1px solid {COLORS['border']}">
                <div style="font-size:12px;font-weight:700;color:{COLORS['navy']};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px">{baslik}</div>
                <div style="font-size:12.5px;color:{COLORS['text_muted']};line-height:1.6">{aciklama}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:13px;font-weight:700;color:{COLORS["text"]};margin-bottom:14px">Veri İşlem Hattı</div>', unsafe_allow_html=True)

    pipeline_steps = [
        ("1", "LeakDB Veri Seti", "17.520 adım/senaryo, 1000 senaryo"),
        ("2", "Özellik Mühendisliği", "161 özellik: basınç, debi, talep, zaman"),
        ("3", "Kademeli Eğitim", "100 senaryo/grup × 7 grup, XGBoost"),
        ("4", "FastAPI Servisi", "/predict → 161 özellik → anlık tahmin"),
        ("5", "Streamlit Arayüzü", "Canlı izleme, harita, bölge analizi"),
    ]
    p_cols = st.columns(5)
    for col, (num, title, desc) in zip(p_cols, pipeline_steps):
        with col:
            st.markdown(f"""<div style="background:{COLORS['panel']};border-radius:10px;padding:16px;border:1px solid {COLORS['border']};text-align:center">
                <div style="font-family:JetBrains Mono;font-size:20px;font-weight:700;color:{COLORS['navy']}">{num}</div>
                <div style="font-size:12px;font-weight:700;color:{COLORS['text']};margin:6px 0 4px">{title}</div>
                <div style="font-size:10.5px;color:{COLORS['text_muted']};line-height:1.4">{desc}</div>
            </div>""", unsafe_allow_html=True)

    # Telegram Yapılandırma Notu
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:13px;font-weight:700;color:{COLORS["text"]};margin-bottom:14px">Telegram Entegrasyonu — Yapılandırma</div>', unsafe_allow_html=True)

    tg_status_ok = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    tg_cls = "ok" if tg_status_ok else "warning"
    tg_msg = "Telegram yapılandırması aktif." if tg_status_ok else "Telegram yapılandırması eksik — BOT_TOKEN veya CHAT_ID tanımlı değil."

    st.markdown(f"""
    <div class="metric-card {tg_cls}">
        <div class="metric-label">Telegram Bot Durumu</div>
        <div style="font-size:14px;font-weight:700;color:{COLORS[tg_cls]};margin-bottom:8px">
            {"✅ Aktif" if tg_status_ok else "⚠️ Yapılandırılmamış"}
        </div>
        <div style="font-size:12.5px;color:{COLORS['text_muted']};line-height:1.7">
            {tg_msg}<br><br>
            Etkinleştirmek için Onrender'da iki environment variable tanımlayın:<br>
            <span style="font-family:JetBrains Mono;background:{COLORS['panel_alt']};padding:2px 8px;border-radius:4px">TELEGRAM_BOT_TOKEN</span> — BotFather'dan alınan bot token<br>
            <span style="font-family:JetBrains Mono;background:{COLORS['panel_alt']};padding:2px 8px;border-radius:4px">TELEGRAM_CHAT_ID</span> — Ekip grup sohbetinin ID'si<br>
            <br>
            Grup ID'sini öğrenmek için: @userinfobot veya @getidsbot'u gruba ekleyin.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""<div class="guide-box-bottom">
    <h4>Bu Sayfa Hakkında</h4>
    Bu sayfa AquaSense'in teknik altyapısını, model performansını ve MVP sınırlarını
    şeffaf biçimde belgeler. Yarışma jürisi ve teknik değerlendiriciler için referans
    niteliğindedir.<br><br>
    <b>Model hakkında:</b> XGBoost modeli, LeakDB açık veri setindeki Hanoi şebeke
    simülasyonları üzerinde kademeli (incremental) öğrenme yöntemiyle eğitilmiştir.
    %82 doğruluk oranı bağımsız test seti üzerinde ölçülmüştür; gerçek şebeke
    koşullarında bu değer değişebilir.<br><br>
    <b>Telegram entegrasyonu hakkında:</b> "Ekibi Gönder" butonu tıklandığında, sistemin
    Telegram Bot API'yi kullanarak önceden tanımlanmış ekip grubuna bildirim göndermesi
    için yalnızca iki environment variable yeterlidir. Gerçek bir implementasyonda
    birden fazla grup (teknik ekip, yönetim) ve onay mekanizması eklenebilir.
    </div>""", unsafe_allow_html=True)
