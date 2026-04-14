# pdf_parser.py
# PDF 재무제표 파싱 및 DB 저장
import re
import datetime

import pdfplumber

from db import upsert_financial, insert_news_bulk
import urllib.parse
import urllib.request
import json


NAVER_CLIENT_ID     = "qZRwJ1zWGto1ylH5LDYg"
NAVER_CLIENT_SECRET = "T4zb9qc9JE"


# ==========================================
# 텍스트·숫자 정규화
# ==========================================
def refine_item_name(text: str) -> str:
    """계정 항목명 정규화: 괄호·번호 제거 후 공백 제거"""
    if not text:
        return ""
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'^[IVXLCDM]+\s*[\.\-]?\s*', '', text)
    text = re.sub(r'^[\d\.]+\s*', '', text)
    return text.replace(" ", "").replace("\n", "").strip()


def clean_number(text) -> int:
    """재무제표 숫자 문자열 → 정수 변환. 괄호 = 음수."""
    if text is None:
        return 0
    try:
        cleaned = (str(text).replace(',', '').replace(' ', '')
                             .replace('(', '-').replace(')', ''))
        match = re.search(r'[-+]?\d*\.?\d+', cleaned)
        return int(float(match.group())) if match else 0
    except Exception:
        return 0


# ==========================================
# 기업명 / 사업연도 추출
# ==========================================
def get_corp_name(pdf, filename: str) -> str:
    """파일명 [기업명] 우선, 없으면 첫 페이지 텍스트에서 추출"""
    match = re.search(r'\[(.*?)\]', filename)
    if match:
        return match.group(1).strip()
    try:
        text = pdf.pages[0].extract_text() or ""
        for pattern in [
            r'([가-힣\w]+)\s?(?:주식회사|\(주\))',
            r'(?:주식회사|\(주\))\s?([가-힣\w]+)',
        ]:
            m = re.search(pattern, text)
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return "알수없음"


def get_fiscal_year(pdf) -> int:
    """사업연도 추출: 사업연도/제N기 맥락 우선, 폴백은 첫 연도 숫자"""
    priority_patterns = [
        r'사업연도[^\d]*(\d{4})',
        r'제\s*\d+\s*기[^\d]*(\d{4})',
    ]
    fallback = None
    try:
        for i in range(min(2, len(pdf.pages))):
            text = pdf.pages[i].extract_text() or ""
            for pat in priority_patterns:
                m = re.search(pat, text)
                if m:
                    return int(m.group(1))
            if fallback is None:
                m = re.search(r'(\d{4})년', text)
                if m:
                    fallback = int(m.group(1))
    except Exception:
        pass
    return fallback or datetime.datetime.now().year


# ==========================================
# PDF 파싱 메인
# ==========================================
def parse_pdfs_and_store(corp_name: str, file_paths: list[str],
                          target_items: list[str]) -> dict[str, list]:
    """
    PDF 파일 목록을 파싱해 DB에 저장하고 표시용 dict 반환.
    반환값: {item_name: [{"year": int, "amount": float}, ...]}
    """
    data_by_item: dict[str, list] = {kw: [] for kw in target_items}

    for path in file_paths:
        import os
        filename = os.path.basename(path)
        with pdfplumber.open(path) as pdf:
            year = get_fiscal_year(pdf)
            for kw in target_items:
                found = False
                for page in pdf.pages:
                    if found:
                        break
                    tables = page.extract_tables()
                    if not tables:
                        continue
                    for table in tables:
                        if found:
                            break
                        for row in table:
                            if not row or not row[0]:
                                continue
                            if kw.replace(" ", "") in refine_item_name(row[0]):
                                nums = [clean_number(c) for c in row[1:]
                                        if clean_number(c) != 0]
                                if nums:
                                    amount = float(nums[0])
                                    upsert_financial(corp_name, "pdf",
                                                     None, year, kw, amount)
                                    data_by_item[kw].append(
                                        {"year": year, "amount": amount}
                                    )
                                    found = True
                                    break

    return data_by_item


# ==========================================
# 네이버 뉴스 (비상장사용 — dart_api.py와 동일 로직)
# ==========================================
def fetch_and_store_news(corp_name: str, s_date, e_date) -> list[dict]:
    results = []
    for start in range(1, 1001, 100):
        url = (
            "https://openapi.naver.com/v1/search/news.json"
            f"?query={urllib.parse.quote(corp_name)}"
            f"&display=100&start={start}&sort=date"
        )
        req = urllib.request.Request(url)
        req.add_header("X-Naver-Client-Id",     NAVER_CLIENT_ID)
        req.add_header("X-Naver-Client-Secret",  NAVER_CLIENT_SECRET)
        try:
            with urllib.request.urlopen(req) as res:
                data = json.loads(res.read().decode("utf-8"))
                for item in data.get("items", []):
                    from datetime import datetime as _dt
                    p_date = _dt.strptime(
                        item["pubDate"], "%a, %d %b %Y %H:%M:%S +0900"
                    ).date()
                    if s_date <= p_date <= e_date:
                        title = (item["title"]
                                 .replace("<b>", "").replace("</b>", "")
                                 .replace("&quot;", '"'))
                        results.append({
                            "작성일": p_date,
                            "제목":   title,
                            "링크":   item.get("originallink") or item.get("link"),
                        })
                    elif p_date < s_date:
                        insert_news_bulk(corp_name, results)
                        return results
        except Exception:
            break

    insert_news_bulk(corp_name, results)
    return results
