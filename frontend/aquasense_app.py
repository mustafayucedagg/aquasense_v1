import streamlit as st
import pandas as pd
import numpy as np
import math
import random
import os
from datetime import datetime, timedelta

# streamlit-folium opsiyonel: kurulu degilse uyari goster, demo modda calis
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
# TASARIM TOKEN'LARI — Açık Tema, Logo Tabanlı
# ─────────────────────────────────────────────────────────────────────────────
COLORS = {
    "navy": "#0B1C36",          # Logo lacivert - ana marka rengi
    "navy_light": "#16315C",    # Lacivert ton (hover, ikincil)
    "bg": "#FAFBFC",            # Ana zemin
    "panel": "#FFFFFF",         # Kart/panel zemini
    "panel_alt": "#F1F4F8",     # Alternatif panel zemini
    "border": "#E2E8F0",        # Çizgi rengi
    "border_strong": "#CBD5E1", # Daha güçlü çizgi
    "text": "#0F1A2E",          # Ana metin
    "text_muted": "#64748B",    # İkincil metin
    "text_faint": "#94A3B8",    # Soluk metin/etiket
    "ok": "#0F766E",            # Normal durum (teal)
    "ok_bg": "#ECFDF8",
    "warning": "#B45309",       # Uyarı (amber, koyu - okunabilirlik için)
    "warning_bg": "#FFFBEB",
    "alarm": "#DC2626",         # Alarm (kırmızı)
    "alarm_bg": "#FEF2F2",
}

API_URL = os.environ.get("API_URL", "http://localhost:8000")

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [data-testid="stAppViewContainer"], .main {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
    font-family: 'Inter', sans-serif;
}}

/* Sidebar */
[data-testid="stSidebar"] {{
    background-color: {COLORS['navy']};
    border-right: 1px solid {COLORS['border']};
}}
[data-testid="stSidebar"] * {{ color: #E8EDF5 !important; }}
[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.12) !important; }}

/* Sidebar nav butonlari */
.nav-item {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 11px 14px;
    border-radius: 8px;
    margin-bottom: 4px;
    font-size: 13.5px;
    font-weight: 500;
    color: #B9C6DC;
    cursor: pointer;
    transition: background 0.15s ease;
}}
.nav-item.active {{
    background: rgba(255,255,255,0.10);
    color: #FFFFFF !important;
    font-weight: 600;
}}

/* Streamlit radio -> sol menu gibi kullaniyoruz, native gorunumu gizle */
[data-testid="stSidebar"] [role="radiogroup"] label {{
    background: transparent;
    border-radius: 8px;
    padding: 9px 12px;
    margin-bottom: 2px;
    transition: background 0.15s ease;
}}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {{
    background: rgba(255,255,255,0.06);
}}

/* Basliklar */
h1, h2, h3, h4 {{ font-family: 'Inter', sans-serif; font-weight: 700; color: {COLORS['text']}; }}

/* Rehber metin kutusu */
.guide-box {{
    background: {COLORS['panel_alt']};
    border-left: 3px solid {COLORS['navy']};
    border-radius: 0 8px 8px 0;
    padding: 13px 18px;
    margin-bottom: 22px;
    font-size: 13px;
    color: {COLORS['text_muted']};
    line-height: 1.65;
}}
.guide-box b {{ color: {COLORS['text']}; }}

/* Ipucu balonu */
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
    padding: 16px 20px;
    margin-bottom: 12px;
    box-shadow: 0 1px 2px rgba(15,23,42,0.04);
}}
.metric-card.alarm {{ border-color: {COLORS['alarm']}; background: {COLORS['alarm_bg']}; }}
.metric-card.warning {{ border-color: {COLORS['warning']}; background: {COLORS['warning_bg']}; }}
.metric-card.ok {{ border-color: {COLORS['ok']}; background: {COLORS['ok_bg']}; }}
.metric-label {{
    font-size: 10.5px; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase;
    color: {COLORS['text_faint']}; margin-bottom: 6px;
}}
.metric-value {{
    font-family: 'JetBrains Mono', monospace; font-size: 25px; font-weight: 600; color: {COLORS['text']};
}}
.metric-sub {{ font-size: 11.5px; color: {COLORS['text_muted']}; margin-top: 3px; }}

