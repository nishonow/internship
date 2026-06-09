import folium
import pandas as pd
from html import escape

_STATION_COLORS = {
    "KN":  "#8e44ad",
    "MAG": "#27ae60",
    "KR":  "#2471a3",
    "KC":  "#148f77",
    "KZ":  "#d35400",
    "QZ":  "#b7950b",
    "TJ":  "#922b21",
    "G":   "#566573",
    "CK":  "#c0392b",
    "GE":  "#1abc9c",
}

_NETWORK_NAMES = {
    "KN":  "KNET (НС РАН)",
    "MAG": "Геомагнитные станции (НС РАН)",
    "KR":  "Кыргызстан",
    "KC":  "ЦАИИЗ",
    "KZ":  "Казахстан",
    "QZ":  "Казахстан",
    "TJ":  "Таджикистан",
    "G":   "Международный",
    "CK":  "ЦАИИЗ",
    "GE":  "Кабул",
}

_STYLES = {
    "Светлая (CartoDB)":      ("CartoDB positron",    False),
    "Тёмная (CartoDB)":       ("CartoDB dark_matter", True),
    "Улицы (OpenStreetMap)":  ("OpenStreetMap",       False),
    "Цветная (CartoDB)":      ("CartoDB voyager",     False),
    "Топо (Esri)":            ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}", False),
    "Спутник (Esri)":         ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", False),
}

_SVG_SEISMIC = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" '
    'fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="3,12 6,12 8,4 11,20 13,8 15,16 17,12 21,12"/>'
    '</svg>'
)

_SVG_HOME = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" '
    'fill="white">'
    '<path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>'
    '</svg>'
)

_SVG_STAR = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" '
    'fill="white">'
    '<polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/>'
    '</svg>'
)

_NS_RAN = {"name": "НС РАН", "lat": 42.68011, "lon": 74.69265, "color": "#e8a020"}

_EQ_CLUSTER_CALLBACK = """
function (row) {
    var size = Math.max(8, Math.min(26, row[2] * 1.6));
    var html = '<div style="width:' + size + 'px;height:' + size + 'px;' +
        'border-radius:50%;background:' + row[3] + ';border:1px solid rgba(255,255,255,0.75);' +
        'box-shadow:0 1px 3px rgba(0,0,0,0.28);opacity:0.72;"></div>';
    var marker = L.marker(new L.LatLng(row[0], row[1]), {
        icon: L.divIcon({
            className: 'eq-fast-marker',
            html: html,
            iconSize: [size, size],
            iconAnchor: [size / 2, size / 2]
        })
    });
    marker.bindPopup(row[4], {maxWidth: 220});
    return marker;
}
"""

# Depth thresholds in km that define the three color groups.
# Change these two values to adjust grouping across the map, legend, and table.
_DEPTH_LOW  = 10
_DEPTH_HIGH = 20


def _depth_color(depth: float, low: float, high: float) -> str:
    if depth < low:
        return "#e63946"
    elif depth < high:
        return "#f4a261"
    else:
        return "#457b9d"


def _marker_radius(row) -> float:
    # K (energy class) is preferred over Ml when available because it is a
    # more precise local measure. Falls back to Ml if K is absent or NaN.
    k = row.get("K")
    if k is not None and pd.notna(k):
        return max(5, float(k) * 1.1)
    ml = row.get("Ml", 2)
    return max(5, float(ml) * 4.5)


def _earthquake_cluster_data(df: pd.DataFrame, low: float, high: float) -> list:
    data = []
    for _, row in df.iterrows():
        origin_str = row["Origin"].strftime("%Y-%m-%d %H:%M:%S") if pd.notna(row["Origin"]) else "N/A"
        depth_val = f"{row['Depth']:.1f}" if pd.notna(row.get("Depth")) else "N/A"
        k_val = f"{row['K']:.1f}" if pd.notna(row.get("K")) else "—"
        ml_val = f"{row['Ml']:.1f}" if pd.notna(row.get("Ml")) else "N/A"
        popup_html = (
            f"<div style='font-size:13px;line-height:1.8'>"
            f"<b>Дата:</b> {escape(origin_str)}<br>"
            f"<b>Широта:</b> {row['Lat']:.4f}<br>"
            f"<b>Долгота:</b> {row['Lon']:.4f}<br>"
            f"<b>Глубина:</b> {escape(depth_val)} км<br>"
            f"<b>M:</b> {escape(ml_val)}<br>"
            f"<b>K:</b> {escape(k_val)}"
            f"</div>"
        )
        data.append([
            float(row["Lat"]),
            float(row["Lon"]),
            _marker_radius(row),
            _depth_color(row.get("Depth", 0), low, high),
            popup_html,
        ])
    return data


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


def _station_icon(network: str) -> folium.DivIcon:
    color = _STATION_COLORS.get(network, "#888888")
    svg = _SVG_HOME if network == "MAG" else _SVG_SEISMIC
    html = (
        f'<div style="position:relative;text-align:center;width:32px;height:44px;">'
        f'<div style="position:absolute;top:0;left:2px;width:28px;height:28px;'
        f'background:{color};border-radius:50%;border:2px solid white;'
        f'box-shadow:0 2px 6px rgba(0,0,0,0.5);display:flex;'
        f'align-items:center;justify-content:center;">'
        f'{svg}</div>'
        f'<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);'
        f'width:0;height:0;border-left:7px solid transparent;'
        f'border-right:7px solid transparent;border-top:16px solid {color};">'
        f'</div></div>'
    )
    return folium.DivIcon(html=html, icon_size=(32, 44), icon_anchor=(16, 44))
