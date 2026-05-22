import streamlit as st
import pandas as pd


def render_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.warning("Нет землетрясений по текущим фильтрам.", icon=":material/filter_alt_off:")
        return

    st.markdown("### :material/table_chart: Отфильтрованные данные о землетрясениях")

    col_left, col_right = st.columns([3, 1])
    with col_left:
        st.caption(f"{len(df):,} записей")
    with col_right:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Скачать CSV",
            data=csv,
            file_name="earthquakes_filtered.csv",
            mime="text/csv",
            icon=":material/download:",
            use_container_width=True,
        )

    display_df = df.copy()
    if "Origin" in display_df.columns:
        display_df["Origin"] = display_df["Origin"].dt.strftime("%Y-%m-%d %H:%M:%S")

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
