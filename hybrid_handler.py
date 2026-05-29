"""
hybrid_handler.py

두 가지 AI 기능을 제공합니다:

1. infer_category(user_input, categories)
   키워드 매칭 실패 시 Gemini Flash로 카테고리 추론.
   반환: {"category": str, "confidence": "high"|"low"} 또는 None

2. generate_impact_note(matched_item, result_text, question_history, carbon_factor)
   결과 화면의 IMPACT NOTE를 Gemini Flash로 동적 생성.
   반환: str (실패 시 matched_item["note"] fallback)
"""

import re


# ──────────────────────────────────────────────
# 공통 헬퍼: Gemini API 키 로드
# ──────────────────────────────────────────────
def _get_api_key() -> str:
    try:
        import streamlit as st
        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        return ""


def _get_gemini_model():
    import google.generativeai as genai
    api_key = _get_api_key()
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")


# ──────────────────────────────────────────────
# 1. 카테고리 추론 (매칭 실패 fallback)
# ──────────────────────────────────────────────
CATEGORIES = [
    "스티로폼", "유리", "금속·캔", "비닐", "플라스틱",
    "종이·종이팩", "폐의약품", "전자제품 및 완충재", "기타",
]

def infer_category(user_input: str, categories: list = None) -> dict | None:
    """
    Gemini Flash로 user_input의 분리배출 카테고리를 추론.

    Returns
    -------
    {"category": str, "confidence": "high"|"low"} 또는 None (API 실패 시)
    """
    if categories is None:
        categories = CATEGORIES

    model = _get_gemini_model()
    if not model:
        return None

    category_list = "\n".join(f"- {c}" for c in categories)
    prompt = f"""당신은 한국 분리배출 전문가예요.
사용자가 입력한 품목이 아래 카테고리 중 어디에 해당하는지 판단해주세요.

[카테고리 목록]
{category_list}

[사용자 입력]
{user_input}

[응답 규칙]
- 반드시 위 카테고리 중 하나만 선택
- JSON만 반환, 다른 텍스트 없음
- confidence: 확신하면 "high", 애매하면 "low"
- 형식: {{"category": "카테고리명", "confidence": "high"}}"""

    try:
        import google.generativeai as genai
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=100,
                temperature=0.1,
            ),
        )
        text = response.text.strip()
        # 마크다운 코드블록 제거
        text = re.sub(r"```json|```", "", text).strip()
        import json
        result = json.loads(text)
        if result.get("category") in categories:
            return result
        return None
    except Exception:
        return None


# ──────────────────────────────────────────────
# 2. IMPACT NOTE 동적 생성
# ──────────────────────────────────────────────
def _carbon_analogy(carbon_kg: float) -> str:
    """탄소 절감량(kg)을 친근한 비유로 변환."""
    if carbon_kg <= 0:
        return ""
    if carbon_kg < 0.05:
        return f"약 {carbon_kg * 1000:.0f}g CO₂ — 스마트폰 완충 {int(carbon_kg / 0.008)}회에 해당하는 에너지를 아꼈어요."
    elif carbon_kg < 0.1:
        return f"약 {carbon_kg:.2f}kg CO₂ — 자동차로 약 {carbon_kg / 0.21 * 1000:.0f}m를 달릴 때 나오는 탄소량이에요."
    elif carbon_kg < 0.5:
        return f"약 {carbon_kg:.2f}kg CO₂ — 자동차로 약 {carbon_kg / 0.21:.1f}km를 달릴 때 나오는 탄소량이에요."
    else:
        return f"약 {carbon_kg:.2f}kg CO₂ — 나무 한 그루가 약 {int(carbon_kg / 0.02)}일 동안 흡수하는 탄소량이에요."


def _format_answer_path(question_history: list) -> str:
    """question_history를 'Q → 답변' 형태의 텍스트로 변환."""
    if not question_history:
        return "질문 없이 바로 결과 도출"
    lines = []
    for item in question_history:
        q = item.get("current_q", {})
        text = q.get("text", "")
        answer = item.get("answer")
        if text:
            answer_str = "예" if answer else "아니오"
            lines.append(f"- {text} → {answer_str}")
    return "\n".join(lines) if lines else "질문 경로 없음"


def generate_impact_note(
    matched_item: dict,
    result_text: str,
    question_history: list,
    carbon_factor: float = 0.0,
) -> str:
    """
    Gemini Flash로 IMPACT NOTE 생성.

    Parameters
    ----------
    matched_item      : items 매칭 항목 (name, category, note 등 포함)
    result_text       : 최종 결과 텍스트
    question_history  : 사용자가 답변한 질문 경로 리스트
    carbon_factor     : 카테고리별 탄소 절감 계수 (kg CO₂e)

    Returns
    -------
    str : AI 생성 IMPACT NOTE (실패 시 기존 note 반환)
    """
    fallback = matched_item.get("note", "") if matched_item else ""

    model = _get_gemini_model()
    if not model:
        return fallback

    is_recycled = "일반쓰레기" not in result_text
    carbon_text = _carbon_analogy(carbon_factor) if is_recycled else ""
    answer_path_text = _format_answer_path(question_history)

    if is_recycled:
        prompt = f"""당신은 분리배출 환경 교육 챗봇의 결과 화면에 표시되는 짧은 환경 설명 문구를 작성하는 역할이에요.

[상황]
- 품목: {matched_item.get('name', matched_item.get('category', ''))}
- 카테고리: {matched_item.get('category', '')}
- 최종 결과: {result_text} (재활용 성공)
- 사용자 답변 경로:
{answer_path_text}
- 탄소 절감 정보: {carbon_text if carbon_text else '집계 중'}

[작성 규칙]
- 3~4문장으로 작성
- 첫 문장: 이 품목이 왜 재활용 가능한지 또는 어떻게 재활용되는지 설명
- 둘째 문장: 탄소 절감 정보 자연스럽게 포함
- 셋째 문장: 칭찬 또는 동기부여 한 마디 (친근한 말투)
- 이모지 사용 금지, 마크다운 사용 금지, 한국어, 150자 이내"""
    else:
        prompt = f"""당신은 분리배출 환경 교육 챗봇의 결과 화면에 표시되는 짧은 환경 설명 문구를 작성하는 역할이에요.

[상황]
- 품목: {matched_item.get('name', matched_item.get('category', ''))}
- 카테고리: {matched_item.get('category', '')}
- 최종 결과: {result_text} (일반쓰레기)
- 사용자 답변 경로:
{answer_path_text}

[작성 규칙]
- 3~4문장으로 작성
- 첫 문장: 이 경로에서 왜 재활용이 안 되는지 구체적으로 설명
- 둘째 문장: 다음에 올바르게 배출하는 팁
- 셋째 문장: 아쉽지만 격려하는 마무리 (친근한 말투)
- 이모지 사용 금지, 마크다운 사용 금지, 한국어, 150자 이내"""

    try:
        import google.generativeai as genai
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=300,
                temperature=0.7,
            ),
        )
        text = response.text.strip()
        text = re.sub(r"\*+", "", text)
        text = re.sub(r"#+\s*", "", text)
        text = text.strip()
        return text if text else fallback
    except Exception:
        return fallback
