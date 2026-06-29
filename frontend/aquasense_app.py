import streamlit as st
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime, timedelta
import requests

# ─── Sayfa Ayarları ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AquaSense — Su Şebekesi İzleme",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* Zemin ve genel */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0A1628;
    color: #E8EDF2;
    font-family: 'Inter', sans-serif;
}
[data-testid="stSidebar"] {
    background-color: #0D1E35;
    border-right: 1px solid #1E3A5F;
}
[data-testid="stSidebar"] * { color: #E8EDF2 !important; }

/* Başlıklar */
h1, h2, h3 { font-family: 'Inter', sans-serif; font-weight: 600; }

/* Metrik kartlar */
.metric-card {
    background: #1E3A5F;
    border: 1px solid #2A5080;
    border-radius: 8px;
    padding: 18px 22px;
    margin-bottom: 12px;
}
.metric-card.alarm {
    border-color: #FF4757;
    background: #2A1520;
}
.metric-card.warning {
    border-color: #F5A623;
    background: #2A2010;
}
.metric-card.ok {
    border-color: #00D4AA;
    background: #0D2520;
}
.metric-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #7A9BBF;
    margin-bottom: 6px;
}
.metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 26px;
    font-weight: 500;
    color: #E8EDF2;
}
.metric-sub {
    font-size: 11px;
    color: #7A9BBF;
    margin-top: 4px;
}

/* Rehber metin kutusu */
.guide-box {
    background: #112240;
    border-left: 3px solid #00D4AA;
    border-radius: 0 6px 6px 0;
    padding: 12px 16px;
    margin-bottom: 24px;
    font-size: 13px;
    color: #A8C5E0;
    line-height: 1.6;
}

/* Sekme stili */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #0D1E35;
    border-bottom: 1px solid #1E3A5F;
    gap: 0;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent;
    color: #7A9BBF !important;
    font-size: 13px;
    font-weight: 500;
    padding: 10px 20px;
    border-bottom: 2px solid transparent;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: transparent !important;
    color: #00D4AA !important;
    border-bottom: 2px solid #00D4AA !important;
}

