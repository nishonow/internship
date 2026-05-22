import folium
import streamlit as st
from streamlit_folium import st_folium
import pandas as pd

_STYLES = {
    "Светлая (CartoDB)":      ("CartoDB positron",    False),
    "Тёмная (CartoDB)":       ("CartoDB dark_matter", True),
    "Улицы (OpenStreetMap)":  ("OpenStreetMap",       False),
    "Цветная (CartoDB)":       ("CartoDB voyager",     False),
    "Топо (Esri)":            ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}", False),
    "Спутник (Esri)":         ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", False),
}


def _depth_color(depth: float) -> str:
    if depth < 30:
        return "#e63946"
    elif depth < 70:
        return "#f4a261"
    else:
        return "#457b9d"


def _marker_radius(ml: float) -> float:
    return max(4, ml * 3.5)


def _legend(dark: bool) -> str:
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
        <span style='color:#e63946'>&#9679;</span> Мелкое (&lt;30 км)<br>
        <span style='color:#f4a261'>&#9679;</span> Среднее (30&ndash;70 км)<br>
        <span style='color:#457b9d'>&#9679;</span> Глубокое (&gt;70 км)
    </div>
    """


def render_map(df: pd.DataFrame, radius_circle: dict | None = None) -> None:
    if df.empty:
        st.warning("No earthquakes match the current filters.", icon=":material/filter_alt_off:")
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
        folium.TileLayer(
            tiles=tile_url,
            attr="Esri",
            name=style_name,
        ).add_to(m)
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

    m.get_root().html.add_child(folium.Element(_legend(is_dark)))

    if radius_circle:
        folium.Circle(
            location=[radius_circle["lat"], radius_circle["lon"]],
            radius=radius_circle["km"] * 1000,
            color="#e63946",
            weight=2,
            fill=True,
            fill_color="#e63946",
            fill_opacity=0.06,
            dash_array="6",
            tooltip=f"Радиус фильтра: {radius_circle['km']} км",
        ).add_to(m)
        folium.CircleMarker(
            location=[radius_circle["lat"], radius_circle["lon"]],
            radius=6,
            color="#e63946",
            fill=True,
            fill_color="#e63946",
            fill_opacity=1,
            tooltip="Центр фильтра",
        ).add_to(m)

    for _, row in df.iterrows():
        origin_str = row["Origin"].strftime("%Y-%m-%d %H:%M:%S") if pd.notna(row["Origin"]) else "N/A"
        depth_val = f"{row['Depth']:.1f}" if pd.notna(row.get("Depth")) else "N/A"
        k_val = f"{row['K']:.1f}" if pd.notna(row.get("K")) else "N/A"
        ml_val = f"{row['Ml']:.1f}" if pd.notna(row.get("Ml")) else "N/A"

        tooltip_html = (
            f"<b>Дата:</b> {origin_str}<br>"
            f"<b>Ml:</b> {ml_val}<br>"
            f"<b>Глубина:</b> {depth_val} км<br>"
            f"<b>K:</b> {k_val}"
        )

        folium.CircleMarker(
            location=[row["Lat"], row["Lon"]],
            radius=_marker_radius(row["Ml"]),
            color=_depth_color(row.get("Depth", 0)),
            fill=True,
            fill_color=_depth_color(row.get("Depth", 0)),
            fill_opacity=0.85,
            weight=1.5,
            tooltip=folium.Tooltip(tooltip_html, sticky=True),
        ).add_to(m)

    st_folium(m, width="100%", height=560, returned_objects=[])
