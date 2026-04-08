"""
carbon.py — 탄소절감량 계산 + usage_log (Google Sheets 연동)

로컬 실행: data/usage_log.json 파일 사용
Streamlit Cloud: Google Sheets에 저장/로드
"""

import json
from datetime import date
from pathlib import Path

# ──────────────────────────────────────────────
# Google Sheets 연동 헬퍼
# ──────────────────────────────────────────────
def _get_sheet():
    """Streamlit secrets로 Google Sheets 연결. 실패하면 None 반환."""
    try:
        import streamlit as st
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
        gc = gspread.authorize(creds)
        sheet_id = st.secrets.get("GSHEET_ID", "")
        if not sheet_id:
            return None
        sh = gc.open_by_key(sheet_id)
        # "usage_log" 시트가 없으면 생성
        try:
            ws = sh.worksheet("usage_log")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title="usage_log", rows=10000, cols=10)
            ws.append_row([
                "timestamp", "user_input", "matched_item_id",
                "matched_by", "category", "final_result", "llm_used"
            ])
        return ws
    except Exception:
        return None


# ──────────────────────────────────────────────
# carbon_factors
# ──────────────────────────────────────────────
def load_carbon_factors(path: str = None) -> dict:
    """carbon_factors.json을 로드해 반환."""
    if path is None:
        path = Path(__file__).parent / "data" / "carbon_factors.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ──────────────────────────────────────────────
# usage_log 로드
# ──────────────────────────────────────────────
def load_usage_log(path: str = None) -> list:
    """
    Google Sheets에서 로드 시도.
    실패하면 로컬 usage_log.json 사용.
    """
    ws = _get_sheet()
    if ws:
        try:
            records = ws.get_all_records()
            return records
        except Exception:
            pass

    # 로컬 fallback
    if path is None:
        path = Path(__file__).parent / "data" / "usage_log.json"
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


# ──────────────────────────────────────────────
# usage_log 저장
# ──────────────────────────────────────────────
def save_usage_log(log: list, path: str = None) -> None:
    """
    마지막 항목만 Google Sheets에 append.
    실패하면 로컬 usage_log.json에 저장.
    """
    if not log:
        return

    ws = _get_sheet()
    if ws:
        try:
            entry = log[-1]  # 마지막 항목만 append
            ws.append_row([
                entry.get("timestamp", ""),
                entry.get("user_input", ""),
                entry.get("matched_item_id", ""),
                entry.get("matched_by", ""),
                entry.get("category", ""),
                entry.get("final_result", ""),
                str(entry.get("llm_used", False)),
            ])
            return
        except Exception:
            pass

    # 로컬 fallback
    if path is None:
        path = Path(__file__).parent / "data" / "usage_log.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────
# 탄소 계산
# ──────────────────────────────────────────────
def get_today_carbon(usage_log: list, carbon_factors: dict) -> float:
    today = date.today().isoformat()
    total = 0.0
    for entry in usage_log:
        if str(entry.get("timestamp", "")).startswith(today):
            category = entry.get("category", "기타")
            factor = carbon_factors.get(category, 0.0)
            total += factor
    return round(total, 2)


def is_carbon_data_ready(carbon_factors: dict) -> bool:
    return any(v > 0 for v in carbon_factors.values())


def format_carbon(value: float) -> str:
    if value == 0.0:
        return "집계 중..."
    return f"{int(value):,} kg"
