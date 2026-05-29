import streamlit as st
import pandas as pd
import numpy as np
from components.map_view import render_map
from components.table_view import render_table
from components.stats_view import render_stats
from components.stations_view import render_stations

st.set_page_config(
    page_title="Визуализатор землетрясений",
    page_icon=":material/earthquake:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { min-width: 300px; }
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebar"] > div > div,
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarContent"] > div { padding-top: 0 !important; margin-top: 0 !important; }
    [data-testid="stSidebarUserContent"] { padding-top: 1rem !important; }

    .block-container { padding-top: 4rem !important; padding-bottom: 1rem !important; }
    hr { margin: 0.4rem 0 !important; }

    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] {
        display: flex !important;
        align-items: center !important;
        justify-content: flex-end !important;
        padding: 0 !important;
        margin: 0 !important;
        min-height: 0 !important;
    }
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button {
        padding: 0 !important;
        min-height: 2.35rem !important;
        height: 2.35rem !important;
        font-size: 1.15rem !important;
        line-height: 1 !important;
        width: 2.35rem !important;
        border-radius: 0.5rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button > div,
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button p {
        padding: 0 !important;
        margin: 0 !important;
        line-height: 1 !important;
    }
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"],
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button[data-testid="baseButton-primaryFormSubmit"] {
        height: auto !important;
        min-height: 2.5rem !important;
        padding: 0.45rem 1rem !important;
        font-size: 1rem !important;
        width: 100% !important;
        border-radius: 0.5rem !important;
        line-height: 1.6 !important;
    }
    [data-testid="stSidebar"] h4 {
        align-items: center !important;
        display: flex !important;
        line-height: 1.2 !important;
        margin: 0 !important;
        min-height: 2.35rem !important;
    }
    [data-testid="stSidebar"] .sidebar-title {
        font-size: 1.35rem;
        font-weight: 800;
        line-height: 1.2;
        margin-bottom: 0.15rem;
    }
    [data-testid="stSidebar"] .sidebar-subtitle {
        color: rgba(128,128,128,0.95);
        font-size: 0.88rem;
        line-height: 1.35;
        margin-bottom: 0.9rem;
    }
    [data-testid="stSidebar"] .sidebar-section {
        color: rgba(128,128,128,0.95);
        font-size: 0.76rem;
        font-weight: 750;
        letter-spacing: 0.06em;
        margin: 1rem 0 0.35rem;
        text-transform: uppercase;
    }
    [data-testid="stSidebar"] .sidebar-status {
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 8px;
        font-size: 0.86rem;
        line-height: 1.35;
        margin: 0.35rem 0 0.6rem;
        padding: 0.55rem 0.65rem;
    }

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

    div[data-testid="metric-container"] {
        background: var(--background-color);
        border: 1px solid rgba(128,128,128,0.2);
        border-radius: 10px;
        padding: 1rem 1.2rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    }
    .map-loading {
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 8px;
        margin-bottom: 0.75rem;
        overflow: hidden;
        padding: 0.75rem 0.9rem;
    }
    .map-loading-label {
        color: rgba(128,128,128,0.95);
        font-size: 0.9rem;
        font-weight: 600;
        margin-bottom: 0.55rem;
    }
    .map-loading-track {
        background: rgba(128,128,128,0.16);
        border-radius: 999px;
        height: 4px;
        overflow: hidden;
    }
    .map-loading-bar {
        animation: mapLoading 1.15s ease-in-out infinite;
        background: #e63946;
        border-radius: 999px;
        height: 100%;
        width: 42%;
    }
    @keyframes mapLoading {
        0% { transform: translateX(-110%); }
        100% { transform: translateX(260%); }
    }
</style>
""", unsafe_allow_html=True)


_REQUIRED_EQ_COLS = ["Origin", "Lat", "Lon", "Ml"]
_REQUIRED_ST_COLS = ["Lat", "Lon"]
_DEFAULT_CIRCLE_LAT = 42.68011
_DEFAULT_CIRCLE_LON = 74.69265


# Uploaded Excel files are cached so sidebar/filter interactions do not re-read
# and re-parse the same workbook on every Streamlit rerun.
@st.cache_data
def load_stations(file):
    try:
        df = pd.read_excel(file)
    except Exception:
        return None, "Не удалось прочитать файл. Убедитесь, что это корректный Excel (.xlsx)."
    df.columns = df.columns.str.strip()
    missing = [c for c in _REQUIRED_ST_COLS if c not in df.columns]
    if missing:
        return None, f"Отсутствуют обязательные колонки: {', '.join(missing)}. Ожидаются: Network, Station_code, Lat, Lon, Elevation."
    for col in ["Lat", "Lon", "Elevation"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["Lat", "Lon"]), None


@st.cache_data
def load_data(file):
    try:
        df = pd.read_excel(file)
    except Exception:
        return None, "Не удалось прочитать файл. Убедитесь, что это корректный Excel (.xlsx)."
    df.columns = df.columns.str.strip()
    missing = [c for c in _REQUIRED_EQ_COLS if c not in df.columns]
    if missing:
        return None, f"Отсутствуют обязательные колонки: {', '.join(missing)}. Ожидаются: Origin, Lat, Lon, Depth, Ml, K."
    df["Origin"] = pd.to_datetime(df["Origin"], errors="coerce")
    for col in ["Lat", "Lon", "Depth", "Ml", "K"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Origin", "Lat", "Lon", "Ml"])
    if df.empty:
        return None, "Файл не содержит строк с корректными данными (Origin, Lat, Lon, Ml)."
    return df, None


# @st.fragment makes this panel re-render independently without triggering a
# full page rerun, so the map is not rebuilt while the user is still typing.
@st.fragment
def _render_filters(min_date, max_date, lat_min, lat_max, lon_min, lon_max):
    # Streamlit has no built-in way to reset a widget's value. Incrementing the
    # key suffix forces Streamlit to treat it as a brand-new widget, which
    # effectively resets it to its default value.
    _dn = st.session_state.get("_date_reset_n", 0)
    _fn = st.session_state.get("_filter_reset_n", 0)

    st.markdown('<div class="sidebar-section">Область выделения</div>', unsafe_allow_html=True)
    _filter_type = st.selectbox(
        "Область выделения",
        ["Нет", "Прямоугольник", "Круг"],
        key="filter_type_select",
        help="Выберите область, которую нужно применить к карте и таблице.",
    )

    with st.form("filters_form"):
        _hc, _hr = st.columns([4, 1], vertical_alignment="center")
        with _hc:
            st.markdown("#### :material/calendar_month: Даты")
        with _hr:
            _reset_date = st.form_submit_button("↺", help="Сбросить даты", key="reset_date")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            _d_start = st.date_input(
                "С",
                value=min_date,
                min_value=min_date,
                max_value=max_date,
                key=f"ds_{_dn}_{min_date}_{max_date}",
                format="YYYY-MM-DD",
            )
        with col_d2:
            _d_end = st.date_input(
                "По",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                key=f"de_{_dn}_{min_date}_{max_date}",
                format="YYYY-MM-DD",
            )

        _bbox_lat_min = _bbox_lon_min = _bbox_lat_max = _bbox_lon_max = None
        _circle_lat = _circle_lon = _circle_radius = None
        _reset_filter = False

        if _filter_type == "Прямоугольник":
            _fc, _fr = st.columns([4, 1], vertical_alignment="center")
            with _fc:
                st.markdown("#### :material/crop_square: Прямоугольник")
            with _fr:
                _reset_filter = st.form_submit_button("↺", help="Сбросить", key="reset_filter")
            col_c, col_d = st.columns(2)
            with col_c:
                _bbox_lat_min = st.number_input("Мин. широта", value=None, step=0.1, format="%.4f", placeholder=f"{lat_min:.4f}", key=f"bbox_lat_min_{_fn}")
                _bbox_lon_min = st.number_input("Мин. долгота", value=None, step=0.1, format="%.4f", placeholder=f"{lon_min:.4f}", key=f"bbox_lon_min_{_fn}")
            with col_d:
                _bbox_lat_max = st.number_input("Макс. широта", value=None, step=0.1, format="%.4f", placeholder=f"{lat_max:.4f}", key=f"bbox_lat_max_{_fn}")
                _bbox_lon_max = st.number_input("Макс. долгота", value=None, step=0.1, format="%.4f", placeholder=f"{lon_max:.4f}", key=f"bbox_lon_max_{_fn}")

        elif _filter_type == "Круг":
            _fc, _fr = st.columns([4, 1], vertical_alignment="center")
            with _fc:
                st.markdown("#### :material/radar: Круг")
            with _fr:
                _reset_filter = st.form_submit_button("↺", help="Сбросить", key="reset_filter")
            col_e, col_f = st.columns(2)
            with col_e:
                _circle_lat = st.number_input("Широта центра", value=_DEFAULT_CIRCLE_LAT, step=0.1, format="%.5f", key=f"circle_lat_{_fn}")
                _circle_lon = st.number_input("Долгота центра", value=_DEFAULT_CIRCLE_LON, step=0.1, format="%.5f", key=f"circle_lon_{_fn}")
            with col_f:
                _circle_radius = st.number_input("Радиус, км", min_value=0.1, value=None, step=10.0, format="%.1f", placeholder="100.0", key=f"circle_radius_{_fn}")

        submitted = st.form_submit_button(
            ":material/play_arrow: Построить",
            width="stretch",
            type="primary",
        )

    if _reset_date:
        st.session_state["_date_reset_n"] = _dn + 1
        st.rerun(scope="fragment")
    if _reset_filter:
        st.session_state["_filter_reset_n"] = _fn + 1
        st.rerun(scope="fragment")

    if submitted:
        if _d_start > _d_end:
            st.error("Дата начала не может быть позже даты окончания.", icon=":material/error:")
            return
        _new_bbox = None
        _new_circle = None
        if _filter_type == "Прямоугольник":
            if all(v is None for v in [_bbox_lat_min, _bbox_lon_min, _bbox_lat_max, _bbox_lon_max]):
                _new_bbox = None
            else:
                _bbox_lat_min = lat_min if _bbox_lat_min is None else _bbox_lat_min
                _bbox_lon_min = lon_min if _bbox_lon_min is None else _bbox_lon_min
                _bbox_lat_max = lat_max if _bbox_lat_max is None else _bbox_lat_max
                _bbox_lon_max = lon_max if _bbox_lon_max is None else _bbox_lon_max
            if _bbox_lat_min is not None and (_bbox_lat_min > _bbox_lat_max or _bbox_lon_min > _bbox_lon_max):
                st.warning("Минимальные координаты не могут быть больше максимальных.", icon=":material/warning:")
                return
            if _bbox_lat_min is not None:
                _new_bbox = dict(
                    lat_min=float(_bbox_lat_min),
                    lon_min=float(_bbox_lon_min),
                    lat_max=float(_bbox_lat_max),
                    lon_max=float(_bbox_lon_max),
                )
        elif _filter_type == "Круг":
            if all(v is None for v in [_circle_lat, _circle_lon, _circle_radius]):
                _new_circle = None
            elif any(v is None for v in [_circle_lat, _circle_lon, _circle_radius]):
                st.warning("Для круга укажите широту, долготу и радиус.", icon=":material/warning:")
                return
            else:
                _new_circle = dict(lat=float(_circle_lat), lon=float(_circle_lon), radius_km=float(_circle_radius))
        st.session_state["bbox"]            = _new_bbox
        st.session_state["circle"]          = _new_circle
        st.session_state["applied_d_start"] = _d_start
        st.session_state["applied_d_end"]   = _d_end
        st.rerun()


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
            <b>{len(df_raw):,}</b> событий<br>
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

    _render_filters(
        min_date=df_raw["Origin"].min().date(),
        max_date=df_raw["Origin"].max().date(),
        lat_min=round(float(df_raw["Lat"].min()), 4),
        lat_max=round(float(df_raw["Lat"].max()), 4),
        lon_min=round(float(df_raw["Lon"].min()), 4),
        lon_max=round(float(df_raw["Lon"].max()), 4),
    )


def _haversine_km_vectorized(center_lat, center_lon, lat, lon):
    # Vectorized distance calculation keeps circle filtering fast for thousands
    # of earthquake rows; avoid df.apply here.
    radius = 6371
    dlat = np.radians(lat - center_lat)
    dlon = np.radians(lon - center_lon)
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(np.radians(center_lat))
        * np.cos(np.radians(lat))
        * np.sin(dlon / 2) ** 2
    )
    return radius * 2 * np.arcsin(np.sqrt(a))


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
    distances = _haversine_km_vectorized(circle["lat"], circle["lon"], df["Lat"], df["Lon"])
    df = df[distances <= circle["radius_km"]]


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

