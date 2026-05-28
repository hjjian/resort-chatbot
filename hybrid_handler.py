"""
hybrid_handler.py — Gemini Flash를 활용한 IMPACT NOTE 동적 생성

generate_impact_note(matched_item, result_text, question_history, carbon_factor)
  → str: 결과 화면의 IMPACT NOTE에 표시할 AI 생성 텍스트
  → 실패 시 fallback으로 matched_item["note"] 반환
"""

import re

# ──────────────────────────────────────────────
# 탄소 비유 텍스트 생성 헬퍼
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


# ──────────────────────────────────────────────
# 답변 경로 텍스트 변환 헬퍼
# ──────────────────────────────────────────────
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


# ──────────────────────────────────────────────
# 메인 함수
# ──────────────────────────────────────────────
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
    matched_item      : items.json 매칭 항목 (name, category, note 등 포함)
    result_text       : 최종 결과 텍스트 (예: "플라스틱 분리배출", "일반쓰레기(종량제)")
    question_history  : 사용자가 답변한 질문 경로 리스트
    carbon_factor     : 카테고리별 탄소 절감 계수 (kg CO₂e)

    Returns
    -------
    str : AI가 생성한 IMPACT NOTE (실패 시 기존 note 반환)
    """
    fallback = matched_item.get("note", "")

    try:
        import streamlit as st
        api_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        api_key = ""

    if not api_key:
        return fallback

    is_recycled = "일반쓰레기" not in result_text

    # 탄소 비유 문장 (재활용 성공 시만 사용)
    carbon_text = _carbon_analogy(carbon_factor) if is_recycled else ""

    # 답변 경로 정리
    answer_path_text = _format_answer_path(question_history)

    # ── 프롬프트 구성 ──
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
- 둘째 문장: 탄소 절감 정보 자연스럽게 포함 (carbon_text 그대로 활용해도 됨)
- 셋째 문장: 칭찬 또는 동기부여 한 마디 (딱딱하지 않게, 친근한 말투)
- 이모지 사용 금지
- 마크다운 사용 금지
- 한국어로 작성
- 150자 이내"""
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
- 첫 문장: 이 경로(답변 내용)에서 왜 재활용이 안 되는지 구체적으로 설명
- 둘째 문장: 비슷하게 생겼지만 재활용 가능한 경우나 다음에 올바르게 배출하는 팁
- 셋째 문장: 아쉽지만 격려하는 마무리 (자극적이지 않게, 친근한 말투)
- 이모지 사용 금지
- 마크다운 사용 금지
- 한국어로 작성
- 150자 이내"""

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=300,
                temperature=0.7,
            ),
        )
        text = response.text.strip()

        # 마크다운 잔재 제거
        text = re.sub(r"\*+", "", text)
        text = re.sub(r"#+\s*", "", text)
        text = text.strip()

        return text if text else fallback

    except Exception:
        return fallback
