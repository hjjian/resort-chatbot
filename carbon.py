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
def _get_workbook():
    """Streamlit secrets로 Google Sheets 워크북 연결. 실패하면 None 반환."""
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
        return gc.open_by_key(sheet_id)
    except Exception:
        return None


def _get_sheet():
    """usage_log 워크시트 반환."""
    try:
        import gspread
        sh = _get_workbook()
        if not sh:
            return None
        try:
            return sh.worksheet("usage_log")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title="usage_log", rows=10000, cols=10)
            ws.append_row([
                "timestamp", "nickname", "user_input", "matched_item_id",
                "matched_by", "category", "final_result", "llm_used"
            ])
            return ws
    except Exception:
        return None


# ──────────────────────────────────────────────
# items 로드 (Google Sheets → 로컬 fallback)
# ──────────────────────────────────────────────
def load_items_from_sheets(local_path: str = None) -> list:
    """
    Google Sheets의 'items' 시트에서 품목 데이터를 로드.
    실패하면 로컬 items.json 사용.

    Sheets 컬럼 구조:
    id | name | category | keywords | skip_questions | steps | note
    (keywords, skip_questions, steps는 쉼표/파이프로 구분된 문자열)
    """
    try:
        import gspread
        sh = _get_workbook()
        if sh:
            try:
                ws = sh.worksheet("items")
            except gspread.WorksheetNotFound:
                # items 시트가 없으면 생성 + 헤더 추가
                ws = sh.add_worksheet(title="items", rows=1000, cols=10)
                ws.append_row([
                    "id", "name", "category", "keywords",
                    "skip_questions", "steps", "note"
                ])
                ws = None  # 새로 만든 빈 시트면 로컬 fallback 사용
            if ws:
                records = ws.get_all_records()
                if records:
                    # 카테고리별 자동 id 생성용 카운터
                    cat_prefix_map = {
                        "스티로폼": "styro", "유리": "glass", "금속·캔": "metal",
                        "플라스틱": "plastic", "종이·종이팩": "paper", "비닐": "vinyl",
                        "전자제품": "elec", "폐의약품": "medi", "기타": "etc"
                    }
                    cat_counter = {}
                    items = []
                    for row in records:
                        category = str(row.get("category", "")).strip()
                        item_id = str(row.get("id", "")).strip()

                        # id가 비어있으면 자동 생성
                        if not item_id:
                            prefix = cat_prefix_map.get(category, "item")
                            cat_counter[prefix] = cat_counter.get(prefix, 0) + 1
                            item_id = f"{prefix}_{cat_counter[prefix]:03d}"
                        
                        items.append({
                            "id":              item_id,
                            "name":            str(row.get("name", "")).strip(),
                            "category":        category,
                            "keywords":        [k.strip() for k in str(row.get("keywords", "")).split(",") if k.strip()],
                            "skip_questions":  [s.strip() for s in str(row.get("skip_questions", "")).split(",") if s.strip()],
                            "extra_questions": None,
                            "steps":           [s.strip() for s in str(row.get("steps", "")).split("|") if s.strip()],
                            "note":            str(row.get("note", "")).strip(),
                        })
                    return items
    except Exception:
        pass

    # 로컬 fallback
    if local_path is None:
        local_path = Path(__file__).parent / "data" / "items.json"
    try:
        import json as _json
        with open(local_path, encoding="utf-8") as f:
            return _json.load(f)["items"]
    except Exception:
        return []


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
                entry.get("nickname", ""),
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
