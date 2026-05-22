import streamlit as st
import pandas as pd
from components.map_view import render_map
from components.table_view import render_table
from components.stats_view import render_stats

st.set_page_config(
    page_title="Визуализатор землетрясений",
    page_icon=":material/earthquake:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { min-width: 300px; }

    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    h1 { margin-bottom: 0.25rem !important; }
    [data-testid="stTabs"] { margin-top: 0.25rem !important; }
    hr { margin: 0.4rem 0 !important; }

    /* ── Tab bar ── */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 6px;
        border-bottom: 2px solid rgba(128,128,128,0.25);
        padding-bottom: 0;
    }

    [data-testid="stTabs"] [data-baseweb="tab"] {
        font-size: 1rem !important;
        font-weight: 600 !important;
        padding: 0.65rem 1.6rem !important;
        border-radius: 8px 8px 0 0 !important;
        border: 1px solid transparent !important;
        border-bottom: none !important;
        background: transparent !important;
        color: var(--text-color) !important;
        opacity: 0.6;
        transition: background 0.15s, color 0.15s;
    }

    [data-testid="stTabs"] [data-baseweb="tab"]:hover {
        background: var(--secondary-background-color) !important;
        opacity: 0.9;
    }

    [data-testid="stTabs"] [aria-selected="true"] {
        background: var(--background-color) !important;
        color: #e63946 !important;
        opacity: 1;
        border-color: rgba(128,128,128,0.25) !important;
        border-bottom-color: var(--background-color) !important;
    }

    [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        display: none !important;
    }

    /* metric cards */
    div[data-testid="metric-container"] {
        background: var(--background-color);
        border: 1px solid rgba(128,128,128,0.2);
        border-radius: 10px;
        padding: 1rem 1.2rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data(file) -> pd.DataFrame:
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    df["Origin"] = pd.to_datetime(df["Origin"], errors="coerce")
    for col in ["Lat", "Lon", "Depth", "Ml", "K"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Origin", "Lat", "Lon", "Ml"])
    return df


# ── Боковая панель ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Визуализатор землетрясений")
    st.markdown("---")

    uploaded_file = st.file_uploader(
        "Загрузите данные о землетрясениях (.xlsx)",
        type=["xlsx"],
        help="Excel файл с колонками: Origin, Lat, Lon, Depth, Ml, K",
    )

    if uploaded_file is None:
        st.info("Загрузите Excel файл для начала работы.", icon=":material/upload_file:")
        st.stop()

    with st.spinner("Загрузка и обработка данных..."):
        df_raw = load_data(uploaded_file)

    st.markdown("#### :material/calendar_month: Диапазон дат")
    min_date = df_raw["Origin"].min().date()
    max_date = df_raw["Origin"].max().date()
    date_range = st.date_input(
        "Выберите диапазон",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        label_visibility="collapsed",
    )

    st.markdown("#### :material/show_chart: Магнитуда (Ml)")
    ml_min, ml_max = float(df_raw["Ml"].min()), float(df_raw["Ml"].max())
    mag_range = st.slider(
        "Диапазон Ml",
        min_value=ml_min,
        max_value=ml_max,
        value=(ml_min, ml_max),
        step=0.1,
        label_visibility="collapsed",
    )

    st.markdown("#### :material/arrow_downward: Глубина (км)")
    dep_min, dep_max = float(df_raw["Depth"].min()), float(df_raw["Depth"].max())
    depth_range = st.slider(
        "Диапазон глубины",
        min_value=dep_min,
        max_value=dep_max,
        value=(dep_min, dep_max),
        step=1.0,
        label_visibility="collapsed",
    )

    st.markdown("#### :material/location_on: Фильтр по местоположению")
    use_location = st.toggle("Включить фильтр по координатам и радиусу", value=False)

    _default_lat = round(float(df_raw["Lat"].mean()), 4)
    _default_lon = round(float(df_raw["Lon"].mean()), 4)
    center_lat = _default_lat
    center_lon = _default_lon
    radius_km = 200

    if use_location:
        col_lat, col_lon = st.columns(2)
        with col_lat:
            _lat_str = st.text_input("Широта", value=str(_default_lat), placeholder="например 42.3")
        with col_lon:
            _lon_str = st.text_input("Долгота", value=str(_default_lon), placeholder="например 75.0")
        _radius_str = st.text_input("Радиус (км)", value="200", placeholder="например 200")

        try:
            center_lat = float(_lat_str)
        except ValueError:
            st.warning("Некорректная широта — используется значение по умолчанию.", icon=":material/warning:")
        try:
            center_lon = float(_lon_str)
        except ValueError:
            st.warning("Некорректная долгота — используется значение по умолчанию.", icon=":material/warning:")
        try:
            radius_km = max(1, int(float(_radius_str)))
        except ValueError:
            st.warning("Некорректный радиус — используется 200 км.", icon=":material/warning:")


# ── Фильтрация ────────────────────────────────────────────────────────────────
df = df_raw.copy()

if len(date_range) == 2:
    start_dt = pd.Timestamp(date_range[0])
    end_dt = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    df = df[(df["Origin"] >= start_dt) & (df["Origin"] <= end_dt)]

df = df[(df["Ml"] >= mag_range[0]) & (df["Ml"] <= mag_range[1])]
df = df[(df["Depth"] >= depth_range[0]) & (df["Depth"] <= depth_range[1])]

if use_location:
    from math import radians, sin, cos, sqrt, atan2
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        return R * 2 * atan2(sqrt(a), sqrt(1 - a))
    df = df[
        df.apply(lambda r: haversine(center_lat, center_lon, r["Lat"], r["Lon"]) <= radius_km, axis=1)
    ]


# ── Основная область ──────────────────────────────────────────────────────────
st.markdown("# :material/earthquake: Панель визуализации землетрясений")
st.divider()

tab_map, tab_table, tab_stats = st.tabs([
    ":material/map: Карта",
    ":material/table_chart: Таблица",
    ":material/bar_chart: Статистика",
])

with tab_map:
    with st.spinner("Загрузка карты..."):
        render_map(df)

with tab_table:
    render_table(df)

with tab_stats:
    render_stats(df)
