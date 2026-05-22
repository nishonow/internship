import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

_RED    = "#e63946"
_BLUE   = "#457b9d"
_ORANGE = "#f4a261"
_GREEN  = "#2a9d8f"

_LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="#f8f9fa",
    font=dict(family="sans-serif", size=13),
    margin=dict(l=40, r=20, t=50, b=60),
)


def _chart(fig):
    st.plotly_chart(fig, width="stretch")


def render_stats(df: pd.DataFrame) -> None:
    if df.empty:
        st.warning("Нет землетрясений по текущим фильтрам.", icon=":material/filter_alt_off:")
        return

    # ── Фильтр по годам ───────────────────────────────────────────────────────
    years = sorted(df["Origin"].dt.year.dropna().unique().tolist())
    if len(years) > 1:
        col_f1, col_f2, _ = st.columns([1, 1, 3])
        with col_f1:
            year_start = st.selectbox("С года", years, index=0, key="stats_year_start")
        with col_f2:
            year_end = st.selectbox("По год", years, index=len(years) - 1, key="stats_year_end")
        if year_start > year_end:
            st.warning("Год 'С' должен быть ≤ году 'По'.", icon=":material/warning:")
            year_start, year_end = year_end, year_start
        dfs = df[df["Origin"].dt.year.between(year_start, year_end)].copy()
    else:
        dfs = df.copy()

    if dfs.empty:
        st.warning("Нет данных за выбранный период.", icon=":material/filter_alt_off:")
        return

    # ── Предварительные вычисления ────────────────────────────────────────────
    has_k = "K" in dfs.columns and dfs["K"].notna().any()

    yearly = (
        dfs.groupby(dfs["Origin"].dt.year)
        .agg(events=("Ml", "count"), avg_ml=("Ml", "mean"), max_ml=("Ml", "max"))
        .reset_index()
        .rename(columns={"Origin": "year"})
    )
    yearly["year"] = yearly["year"].astype(str)

    if has_k:
        dfs_k = dfs.dropna(subset=["K"])
        yearly_k = (
            dfs_k.groupby(dfs_k["Origin"].dt.year)
            .agg(avg_k=("K", "mean"), max_k=("K", "max"))
            .reset_index()
            .rename(columns={"Origin": "year"})
        )
        yearly_k["year"] = yearly_k["year"].astype(str)
        yearly = yearly.merge(yearly_k, on="year", how="left")

    st.markdown("---")

    with st.spinner("Построение графиков..."):
        _render_charts(dfs, has_k, yearly)


