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
    id | name | category | keywords | skip_questions | result | steps | note
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
                    "skip_questions", "result", "steps", "note"
                ])
                ws = None  # 새로 만든 빈 시트면 로컬 fallback 사용
            if ws:
                records = ws.get_all_records()
                if records:
                    # 카테고리별 자동 id 생성용 카운터
                    cat_prefix_map = {
                        "스티로폼": "styro", "유리": "glass", "금속·캔": "metal",
                        "플라스틱": "plastic", "종이·종이팩": "paper", "비닐": "vinyl",
                        "전자제품 및 완충재": "elec", "폐의약품": "medi", "기타": "etc",
                        "일반쓰레기": "trash",
                    }
                    # 이미 존재하는 id 목록 수집 (중복 방지)
                    existing_ids = {
                        str(r.get("id", "")).strip()
                        for r in records
                        if str(r.get("id", "")).strip()
                    }
                    cat_counter = {}
                    items = []
                    rows_to_update = []  # (sheet_row_index, new_id)

                    for i, row in enumerate(records):
                        category = str(row.get("category", "")).strip()
                        item_id = str(row.get("id", "")).strip()

                        # id가 비어있으면 자동 생성 후 Sheets에 다시 쓸 목록에 추가
                        if not item_id:
                            prefix = cat_prefix_map.get(category, "item")
                            cat_counter[prefix] = cat_counter.get(prefix, 0) + 1
                            candidate = f"{prefix}_{cat_counter[prefix]:03d}"
                            # 기존 id와 충돌하면 번호 증가
                            while candidate in existing_ids:
                                cat_counter[prefix] += 1
                                candidate = f"{prefix}_{cat_counter[prefix]:03d}"
                            item_id = candidate
                            existing_ids.add(item_id)
                            rows_to_update.append((i + 2, item_id))  # +2: 헤더행 + 0-index 보정

                        # keywords 또는 key_words 컬럼 둘 다 지원
                        keywords_raw = str(row.get("keywords") or row.get("key_words") or "").strip()
                        items.append({
                            "id":              item_id,
                            "name":            str(row.get("name", "")).strip(),
                            "category":        category,
                            "keywords":        [k.strip() for k in keywords_raw.split(",") if k.strip()],
                            "skip_questions":  [s.strip() for s in str(row.get("skip_questions", "")).split(",") if s.strip()],
                            "extra_questions": None,
                            "result":          str(row.get("result", "")).strip(),
                            "steps":           [s.strip() for s in str(row.get("steps", "")).split("|") if s.strip()],
                            "note":            str(row.get("note", "")).strip(),
                        })

                    # 비어있던 id 셀들을 Sheets A열에 일괄 업데이트
                    if rows_to_update:
                        try:
                            ws.batch_update([{
                                "range": f"A{row_idx}",
                                "values": [[new_id]]
                            } for row_idx, new_id in rows_to_update])
                        except Exception:
                            pass  # 쓰기 실패해도 로드는 정상 반환

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
# 인증 시트 (구글폼 응답) 연동
# ──────────────────────────────────────────────
def _get_cert_sheet():
    """GSHEET_FORM_ID로 폼 응답 워크시트 반환."""
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
        sheet_id = st.secrets.get("GSHEET_FORM_ID", "")
        if not sheet_id:
            return None
        return gc.open_by_key(sheet_id).get_worksheet(0)
    except Exception:
        return None


def load_cert_log() -> list:
    """
    구글폼 인증 응답 로드.
    반환값: [{"nickname": str, ...}, ...] — 닉네임 키로 정규화된 레코드 목록.
    """
    ws = _get_cert_sheet()
    if not ws:
        return []
    try:
        records = ws.get_all_records()
        result = []
        for row in records:
            # '닉네임'으로 시작하는 컬럼을 닉네임으로 사용
            nickname = ""
            for key, val in row.items():
                if str(key).startswith("닉네임"):
                    nickname = str(val).strip()
                    break
            result.append({**row, "nickname": nickname})
        return result
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
# usage_log 마지막 행 llm_used 업데이트
# ──────────────────────────────────────────────
def update_last_llm_used(value: bool) -> None:
    """
    Google Sheets usage_log의 마지막 행 H열(llm_used)을 업데이트.
    render_result()에서 AI 생성 성공 여부 확정 후 호출.
    """
    ws = _get_sheet()
    if ws:
        try:
            last_row = len(ws.get_all_values())  # 헤더 포함 전체 행 수
            if last_row >= 2:  # 헤더 제외 데이터 1행 이상
                ws.update_cell(last_row, 8, str(value))  # H열 = 8번째
            return
        except Exception:
            pass

    # 로컬 fallback
    try:
        path = Path(__file__).parent / "data" / "usage_log.json"
        with open(path, encoding="utf-8") as f:
            log = json.load(f)
        if log:
            log[-1]["llm_used"] = value
            with open(path, "w", encoding="utf-8") as f:
                json.dump(log, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


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
    if value < 1.0:
        return f"{value:.2f} kg"
    return f"{value:,.2f} kg"
