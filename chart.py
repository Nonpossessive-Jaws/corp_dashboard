# chart.py
# Plotly 기반 그래프 생성
import plotly.graph_objects as go
import pandas as pd


# 브랜드 컬러
C_BAR_SALES   = "#2C3E50"   # 매출액 막대
C_BAR_PROFIT  = "#1ABC9C"   # 영업이익 막대
C_LINE_MARGIN = "#E74C3C"   # 영업이익률 꺾은선
C_GRID        = "rgba(200,200,200,0.3)"


def build_performance_chart(data_by_item: dict[str, list],
                             corp_name: str) -> go.Figure | None:
    """
    매출액·영업이익·영업이익률 복합 차트(막대 + 꺾은선) 생성.
    데이터 부족 시 None 반환.
    """
    sales_data  = data_by_item.get("매출액",  [])
    profit_data = data_by_item.get("영업이익", [])

    if not sales_data or not profit_data:
        return None

    df_s = pd.DataFrame(sales_data).rename(columns={"amount": "매출액"})
    df_p = pd.DataFrame(profit_data).rename(columns={"amount": "영업이익"})
    df   = pd.merge(df_s[["year", "매출액"]], df_p[["year", "영업이익"]], on="year")
    df["영업이익률"] = (df["영업이익"] / df["매출액"] * 100).round(2)
    df = df.sort_values("year")

    # 단위 변환: 원 → 억원
    df["매출액_억"]   = (df["매출액"]   / 1e8).round(1)
    df["영업이익_억"] = (df["영업이익"] / 1e8).round(1)

    fig = go.Figure()

    # 막대: 매출액
    fig.add_trace(go.Bar(
        x=df["year"].astype(str), y=df["매출액_억"],
        name="매출액 (억원)",
        marker_color=C_BAR_SALES,
        yaxis="y1",
        text=df["매출액_억"].apply(lambda v: f"{v:,.0f}"),
        textposition="outside",
    ))

    # 막대: 영업이익
    fig.add_trace(go.Bar(
        x=df["year"].astype(str), y=df["영업이익_억"],
        name="영업이익 (억원)",
        marker_color=C_BAR_PROFIT,
        yaxis="y1",
        text=df["영업이익_억"].apply(lambda v: f"{v:,.0f}"),
        textposition="outside",
    ))

    # 꺾은선: 영업이익률
    fig.add_trace(go.Scatter(
        x=df["year"].astype(str), y=df["영업이익률"],
        name="영업이익률 (%)",
        mode="lines+markers+text",
        line=dict(color=C_LINE_MARGIN, width=2.5),
        marker=dict(size=8),
        yaxis="y2",
        text=df["영업이익률"].apply(lambda v: f"{v:.1f}%"),
        textposition="top center",
    ))

    fig.update_layout(
        title=dict(
            text=f"<b>{corp_name}</b> 실적 추이",
            font=dict(size=18, color="#2C3E50"),
            x=0.03,
        ),
        barmode="group",
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            orientation="h",
            yanchor="bottom", y=-0.2,
            xanchor="center", x=0.5,
            font=dict(size=12),
        ),
        xaxis=dict(
            title=None,
            tickfont=dict(size=13),
            showgrid=False,
        ),
        yaxis=dict(
            title="금액 (억원)",
            showgrid=True,
            gridcolor=C_GRID,
            tickfont=dict(size=12),
            zeroline=False,
        ),
        yaxis2=dict(
            title="영업이익률 (%)",
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(size=12),
            ticksuffix="%",
            zeroline=False,
        ),
        margin=dict(t=70, b=60, l=60, r=60),
        height=440,
    )
    return fig
