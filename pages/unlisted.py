# pages/unlisted.py
# 일반 비상장사 — 입력 + 결과 페이지
import os
import streamlit as st
from datetime import date, timedelta

from pdf_parser import parse_pdfs_and_store, fetch_and_store_news, get_corp_name, get_fiscal_year
from chart      import build_performance_chart

import pdfplumber


def _validate(corp_name, uploaded_files, items, news_start, news_end) -> list[str]:
    errors = []
    if not corp_name or corp_name == "회사명 입력":
        errors.append("분석 대상 회사명을 입력해주세요.")
    if not uploaded_files:
        errors.append("재무제표 PDF 파일을 1개 이상 선택해주세요.")
    if not items:
        errors.append("검색할 재무 항목을 입력해주세요.")
    if news_start > news_end:
        errors.append("이슈 검색 기간: 시작일이 종료일보다 늦습니다.")
    return errors


def render():
    # ── 뒤로가기 ──────────────────────────────────────────
    if st.button("← 처음으로", key="unlisted_back"):
        st.session_state.page = "home"
        st.rerun()

    st.markdown("## 📄 일반 비상장사 분석")
    st.divider()

    # ── 회사명 ────────────────────────────────────────────
    st.markdown("### 분석 대상 회사명")
    corp_name = st.text_input("", placeholder="분석할 회사명을 입력하세요",
                               label_visibility="collapsed", key="unlisted_corp")

    st.divider()

    # ── PDF 업로드 ────────────────────────────────────────
    st.markdown("### 📎 재무제표 PDF 선택")
    st.caption("※ 연도별로 분리된 PDF를 여러 개 선택할 수 있습니다. 파일명에 [회사명]을 포함하면 자동으로 인식됩니다.")
    uploaded_files = st.file_uploader(
        "PDF 파일 선택 (복수 선택 가능)",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key="unlisted_pdf",
    )
    if uploaded_files:
        st.success(f"{len(uploaded_files)}개 파일이 선택되었습니다.")
        for f in uploaded_files:
            st.caption(f"• {f.name}")

    st.divider()

    # ── 재무 데이터 검색 ──────────────────────────────────
    st.markdown("### 📂 재무데이터 검색")
    items_raw = st.text_input("검색 항목 (쉼표로 구분)", value="매출액, 영업이익",
                              key="unlisted_items")
    st.caption("※ 그래프 생성을 위해 매출액과 영업이익은 필수 항목입니다.")

    st.divider()

    # ── 이슈 검색 ─────────────────────────────────────────
    st.markdown("### 📰 이슈 검색")
    st.caption("※ 최대 1,000개의 뉴스가 저장됩니다.")

    col_ns, col_ne = st.columns(2)
    with col_ns:
        news_start = st.date_input("시작일", value=date.today() - timedelta(days=90),
                                   key="unlisted_ns")
    with col_ne:
        news_end   = st.date_input("종료일", value=date.today(),
                                   key="unlisted_ne")

    st.divider()

    # ── 실행 버튼 ─────────────────────────────────────────
    if st.button("🔍 분석 실행", type="primary", use_container_width=True, key="unlisted_run"):
        items  = [i.strip() for i in items_raw.split(",") if i.strip()]
        errors = _validate(corp_name, uploaded_files, items, news_start, news_end)

        if errors:
            for e in errors:
                st.error(e)
            return

        # ── 업로드된 PDF를 임시 파일로 저장 후 파싱 ─────────
        import tempfile, os

        tmp_paths  = []
        final_name = corp_name  # 사용자 입력 회사명 우선

        with st.spinner(f"PDF {len(uploaded_files)}개 분석 중..."):
            with tempfile.TemporaryDirectory() as tmpdir:
                for uf in uploaded_files:
                    tmp_path = os.path.join(tmpdir, uf.name)
                    with open(tmp_path, "wb") as fp:
                        fp.write(uf.read())
                    tmp_paths.append(tmp_path)

                data_by_item = parse_pdfs_and_store(
                    final_name, tmp_paths, items
                )

        with st.spinner("뉴스 수집 중..."):
            news_list = fetch_and_store_news(final_name, news_start, news_end)

        st.session_state.result = {
            "corp_name":    final_name,
            "data_by_item": data_by_item,
            "items":        items,
            "news_list":    news_list,
            "source":       "pdf",
        }
        st.session_state.page = "result"
        st.rerun()