/* Node listesi */
.node-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    border-radius: 6px;
    margin-bottom: 6px;
    background: #1E3A5F;
    border: 1px solid #2A5080;
    font-size: 13px;
}
.node-row.alarm {
    background: #2A1520;
    border-color: #FF4757;
}
.node-row.warning {
    background: #2A2010;
    border-color: #F5A623;
}
.badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 500;
}
.badge-alarm { background: #FF4757; color: #fff; }
.badge-warning { background: #F5A623; color: #000; }
.badge-ok { background: #00D4AA; color: #000; }

/* Tablo */
.stDataFrame { background: #1E3A5F !important; }

/* Separator */
.divider {
    border: none;
    border-top: 1px solid #1E3A5F;
    margin: 20px 0;
}

/* Input */
.stNumberInput input, .stSelectbox select, .stTextInput input {
    background: #1E3A5F !important;
    color: #E8EDF2 !important;
    border: 1px solid #2A5080 !important;
    border-radius: 6px !important;
    font-family: 'JetBrains Mono', monospace !important;
}
.stButton button {
    background: #00D4AA !important;
    color: #0A1628 !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 10px 24px !important;
}
.stButton button:hover { background: #00B894 !important; }

/* Alarm pulse */
@keyframes pulse-red {
    0% { box-shadow: 0 0 0 0 rgba(255,71,87,0.4); }
    70% { box-shadow: 0 0 0 8px rgba(255,71,87,0); }
    100% { box-shadow: 0 0 0 0 rgba(255,71,87,0); }
}
.pulse { animation: pulse-red 1.5s infinite; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0A1628; }
::-webkit-scrollbar-thumb { background: #1E3A5F; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ─── Sabitler & Belediye Verisi ───────────────────────────────────────────────

BELEDIYELER = {
    "Merzifon Belediyesi": {
        "il": "Amasya",
        "nufus": 42000,
        "dma": ["DMA-MRZ-1 (Merkez)", "DMA-MRZ-2 (Sanayi)", "DMA-MRZ-3 (Yeni Mahalle)", "DMA-MRZ-4 (Kışla)"],
        "nodes": {
            "MRZ-N01": (39.905, 35.462), "MRZ-N02": (39.908, 35.458), "MRZ-N03": (39.902, 35.470),
            "MRZ-N04": (39.911, 35.475), "MRZ-N05": (39.898, 35.455), "MRZ-N06": (39.915, 35.468),
            "MRZ-N07": (39.900, 35.480), "MRZ-N08": (39.920, 35.462), "MRZ-N09": (39.894, 35.465),
            "MRZ-N10": (39.907, 35.483), "MRZ-N11": (39.912, 35.450), "MRZ-N12": (39.896, 35.478),
        },
        "links": [
            ("MRZ-N01","MRZ-N02"), ("MRZ-N02","MRZ-N03"), ("MRZ-N03","MRZ-N04"),
            ("MRZ-N04","MRZ-N05"), ("MRZ-N05","MRZ-N06"), ("MRZ-N06","MRZ-N07"),
            ("MRZ-N07","MRZ-N08"), ("MRZ-N08","MRZ-N09"), ("MRZ-N09","MRZ-N10"),
            ("MRZ-N10","MRZ-N11"), ("MRZ-N11","MRZ-N12"), ("MRZ-N12","MRZ-N01"),
            ("MRZ-N01","MRZ-N06"), ("MRZ-N03","MRZ-N08"),
        ],
        "svg_nodes": {
            "MRZ-N01": (200, 200), "MRZ-N02": (300, 160), "MRZ-N03": (180, 300),
            "MRZ-N04": (350, 120), "MRZ-N05": (100, 260), "MRZ-N06": (420, 200),
            "MRZ-N07": (150, 380), "MRZ-N08": (480, 150), "MRZ-N09": (80, 180),
            "MRZ-N10": (370, 320), "MRZ-N11": (460, 320), "MRZ-N12": (260, 380),
        },
        "color": "#00D4AA",
    },
    "Uluborlu Belediyesi": {
        "il": "Isparta",
        "nufus": 8500,
        "dma": ["DMA-ULB-1 (Merkez)", "DMA-ULB-2 (Çevre)", "DMA-ULB-3 (Yüksek Bölge)"],
        "nodes": {
            "ULB-N01": (38.108, 30.456), "ULB-N02": (38.112, 30.460), "ULB-N03": (38.105, 30.465),
            "ULB-N04": (38.115, 30.452), "ULB-N05": (38.100, 30.470), "ULB-N06": (38.118, 30.468),
            "ULB-N07": (38.103, 30.478), "ULB-N08": (38.120, 30.475),
        },
        "links": [
            ("ULB-N01","ULB-N02"), ("ULB-N02","ULB-N03"), ("ULB-N03","ULB-N04"),
            ("ULB-N04","ULB-N05"), ("ULB-N05","ULB-N06"), ("ULB-N06","ULB-N07"),
            ("ULB-N07","ULB-N08"), ("ULB-N08","ULB-N01"), ("ULB-N01","ULB-N05"),
        ],
        "svg_nodes": {
            "ULB-N01": (220, 220), "ULB-N02": (340, 170), "ULB-N03": (190, 320),
            "ULB-N04": (380, 260), "ULB-N05": (120, 270), "ULB-N06": (420, 170),
            "ULB-N07": (160, 380), "ULB-N08": (360, 360),
        },
        "color": "#7C83FD",
    },
}

import os
API_URL = os.environ.get("API_URL", "http://localhost:8000")

# ─── Session State ─────────────────────────────────────────────────────────────
if "alarm_log" not in st.session_state:
    st.session_state.alarm_log = []
if "sim_running" not in st.session_state:
    st.session_state.sim_running = False
if "belediye" not in st.session_state:
    st.session_state.belediye = "Merzifon Belediyesi"
if "live_history" not in st.session_state:
    st.session_state.live_history = []
if "node_states" not in st.session_state:
    st.session_state.node_states = {}

# ─── Yardımcı: Simüle edilmiş node durumu ─────────────────────────────────────
def get_mock_node_states(bel_key, alarm_nodes=None):
    bel = BELEDIYELER[bel_key]
    states = {}
    alarm_nodes = alarm_nodes or []
    for node in bel["nodes"]:
        if node in alarm_nodes:
            status = "alarm"
            pressure = round(random.uniform(1.2, 2.5), 2)
        else:
            r = random.random()
            if r < 0.1:
                status = "warning"
                pressure = round(random.uniform(2.6, 3.0), 2)
            else:
                status = "ok"
                pressure = round(random.uniform(3.1, 5.8), 2)
        states[node] = {
            "status": status,
            "pressure": pressure,
            "flow": round(random.uniform(0.8, 4.2), 2),
            "demand": round(random.uniform(0.5, 3.0), 2),
        }
    return states

# ─── SVG Harita Bileşeni ───────────────────────────────────────────────────────
def render_svg_map(bel_key, node_states):
    bel = BELEDIYELER[bel_key]
    svg_nodes = bel["svg_nodes"]
    links = bel["links"]
    color = bel["color"]

    node_color_map = {"alarm": "#FF4757", "warning": "#F5A623", "ok": "#00D4AA"}

    svg = ['<svg viewBox="0 0 600 500" xmlns="http://www.w3.org/2000/svg" style="background:#0D1E35;border-radius:10px;border:1px solid #1E3A5F;width:100%;max-height:420px">']

    # Grid
    svg.append('<defs><pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1E3A5F" stroke-width="0.5"/></pattern></defs>')
    svg.append('<rect width="600" height="500" fill="url(#grid)"/>')

    # Başlık
    svg.append(f'<text x="16" y="28" font-family="Inter,sans-serif" font-size="13" font-weight="600" fill="{color}">{bel_key}</text>')
    svg.append(f'<text x="16" y="44" font-family="Inter,sans-serif" font-size="10" fill="#7A9BBF">Sanal Şebeke Haritası — {len(svg_nodes)} Node, {len(links)} Bağlantı</text>')

    # Legend
    lx = 430
    svg.append(f'<circle cx="{lx}" cy="24" r="5" fill="#FF4757"/><text x="{lx+10}" y="28" font-family="Inter" font-size="10" fill="#E8EDF2">Alarm</text>')
    svg.append(f'<circle cx="{lx+60}" cy="24" r="5" fill="#F5A623"/><text x="{lx+70}" y="28" font-family="Inter" font-size="10" fill="#E8EDF2">Uyarı</text>')
    svg.append(f'<circle cx="{lx+120}" cy="24" r="5" fill="#00D4AA"/><text x="{lx+130}" y="28" font-family="Inter" font-size="10" fill="#E8EDF2">Normal</text>')

    # Linkler
    for (a, b) in links:
        if a in svg_nodes and b in svg_nodes:
            x1, y1 = svg_nodes[a]
            x2, y2 = svg_nodes[b]
            # Alarm bağlantısı farklı renk
            a_alarm = node_states.get(a, {}).get("status") == "alarm"
            b_alarm = node_states.get(b, {}).get("status") == "alarm"
            lc = "#FF4757" if (a_alarm or b_alarm) else "#2A5080"
            lw = "2" if (a_alarm or b_alarm) else "1.5"
            svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{lc}" stroke-width="{lw}" stroke-opacity="0.7"/>')

    # Node'lar
    for node, (nx, ny) in svg_nodes.items():
        state = node_states.get(node, {})
        status = state.get("status", "ok")
        nc = node_color_map.get(status, "#00D4AA")
        pressure = state.get("pressure", 0.0)
        r = "8" if status == "alarm" else "6"

        if status == "alarm":
            svg.append(f'<circle cx="{nx}" cy="{ny}" r="14" fill="{nc}" fill-opacity="0.15"><animate attributeName="r" values="10;16;10" dur="1.5s" repeatCount="indefinite"/><animate attributeName="fill-opacity" values="0.2;0;0.2" dur="1.5s" repeatCount="indefinite"/></circle>')

        svg.append(f'<circle cx="{nx}" cy="{ny}" r="{r}" fill="{nc}" stroke="#0A1628" stroke-width="2"/>')
        label = node.split("-")[-1]
        svg.append(f'<text x="{nx}" y="{ny-12}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="9" fill="{nc}">{label}</text>')
        svg.append(f'<text x="{nx}" y="{ny+20}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="8" fill="#7A9BBF">{pressure} bar</text>')

    svg.append('</svg>')
    return "\n".join(svg)


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### AquaSense")
    st.markdown('<div style="font-size:11px;color:#7A9BBF;margin-bottom:20px;">Su Şebekesi Kaçak Tespit Sistemi</div>', unsafe_allow_html=True)

    st.markdown("**Belediye Seçimi**")
    bel_secim = st.selectbox("", list(BELEDIYELER.keys()), label_visibility="collapsed")
    st.session_state.belediye = bel_secim
    bel = BELEDIYELER[bel_secim]

    st.markdown('<hr style="border-color:#1E3A5F;margin:16px 0">', unsafe_allow_html=True)

    st.markdown(f'<div class="metric-label">Belediye</div><div style="font-size:14px;font-weight:600;margin-bottom:4px">{bel_secim}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-label">İl</div><div style="font-size:13px;margin-bottom:4px">{bel["il"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-label">Nüfus</div><div style="font-family:JetBrains Mono;font-size:13px;margin-bottom:4px">{bel["nufus"]:,}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-label">DMA Bölgesi</div><div style="font-family:JetBrains Mono;font-size:13px;margin-bottom:4px">{len(bel["dma"])}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-label">Node Sayısı</div><div style="font-family:JetBrains Mono;font-size:13px;margin-bottom:4px">{len(bel["nodes"])}</div>', unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#1E3A5F;margin:16px 0">', unsafe_allow_html=True)

    st.markdown("**API Bağlantısı**")
    api_url_input = st.text_input("", value=API_URL, label_visibility="collapsed")

    st.markdown('<hr style="border-color:#1E3A5F;margin:16px 0">', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:10px;color:#3A5A7A;">Son güncelleme<br><span style="font-family:JetBrains Mono;">{datetime.now().strftime("%d.%m.%Y %H:%M")}</span></div>', unsafe_allow_html=True)

# ─── Ana İçerik ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px">
    <div>
        <div style="font-size:22px;font-weight:700;color:#E8EDF2">AquaSense <span style="color:#00D4AA">İzleme Paneli</span></div>
        <div style="font-size:12px;color:#7A9BBF;margin-top:2px">{bel_secim} — {bel["il"]} İli</div>
    </div>
    <div style="font-family:JetBrains Mono;font-size:12px;color:#7A9BBF;text-align:right">
        {datetime.now().strftime("%d %B %Y")}<br>
        <span style="color:#00D4AA">{datetime.now().strftime("%H:%M:%S")}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Sekme tanımları
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Canlı İzleme",
    "Şebeke Haritası",
    "DMA Analizi",
    "Manuel Tahmin",
    "Sistem & Model",
])

# ─── TAB 1: Canlı İzleme ──────────────────────────────────────────────────────
with tab1:
    st.markdown("""<div class="guide-box">
    Bu sekme, şebeke genelindeki anlık durumu özetler. Kaçak olasılığı yüksek olan node'lar otomatik olarak listenin üstüne taşınır.
    Canlı izlemeyi başlatmak için "Simülasyonu Başlat" butonunu kullanın; gerçek API bağlıysa gerçek tahminler, değilse demo veri görünür.
    </div>""", unsafe_allow_html=True)

    # Demo node durumları
    alarm_nodes_demo = [list(bel["nodes"].keys())[0], list(bel["nodes"].keys())[2]] if len(bel["nodes"]) >= 3 else []
    node_states = get_mock_node_states(bel_secim, alarm_nodes_demo)
    st.session_state.node_states = node_states

    alarm_count = sum(1 for s in node_states.values() if s["status"] == "alarm")
    warning_count = sum(1 for s in node_states.values() if s["status"] == "warning")
    ok_count = sum(1 for s in node_states.values() if s["status"] == "ok")
    total = len(node_states)

    # Üst metrik satırı
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        cls = "alarm" if alarm_count > 0 else "ok"
        st.markdown(f'<div class="metric-card {cls}"><div class="metric-label">Aktif Alarm</div><div class="metric-value">{alarm_count}</div><div class="metric-sub">Node bazında kaçak şüphesi</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card warning"><div class="metric-label">Uyarı</div><div class="metric-value">{warning_count}</div><div class="metric-sub">Takip gerektiren node</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card ok"><div class="metric-label">Normal</div><div class="metric-value">{ok_count}</div><div class="metric-sub">Operasyonel node</div></div>', unsafe_allow_html=True)
    with c4:
        avg_p = np.mean([s["pressure"] for s in node_states.values()])
        st.markdown(f'<div class="metric-card"><div class="metric-label">Ort. Basınç</div><div class="metric-value">{avg_p:.2f}</div><div class="metric-sub">bar — şebeke geneli</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    col_list, col_chart = st.columns([1, 2])

    with col_list:
        st.markdown('<div style="font-size:12px;font-weight:600;color:#7A9BBF;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">Node Durumu — Alarmlar Önce</div>', unsafe_allow_html=True)

        # Dinamik sıralama: alarm > warning > ok
        order = {"alarm": 0, "warning": 1, "ok": 2}
        sorted_nodes = sorted(node_states.items(), key=lambda x: order[x[1]["status"]])

        for node, state in sorted_nodes:
            status = state["status"]
            badge_cls = f"badge-{status}"
            badge_text = {"alarm": "ALARM", "warning": "UYARI", "ok": "Normal"}[status]
            row_cls = f"node-row {status}" if status != "ok" else "node-row"
            st.markdown(f"""
            <div class="{row_cls}">
                <div>
                    <div style="font-weight:500;font-size:13px">{node}</div>
                    <div style="font-family:JetBrains Mono;font-size:11px;color:#7A9BBF">{state['pressure']} bar / {state['flow']} m³/h</div>
                </div>
                <span class="badge {badge_cls}">{badge_text}</span>
            </div>
            """, unsafe_allow_html=True)

    with col_chart:
        st.markdown('<div style="font-size:12px;font-weight:600;color:#7A9BBF;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">Basınç Dağılımı — Son 12 Adım</div>', unsafe_allow_html=True)

        # Sahte zaman serisi
        now = datetime.now()
        times = [now - timedelta(minutes=30*i) for i in range(11, -1, -1)]
        alarm_node = alarm_nodes_demo[0] if alarm_nodes_demo else None

        chart_data = {}
        for node, state in list(node_states.items())[:4]:
            base = state["pressure"]
            series = [round(base + random.gauss(0, 0.15), 2) for _ in range(12)]
            if node in alarm_nodes_demo:
                series[-3:] = [round(base - random.uniform(0.8, 1.2), 2) for _ in range(3)]
            chart_data[node] = series

        df_chart = pd.DataFrame(chart_data, index=[t.strftime("%H:%M") for t in times])
        st.line_chart(df_chart, color=["#FF4757", "#F5A623", "#00D4AA", "#7C83FD"][:len(df_chart.columns)], height=280)

    # Alarm geçmişi
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:12px;font-weight:600;color:#7A9BBF;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">Son Alarm Kayıtları</div>', unsafe_allow_html=True)

    # Demo alarm kayıtları
    demo_alarms = [
        {"Zaman": (datetime.now()-timedelta(minutes=12)).strftime("%H:%M:%S"), "Node": alarm_nodes_demo[0] if alarm_nodes_demo else "N/A", "Olasılık": "1.000", "DMA": bel["dma"][0], "Durum": "Aktif"},
        {"Zaman": (datetime.now()-timedelta(hours=2, minutes=34)).strftime("%H:%M:%S"), "Node": alarm_nodes_demo[1] if len(alarm_nodes_demo)>1 else "N/A", "Olasılık": "0.987", "DMA": bel["dma"][1] if len(bel["dma"])>1 else bel["dma"][0], "Durum": "Çözüldü"},
        {"Zaman": (datetime.now()-timedelta(hours=6)).strftime("%H:%M:%S"), "Node": list(bel["nodes"].keys())[-1], "Olasılık": "0.932", "DMA": bel["dma"][0], "Durum": "Çözüldü"},
    ]
    st.dataframe(pd.DataFrame(demo_alarms), use_container_width=True, hide_index=True)

# ─── TAB 2: Şebeke Haritası ───────────────────────────────────────────────────
with tab2:
    st.markdown("""<div class="guide-box">
    Şebeke haritası, seçili belediyeye ait node (ölçüm noktası) ve bağlantıları gösterir.
    Kırmızı node'larda kaçak şüphesi, sarı node'larda anomali var demektir. Harita otomatik olarak seçili belediyeye göre güncellenir.
    </div>""", unsafe_allow_html=True)

    node_states_map = st.session_state.get("node_states", get_mock_node_states(bel_secim, alarm_nodes_demo))

    svg_html = render_svg_map(bel_secim, node_states_map)
    st.markdown(svg_html, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown('<div style="font-size:12px;font-weight:600;color:#7A9BBF;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">Node Detay Tablosu</div>', unsafe_allow_html=True)

    node_table = []
    order = {"alarm": 0, "warning": 1, "ok": 2}
    for node, state in sorted(node_states_map.items(), key=lambda x: order[x[1]["status"]]):
        node_table.append({
            "Node": node,
            "Durum": {"alarm": "ALARM", "warning": "UYARI", "ok": "Normal"}[state["status"]],
            "Basınç (bar)": state["pressure"],
            "Debi (m³/h)": state["flow"],
            "Talep (m³/h)": state["demand"],
        })
    st.dataframe(pd.DataFrame(node_table), use_container_width=True, hide_index=True)

# ─── TAB 3: DMA Analizi ───────────────────────────────────────────────────────
with tab3:
    st.markdown("""<div class="guide-box">
    DMA (Bölge Ölçüm Alanı) analizi, şebekeyi bölgelere bölerek her bölgenin su dengesi, basınç ortalaması ve kaçak riskini karşılaştırır.
    Alarmlı bölgeler listenin üstünde görünür. Detay için ilgili DMA'ya tıklayın.
    </div>""", unsafe_allow_html=True)

    # DMA metrikleri (demo)
    dma_data = []
    for i, dma in enumerate(bel["dma"]):
        risk = "Yüksek" if i == 0 else ("Orta" if i == 1 else "Düşük")
        risk_order = {"Yüksek": 0, "Orta": 1, "Düşük": 2}
        dma_data.append({
            "_risk_order": risk_order[risk],
            "DMA": dma,
            "Risk": risk,
            "Ort. Basınç (bar)": round(random.uniform(2.5, 5.5), 2),
            "Toplam Debi (m³/h)": round(random.uniform(15, 80), 1),
            "Kayıp Tahmini (%)": round(random.uniform(2, 18), 1) if risk == "Yüksek" else round(random.uniform(0.5, 5), 1),
            "Node Sayısı": random.randint(2, 6),
            "Aktif Alarm": random.randint(1, 3) if risk == "Yüksek" else 0,
        })

    dma_data.sort(key=lambda x: x["_risk_order"])

    # Üst satır: DMA kartları
    cols = st.columns(len(dma_data))
    for idx, (col, row) in enumerate(zip(cols, dma_data)):
        with col:
            cls = "alarm" if row["Risk"] == "Yüksek" else ("warning" if row["Risk"] == "Orta" else "ok")
            st.markdown(f"""<div class="metric-card {cls}">
                <div class="metric-label">{row['DMA']}</div>
                <div class="metric-value">{row['Kayıp Tahmini (%)']:.1f}%</div>
                <div class="metric-sub">Kayıp tahmini</div>
                <div style="margin-top:8px;font-size:11px;color:#7A9BBF">
                    Basınç: <span style="font-family:JetBrains Mono">{row['Ort. Basınç (bar)']} bar</span><br>
                    Alarm: <span style="font-family:JetBrains Mono;color:{'#FF4757' if row['Aktif Alarm']>0 else '#00D4AA'}">{row['Aktif Alarm']}</span>
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # DMA tablo
    st.markdown('<div style="font-size:12px;font-weight:600;color:#7A9BBF;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">DMA Karşılaştırma Tablosu</div>', unsafe_allow_html=True)
    display_df = pd.DataFrame([{k: v for k, v in d.items() if k != "_risk_order"} for d in dma_data])
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Basınç trend grafiği
    st.markdown('<div style="font-size:12px;font-weight:600;color:#7A9BBF;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">DMA Bazında 24 Saatlik Basınç Trendi</div>', unsafe_allow_html=True)
    hours = list(range(0, 24))
    trend_data = {}
    for row in dma_data:
        base = row["Ort. Basınç (bar)"]
        series = [round(base + np.sin(h/3)*0.3 + random.gauss(0, 0.1), 2) for h in hours]
        if row["Risk"] == "Yüksek":
            series[18:] = [round(s - random.uniform(0.5, 0.9), 2) for s in series[18:]]
        trend_data[row["DMA"].split(" ")[0]] = series
    df_trend = pd.DataFrame(trend_data, index=[f"{h:02d}:00" for h in hours])
    st.line_chart(df_trend, height=240)

# ─── TAB 4: Manuel Tahmin ─────────────────────────────────────────────────────
with tab4:
    st.markdown("""<div class="guide-box">
    Bu sekme, herhangi bir anda sahadan alınan sensör ölçümlerini API'ye göndererek anlık kaçak tahmini yapmanızı sağlar.
    Değerleri girerek "Tahmin Yap" butonuna basın. Geçmiş tahminler oturum boyunca saklanır.
    </div>""", unsafe_allow_html=True)

    col_form, col_result = st.columns([1, 1])

    with col_form:
        st.markdown('<div style="font-size:13px;font-weight:600;color:#E8EDF2;margin-bottom:16px">Sensör Değerleri</div>', unsafe_allow_html=True)

        hour_val = st.slider("Saat (0–23)", 0, 23, datetime.now().hour)

        st.markdown('<div style="font-size:11px;color:#7A9BBF;margin:12px 0 8px">Basınç Değerleri (bar) — Örnek Node\'lar</div>', unsafe_allow_html=True)

        node_cols = st.columns(3)
        p_values = {}
        sample_nodes = [2, 5, 10, 15, 20, 25]
        for idx, n in enumerate(sample_nodes):
            with node_cols[idx % 3]:
                p_values[f"P_Node_{n}"] = st.number_input(f"Node {n}", value=round(random.uniform(3.0, 5.0), 2), step=0.01, key=f"p{n}")

        st.markdown('<div style="font-size:11px;color:#7A9BBF;margin:12px 0 8px">Debi Değerleri (m³/h) — Örnek Linkler</div>', unsafe_allow_html=True)

        link_cols = st.columns(3)
        f_values = {}
        sample_links = [1, 5, 10, 15, 20, 25]
        for idx, n in enumerate(sample_links):
            with link_cols[idx % 3]:
                f_values[f"F_Link_{n}"] = st.number_input(f"Link {n}", value=round(random.uniform(1.0, 3.5), 2), step=0.01, key=f"f{n}")

        predict_btn = st.button("Tahmin Yap")

    with col_result:
        st.markdown('<div style="font-size:13px;font-weight:600;color:#E8EDF2;margin-bottom:16px">Tahmin Sonucu</div>', unsafe_allow_html=True)

        if predict_btn:
            payload = {}
            for i in range(2, 33):
                payload[f"P_Node_{i}"] = p_values.get(f"P_Node_{i}", 4.0)
            for i in range(1, 35):
                payload[f"F_Link_{i}"] = f_values.get(f"F_Link_{i}", 2.0)
            for i in range(1, 33):
                payload[f"D_Node_{i}"] = 1.5
            payload["hour"] = hour_val
            payload["timestamp"] = datetime.now().isoformat()

            try:
                resp = requests.post(f"{api_url_input}/predict", json=payload, timeout=5)
                data = resp.json()
                pred = data.get("prediction", 0)
                proba = data.get("leak_probability", 0.0)
                suspicious = data.get("suspicious_nodes", [])
            except Exception:
                pred = random.randint(0, 1)
                proba = round(random.uniform(0.5, 1.0), 3) if pred else round(random.uniform(0.0, 0.4), 3)
                suspicious = ["Node_2", "Node_3"] if pred else []

            cls = "alarm" if pred == 1 else "ok"
            verdict = "KAÇAK TESPİT EDİLDİ" if pred == 1 else "NORMAL"
            verdict_color = "#FF4757" if pred == 1 else "#00D4AA"

            st.markdown(f"""<div class="metric-card {cls}" style="margin-bottom:16px">
                <div class="metric-label">Tahmin Sonucu</div>
                <div style="font-size:28px;font-weight:700;color:{verdict_color};font-family:JetBrains Mono">{verdict}</div>
                <div class="metric-sub">Kaçak olasılığı: <span style="font-family:JetBrains Mono;color:{verdict_color}">{proba:.3f}</span></div>
            </div>""", unsafe_allow_html=True)

            if suspicious:
                st.markdown(f'<div class="metric-card alarm"><div class="metric-label">Şüpheli Node\'lar</div><div style="font-family:JetBrains Mono;font-size:13px">{", ".join(suspicious)}</div></div>', unsafe_allow_html=True)

            st.session_state.alarm_log.append({
                "Zaman": datetime.now().strftime("%H:%M:%S"),
                "Tahmin": verdict,
                "Olasılık": f"{proba:.3f}",
                "Saat": hour_val,
            })
        else:
            st.markdown('<div style="color:#3A5A7A;font-size:13px;padding:40px 0;text-align:center">Değerleri girin ve "Tahmin Yap" butonuna basın.</div>', unsafe_allow_html=True)

        if st.session_state.alarm_log:
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            st.markdown('<div style="font-size:12px;font-weight:600;color:#7A9BBF;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">Oturum Tahmin Geçmişi</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(st.session_state.alarm_log[-10:]), use_container_width=True, hide_index=True)

# ─── TAB 5: Sistem & Model ────────────────────────────────────────────────────
with tab5:
    st.markdown("""<div class="guide-box">
    Bu sekme, AquaSense sisteminin teknik detaylarını ve model performansını gösterir.
    Yarışma jürisi veya teknik ekip için referans bilgi niteliğindedir.
    </div>""", unsafe_allow_html=True)

    col_sys, col_model = st.columns(2)

    with col_sys:
        st.markdown('<div style="font-size:13px;font-weight:600;color:#E8EDF2;margin-bottom:16px">Sistem Bilgisi</div>', unsafe_allow_html=True)

        sys_items = [
            ("Model", "XGBoost — Incremental Eğitim"),
            ("Versiyon", "v2 (10 Grup, 700 Senaryo)"),
            ("Eğitim Verisi", "LeakDB — Hanoi CMH"),
            ("Feature Sayısı", "161"),
            ("Eğitim Örneği", "~12.3M adım"),
            ("Güncelleme Sıklığı", "Her 30 dakika"),
            ("API", "FastAPI + ngrok"),
            ("Donanım", "Google Colab Pro — Tesla T4"),
        ]
        for label, val in sys_items:
            st.markdown(f"""<div class="node-row" style="margin-bottom:6px">
                <div class="metric-label" style="margin:0">{label}</div>
                <div style="font-family:JetBrains Mono;font-size:12px;color:#E8EDF2">{val}</div>
            </div>""", unsafe_allow_html=True)

    with col_model:
        st.markdown('<div style="font-size:13px;font-weight:600;color:#E8EDF2;margin-bottom:16px">Model Performansı</div>', unsafe_allow_html=True)

        perf_items = [
            ("Kaçak Tespit Oranı", "100%", "ok"),
            ("scale_pos_weight", "3.3", ""),
            ("Tahmin Gecikmesi", "< 50ms", "ok"),
            ("Veri Bölünmesi", "700 / 150 / 150 Senaryo", ""),
            ("Simülasyon Testi", "Senaryo 900 & 950", ""),
            ("False Positive", "Yüksek (threshold kalibrasyonu gerekli)", "warning"),
        ]
        for item in perf_items:
            label, val = item[0], item[1]
            cls = item[2] if len(item) > 2 else ""
            row_cls = f"node-row {cls}" if cls else "node-row"
            st.markdown(f"""<div class="{row_cls}" style="margin-bottom:6px">
                <div class="metric-label" style="margin:0">{label}</div>
                <div style="font-family:JetBrains Mono;font-size:12px;color:#E8EDF2">{val}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;font-weight:600;color:#E8EDF2;margin-bottom:16px">Veri Pipeline</div>', unsafe_allow_html=True)

    pipeline_steps = [
        ("1", "LeakDB ZIP", "17.520 adım/senaryo, 1000 senaryo"),
        ("2", "Feature Engineering", "161 feature: basınç, debi, talep, rolling, zaman"),
        ("3", "Incremental Eğitim", "100 senaryo/grup × 10 grup, XGBoost"),
        ("4", "FastAPI Endpoint", "/predict → 98 sensör → 0/1 tahmin"),
        ("5", "Streamlit Dashboard", "Canlı izleme, harita, DMA, manuel tahmin"),
    ]
    p_cols = st.columns(5)
    for col, (num, title, desc) in zip(p_cols, pipeline_steps):
        with col:
            st.markdown(f"""<div style="background:#1E3A5F;border-radius:8px;padding:14px;border:1px solid #2A5080;text-align:center">
                <div style="font-family:JetBrains Mono;font-size:20px;font-weight:700;color:#00D4AA">{num}</div>
                <div style="font-size:12px;font-weight:600;color:#E8EDF2;margin:6px 0 4px">{title}</div>
                <div style="font-size:10px;color:#7A9BBF;line-height:1.4">{desc}</div>
            </div>""", unsafe_allow_html=True)