/* Durum rozeti */
.badge {{
    font-family: 'JetBrains Mono', monospace; font-size: 10.5px; padding: 3px 9px;
    border-radius: 5px; font-weight: 600; letter-spacing: 0.03em;
}}
.badge-alarm {{ background: {COLORS['alarm']}; color: #fff; }}
.badge-warning {{ background: {COLORS['warning']}; color: #fff; }}
.badge-ok {{ background: {COLORS['ok']}; color: #fff; }}

/* Olcum noktasi satiri */
.node-row {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 11px 14px; border-radius: 8px; margin-bottom: 6px;
    background: {COLORS['panel']}; border: 1px solid {COLORS['border']}; font-size: 13px;
}}
.node-row.alarm {{ background: {COLORS['alarm_bg']}; border-color: #FCA5A5; }}
.node-row.warning {{ background: {COLORS['warning_bg']}; border-color: #FCD34D; }}

/* Durum gostergesi (baglanti) */
.status-pill {{
    display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600;
    padding: 6px 13px; border-radius: 20px; background: {COLORS['ok_bg']}; color: {COLORS['ok']};
    border: 1px solid #99E6DA;
}}
.status-pill.offline {{ background: {COLORS['alarm_bg']}; color: {COLORS['alarm']}; border-color: #FCA5A5; }}
.status-dot {{
    width: 7px; height: 7px; border-radius: 50%; background: currentColor;
    animation: pulse-dot 2s infinite;
}}
@keyframes pulse-dot {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.35; }} }}

/* Sekme stili (ust sekmeler - alt-navigasyon icin) */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background: transparent; border-bottom: 1px solid {COLORS['border']}; gap: 4px;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    background: transparent; color: {COLORS['text_muted']} !important; font-size: 13px;
    font-weight: 500; padding: 9px 18px;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    color: {COLORS['navy']} !important; border-bottom: 2px solid {COLORS['navy']} !important; font-weight: 600;
}}

/* Tablo */
.stDataFrame {{ border: 1px solid {COLORS['border']} !important; border-radius: 8px !important; }}

/* Ayirici */
.divider {{ border: none; border-top: 1px solid {COLORS['border']}; margin: 22px 0; }}

/* Inputlar */
.stNumberInput input, .stSelectbox > div, .stTextInput input {{
    background: {COLORS['panel']} !important; color: {COLORS['text']} !important;
    border: 1px solid {COLORS['border_strong']} !important; border-radius: 8px !important;
}}

/* Butonlar */
.stButton button {{
    background: {COLORS['navy']} !important; color: #FFFFFF !important; font-weight: 600 !important;
    border: none !important; border-radius: 8px !important; padding: 10px 22px !important;
    font-size: 13.5px !important; transition: background 0.15s ease;
}}
.stButton button:hover {{ background: {COLORS['navy_light']} !important; }}
.stButton button:disabled {{
    background: {COLORS['border']} !important; color: {COLORS['text_faint']} !important;
}}

/* Birincil eylem butonu (Ekibi Gonder gibi) */
.action-btn-active button {{
    background: {COLORS['alarm']} !important;
}}
.action-btn-active button:hover {{ background: #B91C1C !important; }}

/* Logo basligi */
.brand-header {{
    display: flex; align-items: center; gap: 10px; padding: 4px 4px 18px 4px;
}}
.brand-title {{ font-size: 17px; font-weight: 800; color: #fff; letter-spacing: -0.01em; }}
.brand-sub {{ font-size: 10.5px; color: #8FA3C2; margin-top: -2px; }}

/* Scrollbar */
::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-track {{ background: {COLORS['bg']}; }}
::-webkit-scrollbar-thumb {{ background: {COLORS['border_strong']}; border-radius: 3px; }}

/* Onay/basari mesaji */
.success-banner {{
    background: {COLORS['ok_bg']}; border: 1px solid #99E6DA; border-radius: 8px;
    padding: 13px 16px; color: {COLORS['ok']}; font-size: 13px; font-weight: 600;
    margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
}}
</style>
""", unsafe_allow_html=True)
# ─────────────────────────────────────────────────────────────────────────────
# EPANET TOPOLOJISI (Hanoi_CMH.inp'den cikarilan gercek sebeke yapisi)
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
PRESSURE_NODE_IDS = list(range(2, 33))  # Node_1 rezervuar, feature degil
FLOW_LINK_IDS = list(range(1, 35))
DEMAND_NODE_IDS = list(range(1, 33))


@st.cache_data
def local_to_latlon(center_lat, center_lon, span_km=1.8):
    """
    EPANET'in yerel X/Y koordinatlarini, sehir merkezi etrafinda gercekci
    bir cografi alana olcekleyip lat/lon'a cevirir. Sebekenin gercek
    topolojik sekli (node'larin birbirine gore konumu) korunur.
    """
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


# ─────────────────────────────────────────────────────────────────────────────
# BELEDIYE VERISI
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


def get_node_assignments(bel_key, n_zones):
    """Node'lari izole bolgelere (DMA) deterministik olarak dagitir."""
    node_ids = PRESSURE_NODE_IDS
    chunk = len(node_ids) // n_zones
    assignments = {}
    for i, nid in enumerate(node_ids):
        zone_idx = min(i // max(chunk, 1), n_zones - 1)
        assignments[nid] = zone_idx
    return assignments
# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "belediye": "Merzifon Belediyesi",
        "alarm_log": [],
        "ekip_gonderildi": [],
        "manuel_tahmin_log": [],
        "secili_node": None,
        "api_durumu_kontrol_edildi": False,
        "api_aktif": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get_node_states(bel_key, alarm_node_ids=None, seed_offset=0):
    """Demo amacli node durumlarini uretir (gercek API baglandiginda
    bu fonksiyonun yerini /predict cevaplari alacak)."""
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
    """Backend API'nin erisilebilir olup olmadigini kontrol eder."""
    try:
        resp = requests.get(f"{API_URL}/health", timeout=3)
        return resp.status_code == 200 and resp.json().get("model_loaded", False)
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# FOLIUM HARITA URETIMI
# ─────────────────────────────────────────────────────────────────────────────
STATUS_COLOR = {"alarm": "#DC2626", "warning": "#B45309", "ok": "#0F766E"}
STATUS_LABEL = {"alarm": "Alarm", "warning": "Uyarı", "ok": "Normal"}


def build_network_map(bel_key, node_states, detay_seviyesi="ozet", highlight_node=None):
    """
    Gercek OpenStreetMap uzerine, EPANET topolojisinden turetilmis
    sebeke gorselini (node + boru hatlari) cizer.
    detay_seviyesi: 'ozet' (Canli Izleme icin sade) | 'detay' (Sebeke Haritasi icin tum bilgi)
    """
    bel = BELEDIYELER[bel_key]
    latlon = local_to_latlon(*bel["merkez"], span_km=bel["span_km"])

    center = bel["merkez"]
    m = folium.Map(
        location=center, zoom_start=15, tiles="CartoDB positron",
        control_scale=True,
    )

    # Boru hatlari (linkler)
    for pipe_id, n1, n2 in PIPES:
        if n1 in latlon and n2 in latlon:
            s1 = node_states.get(n1, {}).get("status", "ok") if n1 != RESERVOIR_ID else "ok"
            s2 = node_states.get(n2, {}).get("status", "ok") if n2 != RESERVOIR_ID else "ok"
            is_alarm_line = (s1 == "alarm" or s2 == "alarm")
            folium.PolyLine(
                locations=[latlon[n1], latlon[n2]],
                color="#DC2626" if is_alarm_line else "#94A3B8",
                weight=4 if is_alarm_line else 2.4,
                opacity=0.85 if is_alarm_line else 0.55,
            ).add_to(m)

    # Rezervuar
    if RESERVOIR_ID in latlon:
        folium.CircleMarker(
            location=latlon[RESERVOIR_ID], radius=9, color="#0B1C36",
            fill=True, fill_color="#0B1C36", fill_opacity=1, weight=2,
            popup=folium.Popup("Rezervuar (Ana Su Kaynağı)", max_width=200),
            tooltip="Rezervuar",
        ).add_to(m)

    # Olcum noktalari (node'lar)
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
                fill=True, fill_opacity=0.10, weight=1, opacity=0.4,
            ).add_to(m)

    return m, latlon
init_state()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — SOL MENU
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="brand-header">
        <div class="brand-title">AquaSense</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="brand-sub" style="margin-top:-14px;margin-bottom:18px">Su Şebekesi Kaçak Tespit Sistemi</div>', unsafe_allow_html=True)

    sayfa = st.radio(
        label="Navigasyon",
        options=[
            "Canlı İzleme",
            "Şebeke Haritası",
            "İzole Ölçüm Bölgeleri",
            "Manuel Tahmin",
            "Sistem & Model",
        ],
        label_visibility="collapsed",
    )

    st.markdown('<hr>', unsafe_allow_html=True)

    st.markdown('<div class="metric-label" style="color:#8FA3C2">Belediye Seçimi</div>', unsafe_allow_html=True)
    bel_secim = st.selectbox("Belediye", list(BELEDIYELER.keys()), label_visibility="collapsed")
    st.session_state.belediye = bel_secim
    bel = BELEDIYELER[bel_secim]

    st.markdown('<hr>', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="font-size:12px;line-height:1.9;color:#B9C6DC">
        <b style="color:#fff">İl:</b> {bel['il']}<br>
        <b style="color:#fff">Nüfus:</b> {bel['nufus']:,}<br>
        <b style="color:#fff">İzole Bölge:</b> {len(bel['izole_bolgeler'])}<br>
        <b style="color:#fff">Ölçüm Noktası:</b> {len(PRESSURE_NODE_IDS)}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr>', unsafe_allow_html=True)

    # Baglanti durumu kontrolu
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
    st.markdown(f'<div style="font-size:10px;color:#5C7299;">Son güncelleme<br><span style="font-family:JetBrains Mono;color:#8FA3C2">{datetime.now().strftime("%d.%m.%Y %H:%M")}</span></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# UST BASLIK (her sayfada ortak)
# ─────────────────────────────────────────────────────────────────────────────
def render_page_header(title, subtitle=None):
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
        <div>
            <div style="font-size:21px;font-weight:800;color:{COLORS['text']}">{title}</div>
            <div style="font-size:12.5px;color:{COLORS['text_muted']};margin-top:2px">{subtitle or f"{bel_secim} — {bel['il']} İli"}</div>
        </div>
        <div style="font-family:JetBrains Mono;font-size:12px;color:{COLORS['text_muted']};text-align:right">
            {datetime.now().strftime("%d %B %Y")}<br>
            <span style="color:{COLORS['navy']};font-weight:600">{datetime.now().strftime("%H:%M:%S")}</span>
        </div>
    </div>
    <hr style="border-color:{COLORS['border']};margin:14px 0 22px 0">
    """, unsafe_allow_html=True)
# ═════════════════════════════════════════════════════════════════════════════
# SAYFA: CANLI İZLEME
# ═════════════════════════════════════════════════════════════════════════════
if sayfa == "Canlı İzleme":
    render_page_header("Canlı İzleme")

    st.markdown("""<div class="guide-box">
    Bu sayfa şebeke genelindeki anlık durumu özetler. <b>Harita</b> üzerinde tüm ölçüm noktaları görünür;
    kaçak şüphesi taşıyan noktalar kırmızı renkle işaretlenir. Sağdaki liste, alarm durumundaki noktaları
    otomatik olarak üste taşır. Bir kaçak tespit edildiğinde <b>"Ekibi Gönder"</b> butonu aktif hale gelir.
    </div>""", unsafe_allow_html=True)

    # --- Ust satir: gecmis alarmlar + pdf indir ---
    col_spacer, col_hist, col_pdf = st.columns([6, 1.3, 1.3])
    with col_hist:
        gecmis_ac = st.button("Geçmiş Alarmlar", use_container_width=True)
    with col_pdf:
        st.button("PDF Olarak İndir", use_container_width=True, key="pdf_canli")

    if gecmis_ac:
        with st.expander("Geçmiş Müdahale Kayıtları", expanded=True):
            if st.session_state.ekip_gonderildi:
                st.dataframe(pd.DataFrame(st.session_state.ekip_gonderildi), use_container_width=True, hide_index=True)
            else:
                st.markdown(f'<div style="color:{COLORS["text_faint"]};font-size:13px;padding:12px 0">Henüz ekip yönlendirmesi yapılmadı.</div>', unsafe_allow_html=True)

    # --- Demo durum uretimi (gercek API baglandiginda /predict cevaplariyla degisecek) ---
    demo_alarm_nodes = [PRESSURE_NODE_IDS[3]]  # ornek: bir node alarmda
    node_states = get_node_states(bel_secim, demo_alarm_nodes)

    alarm_count = sum(1 for s in node_states.values() if s["status"] == "alarm")
    warning_count = sum(1 for s in node_states.values() if s["status"] == "warning")
    ok_count = sum(1 for s in node_states.values() if s["status"] == "ok")

    # --- Ust metrik satiri ---
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

    # --- Harita + Dinamik Liste ---
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
                        <div style="font-weight:600;font-size:13px">Ölçüm Noktası {nid}</div>
                        <div style="font-family:JetBrains Mono;font-size:11px;color:{COLORS['text_muted']}">{state['pressure']} bar · {state['flow']} m³/h</div>
                    </div>
                    <span class="badge {badge_cls}">{badge_text}</span>
                </div>
                """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # --- Detay paneli + Ekibi Gonder ---
    col_detail, col_action = st.columns([2, 1])

    alarm_nodes_list = [nid for nid, s in node_states.items() if s["status"] == "alarm"]
    has_alarm = len(alarm_nodes_list) > 0

    with col_detail:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px">Detay ve Açıklama Paneli</div>', unsafe_allow_html=True)
        if has_alarm:
            primary = alarm_nodes_list[0]
            st_data = node_states[primary]
            st.markdown(f"""
            <div class="metric-card alarm">
                <div class="metric-label">Tespit Edilen Anomali</div>
                <div style="font-size:15px;font-weight:700;color:{COLORS['alarm']};margin-bottom:6px">Ölçüm Noktası {primary} — Kaçak Şüphesi</div>
                <div style="font-size:12.5px;color:{COLORS['text_muted']};line-height:1.7">
                    Bu noktada anlık basınç değeri ({st_data['pressure']} bar) beklenen aralığın
                    önemli ölçüde altında. Model, bu örüntüyü <b>%{st_data['probability']*100:.1f}</b> olasılıkla
                    kaçak olarak sınıflandırdı. Şebeke topolojisine göre bu nokta, ana hat üzerinde
                    yer almakta ve çevresindeki {len([p for p in PIPES if primary in (p[1], p[2])])} boru hattını etkilemektedir.
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="metric-card ok">
                <div class="metric-label">Genel Durum</div>
                <div style="font-size:15px;font-weight:700;color:{COLORS['ok']};margin-bottom:6px">Şebeke Normal Çalışıyor</div>
                <div style="font-size:12.5px;color:{COLORS['text_muted']};line-height:1.7">
                    Şu anda hiçbir ölçüm noktasında kaçak şüphesi tespit edilmedi. Tüm basınç ve debi
                    değerleri beklenen aralıklar içinde. Sistem her 30 dakikada bir otomatik olarak
                    yeniden değerlendirme yapar.
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_action:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px">Operasyon</div>', unsafe_allow_html=True)

        btn_container_cls = "action-btn-active" if has_alarm else ""
        st.markdown(f'<div class="{btn_container_cls}">', unsafe_allow_html=True)
        ekip_gonder_clicked = st.button(
            "Ekibi Gönder" if has_alarm else "Ekibi Gönder (Alarm Yok)",
            disabled=not has_alarm,
            use_container_width=True,
            key="ekip_gonder_btn",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        if ekip_gonder_clicked and has_alarm:
            primary = alarm_nodes_list[0]
            adres = random.choice(bel["ornek_adresler"])
            st.session_state.ekip_gonderildi.append({
                "Zaman": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                "Ölçüm Noktası": f"Node {primary}",
                "Adres": adres,
                "Belediye": bel_secim,
            })
            st.markdown(f"""
            <div class="success-banner">
                ✓ Birlik Gönderildi — Hedef Adres: {adres}
            </div>
            """, unsafe_allow_html=True)

        if not has_alarm:
            st.markdown(f'<div style="font-size:11.5px;color:{COLORS["text_faint"]};margin-top:8px;line-height:1.6">Buton, sistem bir kaçak tespit ettiğinde otomatik olarak aktif hale gelir.</div>', unsafe_allow_html=True)
# ═════════════════════════════════════════════════════════════════════════════
# SAYFA: ŞEBEKE HARİTASI (detayli seviye)
# ═════════════════════════════════════════════════════════════════════════════
elif sayfa == "Şebeke Haritası":
    render_page_header("Şebeke Haritası")

    st.markdown("""<div class="guide-box">
    Bu sayfa, seçili belediyeye ait tüm ölçüm noktalarını ve boru hatlarını gerçek coğrafi konumları
    üzerinde gösterir. Şebeke yapısı, EPANET hidrolik model verisinden türetilmiştir.
    Bir noktaya tıklayarak basınç, debi ve kaçak olasılığı detaylarını görüntüleyebilirsiniz.
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
            ("Veri Kaynağı", "EPANET / Hanoi Topolojisi"),
        ]
        for label, val in info_items:
            st.markdown(f"""<div class="node-row" style="margin-bottom:6px">
                <div class="metric-label" style="margin:0">{label}</div>
                <div style="font-family:JetBrains Mono;font-size:12px;color:{COLORS['text']}">{val}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="font-size:11.5px;color:{COLORS['text_muted']};line-height:1.7">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{COLORS['alarm']};margin-right:6px"></span>Alarm<br>
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{COLORS['warning']};margin-right:6px"></span>Uyarı<br>
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{COLORS['ok']};margin-right:6px"></span>Normal<br>
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{COLORS['navy']};margin-right:6px"></span>Rezervuar
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


# ═════════════════════════════════════════════════════════════════════════════
# SAYFA: İZOLE ÖLÇÜM BÖLGELERİ (DMA)
# ═════════════════════════════════════════════════════════════════════════════
elif sayfa == "İzole Ölçüm Bölgeleri":
    render_page_header("İzole Ölçüm Bölgeleri")

    st.markdown("""<div class="guide-box">
    İzole Ölçüm Bölgesi (İÖB), şebekenin su dengesi ve kaçak riskinin ayrı ayrı izlenebilmesi için
    bölündüğü alt bölgelerdir. Bu sayfa her bölgenin ortalama basınç, debi ve tahmini kayıp oranını
    karşılaştırır. Riskli bölgeler listenin en üstünde gösterilir.
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
                <div style="margin-top:8px;font-size:11px;color:{COLORS['text_muted']}">
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
# ═════════════════════════════════════════════════════════════════════════════
# SAYFA: MANUEL TAHMIN
# ═════════════════════════════════════════════════════════════════════════════
elif sayfa == "Manuel Tahmin":
    render_page_header("Manuel Tahmin")

    st.markdown("""<div class="guide-box">
    Bu sayfa, sahadan alınan anlık sensör ölçümlerini modele göndererek tek seferlik kaçak tahmini
    yapmanızı sağlar. Değerleri girip <b>"Tahmin Yap"</b> butonuna basın. Sonuç, kaçak olasılığı ve
    şüpheli ölçüm noktalarıyla birlikte gösterilir.
    </div>""", unsafe_allow_html=True)

    col_form, col_result = st.columns([1, 1])

    with col_form:
        st.markdown(f'<div style="font-size:13px;font-weight:700;color:{COLORS["text"]};margin-bottom:14px">Sensör Değerleri <span class="hint">Saat ve örnek noktalar</span></div>', unsafe_allow_html=True)

        hour_val = st.slider("Saat (0–23)", 0, 23, datetime.now().hour)

        st.markdown(f'<div style="font-size:11.5px;color:{COLORS["text_muted"]};margin:14px 0 8px;font-weight:600">Basınç Değerleri (bar)</div>', unsafe_allow_html=True)
        node_cols = st.columns(3)
        p_values = {}
        sample_nodes = [2, 5, 10, 15, 20, 25]
        for idx, n in enumerate(sample_nodes):
            with node_cols[idx % 3]:
                p_values[f"P_Node_{n}"] = st.number_input(f"Nokta {n}", value=4.0, step=0.1, key=f"p{n}")

        st.markdown(f'<div style="font-size:11.5px;color:{COLORS["text_muted"]};margin:14px 0 8px;font-weight:600">Debi Değerleri (m³/h)</div>', unsafe_allow_html=True)
        link_cols = st.columns(3)
        f_values = {}
        sample_links = [1, 5, 10, 15, 20, 25]
        for idx, n in enumerate(sample_links):
            with link_cols[idx % 3]:
                f_values[f"F_Link_{n}"] = st.number_input(f"Hat {n}", value=2.0, step=0.1, key=f"f{n}")

        predict_btn = st.button("Tahmin Yap", use_container_width=True)

    with col_result:
        st.markdown(f'<div style="font-size:13px;font-weight:700;color:{COLORS["text"]};margin-bottom:14px">Tahmin Sonucu</div>', unsafe_allow_html=True)

        if predict_btn:
            payload = {}
            for i in PRESSURE_NODE_IDS:
                payload[f"P_Node_{i}"] = p_values.get(f"P_Node_{i}", 4.0)
            for i in FLOW_LINK_IDS:
                payload[f"F_Link_{i}"] = f_values.get(f"F_Link_{i}", 2.0)
            for i in DEMAND_NODE_IDS:
                payload[f"D_Node_{i}"] = 1.5
            payload["hour"] = hour_val
            payload["timestamp"] = datetime.now().isoformat()

            api_ok = True
            try:
                resp = requests.post(f"{API_URL}/predict", json=payload, timeout=6)
                data = resp.json()
                pred = data.get("prediction", 0)
                proba = data.get("leak_probability", 0.0)
                suspicious = data.get("suspicious_nodes", [])
            except Exception:
                api_ok = False
                pred, proba, suspicious = 0, 0.0, []

            if not api_ok:
                st.markdown(f'<div class="status-pill offline" style="margin-bottom:14px">Sunucuya erişilemedi — lütfen bağlantıyı kontrol edin</div>', unsafe_allow_html=True)
            else:
                cls = "alarm" if pred == 1 else "ok"
                verdict = "KAÇAK TESPİT EDİLDİ" if pred == 1 else "NORMAL"
                verdict_color = COLORS["alarm"] if pred == 1 else COLORS["ok"]

                st.markdown(f"""<div class="metric-card {cls}" style="margin-bottom:16px">
                    <div class="metric-label">Tahmin Sonucu</div>
                    <div style="font-size:24px;font-weight:800;color:{verdict_color};font-family:JetBrains Mono">{verdict}</div>
                    <div class="metric-sub">Kaçak olasılığı: <span style="font-family:JetBrains Mono;color:{verdict_color};font-weight:700">{proba:.3f}</span></div>
                </div>""", unsafe_allow_html=True)

                if suspicious:
                    st.markdown(f'<div class="metric-card alarm"><div class="metric-label">Şüpheli Ölçüm Noktaları</div><div style="font-family:JetBrains Mono;font-size:13px">{", ".join(suspicious)}</div></div>', unsafe_allow_html=True)

                st.session_state.manuel_tahmin_log.append({
                    "Zaman": datetime.now().strftime("%H:%M:%S"),
                    "Tahmin": verdict,
                    "Olasılık": f"{proba:.3f}",
                    "Saat": hour_val,
                })
        else:
            st.markdown(f'<div style="color:{COLORS["text_faint"]};font-size:13px;padding:50px 0;text-align:center">Değerleri girin ve "Tahmin Yap" butonuna basın.</div>', unsafe_allow_html=True)

        if st.session_state.manuel_tahmin_log:
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px">Oturum Tahmin Geçmişi</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(st.session_state.manuel_tahmin_log[-10:]), use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════════════════════════════════════
# SAYFA: SİSTEM & MODEL
# ═════════════════════════════════════════════════════════════════════════════
elif sayfa == "Sistem & Model":
    render_page_header("Sistem & Model")

    st.markdown("""<div class="guide-box">
    Bu sayfa AquaSense sisteminin teknik altyapısını ve model performansını özetler.
    Yarışma jürisi veya teknik ekip için referans niteliğindedir.
    </div>""", unsafe_allow_html=True)

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
    st.markdown(f'<div style="font-size:13px;font-weight:700;color:{COLORS["text"]};margin-bottom:14px">Veri İşlem Hattı</div>', unsafe_allow_html=True)

    pipeline_steps = [
        ("1", "LeakDB Veri Seti", "17.520 adım/senaryo, 1000 senaryo"),
        ("2", "Özellik Mühendisliği", "161 özellik: basınç, debi, talep, zaman"),
        ("3", "Kademeli Eğitim", "100 senaryo/grup × 7 grup, XGBoost"),
        ("4", "FastAPI Servisi", "/predict → 98 sensör → anlık tahmin"),
        ("5", "Streamlit Arayüzü", "Canlı izleme, harita, bölge analizi"),
    ]
    p_cols = st.columns(5)
    for col, (num, title, desc) in zip(p_cols, pipeline_steps):
        with col:
            st.markdown(f"""<div style="background:{COLORS['panel']};border-radius:10px;padding:16px;border:1px solid {COLORS['border']};text-align:center">
                <div style="font-family:JetBrains Mono;font-size:19px;font-weight:700;color:{COLORS['navy']}">{num}</div>
                <div style="font-size:12px;font-weight:700;color:{COLORS['text']};margin:6px 0 4px">{title}</div>
                <div style="font-size:10.5px;color:{COLORS['text_muted']};line-height:1.4">{desc}</div>
            </div>""", unsafe_allow_html=True)
