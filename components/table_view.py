import streamlit as st
import pandas as pd


def render_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.warning("Нет землетрясений по текущим фильтрам.", icon=":material/filter_alt_off:")
        return

    st.markdown("### :material/table_chart: Данные о землетрясениях")

    col_search, col_count = st.columns([3, 1])
    with col_search:
        query = st.text_input(
            "Поиск",
            placeholder="Введите дату, магнитуду, глубину...",
            label_visibility="collapsed",
        )
    with col_count:
        st.markdown("<div style='padding-top:8px'></div>", unsafe_allow_html=True)

    display_df = df.copy()
    if "Origin" in display_df.columns:
        display_df["Origin"] = display_df["Origin"].dt.strftime("%Y-%m-%d %H:%M:%S")

    if query.strip():
        mask = display_df.apply(
            lambda col: col.astype(str).str.contains(query.strip(), case=False, na=False)
        ).any(axis=1)
        display_df = display_df[mask]

    with col_count:
        st.caption(f"{len(display_df):,} записей")

    st.dataframe(
        display_df,
        width="stretch",
        height=520,
        column_config={
            "Lat": st.column_config.NumberColumn("Широта", format="%.4f"),
            "Lon": st.column_config.NumberColumn("Долгота", format="%.4f"),
            "Depth": st.column_config.NumberColumn("Глубина (км)", format="%.1f"),
            "Ml": st.column_config.NumberColumn("Магнитуда (Ml)", format="%.1f"),
            "K": st.column_config.NumberColumn("K", format="%.1f"),
        },
    )
