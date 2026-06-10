import folium
import math
import streamlit as st
from streamlit_folium import st_folium
from folium.plugins import Draw, FastMarkerCluster
import pandas as pd
from typing import Optional, Dict, Any

from components.map_config import (
    _STYLES, _SVG_STAR, _NS_RAN,
    _EQ_CLUSTER_CALLBACK, _DEPTH_LOW, _DEPTH_HIGH,
    _NETWORK_NAMES, _STATION_COLORS,
    _earthquake_cluster_data,
    _legend, _station_icon,
)


def _extract_drawn_bbox(map_data: Optional[dict]) -> Optional[dict]:
    if not map_data:
        return None
    drawing = map_data.get("last_active_drawing")
    if not drawing or drawing.get("geometry", {}).get("type") != "Polygon":
        return None
    coords = drawing["geometry"]["coordinates"][0]
    return dict(
        lat_min=min(c[1] for c in coords),
        lat_max=max(c[1] for c in coords),
        lon_min=min(c[0] for c in coords),
        lon_max=max(c[0] for c in coords),
    )


@st.dialog("Выбор области на карте", width="large")
def draw_bbox_dialog(lat_min: float, lat_max: float, lon_min: float, lon_max: float) -> None:
    center_lat = (lat_min + lat_max) / 2
    center_lon = (lon_min + lon_max) / 2
    span = max(lat_max - lat_min, lon_max - lon_min)
    zoom = max(2, min(10, int(math.log2(360 / span)) - 1)) if span > 0 else 6

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom,
        tiles="CartoDB positron",
        control_scale=True,
    )
    m.get_root().html.add_child(folium.Element(
        "<style>.leaflet-control-attribution{display:none!important}</style>"
    ))
    m.get_root().html.add_child(folium.Element("""
<script>
(function() {
  var dl = window.L && L.drawLocal;
  if (!dl) return;
  dl.draw.toolbar.actions.title = 'Отменить рисование';
  dl.draw.toolbar.actions.text  = 'Отменить';
  dl.draw.toolbar.buttons.rectangle = 'Нарисовать прямоугольник';
  dl.draw.handlers.rectangle.tooltip.start    = 'Нажмите и перетащите для выделения области.';
  dl.draw.handlers.simpleshape.tooltip.end    = 'Отпустите для завершения.';
})();
</script>
"""))
    Draw(
        draw_options={
            "rectangle": {"shapeOptions": {"color": "#e63946", "weight": 2, "fillOpacity": 0.05}},
            "polygon": False, "circle": False, "marker": False,
            "circlemarker": False, "polyline": False,
        },
        edit_options={"edit": False, "remove": False},
    ).add_to(m)

    map_data = st_folium(
        m, width="100%", height=430,
        returned_objects=["last_active_drawing"],
        key="draw_dlg_map",
    )
    bbox = _extract_drawn_bbox(map_data)

    if bbox:
        st.markdown(
            f"<div style='font-size:0.82rem;color:#888;line-height:1.8;padding:2px 0;'>"
            f"Ш: {bbox['lat_min']:.4f}° – {bbox['lat_max']:.4f}° &nbsp;·&nbsp; "
            f"Д: {bbox['lon_min']:.4f}° – {bbox['lon_max']:.4f}°</div>",
            unsafe_allow_html=True,
        )
    else:
        st.caption("Нажмите кнопку □ на карте, затем выделите прямоугольную область.")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Применить", type="primary", use_container_width=True, disabled=bbox is None):
            st.session_state["drawn_bbox"] = bbox
            st.session_state["bbox"] = bbox
            st.rerun()
    with col_b:
        if st.button("Сбросить", use_container_width=True):
            st.session_state["drawn_bbox"] = None
            st.session_state["bbox"] = None
            st.rerun()


# The dialog uses separate "dlg_" prefixed keys because Streamlit dialogs run
# in an isolated scope. The Apply button copies the dialog state into the main
# session_state keys that render_map reads, then reruns the full page.
@st.dialog("Сети")
def _seti_dialog(all_nets: list, has_stations: bool) -> None:
    if all_nets:
        for net in all_nets:
            name = _NETWORK_NAMES.get(net, "")
            label = f"{net} — {name}" if name else net
            st.checkbox(label, value=st.session_state.get(f"map_net_{net}", False), key=f"dlg_net_{net}")
        st.divider()

    st.checkbox("НС РАН", value=st.session_state.get("map_ns_ran", False), key="dlg_ns_ran")
    st.checkbox("Землетрясения", value=st.session_state.get("show_earthquakes", True), key="dlg_earthquakes")

    if st.button("Применить", type="primary", use_container_width=True):
        if has_stations:
            for net in all_nets:
                st.session_state[f"map_net_{net}"] = st.session_state[f"dlg_net_{net}"]
        st.session_state["map_ns_ran"] = st.session_state["dlg_ns_ran"]
        st.session_state["show_earthquakes"] = st.session_state["dlg_earthquakes"]
        st.rerun()


