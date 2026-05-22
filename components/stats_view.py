import streamlit as st
import pandas as pd
import plotly.graph_objects as go

_BLUE  = "#457b9d"
_GREEN = "#2a9d8f"

_LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="#f8f9fa",
    font=dict(family="sans-serif", size=13),
    margin=dict(l=40, r=20, t=50, b=60),
)


def _chart(fig):
    st.plotly_chart(fig, width="stretch")


def _time_line(dfs, time_group, col, color, title, y_label, x_label_time):
    plot_df = dfs[[col]].dropna(subset=[col]).copy()
    plot_df["_period"] = time_group[plot_df.index]

    grouped = (
        plot_df.groupby("_period")[col]
        .agg(avg="mean", count="count", mx="max", mn="min")
        .reset_index()
    )

    hover = (
        "<b>" + grouped["_period"].astype(str) + "</b><br>"
        + y_label + ": " + grouped["avg"].round(2).astype(str) + "<br>"
        + "Макс: " + grouped["mx"].round(2).astype(str) + "<br>"
        + "Мин: " + grouped["mn"].round(2).astype(str) + "<br>"
        + "Событий: " + grouped["count"].astype(str)
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=grouped["_period"], y=grouped["avg"],
        mode="lines+markers",
        line=dict(color=color, width=2.5),
        marker=dict(size=6, color=color),
        hovertext=hover,
        hoverinfo="text",
        showlegend=False,
    ))
    fig.update_layout(
        **_LAYOUT,
        title=title,
        xaxis_title=x_label_time,
        yaxis_title=y_label,
    )
    return fig


def render_stats(df: pd.DataFrame) -> None:
    if df.empty:
        st.warning("Нет землетрясений по текущим фильтрам.", icon=":material/filter_alt_off:")
        return

    dfs = df.copy()
    has_k = "K" in dfs.columns and dfs["K"].notna().any()

    date_span = (dfs["Origin"].max() - dfs["Origin"].min()).days
    if date_span > 730:
        time_group = dfs["Origin"].dt.to_period("Y").astype(str)
        x_label_time = "Год"
    elif date_span > 60:
        time_group = dfs["Origin"].dt.to_period("M").astype(str)
        x_label_time = "Месяц"
    else:
        time_group = dfs["Origin"].dt.strftime("%Y-%m-%d")
        x_label_time = "Дата"

    yearly = (
        dfs.groupby(time_group)
        .agg(events=("Ml", "count"))
        .reset_index()
        .rename(columns={"Origin": "period"})
    )

    st.markdown("---")
    _render_charts(dfs, has_k, yearly, x_label_time, time_group)


def _render_charts(dfs: pd.DataFrame, has_k: bool, yearly: pd.DataFrame, x_label_time: str, time_group) -> None:

    # ── 1. Глубина по времени ─────────────────────────────────────────────────
    st.markdown("### :material/arrow_downward: Глубина по времени")
    _dm1, _dm2 = st.columns(2)
    _dm1.metric("Мин. глубина", f"{dfs['Depth'].min():.1f} км")
    _dm2.metric("Макс. глубина", f"{dfs['Depth'].max():.1f} км")
    _chart(_time_line(
        dfs, time_group, "Depth", "#f4a261",
        "Средняя глубина (км)", "Глубина (км)", x_label_time,
    ))

    st.markdown("---")

    # ── 2. События по времени ─────────────────────────────────────────────────
    st.markdown("### :material/calendar_month: События по времени")
    fig_ev = go.Figure(go.Bar(
        x=yearly["period"], y=yearly["events"],
        marker_color=_BLUE,
        text=yearly["events"],
        textposition="inside",
        textfont=dict(color="white", size=11),
    ))
    fig_ev.update_layout(
        **_LAYOUT,
        title="Количество землетрясений",
        xaxis_title=x_label_time,
        yaxis_title="Количество",
        uniformtext_minsize=9,
        uniformtext_mode="hide",
    )
    _chart(fig_ev)

    st.markdown("---")

    # ── 3 & 4. Магнитуда и K по времени ──────────────────────────────────────
    if has_k:
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("### :material/show_chart: Магнитуда по времени")
            _chart(_time_line(
                dfs, time_group, "Ml", _BLUE,
                "Средняя магнитуда (Ml)", "Магнитуда (Ml)", x_label_time,
            ))
        with col_r:
            st.markdown("### :material/bolt: Энергетический класс (K) по времени")
            _chart(_time_line(
                dfs, time_group, "K", _GREEN,
                "Средний энергетический класс (K)", "K", x_label_time,
            ))
    else:
        st.markdown("### :material/show_chart: Магнитуда по времени")
        _chart(_time_line(
            dfs, time_group, "Ml", _BLUE,
            "Средняя магнитуда (Ml)", "Магнитуда (Ml)", x_label_time,
        ))
