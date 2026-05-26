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
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebar"] > div > div,
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarContent"] > div { padding-top: 0 !important; margin-top: 0 !important; }
    [data-testid="stSidebarUserContent"] { padding-top: 1rem !important; }

    .block-container { padding-top: 4rem !important; padding-bottom: 1rem !important; }
    hr { margin: 0.4rem 0 !important; }

    /* reset button columns — shrink to content, vertically center */
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] {
        display: flex !important;
        align-items: center !important;
        justify-content: flex-end !important;
        padding: 0 !important;
        margin: 0 !important;
        min-height: 0 !important;
    }
    /* all form submit buttons compact */
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
    /* restore primary Построить button */
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
    /* reduce heading margins inside sidebar form */
    [data-testid="stSidebar"] h4 {
        margin-top: 0.4rem !important;
        margin-bottom: 0.1rem !important;
    }

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

    min_date = df_raw["Origin"].min().date()
    max_date = df_raw["Origin"].max().date()
    _lat_min = round(float(df_raw["Lat"].min()), 4)
    _lat_max = round(float(df_raw["Lat"].max()), 4)
    _lon_min = round(float(df_raw["Lon"].min()), 4)
    _lon_max = round(float(df_raw["Lon"].max()), 4)

    _dn = st.session_state.get("_date_reset_n", 0)
    _ln = st.session_state.get("_loc_reset_n", 0)

    with st.form("filters_form"):
        _hc, _hr = st.columns([4, 1])
        with _hc:
            st.markdown("#### :material/calendar_month: Диапазон дат")
        with _hr:
            _reset_date = st.form_submit_button("↺", help="Сбросить даты")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            _d_start = st.date_input("С", value=min_date, key=f"ds_{_dn}", format="YYYY-MM-DD", label_visibility="collapsed")
        with col_d2:
            _d_end = st.date_input("По", value=max_date, key=f"de_{_dn}", format="YYYY-MM-DD", label_visibility="collapsed")

        _lc, _lr = st.columns([4, 1])
        with _lc:
            st.markdown("#### :material/location_on: Фильтр по области")
        with _lr:
            _reset_loc = st.form_submit_button("⟳", help="Сбросить область")

        col_c, col_d = st.columns(2)
        with col_c:
            _s1 = st.text_input("Мин. широта", key=f"s1_{_ln}")
            _s2 = st.text_input("Мин. долгота", key=f"s2_{_ln}")
        with col_d:
            _s3 = st.text_input("Макс. широта", key=f"s3_{_ln}")
            _s4 = st.text_input("Макс. долгота", key=f"s4_{_ln}")

        submitted = st.form_submit_button(
            ":material/play_arrow: Построить",
            use_container_width=True,
            type="primary",
        )

    if _reset_date:
        st.session_state["_date_reset_n"] = _dn + 1
        st.rerun()
    if _reset_loc:
        st.session_state["_loc_reset_n"] = _ln + 1
        st.rerun()

    # ── Только при нажатии Построить сохраняем все фильтры ────────────────────
    if submitted:
        _new_bbox = None
        if _s1 or _s2 or _s3 or _s4:
            try:
                _new_bbox = dict(
                    lat_min=float(_s1) if _s1 else _lat_min,
                    lon_min=float(_s2) if _s2 else _lon_min,
                    lat_max=float(_s3) if _s3 else _lat_max,
                    lon_max=float(_s4) if _s4 else _lon_max,
                )
            except ValueError:
                st.sidebar.warning("Некорректные координаты.", icon=":material/warning:")
        st.session_state["bbox"]            = _new_bbox
        st.session_state["applied_d_start"] = _d_start
        st.session_state["applied_d_end"]   = _d_end


# ── Фильтрация — только применённые значения из session_state ────────────────
df = df_raw.copy()
bbox = st.session_state.get("bbox")

_ad_start = st.session_state.get("applied_d_start", str(min_date))
_ad_end   = st.session_state.get("applied_d_end",   str(max_date))

try:
    start_dt = pd.Timestamp(_ad_start)
    end_dt   = pd.Timestamp(_ad_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    df = df[(df["Origin"] >= start_dt) & (df["Origin"] <= end_dt)]
except Exception:
    pass

if bbox:
    df = df[
        (df["Lat"] >= bbox["lat_min"]) & (df["Lat"] <= bbox["lat_max"]) &
        (df["Lon"] >= bbox["lon_min"]) & (df["Lon"] <= bbox["lon_max"])
    ]


# ── Основная область ──────────────────────────────────────────────────────────
tab_map, tab_table, tab_stats = st.tabs([
    ":material/map: Карта",
    ":material/table_chart: Таблица",
    ":material/bar_chart: Статистика",
])

with tab_map:
    with st.spinner("Загрузка карты..."):
        render_map(df, bbox=bbox)

with tab_table:
    render_table(df)

with tab_stats:
    render_stats(df)
