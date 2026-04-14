# pages/result.py
# 결과 페이지: 재무 테이블 + 차트 + 뉴스
import streamlit as st
import pandas as pd

from chart import build_performance_chart


def render():
    r          = st.session_state.get("result", {})
    corp_name  = r.get("corp_name", "")
    data_dict  = r.get("data_by_item", {})
    items      = r.get("items", [])
    news_list  = r.get("news_list", [])

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
        # 연도 × 항목 피벗 테이블 구성
        rows = {}
        for item, records in data_dict.items():
            for rec in records:
                yr  = rec["year"]
                amt = rec["amount"]
                if yr not in rows:
                    rows[yr] = {"연도": yr}
                # 억원 단위로 표시
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
    # 3. 뉴스 검색 결과
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

        # 링크를 클릭 가능한 HTML로 렌더링
        def make_link(url):
            if url:
                return f'<a href="{url}" target="_blank">🔗 기사 보기</a>'
            return ""

        df_news["링크"] = df_news["링크"].apply(make_link)
        st.write(
            df_news.to_html(escape=False, index=False),
            unsafe_allow_html=True,
        )
