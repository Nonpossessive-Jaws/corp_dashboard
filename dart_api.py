# dart_api.py
# DART 재무 데이터 + 네이버 뉴스 API 수집
import io
import json
import zipfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

import requests
import pandas as pd
import streamlit as st

from db import upsert_financial, insert_news_bulk

# ==========================================
# 인증키 (Streamlit Secrets에서 로드)
# ==========================================
DART_API_KEY        = st.secrets["DART_API_KEY"]
NAVER_CLIENT_ID     = st.secrets["NAVER_CLIENT_ID"]
NAVER_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]


# ==========================================
# DART API
# ==========================================
def get_corp_code(corp_name: str) -> str | None:
    """DART 기업 고유번호 조회"""
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    res = requests.get(url, params={"crtfc_key": DART_API_KEY})
    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
        with z.open("CORPCODE.xml") as f:
            root = ET.parse(f).getroot()
            for node in root.findall("list"):
                if node.find("corp_name").text == corp_name:
                    return node.find("corp_code").text
    return None


def fetch_and_store_financials(corp_name: str, corp_code: str,
                               years: range, items: list[str],
                               fs_div: str) -> dict[str, list]:
    """
    DART에서 연도별 재무 항목을 수집해 DB에 저장하고,
    화면 표시용 dict도 반환.
    반환값: {item_name: [{"year": int, "amount": float, "fs_div": str}, ...]}
    """
    data_by_item: dict[str, list] = {name: [] for name in items}

    for item in items:
        for y in years:
            params = {
                "crtfc_key":  DART_API_KEY,
                "corp_code":  corp_code,
                "bsns_year":  str(y),
                "reprt_code": "11011",
            }
            res = requests.get(
                "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json",
                params=params
            ).json()
            if res.get("status") != "000":
                continue

            df = pd.DataFrame(res["list"])
            target = df[
                df["account_nm"].str.replace(" ", "").str.contains(
                    item.replace(" ", ""), na=False
                )
            ].copy()
            if fs_div != "ALL":
                target = target[target["fs_div"] == fs_div]
            if target.empty:
                continue

            row = target.iloc[0]
            amount = float(str(row["thstrm_amount"]).replace(",", "") or 0)
            div    = row["fs_div"]

            upsert_financial(corp_name, "dart", div, y, item, amount)
            data_by_item[item].append({"year": y, "amount": amount, "fs_div": div})

    return data_by_item


# ==========================================
# 네이버 뉴스 API
# ==========================================
def fetch_and_store_news(corp_name: str, s_date, e_date) -> list[dict]:
    """
    네이버 뉴스를 수집해 DB에 저장하고 리스트로 반환.
    """
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
                    p_date = datetime.strptime(
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
