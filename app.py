import streamlit as st
import pandas as pd
import math
from datetime import date
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
        padding: 0 8px !important;
        min-height: 0 !important;
        height: 1.5rem !important;
        font-size: 0.95rem !important;
        line-height: 1.5rem !important;
        width: auto !important;
        border-radius: 4px !important;
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
        margin-top: 0.4rem !important;
        margin-bottom: 0.1rem !important;
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
</style>
""", unsafe_allow_html=True)


_REQUIRED_EQ_COLS = ["Origin", "Lat", "Lon", "Ml"]
_REQUIRED_ST_COLS = ["Lat", "Lon"]


# Streamlit reruns the entire script on every interaction, so @st.cache_data
# prevents re-reading the Excel file on each rerun — it caches by file identity.
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

    st.markdown("#### :material/select_all: Область выделения")
    _filter_type = st.selectbox(
        "Область выделения",
        ["Нет", "Прямоугольник", "Круг"],
        key="filter_type_select",
        label_visibility="collapsed",
    )

    with st.form("filters_form"):
        _hc, _hr = st.columns([4, 1])
        with _hc:
            st.markdown("#### :material/calendar_month: Диапазон дат")
        with _hr:
            _reset_date = st.form_submit_button("↺", help="Сбросить даты", key="reset_date")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            _d_start_str = st.text_input("С", value=str(min_date), key=f"ds_{_dn}", placeholder="ГГГГ-ММ-ДД", label_visibility="collapsed")
        with col_d2:
            _d_end_str = st.text_input("По", value=str(max_date), key=f"de_{_dn}", placeholder="ГГГГ-ММ-ДД", label_visibility="collapsed")

        _s1 = _s2 = _s3 = _s4 = ""
        _clat = _clon = _ckm = ""
        _reset_filter = False

        if _filter_type == "Прямоугольник":
            _fc, _fr = st.columns([4, 1])
            with _fc:
                st.markdown("#### :material/crop_square: Прямоугольник")
            with _fr:
                _reset_filter = st.form_submit_button("↺", help="Сбросить", key="reset_filter")
            col_c, col_d = st.columns(2)
            with col_c:
                _s1 = st.text_input("Мин. широта", key=f"s1_{_fn}")
                _s2 = st.text_input("Мин. долгота", key=f"s2_{_fn}")
            with col_d:
                _s3 = st.text_input("Макс. широта", key=f"s3_{_fn}")
                _s4 = st.text_input("Макс. долгота", key=f"s4_{_fn}")

        elif _filter_type == "Круг":
            _fc, _fr = st.columns([4, 1])
            with _fc:
                st.markdown("#### :material/radar: Круг")
            with _fr:
                _reset_filter = st.form_submit_button("↺", help="Сбросить", key="reset_filter")
            col_e, col_f = st.columns(2)
            with col_e:
                _clat = st.text_input("Широта центра", key=f"clat_{_fn}")
                _clon = st.text_input("Долгота центра", key=f"clon_{_fn}")
            with col_f:
                _ckm = st.text_input("Радиус (км)", key=f"ckm_{_fn}")

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
        try:
            _d_start = date.fromisoformat(_d_start_str.strip())
        except ValueError:
            st.error(f"Некорректная дата начала: «{_d_start_str}». Формат: ГГГГ-ММ-ДД", icon=":material/error:")
            return
        try:
            _d_end = date.fromisoformat(_d_end_str.strip())
        except ValueError:
            st.error(f"Некорректная дата окончания: «{_d_end_str}». Формат: ГГГГ-ММ-ДД", icon=":material/error:")
            return
        if _d_start > _d_end:
            st.error("Дата начала не может быть позже даты окончания.", icon=":material/error:")
            return
        _new_bbox = None
        _new_circle = None
        if _filter_type == "Прямоугольник" and (_s1 or _s2 or _s3 or _s4):
            try:
                _new_bbox = dict(
                    lat_min=float(_s1) if _s1 else lat_min,
                    lon_min=float(_s2) if _s2 else lon_min,
                    lat_max=float(_s3) if _s3 else lat_max,
                    lon_max=float(_s4) if _s4 else lon_max,
                )
            except ValueError:
                st.warning("Некорректные координаты.", icon=":material/warning:")
        elif _filter_type == "Круг" and (_clat or _clon or _ckm):
            try:
                _new_circle = dict(lat=float(_clat), lon=float(_clon), radius_km=float(_ckm))
            except ValueError:
                st.warning("Некорректные координаты радиуса.", icon=":material/warning:")
        st.session_state["bbox"]            = _new_bbox
        st.session_state["circle"]          = _new_circle
        st.session_state["applied_d_start"] = _d_start
        st.session_state["applied_d_end"]   = _d_end
        st.rerun()


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
        df_raw, err = load_data(uploaded_file)
    if err:
        st.error(err, icon=":material/error:")
        st.stop()

    st.markdown("---")
    stations_file = st.file_uploader(
        "Загрузите данные о станциях (.xlsx)",
        type=["xlsx"],
        help="Excel файл с колонками: Network, Station_code, Lat, Lon, Elevation",
        key="stations_upload",
    )
    df_stations = None
    if stations_file is not None:
        with st.spinner("Загрузка станций..."):
            df_stations, st_err = load_stations(stations_file)
        if st_err:
            st.error(st_err, icon=":material/error:")
            df_stations = None

    _render_filters(
        min_date=df_raw["Origin"].min().date(),
        max_date=df_raw["Origin"].max().date(),
        lat_min=round(float(df_raw["Lat"].min()), 4),
        lat_max=round(float(df_raw["Lat"].max()), 4),
        lon_min=round(float(df_raw["Lon"].min()), 4),
        lon_max=round(float(df_raw["Lon"].max()), 4),
    )


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


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
    df = df[
        df.apply(lambda r: _haversine_km(circle["lat"], circle["lon"], r["Lat"], r["Lon"]) <= circle["radius_km"], axis=1)
    ]


tab_map, tab_table, tab_stats, tab_stations = st.tabs([
    ":material/map: Карта",
    ":material/table_chart: Таблица",
    ":material/bar_chart: Статистика",
    ":material/sensors: Станции",
])

with tab_map:
    with st.spinner("Загрузка карты..."):
        render_map(df, bbox=bbox, circle=circle, df_stations=df_stations)

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

