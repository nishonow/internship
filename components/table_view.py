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

    # Work on a copy so the datetime column is formatted as a string for display
    # without mutating the original df that other tabs depend on.
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

    def _depth_style(val):
        if pd.isna(val):
            return ""
        if val < 10:
            return "background-color: rgba(230,57,70,0.18); color: #e63946; font-weight:600"
        elif val < 20:
            return "background-color: rgba(244,162,97,0.18); color: #f4a261; font-weight:600"
        else:
            return "background-color: rgba(69,123,157,0.18); color: #457b9d; font-weight:600"

    styled = display_df.style.format({
        "Lat": "{:.4f}", "Lon": "{:.4f}",
        "Depth": "{:.1f}", "Ml": "{:.1f}", "K": "{:.1f}",
    }, na_rep="—")
    if "Depth" in display_df.columns:
        styled = styled.map(_depth_style, subset=["Depth"])

    st.dataframe(styled, width="stretch", height=520)
