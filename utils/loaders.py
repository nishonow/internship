import streamlit as st
import pandas as pd

_REQUIRED_EQ_COLS = ["Origin", "Lat", "Lon", "Ml"]
_REQUIRED_ST_COLS = ["Lat", "Lon"]


@st.cache_data
def load_stations(file):
    try:
        df = pd.read_excel(file)
    except Exception:
        return None, "Не удалось прочитать файл. Убедитесь, что это корректный Excel (.xlsx)."
    df.columns = df.columns.str.strip()
    missing = [c for c in _REQUIRED_ST_COLS if c not in df.columns]
    if missing:
        return None, f"Отсутствуют обязательные колонки: {', '.join(missing)}. Ожидаются: Network, Station_code, Lat, Lon, Elevation."
    for col in ["Lat", "Lon", "Elevation"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["Lat", "Lon"]), None


@st.cache_data
def load_data(file):
    try:
        df = pd.read_excel(file)
    except Exception:
        return None, "Не удалось прочитать файл. Убедитесь, что это корректный Excel (.xlsx)."
    df.columns = df.columns.str.strip()
    missing = [c for c in _REQUIRED_EQ_COLS if c not in df.columns]
    if missing:
        return None, f"Отсутствуют обязательные колонки: {', '.join(missing)}. Ожидаются: Origin, Lat, Lon, Depth, Ml, K."
    df["Origin"] = pd.to_datetime(df["Origin"], errors="coerce")
    for col in ["Lat", "Lon", "Depth", "Ml", "K"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Origin", "Lat", "Lon", "Ml"])
    if df.empty:
        return None, "Файл не содержит строк с корректными данными (Origin, Lat, Lon, Ml)."
    return df, None
