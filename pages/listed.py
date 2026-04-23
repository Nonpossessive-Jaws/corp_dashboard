# pages/listed.py
# 상장사 및 주요 비상장사 — 입력 + 결과 페이지
import streamlit as st
import pandas as pd
from datetime import date, timedelta

from dart_api import get_corp_code, fetch_and_store_financials, fetch_and_store_news
from db      import query_financial, query_news
from chart   import build_performance_chart


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


def fetch_stock_info(corp_name: str) -> dict | None:
    try:
        import FinanceDataReader as fdr
        import yfinance as yf
        from datetime import datetime

        df_krx = fdr.StockListing('KRX')
        exact  = df_krx[df_krx['Name'] == corp_name]
        target = exact if not exact.empty else df_krx[df_krx['Name'].str.contains(corp_name, na=False)]

        if target.empty:
            return None

        row    = target.iloc[0]
        symbol = row['Code']
        market = row['Market']
        name   = row['Name']

        industry = None
        sector   = None
        for col in df_krx.columns:
            cl = col.strip().lower()
            if cl in ("industry", "industrycode", "업종"):
                industry = str(row[col]) if pd.notna(row[col]) else None
            if cl in ("sector", "sectorcode", "섹터"):
                sector = str(row[col]) if pd.notna(row[col]) else None

        suffix = ".KS" if market == "KOSPI" else ".KQ"
        ticker = f"{symbol}{suffix}"

        stock = yf.Ticker(ticker)
        info  = stock.info

        if not sector:
            sector   = info.get("sector")
        if not industry:
            industry = info.get("industry")

        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        if current_price is None:
            return None

        prev_close = info.get("previousClose")
        change     = current_price - prev_close if prev_close else None
        change_pct = (change / prev_close * 100) if (prev_close and change is not None) else None

        return {
            "종목명":   name,
            "종목코드": symbol,
            "시장":     market,
            "섹터":     sector,
            "업종":     industry,
            "현재가":   current_price,
            "전일종가": prev_close,
            "등락":     change,
            "등락률":   change_pct,
            "시가":     info.get("open"),
            "고가":     info.get("dayHigh"),
            "저가":     info.get("dayLow"),
            "거래량":   info.get("volume"),
            "시가총액": info.get("marketCap"),
            "ticker":   ticker,
            "조회시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception:
        return None


def fetch_sector_benchmark(ticker: str, industry: str | None) -> dict | None:
    try:
        import FinanceDataReader as fdr
        import yfinance as yf

        if not industry:
            return None

        df_krx = fdr.StockListing('KRX')

        industry_col = None
        for col in df_krx.columns:
            if col.strip().lower() in ("industry", "industrycode", "업종"):
                industry_col = col
                break
        if industry_col is None:
            return None

        peers = df_krx[df_krx[industry_col].astype(str) == str(industry)]
        if len(peers) < 2:
            return None

        sample = peers.head(10)
        oper_margins, pers, pbrs = [], [], []

        for _, r in sample.iterrows():
            sym = r['Code']
            mkt = r['Market']
            sfx = ".KS" if mkt == "KOSPI" else ".KQ"
            try:
                info = yf.Ticker(f"{sym}{sfx}").info
                om  = info.get("operatingMargins")
                per = info.get("trailingPE")
                pbr = info.get("priceToBook")
                if om  is not None: oper_margins.append(om * 100)
                if per is not None: pers.append(per)
                if pbr is not None: pbrs.append(pbr)
            except Exception:
                continue

        if not oper_margins:
            return None

        return {
            "업종명":         industry,
            "샘플수":         len(sample),
            "평균영업이익률": round(sum(oper_margins) / len(oper_margins), 2) if oper_margins else None,
            "평균PER":        round(sum(pers) / len(pers), 2) if pers else None,
            "평균PBR":        round(sum(pbrs) / len(pbrs), 2) if pbrs else None,
        }
    except Exception:
        return None


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

        with st.spinner("주가 정보 조회 중..."):
            stock_info = fetch_stock_info(corp_name)

        sector_benchmark = None
        if stock_info:
            with st.spinner("업종 벤치마크 데이터 조회 중..."):
                sector_benchmark = fetch_sector_benchmark(
                    stock_info.get("ticker", ""),
                    stock_info.get("업종")
                )

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
