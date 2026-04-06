"""
carbon.py — 탄소절감량 계산 로직

get_today_carbon(usage_log, carbon_factors) → float
  오늘 날짜(00:00~현재)의 usage_log 항목에서
  카테고리별 carbon_factors를 합산해 반환.
"""

import json
from datetime import date
from pathlib import Path


def load_carbon_factors(path: str = None) -> dict:
    """carbon_factors.json을 로드해 반환."""
    if path is None:
        path = Path(__file__).parent / "data" / "carbon_factors.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_usage_log(path: str = None) -> list:
    """usage_log.json을 로드해 반환. 파일이 없거나 비어있으면 빈 리스트."""
    if path is None:
        path = Path(__file__).parent / "data" / "usage_log.json"
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_usage_log(log: list, path: str = None) -> None:
    """usage_log 리스트를 usage_log.json에 저장."""
    if path is None:
        path = Path(__file__).parent / "data" / "usage_log.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def get_today_carbon(usage_log: list, carbon_factors: dict) -> float:
    """
    오늘 날짜(00:00~현재) usage_log 항목의 탄소절감량 합산.
    carbon_factors가 모두 0.0이면 0.0 반환.
    """
    today = date.today().isoformat()  # "2025-04-06"
    total = 0.0
    for entry in usage_log:
        if entry.get("timestamp", "").startswith(today):
            category = entry.get("category", "기타")
            factor = carbon_factors.get(category, 0.0)
            total += factor
    return round(total, 2)


def is_carbon_data_ready(carbon_factors: dict) -> bool:
    """carbon_factors 값이 하나라도 0보다 크면 True."""
    return any(v > 0 for v in carbon_factors.values())


def format_carbon(value: float) -> str:
    """
    탄소절감량을 화면 표시용 문자열로 변환.
    - 데이터 미준비(0.0) → "집계 중..."
    - 준비됨 → "2,481 kg" 형식 (천 단위 쉼표, 소수점 없음)
    """
    if value == 0.0:
        return "집계 중..."
    return f"{int(value):,} kg"
