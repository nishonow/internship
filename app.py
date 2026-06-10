import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

from components.map_view import render_map
from components.filters import render_filters
from components.table_view import render_table
from components.stats_view import render_stats
from components.stations_view import render_stations
from utils.loaders import load_data, load_stations

st.set_page_config(
    page_title="Визуализатор землетрясений",
    page_icon=":material/earthquake:",
    layout="wide",
    initial_sidebar_state="expanded",
)

_css = (Path(__file__).parent / "assets" / "styles.css").read_text(encoding="utf-8")
st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)


def _haversine_km(center_lat, center_lon, lat, lon):
    r = 6371
    dlat = np.radians(lat - center_lat)
    dlon = np.radians(lon - center_lon)
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(np.radians(center_lat)) * np.cos(np.radians(lat)) * np.sin(dlon / 2) ** 2
    )
    return r * 2 * np.arcsin(np.sqrt(a))


with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-title">Визуализатор землетрясений</div>
        <div class="sidebar-subtitle">Загрузите каталог событий, настройте период и выберите область анализа.</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-section">Данные</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Каталог землетрясений (.xlsx)",
        type=["xlsx"],
        help="Excel файл с колонками: Origin, Lat, Lon, Depth, Ml, K",
    )

    if uploaded_file is None:
        st.info("Загрузите Excel файл для начала работы.", icon=":material/upload_file:")
        st.stop()

    with st.spinner("Загрузка и обработка данных..."):
        df_raw, err = load_data(uploaded_file)
    if err:
        st.error(err, icon=":material/error:")
        st.stop()

    st.markdown(
        f"""
        <div class="sidebar-status">
            Количество событий: <b>{len(df_raw):,}</b><br>
            {df_raw["Origin"].min().date()} — {df_raw["Origin"].max().date()}
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_stations = None
    with st.expander("Станции наблюдения", expanded=False):
        stations_file = st.file_uploader(
            "Файл станций (.xlsx)",
            type=["xlsx"],
            help="Excel файл с колонками: Network, Station_code, Lat, Lon, Elevation",
            key="stations_upload",
        )
        if stations_file is not None:
            with st.spinner("Загрузка станций..."):
                df_stations, st_err = load_stations(stations_file)
            if st_err:
                st.error(st_err, icon=":material/error:")
                df_stations = None
            elif df_stations is not None:
                st.success(f"Загружено станций: {len(df_stations):,}", icon=":material/check_circle:")
        else:
            st.caption("Необязательно. Добавляет станции на карту и во вкладку «Станции».")

    render_filters(
        min_date=df_raw["Origin"].min().date(),
        max_date=df_raw["Origin"].max().date(),
        lat_min=round(float(df_raw["Lat"].min()), 4),
        lat_max=round(float(df_raw["Lat"].max()), 4),
        lon_min=round(float(df_raw["Lon"].min()), 4),
        lon_max=round(float(df_raw["Lon"].max()), 4),
    )

# — Apply filters ——————————————————————————————————————————————————————————————

df = df_raw.copy()
bbox   = st.session_state.get("bbox")
circle = st.session_state.get("circle")

_ad_start = st.session_state.get("applied_d_start", str(df_raw["Origin"].min().date()))
_ad_end   = st.session_state.get("applied_d_end",   str(df_raw["Origin"].max().date()))

try:
    start_dt = pd.Timestamp(_ad_start)
    # Add almost a full day so the end date is inclusive (covers 23:59:59).
    end_dt   = pd.Timestamp(_ad_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    df = df[(df["Origin"] >= start_dt) & (df["Origin"] <= end_dt)]
except Exception:
    pass

if bbox:
    df = df[
        (df["Lat"] >= bbox["lat_min"]) & (df["Lat"] <= bbox["lat_max"]) &
        (df["Lon"] >= bbox["lon_min"]) & (df["Lon"] <= bbox["lon_max"])
    ]

if circle:
    df = df[_haversine_km(circle["lat"], circle["lon"], df["Lat"], df["Lon"]) <= circle["radius_km"]]

# — Tabs ———————————————————————————————————————————————————————————————————————

tab_map, tab_table, tab_stats, tab_stations = st.tabs([
    ":material/map: Карта",
    ":material/table_chart: Таблица",
    ":material/bar_chart: Статистика",
    ":material/sensors: Станции",
])

with tab_map:
    map_loader = st.empty()
    map_loader.markdown(
        """
        <div class="map-loading">
            <div class="map-loading-label">Подготовка карты...</div>
            <div class="map-loading-track"><div class="map-loading-bar"></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_map(df, bbox=bbox, circle=circle, df_stations=df_stations)
    map_loader.empty()

with tab_table:
    render_table(df)

with tab_stats:
    # Intentionally passes the full unfiltered dataset so the Stats tab always
    # shows the overall picture regardless of the active spatial/date filters.
    render_stats(df_raw)

with tab_stations:
    if df_stations is not None:
        render_stations(df_stations)
    else:
        st.info(
            "Загрузите файл данных о станциях в боковой панели для просмотра.",
            icon=":material/upload_file:",
        )
