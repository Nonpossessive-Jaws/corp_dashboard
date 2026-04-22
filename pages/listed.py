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
    """
    KRX 종목 리스트에서 기업명으로 티커를 찾고,
    yfinance로 현재 주가 정보를 조회해 dict로 반환.
    조회 실패 시 None 반환. 디버그 로그는 session_state.stock_debug에 저장.
    """
    logs = []
    logs.append("① fetch_stock_info 호출됨")

    try:
        logs.append("② FinanceDataReader import 시도...")
        import FinanceDataReader as fdr
        logs.append("② FinanceDataReader import 성공")

        logs.append("③ yfinance import 시도...")
        import yfinance as yf
        logs.append("③ yfinance import 성공")

        from datetime import datetime

        logs.append("④ KRX 종목 리스트 조회 시도...")
        df_krx = fdr.StockListing('KRX')
        logs.append(f"④ KRX 조회 성공 | shape: {df_krx.shape} | 컬럼: {df_krx.columns.tolist()}")

        exact  = df_krx[df_krx['Name'] == corp_name]
        target = exact if not exact.empty else df_krx[df_krx['Name'].str.contains(corp_name, na=False)]
        logs.append(f"⑤ 종목 검색 결과: {len(target)}건 (입력명: '{corp_name}')")

        if target.empty:
            logs.append("⑤ 일치 종목 없음 → None 반환")
            st.session_state.stock_debug = logs
            return None

        row    = target.iloc[0]
        symbol = row['Code']
        market = row['Market']
        name   = row['Name']
        suffix = ".KS" if market == "KOSPI" else ".KQ"
        ticker = f"{symbol}{suffix}"
        logs.append(f"⑥ 종목 확정: {name} / {ticker} / {market}")

        logs.append("⑦ yfinance Ticker.info 조회 시도...")
        stock = yf.Ticker(ticker)
        info  = stock.info
        logs.append(f"⑦ info 키 수: {len(info)}개")

        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        logs.append(f"⑧ currentPrice: {info.get('currentPrice')} / regularMarketPrice: {info.get('regularMarketPrice')}")

        if current_price is None:
            logs.append("⑧ 현재가 없음 → None 반환")
            st.session_state.stock_debug = logs
            return None

        prev_close = info.get("previousClose")
        change     = current_price - prev_close if prev_close else None
        change_pct = (change / prev_close * 100) if (prev_close and change is not None) else None

        logs.append("⑨ 주가 데이터 수집 완료 ✅")
        st.session_state.stock_debug = logs

        return {
            "종목명":   name,
            "종목코드": symbol,
            "시장":     market,
            "현재가":   current_price,
            "전일종가": prev_close,
            "등락":     change,
            "등락률":   change_pct,
            "시가":     info.get("open"),
            "고가":     info.get("dayHigh"),
            "저가":     info.get("dayLow"),
            "거래량":   info.get("volume"),
            "시가총액": info.get("marketCap"),
            "조회시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    except Exception as e:
        import traceback
        logs.append(f"❌ 예외 발생: {e}")
        logs.append(f"❌ traceback:\n{traceback.format_exc()}")
        st.session_state.stock_debug = logs
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

        # ── 주가 정보 수집 (실패해도 결과 페이지는 정상 표시) ──
        with st.spinner("주가 정보 조회 중..."):
            stock_info = fetch_stock_info(corp_name)

        # 결과를 session_state에 저장 후 결과 페이지로 전환
        st.session_state.result = {
            "corp_name":    corp_name,
            "data_by_item": data_by_item,
            "items":        items,
            "news_list":    news_list,
            "source":       "dart",
            "stock_info":   stock_info,
            "stock_debug":  st.session_state.get("stock_debug", []),
        }
        st.session_state.page = "result"
        st.rerun()
