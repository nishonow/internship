import folium
import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
from typing import Optional

_STYLES = {
    "Светлая (CartoDB)":      ("CartoDB positron",    False),
    "Тёмная (CartoDB)":       ("CartoDB dark_matter", True),
    "Улицы (OpenStreetMap)":  ("OpenStreetMap",       False),
    "Цветная (CartoDB)":      ("CartoDB voyager",     False),
    "Топо (Esri)":            ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}", False),
    "Спутник (Esri)":         ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", False),
}


def _depth_color(depth: float, low: float, high: float) -> str:
    if depth < low:
        return "#e63946"
    elif depth < high:
        return "#f4a261"
    else:
        return "#457b9d"


def _marker_radius(row) -> float:
    k = row.get("K")
    if k is not None and pd.notna(k):
        return max(4, float(k) * 0.9)
    ml = row.get("Ml", 2)
    return max(4, float(ml) * 3.5)


def _legend(dark: bool, low: float, high: float) -> str:
    if dark:
        bg = "rgba(30,30,40,0.92)"
        border = "1px solid rgba(255,255,255,0.1)"
        color = "#e0e0e0"
        title_color = "#ffffff"
    else:
        bg = "rgba(255,255,255,0.92)"
        border = "1px solid #ddd"
        color = "#333"
        title_color = "#111"
    return f"""
    <div style="position:fixed;bottom:30px;right:30px;z-index:1000;
        background:{bg};padding:12px 16px;border-radius:10px;
        box-shadow:0 2px 12px rgba(0,0,0,0.3);font-size:13px;
        line-height:1.9;color:{color};border:{border};">
        <b style="color:{title_color};">Глубина</b><br>
        <span style='color:#e63946'>&#9679;</span> Группа 1 (&lt;{low:.0f} км)<br>
        <span style='color:#f4a261'>&#9679;</span> Группа 2 ({low:.0f}&ndash;{high:.0f} км)<br>
        <span style='color:#457b9d'>&#9679;</span> Группа 3 (&gt;{high:.0f} км)
    </div>
    """


_DEPTH_LOW  = 10
_DEPTH_HIGH = 20


def render_map(df: pd.DataFrame, bbox: Optional[dict] = None) -> None:
    _low, _high = _DEPTH_LOW, _DEPTH_HIGH
    if df.empty:
        st.warning("Нет землетрясений по текущим фильтрам.", icon=":material/filter_alt_off:")
        return

    col_style, _ = st.columns([2, 5])
    with col_style:
        style_name = st.selectbox(
            "Стиль карты",
            list(_STYLES.keys()),
            index=0,
            key="map_style",
        )

    tile_url, is_dark = _STYLES[style_name]
    is_custom_url = tile_url.startswith("http")
    center_lat = df["Lat"].mean()
    center_lon = df["Lon"].mean()

    if is_custom_url:
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=6,
            tiles=None,
            control_scale=True,
        )
        folium.TileLayer(tiles=tile_url, attr="Esri", name=style_name).add_to(m)
    else:
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=6,
            tiles=tile_url,
            control_scale=True,
        )

    sw = [df["Lat"].min(), df["Lon"].min()]
    ne = [df["Lat"].max(), df["Lon"].max()]
    m.fit_bounds([sw, ne])

    m.get_root().html.add_child(folium.Element(_legend(is_dark, _low, _high)))

    if bbox:
        folium.Rectangle(
            bounds=[
                [bbox["lat_min"], bbox["lon_min"]],
                [bbox["lat_max"], bbox["lon_max"]],
            ],
            color="#e63946",
            weight=2,
            fill=True,
            fill_color="#e63946",
            fill_opacity=0.05,
            dash_array="6",
        ).add_to(m)

    for _, row in df.iterrows():
        origin_str = row["Origin"].strftime("%Y-%m-%d %H:%M:%S") if pd.notna(row["Origin"]) else "N/A"
        depth_val = f"{row['Depth']:.1f}" if pd.notna(row.get("Depth")) else "N/A"
        k_val = f"{row['K']:.1f}" if pd.notna(row.get("K")) else "—"
        ml_val = f"{row['Ml']:.1f}" if pd.notna(row.get("Ml")) else "N/A"

        popup_html = (
            f"<div style='font-size:13px;line-height:1.8'>"
            f"<b>Дата:</b> {origin_str}<br>"
            f"<b>Глубина:</b> {depth_val} км<br>"
            f"<b>M:</b> {ml_val}<br>"
            f"<b>K:</b> {k_val}"
            f"</div>"
        )

        folium.CircleMarker(
            location=[row["Lat"], row["Lon"]],
            radius=_marker_radius(row),
            color=_depth_color(row.get("Depth", 0), _low, _high),
            fill=True,
            fill_color=_depth_color(row.get("Depth", 0), _low, _high),
            fill_opacity=0.85,
            weight=1.5,
            popup=folium.Popup(popup_html, max_width=220),
        ).add_to(m)

    st_folium(m, width="100%", height=560, returned_objects=[])