def _render_charts(dfs: pd.DataFrame, has_k: bool, yearly: pd.DataFrame) -> None:

    # ── Сводные карточки ──────────────────────────────────────────────────────
    st.markdown("### :material/summarize: Сводка")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Всего событий",      f"{len(dfs):,}")
    c2.metric("Средняя магнитуда",  f"{dfs['Ml'].mean():.2f}")
    c3.metric("Макс. магнитуда",    f"{dfs['Ml'].max():.1f}")
    c4.metric("Средняя глубина (км)", f"{dfs['Depth'].mean():.1f}")

    st.markdown("---")

    # ── Обзор по годам ────────────────────────────────────────────────────────
    st.markdown("### :material/calendar_month: Обзор по годам")

    col_ya, col_yb = st.columns(2)

    with col_ya:
        fig_ev = go.Figure(go.Bar(
            x=yearly["year"], y=yearly["events"],
            marker_color=_BLUE,
            text=yearly["events"],
            textposition="inside",
            textfont=dict(color="white", size=11),
        ))
        fig_ev.update_layout(
            **_LAYOUT,
            title="События по годам",
            xaxis_title="Год",
            yaxis_title="Количество",
            uniformtext_minsize=9,
            uniformtext_mode="hide",
        )
        _chart(fig_ev)

    with col_yb:
        fig_ml = go.Figure()
        fig_ml.add_trace(go.Bar(
            x=yearly["year"], y=yearly["avg_ml"],
            name="Ср. Ml", marker_color=_ORANGE, yaxis="y1",
        ))
        fig_ml.add_trace(go.Scatter(
            x=yearly["year"], y=yearly["max_ml"],
            name="Макс. Ml", mode="lines+markers",
            line=dict(color=_RED, width=2.5), marker=dict(size=7),
            yaxis="y2",
        ))
        fig_ml.update_layout(
            **_LAYOUT,
            title="Магнитуда по годам",
            xaxis_title="Год",
            yaxis=dict(title="Ср. Ml", color=_ORANGE),
            yaxis2=dict(title="Макс. Ml", color=_RED,
                        overlaying="y", side="right", showgrid=False),
            legend=dict(orientation="h", x=0, y=-0.25),
        )
        _chart(fig_ml)

    # ── K по годам ────────────────────────────────────────────────────────────
    if has_k and "avg_k" in yearly.columns:
        peak_idx  = yearly["avg_k"].idxmax()
        peak_year = yearly.loc[peak_idx, "year"]
        peak_val  = yearly.loc[peak_idx, "avg_k"]

        st.markdown("### :material/bolt: Энергетический класс (K) по годам")
        st.caption(f"Пиковое среднее K: **{peak_val:.1f}** в **{peak_year}** году")

        fig_ky = go.Figure()
        fig_ky.add_trace(go.Bar(
            x=yearly["year"], y=yearly["avg_k"],
            name="Ср. K", marker_color=_GREEN, yaxis="y1",
        ))
        fig_ky.add_trace(go.Scatter(
            x=yearly["year"], y=yearly["max_k"],
            name="Макс. K", mode="lines+markers",
            line=dict(color=_ORANGE, width=2.5), marker=dict(size=7),
            yaxis="y2",
        ))
        fig_ky.update_layout(
            **_LAYOUT,
            title="Энергетический класс K по годам",
            xaxis_title="Год",
            yaxis=dict(title="Ср. K", color=_GREEN),
            yaxis2=dict(title="Макс. K", color=_ORANGE,
                        overlaying="y", side="right", showgrid=False),
            legend=dict(orientation="h", x=0, y=-0.25),
        )
        _chart(fig_ky)

    st.markdown("---")

    # ── Ежемесячный тренд ─────────────────────────────────────────────────────
    st.markdown("### :material/timeline: Количество событий по месяцам")
    monthly = (
        dfs.set_index("Origin")
        .resample("ME")
        .size()
        .reset_index(name="count")
    )
    monthly["month"] = monthly["Origin"].dt.strftime("%Y-%m")

    fig_line = go.Figure(go.Scatter(
        x=monthly["month"], y=monthly["count"],
        mode="lines+markers",
        line=dict(color=_RED, width=2.5),
        marker=dict(size=5, color=_RED),
        fill="tozeroy",
        fillcolor="rgba(230,57,70,0.08)",
    ))
    fig_line.update_layout(
        **_LAYOUT,
        xaxis_title="Месяц",
        yaxis_title="Количество событий",
        hovermode="x unified",
    )
    _chart(fig_line)

    # ── Гистограмма магнитуды + Глубина vs Магнитуда ─────────────────────────
    col_h, col_s = st.columns(2)

    with col_h:
        st.markdown("### :material/bar_chart: Распределение магнитуды")
        fig_hist = px.histogram(
            dfs, x="Ml", nbins=30,
            color_discrete_sequence=[_BLUE],
            labels={"Ml": "Магнитуда (Ml)"},
        )
        fig_hist.update_layout(
            **_LAYOUT,
            bargap=0.05,
            xaxis_title="Магнитуда (Ml)",
            yaxis_title="Количество",
            showlegend=False,
        )
        _chart(fig_hist)

    with col_s:
        st.markdown("### :material/scatter_plot: Глубина vs Магнитуда")
        hover_cols = ["Origin"]
        if has_k:
            hover_cols.append("K")
        fig_sc = px.scatter(
            dfs, x="Ml", y="Depth", color="Depth",
            color_continuous_scale=[[0, _RED], [0.4, _ORANGE], [1, _BLUE]],
            labels={"Ml": "Магнитуда (Ml)", "Depth": "Глубина (км)"},
            opacity=0.65,
            hover_data=hover_cols,
        )
        fig_sc.update_layout(
            **_LAYOUT,
            xaxis_title="Магнитуда (Ml)",
            yaxis_title="Глубина (км)",
            coloraxis_colorbar=dict(title="Глубина (км)"),
        )
        fig_sc.update_yaxes(autorange="reversed")
        _chart(fig_sc)

    # ── Распределение K ───────────────────────────────────────────────────────
    if has_k:
        st.markdown("### :material/bolt: Распределение энергетического класса (K)")
        fig_k = px.histogram(
            dfs.dropna(subset=["K"]), x="K", nbins=25,
            color_discrete_sequence=[_ORANGE],
            labels={"K": "Энергетический класс (K)"},
        )
        fig_k.update_layout(
            **_LAYOUT,
            bargap=0.05,
            xaxis_title="K",
            yaxis_title="Количество",
            showlegend=False,
        )
        _chart(fig_k)
