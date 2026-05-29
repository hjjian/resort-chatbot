"""
matcher.py — items 키워드 기반 품목 매칭 로직

match_item(user_input, items) → 매칭된 item 딕셔너리 또는 None

매칭 우선순위:
  1. 완전 일치 (keyword == user_input)
  2. 공백 제거 후 완전 일치 (compact_exact)

3순위 이하 전부 제거 — 오매칭 방지.
매칭 실패 시 hybrid_handler.infer_category()로 AI 추론.
"""

import json
import re
from pathlib import Path


def load_items(path: str = None) -> list:
    """items.json을 로드해 items 리스트 반환."""
    if path is None:
        path = Path(__file__).parent / "data" / "items.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)["items"]


def _normalize(text: str) -> str:
    """소문자 변환 + 특수문자 제거 + 공백 정규화."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s가-힣]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _compact(text: str) -> str:
    """정규화된 문자열에서 공백 제거."""
    return _normalize(text).replace(" ", "")


def match_item(user_input: str, items: list) -> dict | None:
    """
    user_input과 가장 잘 매칭되는 item을 반환. 없으면 None.

    반환값: item 딕셔너리 (matched_by 필드 추가)
      - matched_by: "exact" | "compact_exact"
    """
    normalized = _normalize(user_input)
    normalized_compact = _compact(user_input)

    candidates = []

    for item in items:
        best_score, best_priority, best_by = -1, 99, None

        for kw in item["keywords"]:
            kw_norm = _normalize(kw)
            kw_compact = _compact(kw)

            # 1. 완전 일치
            if normalized == kw_norm:
                best_score, best_priority, best_by = 100, 0, "exact"
                break

            # 1-1. 공백 제거 완전 일치
            if normalized_compact and normalized_compact == kw_compact:
                best_score, best_priority, best_by = 98, 0, "compact_exact"
                break

            # ※ 3순위 이하 전부 제거 (keyword_in_input 포함)
            #    오매칭 방지 — 매칭 실패 시 AI(infer_category)로 처리

        if best_score > 0:
            candidates.append((best_score, best_priority, item, best_by))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (-x[0], x[1]))
    _, _, best_item, matched_by = candidates[0]

    result = dict(best_item)
    result["matched_by"] = matched_by
    return result


def match_item_from_file(user_input: str, items_path: str = None) -> dict | None:
    """파일에서 items를 로드해 매칭. 편의 함수."""
    items = load_items(items_path)
    return match_item(user_input, items)
