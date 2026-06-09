import streamlit as st
from components.map_view import draw_bbox_dialog

_DEFAULT_CIRCLE_LAT = 42.68011
_DEFAULT_CIRCLE_LON = 74.69265


# @st.fragment makes this panel re-render independently without triggering a
# full page rerun, so the map is not rebuilt while the user is still typing.
@st.fragment
def render_filters(min_date, max_date, lat_min, lat_max, lon_min, lon_max):
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

    if _filter_type == "Прямоугольник":
        _drawn = st.session_state.get("drawn_bbox")
        if st.button("Нарисовать на карте", use_container_width=True,
                     help="Откройте карту для выделения области прямоугольником."):
            draw_bbox_dialog(lat_min, lat_max, lon_min, lon_max)
        if _drawn:
            st.markdown(
                f"<div style='font-size:0.82rem;color:#888;line-height:1.8;padding:2px 0 4px;'>"
                f"Ш: {_drawn['lat_min']:.4f}° – {_drawn['lat_max']:.4f}°<br>"
                f"Д: {_drawn['lon_min']:.4f}° – {_drawn['lon_max']:.4f}°"
                f"</div>",
                unsafe_allow_html=True,
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
        st.session_state["drawn_bbox"] = None
        st.rerun(scope="fragment")

    if submitted:
        if _d_start > _d_end:
            st.error("Дата начала не может быть позже даты окончания.", icon=":material/error:")
            return
        _new_bbox = None
        _new_circle = None
        if _filter_type == "Прямоугольник":
            if all(v is None for v in [_bbox_lat_min, _bbox_lon_min, _bbox_lat_max, _bbox_lon_max]):
                _new_bbox = st.session_state.get("drawn_bbox")
            else:
                _bbox_lat_min = lat_min if _bbox_lat_min is None else _bbox_lat_min
                _bbox_lon_min = lon_min if _bbox_lon_min is None else _bbox_lon_min
                _bbox_lat_max = lat_max if _bbox_lat_max is None else _bbox_lat_max
                _bbox_lon_max = lon_max if _bbox_lon_max is None else _bbox_lon_max
                if _bbox_lat_min > _bbox_lat_max or _bbox_lon_min > _bbox_lon_max:
                    st.warning("Минимальные координаты не могут быть больше максимальных.", icon=":material/warning:")
                    return
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
