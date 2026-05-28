import streamlit as st
import pandas as pd


def render_stations(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Нет данных о станциях.", icon=":material/sensors_off:")
        return

    display_cols = [c for c in ["Network", "Station_code", "Lat", "Lon", "Elevation", "Info"] if c in df.columns]

    st.markdown(f"**{len(df)}** станций")
    st.dataframe(
        df[display_cols].reset_index(drop=True),
        width="stretch",
        height=560,
        column_config={
            "Network":      st.column_config.TextColumn("Сеть",         width="small"),
            "Station_code": st.column_config.TextColumn("Код",          width="small"),
            "Lat":          st.column_config.NumberColumn("Широта",     format="%.4f"),
            "Lon":          st.column_config.NumberColumn("Долгота",    format="%.4f"),
            "Elevation":    st.column_config.NumberColumn("Высота, м",  format="%.0f"),
            "Info":         st.column_config.TextColumn("Info", width="large"),
        },
        hide_index=True,
    )
