# pages/result.py
# 결과 페이지: 재무 테이블 + 차트 + 주가 정보 + 뉴스
import streamlit as st
import pandas as pd

from chart import build_performance_chart


def _fmt_price(val) -> str:
    """숫자를 천 단위 콤마 + 원 형식으로 포맷. None이면 N/A"""
    if val is None:
        return "N/A"
    try:
        return f"{int(val):,}원"
    except Exception:
        return str(val)


def _fmt_volume(val) -> str:
    if val is None:
        return "N/A"
    try:
        return f"{int(val):,}주"
    except Exception:
        return str(val)


def _fmt_market_cap(val) -> str:
    if val is None:
        return "N/A"
    try:
        billion = int(val) // 100_000_000
        return f"{billion:,}억원"
    except Exception:
        return str(val)


def render_stock_section(stock: dict):
    """주가 정보 섹션 렌더링"""

    change     = stock.get("등락")
    change_pct = stock.get("등락률")

    if change is not None and change_pct is not None:
        arrow      = "▲" if change >= 0 else "▼"
        sign       = "+" if change >= 0 else ""
        color_cls  = "up" if change >= 0 else "down"
        change_str = f"{arrow} {sign}{int(change):,}원 ({sign}{change_pct:.2f}%)"
    else:
        color_cls  = "neutral"
        change_str = "N/A"

    current_str = _fmt_price(stock.get("현재가"))
    query_time  = stock.get("조회시각", "")
    market_name = stock.get("시장", "")
    ticker_code = stock.get("종목코드", "")

    st.markdown(f"""
    <style>
    .stock-card {{
        background: #ffffff;
        border: 1.5px solid #E8EAED;
        border-radius: 14px;
        padding: 24px 28px 20px;
        margin-bottom: 8px;
    }}
    .stock-header {{
        display: flex;
        align-items: baseline;
        gap: 10px;
        margin-bottom: 4px;
    }}
    .stock-name {{
        font-size: 18px;
        font-weight: 700;
        color: #2C3E50;
    }}
    .stock-meta {{
        font-size: 12px;
        color: #95A5A6;
    }}
    .stock-price-row {{
        display: flex;
        align-items: baseline;
        gap: 14px;
        margin: 8px 0 6px;
    }}
    .stock-price {{
        font-size: 32px;
        font-weight: 700;
        color: #2C3E50;
        letter-spacing: -0.5px;
    }}
    .stock-change.up   {{ font-size: 16px; font-weight: 600; color: #E74C3C; }}
    .stock-change.down {{ font-size: 16px; font-weight: 600; color: #2980B9; }}
    .stock-change.neutral {{ font-size: 16px; color: #95A5A6; }}
    .stock-timestamp {{
        font-size: 11px;
        color: #BDC3C7;
        margin-bottom: 18px;
    }}
    .stock-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0;
        border-top: 1px solid #F0F0F0;
        padding-top: 16px;
    }}
    .stock-cell {{
        padding: 6px 12px 6px 0;
    }}
    .stock-cell-label {{
        font-size: 11px;
        color: #95A5A6;
        margin-bottom: 3px;
    }}
    .stock-cell-value {{
        font-size: 14px;
        font-weight: 500;
        color: #2C3E50;
    }}
    </style>

    <div class="stock-card">
        <div class="stock-header">
            <span class="stock-name">{stock.get("종목명", "")}</span>
            <span class="stock-meta">{ticker_code} · {market_name}</span>
        </div>
        <div class="stock-price-row">
            <span class="stock-price">{current_str}</span>
            <span class="stock-change {color_cls}">{change_str}</span>
        </div>
        <div class="stock-timestamp">📅 조회 시점: {query_time} 기준 &nbsp;·&nbsp; 실시간 시세가 아닙니다</div>
        <div class="stock-grid">
            <div class="stock-cell">
                <div class="stock-cell-label">전일종가</div>
                <div class="stock-cell-value">{_fmt_price(stock.get("전일종가"))}</div>
            </div>
            <div class="stock-cell">
                <div class="stock-cell-label">시가</div>
                <div class="stock-cell-value">{_fmt_price(stock.get("시가"))}</div>
            </div>
            <div class="stock-cell">
                <div class="stock-cell-label">고가</div>
                <div class="stock-cell-value">{_fmt_price(stock.get("고가"))}</div>
            </div>
            <div class="stock-cell">
                <div class="stock-cell-label">저가</div>
                <div class="stock-cell-value">{_fmt_price(stock.get("저가"))}</div>
            </div>
            <div class="stock-cell">
                <div class="stock-cell-label">거래량</div>
                <div class="stock-cell-value">{_fmt_volume(stock.get("거래량"))}</div>
            </div>
            <div class="stock-cell">
                <div class="stock-cell-label">시가총액</div>
                <div class="stock-cell-value">{_fmt_market_cap(stock.get("시가총액"))}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render():
    r          = st.session_state.get("result", {})
    corp_name  = r.get("corp_name", "")
    data_dict  = r.get("data_by_item", {})
    items      = r.get("items", [])
    news_list  = r.get("news_list", [])
    stock_info = r.get("stock_info")        # listed.py에서만 존재, 없으면 None

    # ── 헤더 ──────────────────────────────────────────────
    col_back, col_title = st.columns([1, 7])
    with col_back:
        if st.button("← 처음으로", key="result_back"):
            st.session_state.page = "home"
            st.session_state.pop("result", None)
            st.rerun()
    with col_title:
        st.markdown(f"## 📋 {corp_name} — 분석 결과")

    st.divider()

    # ══════════════════════════════════════════════════════
    # 1. 재무 데이터 테이블
    # ══════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════
    # 🔧 주가 디버그 패널 (확인 후 삭제 예정)
    # ══════════════════════════════════════════════════════
    debug_logs = st.session_state.get("stock_debug")
    if debug_logs is not None:
        with st.expander("🔧 [임시] 주가 조회 디버그 로그", expanded=True):
            for line in debug_logs:
                st.text(line)

    st.markdown("### 재무 데이터")

    has_any_data = any(v for v in data_dict.values())
    if not has_any_data:
        st.info("수집된 재무 데이터가 없습니다.")
    else:
        rows = {}
        for item, records in data_dict.items():
            for rec in records:
                yr  = rec["year"]
                amt = rec["amount"]
                if yr not in rows:
                    rows[yr] = {"연도": yr}
                rows[yr][item] = f"{int(amt / 1e8):,} 억원" if amt != 0 else "-"

        if rows:
            df_table = (pd.DataFrame(rows.values())
                          .sort_values("연도", ascending=False)
                          .reset_index(drop=True))
            st.dataframe(df_table, use_container_width=True, hide_index=True)

    st.divider()

    # ══════════════════════════════════════════════════════
    # 2. 실적 차트
    # ══════════════════════════════════════════════════════
    st.markdown("### 실적 추이 차트")

    fig = build_performance_chart(data_dict, corp_name)
    if fig is None:
        st.warning("매출액 또는 영업이익 데이터가 존재하지 않아 그래프가 생략되었습니다.")
    else:
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ══════════════════════════════════════════════════════
    # 3. 주가 정보 (상장사 조회 성공 시에만 표시)
    # ══════════════════════════════════════════════════════
    if stock_info:
        st.markdown("### 주가 정보")
        render_stock_section(stock_info)
        st.divider()

    # ══════════════════════════════════════════════════════
    # 4. 뉴스 검색 결과
    # ══════════════════════════════════════════════════════
    st.markdown("### 관련 뉴스")

    if not news_list:
        st.info("검색된 뉴스가 없습니다.")
    else:
        st.caption(f"총 {len(news_list)}건")
        df_news = pd.DataFrame([
            {
                "작성일": str(n.get("작성일") or n.get("pub_date", "")),
                "제목":   n.get("제목") or n.get("title", ""),
                "링크":   n.get("링크") or n.get("link", ""),
            }
            for n in news_list
        ])

        def make_link(url):
            if url:
                return f'<a href="{url}" target="_blank">🔗 기사 보기</a>'
            return ""

        df_news["링크"] = df_news["링크"].apply(make_link)
        st.write(
            df_news.to_html(escape=False, index=False),
            unsafe_allow_html=True,
        )
