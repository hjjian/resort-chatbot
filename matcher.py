"""
matcher.py — items.json keywords 기반 품목 매칭 로직

match_item(user_input, items) → 매칭된 item 딕셔너리 또는 None

매칭 우선순위:
  1. 완전 일치 (keyword == user_input)
  2. 키워드가 입력에 포함 (keyword in user_input)
  3. 입력이 키워드에 포함 (user_input in keyword)
  4. 형태소 단위 부분 일치 (공백 분리 토큰 교집합)
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


def _token_overlap(a: str, b: str) -> int:
    """두 문자열의 공백 분리 토큰 교집합 크기 반환."""
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    return len(tokens_a & tokens_b)


def match_item(user_input: str, items: list) -> dict | None:
    """
    user_input과 가장 잘 매칭되는 item을 반환. 없으면 None.

    반환값: item 딕셔너리 (matched_by 필드 추가)
      - matched_by: "exact" | "keyword_in_input" | "input_in_keyword" | "token_overlap"
    """
    normalized = _normalize(user_input)

    # 점수 기반 후보 수집: (score, priority, item, matched_by)
    candidates = []

    for item in items:
        best_score, best_priority, best_by = -1, 99, None

        for kw in item["keywords"]:
            kw_norm = _normalize(kw)

            # 1. 완전 일치
            if normalized == kw_norm:
                best_score, best_priority, best_by = 100, 0, "exact"
                break  # 완전 일치면 더 볼 필요 없음

            # 2. 키워드가 입력에 포함
            if kw_norm and kw_norm in normalized:
                score = 80 + len(kw_norm)
                if score > best_score:
                    best_score, best_priority, best_by = score, 1, "keyword_in_input"
                continue

            # 3. 입력이 키워드에 포함
            if normalized and normalized in kw_norm:
                score = 60 + len(normalized)
                if score > best_score:
                    best_score, best_priority, best_by = score, 2, "input_in_keyword"
                continue

            # 4. 토큰 겹침
            overlap = _token_overlap(normalized, kw_norm)
            if overlap > 0:
                score = overlap * 10
                if score > best_score:
                    best_score, best_priority, best_by = score, 3, "token_overlap"

        if best_score > 0:
            candidates.append((best_score, best_priority, item, best_by))

    if not candidates:
        return None

    # score 내림차순, priority 오름차순으로 정렬 후 최상위 반환
    candidates.sort(key=lambda x: (-x[0], x[1]))
    _, _, best_item, matched_by = candidates[0]

    result = dict(best_item)
    result["matched_by"] = matched_by
    return result


def match_item_from_file(user_input: str, items_path: str = None) -> dict | None:
    """파일에서 items를 로드해 매칭. 편의 함수."""
    items = load_items(items_path)
    return match_item(user_input, items)
