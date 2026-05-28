import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="sans-serif", size=13),
    margin=dict(l=40, r=20, t=50, b=60),
)


def render_stats(df: pd.DataFrame) -> None:
    if df.empty:
        st.warning("Нет данных для статистики.", icon=":material/filter_alt_off:")
        return

    min_date = df["Origin"].min().date()
    max_date = df["Origin"].max().date()

    col_d1, col_d2, col_spacer = st.columns([2, 2, 5])
    with col_d1:
        s_start = st.date_input("С", value=min_date, min_value=min_date, max_value=max_date, key="stats_start", format="YYYY-MM-DD")
    with col_d2:
        s_end = st.date_input("По", value=max_date, min_value=min_date, max_value=max_date, key="stats_end", format="YYYY-MM-DD")

    df = df[(df["Origin"].dt.date >= s_start) & (df["Origin"].dt.date <= s_end)]

    if df.empty:
        st.warning("Нет землетрясений в выбранном диапазоне.", icon=":material/filter_alt_off:")
        return

    col_l, col_r = st.columns(2)

    def _hist_with_line(data, bin_size, bar_color, line_color, x_label, x_suffix=""):
        counts, bins = np.histogram(data, bins=np.arange(data.min(), data.max() + bin_size, bin_size))
        centers = (bins[:-1] + bins[1:]) / 2
        hover = [f"{bins[i]:.4g}–{bins[i+1]:.4g}{x_suffix}<br>Количество: {counts[i]}" for i in range(len(counts))]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=centers, y=counts,
            marker_color=bar_color, marker_opacity=0.6,
            width=bin_size * 0.92,
            hovertext=hover, hoverinfo="text",
            showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=centers, y=counts,
            mode="lines",
            line=dict(color=line_color, width=2),
            hoverinfo="skip",
            showlegend=False,
        ))
        fig.update_layout(**_LAYOUT, xaxis_title=x_label, yaxis_title="Количество", bargap=0)
        return fig

    with col_l:
        depth_data = df["Depth"].dropna()
        fig_depth = _hist_with_line(depth_data, 5, "#f4a261", "#e07b2a", "Глубина (км)", " км")
        fig_depth.update_layout(title="Распределение глубины")
        st.plotly_chart(fig_depth, width="stretch", config={"displayModeBar": False})

    with col_r:
        if "K" in df.columns and df["K"].notna().any():
            k_data = df["K"].dropna()
            fig_k = _hist_with_line(k_data, 0.5, "#457b9d", "#2c5f7a", "K")
            fig_k.update_layout(title="Распределение K")
            st.plotly_chart(fig_k, width="stretch", config={"displayModeBar": False})
        else:
            st.info("Нет данных по K.", icon=":material/info:")


    date_range = (df["Origin"].max() - df["Origin"].min()).days

    # Auto-select time granularity so the chart stays readable at any date range:
    # >2 years → group by year, >2 months → group by month, else group by day.
    if date_range > 730:
        grouped = df.groupby(df["Origin"].dt.strftime("%Y")).size().reset_index(name="count")
        x_title = "Год"
    elif date_range > 60:
        grouped = df.groupby(df["Origin"].dt.strftime("%Y-%m")).size().reset_index(name="count")
        x_title = "Месяц"
    else:
        grouped = df.groupby(df["Origin"].dt.date).size().reset_index(name="count")
        x_title = "День"

    grouped.columns = ["date", "count"]

    fig_events = go.Figure()
    fig_events.add_trace(go.Scatter(
        x=grouped["date"],
        y=grouped["count"],
        mode="lines+markers",
        fill="tozeroy",
        line=dict(color="#e63946", width=2),
        fillcolor="rgba(230,57,70,0.12)",
        marker=dict(size=5, color="#e63946"),
        hovertemplate=f"{x_title}: %{{x}}<br>Событий: %{{y}}<extra></extra>",
    ))
    fig_events.update_layout(
        **_LAYOUT,
        xaxis_title=x_title,
        yaxis_title="Количество",
        height=380,
        hovermode="x unified",
        xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
    )
    fig_events.update_layout(margin=dict(l=40, r=20, t=30, b=80))
    st.plotly_chart(fig_events, width="stretch", config={"displayModeBar": False})
