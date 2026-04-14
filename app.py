# app.py  ←  실행 파일: streamlit run app.py
import streamlit as st
from db import init_db

# ── 페이지 기본 설정 ───────────────────────────────────
st.set_page_config(
    page_title="기업 분석 대시보드",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── 전역 스타일 ───────────────────────────────────────
st.markdown("""
<style>
/* 구글 폰트 */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=Bebas+Neue&display=swap');

/* 배경 및 기본 타이포 */
html, body, [data-testid="stAppViewContainer"] {
    background: #F7F8FA;
    font-family: 'Noto Sans KR', sans-serif;
}

/* 헤더 숨김 */
[data-testid="stHeader"] { display: none; }

/* 홈 히어로 영역 */
.hero-wrap {
    text-align: center;
    padding: 72px 0 48px;
}
.hero-badge {
    display: inline-block;
    background: #2C3E50;
    color: #1ABC9C;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 3px;
    text-transform: uppercase;
    padding: 5px 16px;
    border-radius: 20px;
    margin-bottom: 28px;
}
.hero-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 64px;
    line-height: 1.1;
    color: #2C3E50;
    letter-spacing: 2px;
    margin: 0 0 16px;
}
.hero-title span { color: #1ABC9C; }
.hero-sub {
    font-size: 15px;
    color: #7F8C8D;
    font-weight: 300;
    margin-bottom: 52px;
}

/* 선택 카드 */
.card-row {
    display: flex;
    gap: 20px;
    justify-content: center;
    flex-wrap: wrap;
    margin-bottom: 56px;
}
.type-card {
    background: #FFFFFF;
    border: 2px solid #E8EAED;
    border-radius: 16px;
    padding: 36px 32px;
    width: 220px;
    height: 260px;
    cursor: pointer;
    transition: all .2s ease;
    text-align: center;
    text-decoration: none;
}
.type-card:hover {
    border-color: #1ABC9C;
    box-shadow: 0 8px 28px rgba(26,188,156,.15);
    transform: translateY(-3px);
}
.type-card .icon {
    font-size: 38px;
    margin-bottom: 14px;
}
.type-card .label {
    font-size: 15px;
    font-weight: 700;
    color: #2C3E50;
    margin-bottom: 8px;
}
.type-card .desc {
    font-size: 12px;
    color: #95A5A6;
    line-height: 1.6;
}

/* 구분선 텍스트 */
.divider-text {
    text-align: center;
    color: #BDC3C7;
    font-size: 12px;
    letter-spacing: 2px;
    margin-bottom: 48px;
}

/* 섹션 제목 */
h2, h3 { font-family: 'Noto Sans KR', sans-serif !important; }

/* primary 버튼 */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #2C3E50 !important;
    color: white !important;
    border: none !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    height: 52px !important;
    border-radius: 10px !important;
    letter-spacing: 1px;
    transition: background .2s;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #1ABC9C !important;
}

/* 일반 버튼 (뒤로가기 등) */
div[data-testid="stButton"] > button {
    border-radius: 8px !important;
}

/* 입력 필드 */
input[type="text"], textarea {
    border-radius: 8px !important;
}

/* 라디오 가로 배치 간격 */
div[data-testid="stRadio"] > div { gap: 24px; }

/* 구분선 */
hr { border-color: #E8EAED !important; }

/* 테이블 */
table { font-size: 13px !important; }
th { background: #2C3E50 !important; color: white !important; }
td a { color: #1ABC9C !important; }
</style>
""", unsafe_allow_html=True)

# ── DB 초기화 ─────────────────────────────────────────
init_db()

# ── session_state 초기화 ──────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "home"


# ══════════════════════════════════════════════════════
# 홈 화면
# ══════════════════════════════════════════════════════
def render_home():
    st.markdown("""
    <div class="hero-wrap">
        <div class="hero-badge">CORP ANALYTICS PLATFORM</div>
        <div class="hero-title">기업 분석<br><span>대시보드</span></div>
        <div class="hero-sub">DART API 및 재무제표 PDF 기반의 기업 재무 분석 및 이슈 모니터링</div>
    </div>
    <div class="divider-text">— 검색할 기업 유형을 선택하세요 —</div>
    """, unsafe_allow_html=True)

    col1, col_gap, col2 = st.columns([5, 1, 5])

    with col1:
        st.markdown("""
        <div class="type-card" style="pointer-events:none; margin: 0 auto;">
            <div class="icon">🏢</div>
            <div class="label">상장사 및<br>주요 비상장사</div>
            <div class="desc">DART API를 통해<br>재무 데이터를 자동 수집합니다</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("선택", key="btn_listed", use_container_width=True, type="primary"):
            st.session_state.page = "listed"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="type-card" style="pointer-events:none; margin: 0 auto;">
            <div class="icon">📄</div>
            <div class="label">일반 비상장사</div>
            <div class="desc">재무제표 PDF를 직접 업로드해<br>데이터를 추출합니다</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("선택", key="btn_unlisted", use_container_width=True, type="primary"):
            st.session_state.page = "unlisted"
            st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align:center; color:#BDC3C7; font-size:12px;'>
        Powered by DART API · 네이버 뉴스 API · pdfplumber · SQLite
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# 라우팅
# ══════════════════════════════════════════════════════
page = st.session_state.page

if page == "home":
    render_home()

elif page == "listed":
    from pages.listed import render
    render()

elif page == "unlisted":
    from pages.unlisted import render
    render()

elif page == "result":
    from pages.result import render
    render()

else:
    st.session_state.page = "home"
    st.rerun()
