# pages/result.py
# 결과 페이지: 재무 테이블 + 차트 + 주가 정보 + 업종 벤치마크 + 뉴스
import streamlit as st
import pandas as pd

from chart    import build_performance_chart
from dart_api import fetch_stock_info


def _fmt_price(val) -> str:
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


def render_stock_section(stock: dict, corp_name: str):
    """주가 정보 카드 + 새로고침 버튼"""
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

    current_str  = _fmt_price(stock.get("현재가"))
    query_time   = stock.get("조회시각", "")
    ticker_code  = stock.get("종목코드", "")
    market_name  = stock.get("시장", "")
    sector_str   = stock.get("섹터") or ""
    industry_str = stock.get("업종") or ""
    meta_parts   = [p for p in [ticker_code, market_name, sector_str, industry_str] if p]
    meta_str     = " · ".join(meta_parts)

    st.markdown(f"""
    <style>
    .stock-card {{
        background: #ffffff;
        border: 1.5px solid #E8EAED;
        border-radius: 14px;
        padding: 24px 28px 20px;
        margin-bottom: 8px;
    }}
    .stock-header {{ display: flex; align-items: baseline; gap: 10px; margin-bottom: 4px; }}
    .stock-name {{ font-size: 18px; font-weight: 700; color: #2C3E50; }}
    .stock-meta {{ font-size: 12px; color: #95A5A6; }}
    .stock-price-row {{ display: flex; align-items: baseline; gap: 14px; margin: 8px 0 6px; }}
    .stock-price {{ font-size: 32px; font-weight: 700; color: #2C3E50; letter-spacing: -0.5px; }}
    .stock-change.up      {{ font-size: 16px; font-weight: 600; color: #E74C3C; }}
    .stock-change.down    {{ font-size: 16px; font-weight: 600; color: #2980B9; }}
    .stock-change.neutral {{ font-size: 16px; color: #95A5A6; }}
    .stock-timestamp {{ font-size: 11px; color: #BDC3C7; margin-bottom: 18px; }}
    .stock-grid {{
        display: grid; grid-template-columns: repeat(3, 1fr);
        gap: 0; border-top: 1px solid #F0F0F0; padding-top: 16px;
    }}
    .stock-cell {{ padding: 6px 12px 6px 0; }}
    .stock-cell-label {{ font-size: 11px; color: #95A5A6; margin-bottom: 3px; }}
    .stock-cell-value {{ font-size: 14px; font-weight: 500; color: #2C3E50; }}
    </style>

    <div class="stock-card">
        <div class="stock-header">
            <span class="stock-name">{stock.get("종목명", "")}</span>
            <span class="stock-meta">{meta_str}</span>
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

    # ── 새로고침 버튼 ─────────────────────────────────────
    if st.button("🔄 주가 새로고침", key="stock_refresh"):
        with st.spinner("주가 정보 업데이트 중..."):
            new_info = fetch_stock_info(corp_name)
        if new_info:
            st.session_state.result["stock_info"] = new_info
            st.rerun()
        else:
            st.warning("주가 정보를 불러오지 못했습니다.")


def render_sector_section(stock: dict, benchmark: dict):
    """업종/섹터 분류 및 벤치마크 비교 섹션"""
    industry_str = stock.get("업종") or "정보 없음"
    sector_str   = stock.get("섹터") or "정보 없음"

    avg_om  = benchmark.get("평균영업이익률")
    avg_per = benchmark.get("평균PER")
    avg_pbr = benchmark.get("평균PBR")
    sample  = benchmark.get("샘플수", 0)

    st.markdown(f"""
    <style>
    .sector-card {{
        background: #ffffff;
        border: 1.5px solid #E8EAED;
        border-radius: 14px;
        padding: 22px 28px;
        margin-bottom: 8px;
    }}
    .sector-badge-row {{ display: flex; gap: 10px; margin-bottom: 18px; flex-wrap: wrap; }}
    .sector-badge {{
        background: #F0F8FF; border: 1px solid #D6EAF8;
        border-radius: 20px; padding: 5px 14px;
        font-size: 12px; color: #2C3E50; font-weight: 500;
    }}
    .sector-badge .badge-label {{ color: #95A5A6; margin-right: 4px; }}
    .bench-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
    .bench-cell {{
        background: #F7F8FA; border-radius: 10px;
        padding: 14px 16px; text-align: center;
    }}
    .bench-label {{ font-size: 11px; color: #95A5A6; margin-bottom: 6px; }}
    .bench-value {{ font-size: 20px; font-weight: 700; color: #2C3E50; }}
    .bench-sub {{ font-size: 11px; color: #BDC3C7; margin-top: 4px; }}
    </style>

    <div class="sector-card">
        <div class="sector-badge-row">
            <div class="sector-badge"><span class="badge-label">섹터</span>{sector_str}</div>
            <div class="sector-badge"><span class="badge-label">업종</span>{industry_str}</div>
        </div>
        <div class="bench-grid">
            <div class="bench-cell">
                <div class="bench-label">업종 평균 영업이익률</div>
                <div class="bench-value">{f"{avg_om:.1f}%" if avg_om is not None else "N/A"}</div>
                <div class="bench-sub">동종업계 {sample}개사 평균</div>
            </div>
            <div class="bench-cell">
                <div class="bench-label">업종 평균 PER</div>
                <div class="bench-value">{f"{avg_per:.1f}x" if avg_per is not None else "N/A"}</div>
                <div class="bench-sub">주가수익비율</div>
            </div>
            <div class="bench-cell">
                <div class="bench-label">업종 평균 PBR</div>
                <div class="bench-value">{f"{avg_pbr:.1f}x" if avg_pbr is not None else "N/A"}</div>
                <div class="bench-sub">주가순자산비율</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render():
    r                = st.session_state.get("result", {})
    corp_name        = r.get("corp_name", "")
    data_dict        = r.get("data_by_item", {})
    items            = r.get("items", [])
    news_list        = r.get("news_list", [])
    stock_info       = r.get("stock_info")
    sector_benchmark = r.get("sector_benchmark")

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
        render_stock_section(stock_info, corp_name)
        st.divider()

    # ══════════════════════════════════════════════════════
    # 4. 업종/섹터 분류 및 벤치마크
    # ══════════════════════════════════════════════════════
    if stock_info and (stock_info.get("섹터") or stock_info.get("업종") or sector_benchmark):
        st.markdown("### 업종 분류 및 벤치마크")
        render_sector_section(stock_info, sector_benchmark or {})
        st.divider()

    # ══════════════════════════════════════════════════════
    # 5. 뉴스 검색 결과
    # ══════════════════════════════════════════════════════
    st.markdown("### 관련 뉴스")

    if not news_list:
        st.info("검색된 뉴스가 없습니다.")
    else:
        # ── 키워드 필터 ───────────────────────────────────
        keyword = st.text_input(
            "🔍 뉴스 키워드 필터",
            placeholder="제목에서 검색할 키워드를 입력하세요",
            key="news_filter"
        )

        df_news = pd.DataFrame([
            {
                "작성일": str(n.get("작성일") or n.get("pub_date", "")),
                "제목":   n.get("제목") or n.get("title", ""),
                "링크":   n.get("링크") or n.get("link", ""),
            }
            for n in news_list
        ])

        if keyword.strip():
            df_news = df_news[df_news["제목"].str.contains(keyword.strip(), case=False, na=False)]

        st.caption(f"{'필터 결과' if keyword.strip() else '총'} {len(df_news)}건"
                   + (f" / 전체 {len(news_list)}건" if keyword.strip() else ""))

        if df_news.empty:
            st.info("검색된 뉴스가 없습니다.")
        else:
            def make_link(url):
                if url:
                    return f'<a href="{url}" target="_blank">🔗 기사 보기</a>'
                return ""

            df_news["링크"] = df_news["링크"].apply(make_link)
            st.write(
                df_news.to_html(escape=False, index=False),
                unsafe_allow_html=True,
            )
