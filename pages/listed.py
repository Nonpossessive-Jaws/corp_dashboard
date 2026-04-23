# pages/listed.py
# 상장사 및 주요 비상장사 — 입력 + 결과 페이지
import streamlit as st
import pandas as pd
from datetime import date, timedelta

from dart_api import (get_corp_code, fetch_and_store_financials,
                      fetch_and_store_news, fetch_stock_info,
                      fetch_sector_benchmark)
from db    import query_financial, query_news
from chart import build_performance_chart


def _validate(corp_name, items, dart_start, dart_end, news_start, news_end) -> list[str]:
    errors = []
    if not corp_name or corp_name == "회사명 입력":
        errors.append("분석 대상 회사명을 입력해주세요.")
    if not items:
        errors.append("검색할 재무 항목을 입력해주세요.")
    if dart_start > dart_end:
        errors.append("재무데이터 검색 기간: 시작일이 종료일보다 늦습니다.")
    if news_start > news_end:
        errors.append("이슈 검색 기간: 시작일이 종료일보다 늦습니다.")
    return errors


def render():
    # ── 뒤로가기 ──────────────────────────────────────────
    if st.button("← 처음으로", key="listed_back"):
        st.session_state.page = "home"
        st.rerun()

    st.markdown("## 📊 상장사 및 주요 비상장사 분석")
    st.divider()

    # ── 회사명 ────────────────────────────────────────────
    st.markdown("### 분석 대상 회사명")
    corp_name = st.text_input("", placeholder="DART 등록 회사명을 정확히 입력하세요",
                               label_visibility="collapsed", key="listed_corp")
    st.caption("※ DART 상의 회사명을 정확히 기입해주세요.")

    st.divider()

    # ── 재무 데이터 검색 ──────────────────────────────────
    st.markdown("### 📂 재무데이터 검색")

    col_s, col_e = st.columns(2)
    with col_s:
        dart_start = st.date_input("시작일", value=date.today().replace(year=date.today().year - 3),
                                   key="listed_ds")
    with col_e:
        dart_end   = st.date_input("종료일", value=date.today(),
                                   key="listed_de")

    fs_div = st.radio("재무제표 유형", ["연결 (CFS)", "개별 (OFS)", "모두"],
                      horizontal=True, key="listed_fsdiv")
    fs_map = {"연결 (CFS)": "CFS", "개별 (OFS)": "OFS", "모두": "ALL"}

    items_raw = st.text_input("검색 항목 (쉼표로 구분)", value="매출액, 영업이익",
                              key="listed_items")
    st.caption("※ 그래프 생성을 위해 매출액과 영업이익은 필수 항목입니다.")

    st.divider()

    # ── 이슈 검색 ─────────────────────────────────────────
    st.markdown("### 📰 이슈 검색")
    st.caption("※ 최대 1,000개의 뉴스가 저장됩니다.")

    col_ns, col_ne = st.columns(2)
    with col_ns:
        news_start = st.date_input("시작일 ", value=date.today() - timedelta(days=90),
                                   key="listed_ns")
    with col_ne:
        news_end   = st.date_input("종료일 ", value=date.today(),
                                   key="listed_ne")

    st.divider()

    # ── 실행 버튼 ─────────────────────────────────────────
    if st.button("🔍 분석 실행", type="primary", use_container_width=True, key="listed_run"):
        items  = [i.strip() for i in items_raw.split(",") if i.strip()]
        errors = _validate(corp_name, items, dart_start, dart_end, news_start, news_end)

        if errors:
            for e in errors:
                st.error(e)
            return

        # ── 데이터 수집 ───────────────────────────────────
        with st.spinner("DART에서 기업 코드 조회 중..."):
            corp_code = get_corp_code(corp_name)
        if not corp_code:
            st.error(f"'{corp_name}' 기업을 DART에서 찾을 수 없습니다. 회사명을 확인해주세요.")
            return

        years = range(dart_start.year, dart_end.year + 1)
        with st.spinner(f"재무 데이터 수집 중... (총 {len(list(years))}개 연도 × {len(items)}개 항목)"):
            data_by_item = fetch_and_store_financials(
                corp_name, corp_code, years, items, fs_map[fs_div]
            )

        with st.spinner("뉴스 수집 중..."):
            news_list = fetch_and_store_news(corp_name, news_start, news_end)

        # ── 주가 정보 수집 ────────────────────────────────
        with st.spinner("주가 정보 조회 중..."):
            stock_info = fetch_stock_info(corp_name)

        # ── 업종 벤치마크 수집 ────────────────────────────
        sector_benchmark = None
        if stock_info:
            with st.spinner("업종 벤치마크 데이터 조회 중..."):
                sector_benchmark = fetch_sector_benchmark(
                    stock_info.get("ticker", ""),
                    stock_info.get("업종")
                )

        # 결과를 session_state에 저장 후 결과 페이지로 전환
        st.session_state.result = {
            "corp_name":        corp_name,
            "data_by_item":     data_by_item,
            "items":            items,
            "news_list":        news_list,
            "source":           "dart",
            "stock_info":       stock_info,
            "sector_benchmark": sector_benchmark,
        }
        st.session_state.page = "result"
        st.rerun()