@st.fragment
def _layer_controls(all_nets: list, has_stations: bool) -> None:
    if st.button("Сети"):
        _seti_dialog(all_nets, has_stations)


def render_map(
    df: pd.DataFrame,
    bbox: Optional[dict] = None,
    circle: Optional[Dict[str, Any]] = None,
    df_stations: Optional[pd.DataFrame] = None,
) -> None:
    _low, _high = _DEPTH_LOW, _DEPTH_HIGH
    if df.empty:
        st.warning("Нет землетрясений по текущим фильтрам.", icon=":material/filter_alt_off:")
        return

    has_stations = df_stations is not None and not df_stations.empty

    # Initialize layer visibility flags only on first load; preserve user choices on reruns.
    if "show_earthquakes" not in st.session_state:
        st.session_state["show_earthquakes"] = True
    if "map_ns_ran" not in st.session_state:
        st.session_state["map_ns_ran"] = False

    if has_stations:
        all_nets = sorted(df_stations["Network"].dropna().unique().tolist())
        for net in all_nets:
            # New networks found in a freshly uploaded file default to hidden.
            if f"map_net_{net}" not in st.session_state:
                st.session_state[f"map_net_{net}"] = False
    else:
        all_nets = []

    col_style, col_btn = st.columns([2, 4], vertical_alignment="bottom")
    with col_style:
        style_names = list(_STYLES.keys())
        style_name = st.selectbox("Стиль карты", style_names, index=0, key="map_style")
    with col_btn:
        _layer_controls(all_nets, has_stations)

    show_earthquakes = st.session_state.get("show_earthquakes", True)
    tile_url, is_dark = _STYLES[style_name]
    is_custom_url = tile_url.startswith("http")

    lat_min, lat_max = df["Lat"].min(), df["Lat"].max()
    lon_min, lon_max = df["Lon"].min(), df["Lon"].max()
    center_lat = (lat_min + lat_max) / 2
    center_lon = (lon_min + lon_max) / 2
    span = max(lat_max - lat_min, lon_max - lon_min)
    zoom = max(2, min(12, int(math.log2(360 / span)) - 1)) if span > 0 else 8

    # Esri tile URLs must be added via TileLayer because Folium only recognises
    # named providers (e.g. "OpenStreetMap") in the tiles= parameter directly.
    if is_custom_url:
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles=None, control_scale=True)
        folium.TileLayer(tiles=tile_url, attr="Esri", name=style_name).add_to(m)
    else:
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles=tile_url, control_scale=True)

    m.get_root().html.add_child(folium.Element(_legend(is_dark, _low, _high)))
    m.get_root().html.add_child(folium.Element(
        "<style>.leaflet-control-attribution{display:none!important}"
        ".eq-fast-marker{background:transparent!important;border:none!important;}</style>"
    ))

    if circle:
        folium.Circle(
            location=[circle["lat"], circle["lon"]],
            radius=circle["radius_km"] * 1000,
            color="#e63946", weight=2, fill=True,
            fill_color="#e63946", fill_opacity=0.05, dash_array="6",
        ).add_to(m)

    if bbox:
        folium.Rectangle(
            bounds=[[bbox["lat_min"], bbox["lon_min"]], [bbox["lat_max"], bbox["lon_max"]]],
            color="#e63946", weight=2, fill=True,
            fill_color="#e63946", fill_opacity=0.05, dash_array="6",
        ).add_to(m)

    if show_earthquakes:
        FastMarkerCluster(
            data=_earthquake_cluster_data(df, _low, _high),
            callback=_EQ_CLUSTER_CALLBACK,
            options={"spiderfyOnMaxZoom": True, "disableClusteringAtZoom": 18, "minimumClusterSize": 3},
        ).add_to(m)

    if has_stations:
        from html import escape
        for _, srow in df_stations.iterrows():
            if pd.isna(srow.get("Lat")) or pd.isna(srow.get("Lon")):
                continue
            net  = str(srow.get("Network", ""))
            code = str(srow.get("Station_code", ""))
            if not st.session_state.get(f"map_net_{net}", False):
                continue
            elev = srow.get("Elevation")
            elev_str = f"{float(elev):.0f} м" if pd.notna(elev) else "—"
            info = srow.get("Info", "")
            info_str = str(info).strip() if pd.notna(info) and str(info).strip() else ""
            popup_html = (
                f"<div style='font-size:13px;line-height:1.8'>"
                f"<b>{escape(code)}</b><br>"
                f"<b>Сеть:</b> {escape(net)}<br>"
                f"<b>Широта:</b> {float(srow['Lat']):.4f}<br>"
                f"<b>Долгота:</b> {float(srow['Lon']):.4f}<br>"
                f"<b>Высота:</b> {elev_str}"
                + (f"<br><b>Info:</b> {escape(info_str)}" if info_str else "")
                + f"</div>"
            )
            folium.Marker(
                location=[float(srow["Lat"]), float(srow["Lon"])],
                icon=_station_icon(net),
                popup=folium.Popup(popup_html, max_width=200),
            ).add_to(m)

    if st.session_state.get("map_ns_ran", False):
        color = _NS_RAN["color"]
        html = (
            f'<div style="position:relative;text-align:center;width:32px;height:44px;">'
            f'<div style="position:absolute;top:0;left:2px;width:28px;height:28px;'
            f'background:{color};border-radius:50%;border:2px solid white;'
            f'box-shadow:0 2px 6px rgba(0,0,0,0.5);display:flex;'
            f'align-items:center;justify-content:center;">'
            f'{_SVG_STAR}</div>'
            f'<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);'
            f'width:0;height:0;border-left:7px solid transparent;'
            f'border-right:7px solid transparent;border-top:16px solid {color};">'
            f'</div></div>'
        )
        popup_html = (
            f"<div style='font-size:13px;line-height:1.8'>"
            f"<b>НС РАН</b><br>"
            f"<b>Широта:</b> {_NS_RAN['lat']}<br>"
            f"<b>Долгота:</b> {_NS_RAN['lon']}"
            f"</div>"
        )
        folium.Marker(
            location=[_NS_RAN["lat"], _NS_RAN["lon"]],
            icon=folium.DivIcon(html=html, icon_size=(32, 44), icon_anchor=(16, 44)),
            popup=folium.Popup(popup_html, max_width=200),
        ).add_to(m)

    # A stable key prevents st_folium from re-rendering the map on every rerun.
    # The key encodes all visible state so the map does refresh when data changes.
    style_idx = style_names.index(style_name)
    time_start = int(df["Origin"].min().value) if "Origin" in df.columns else 0
    time_end = int(df["Origin"].max().value) if "Origin" in df.columns else 0
    map_key = f"map_{len(df)}_{center_lat:.4f}_{center_lon:.4f}_{zoom}_s{style_idx}_t{time_start}_{time_end}"
    if bbox:
        map_key += f"_b{bbox['lat_min']}{bbox['lon_min']}{bbox['lat_max']}{bbox['lon_max']}"
    if circle:
        map_key += f"_c{circle['lat']}{circle['lon']}{circle['radius_km']}"
    map_key += f"_eq{int(show_earthquakes)}_ns{int(st.session_state.get('map_ns_ran', False))}"
    if has_stations:
        active_nets_str = "".join(n for n in all_nets if st.session_state.get(f"map_net_{n}", False))
        map_key += f"_st{active_nets_str}"

    st_folium(m, width="100%", height=560, returned_objects=[], key=map_key)

    if not (bbox or circle):
        return

    eq_count = len(df)

    if circle:
        filter_desc = f"Круг &nbsp;·&nbsp; центр {circle['lat']:.4f}°N, {circle['lon']:.4f}°E &nbsp;·&nbsp; радиус {circle['radius_km']:.0f} км"
        filter_icon = "◎"
    else:
        filter_desc = (
            f"Прямоугольник &nbsp;·&nbsp; {bbox['lat_min']:.4f}°–{bbox['lat_max']:.4f}°N, "
            f"{bbox['lon_min']:.4f}°–{bbox['lon_max']:.4f}°E"
        )
        filter_icon = "▭"

    if eq_count > 0:
        ml_min  = df["Ml"].min()
        ml_max  = df["Ml"].max()
        ml_mean = df["Ml"].mean()
        d_min   = df["Depth"].min() if df["Depth"].notna().any() else None
        d_max   = df["Depth"].max() if df["Depth"].notna().any() else None
        t_min   = df["Origin"].min().strftime("%d.%m.%Y")
        t_max   = df["Origin"].max().strftime("%d.%m.%Y")
        depth_str = f"{d_min:.0f} – {d_max:.0f} км" if d_min is not None else "—"

        stats_html = f"""
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px;">
          <div style="background:var(--background-color);border:1px solid rgba(128,128,128,0.18);
               border-radius:10px;padding:14px 16px;text-align:center;">
            <div style="font-size:10px;font-weight:600;color:#999;text-transform:uppercase;
                 letter-spacing:.6px;margin-bottom:8px;">Землетрясений</div>
            <div style="font-size:28px;font-weight:800;color:#e63946;line-height:1;">{eq_count}</div>
          </div>
          <div style="background:var(--background-color);border:1px solid rgba(128,128,128,0.18);
               border-radius:10px;padding:14px 16px;text-align:center;">
            <div style="font-size:10px;font-weight:600;color:#999;text-transform:uppercase;
                 letter-spacing:.6px;margin-bottom:8px;">Магнитуда (Ml)</div>
            <div style="font-size:20px;font-weight:700;line-height:1;">{ml_min:.1f} – {ml_max:.1f}</div>
            <div style="font-size:12px;color:#999;margin-top:5px;">среднее {ml_mean:.1f}</div>
          </div>
          <div style="background:var(--background-color);border:1px solid rgba(128,128,128,0.18);
               border-radius:10px;padding:14px 16px;text-align:center;">
            <div style="font-size:10px;font-weight:600;color:#999;text-transform:uppercase;
                 letter-spacing:.6px;margin-bottom:8px;">Глубина</div>
            <div style="font-size:20px;font-weight:700;line-height:1;">{depth_str}</div>
          </div>
          <div style="background:var(--background-color);border:1px solid rgba(128,128,128,0.18);
               border-radius:10px;padding:14px 16px;text-align:center;">
            <div style="font-size:10px;font-weight:600;color:#999;text-transform:uppercase;
                 letter-spacing:.6px;margin-bottom:8px;">Период</div>
            <div style="font-size:15px;font-weight:700;line-height:1.3;">{t_min}<br>
              <span style="color:#999;font-weight:400;font-size:12px;">→</span> {t_max}</div>
          </div>
        </div>"""
    else:
        stats_html = """
        <div style="background:var(--background-color);border:1px solid rgba(128,128,128,0.18);
             border-radius:10px;padding:14px 18px;color:#999;font-size:14px;margin-bottom:12px;">
          В выбранной области нет землетрясений.
        </div>"""

    def _station_in_circle(row, c):
        dlat = math.radians(row["Lat"] - c["lat"])
        dlon = math.radians(row["Lon"] - c["lon"])
        a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(c["lat"]))
             * math.cos(math.radians(row["Lat"])) * math.sin(dlon / 2) ** 2)
        return 6371 * 2 * math.asin(math.sqrt(a)) <= c["radius_km"]

    stations_html = ""
    if has_stations:
        active_nets = [n for n in all_nets if st.session_state.get(f"map_net_{n}", False)]
        rows_html = ""
        for net in active_nets:
            net_df = df_stations[df_stations["Network"] == net]
            if circle:
                net_df = net_df[net_df.apply(_station_in_circle, axis=1, c=circle)]
            elif bbox:
                net_df = net_df[
                    (net_df["Lat"] >= bbox["lat_min"]) & (net_df["Lat"] <= bbox["lat_max"]) &
                    (net_df["Lon"] >= bbox["lon_min"]) & (net_df["Lon"] <= bbox["lon_max"])
                ]
            if net_df.empty:
                continue
            color     = _STATION_COLORS.get(net, "#888")
            name      = _NETWORK_NAMES.get(net, "")
            net_label = f"{net} — {name}" if name else net
            pills     = "".join(
                f"<span style='display:inline-block;background:rgba(128,128,128,0.1);"
                f"border-radius:5px;padding:2px 8px;margin:2px 4px 2px 0;"
                f"font-size:12px;font-weight:500;'>{c}</span>"
                for c in net_df["Station_code"].dropna().astype(str)
            )
            rows_html += f"""
            <div style="display:flex;align-items:flex-start;gap:12px;padding:10px 0;
                 border-top:1px solid rgba(128,128,128,0.12);">
              <div style="width:11px;height:11px;border-radius:50%;background:{color};
                   margin-top:4px;flex-shrink:0;box-shadow:0 0 0 2px {color}33;"></div>
              <div style="flex:1;">
                <span style="font-size:13px;font-weight:600;">{net_label}</span>
                <span style="font-size:12px;color:#999;margin-left:8px;">{len(net_df)} ст.</span>
                <div style="margin-top:5px;">{pills}</div>
              </div>
            </div>"""

        if rows_html:
            stations_html = f"""
            <div style="background:var(--background-color);border:1px solid rgba(128,128,128,0.18);
                 border-radius:10px;padding:14px 18px;margin-bottom:12px;">
              <div style="font-size:10px;font-weight:600;color:#999;text-transform:uppercase;
                   letter-spacing:.6px;margin-bottom:4px;">Станции в области</div>
              {rows_html}
            </div>"""

    st.html(
        f"""<div style="margin-top:20px;">
          <div style="font-size:11px;color:#aaa;margin-bottom:12px;letter-spacing:.3px;">
            {filter_icon}&nbsp; {filter_desc}
          </div>
          {stats_html}
          {stations_html}
        </div>""",
    )
