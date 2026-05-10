# Re:Sort 분리배출 챗봇 개발 요청

## 프로젝트 개요
분리배출을 어떻게 해야 할지 모르는 자취생·대학생을 위한 Streamlit 챗봇.
사용자가 쓰레기 품목을 자연어로 입력하면 Yes/No 질문을 통해 올바른 배출 방법을 안내하고,
왜 그렇게 분류해야 하는지 환경적 이유도 함께 설명한다.

---

## 파일 구조

resort-chatbot/
├── app.py                  # Streamlit 메인 앱 (사용자 화면)
├── admin.py                # 관리자 대시보드
├── decision_tree.py        # 카테고리별 Yes/No 트리 로직
├── matcher.py              # 키워드 매칭 로직
├── hybrid_handler.py       # Gemini API fallback (Phase 2)
├── carbon.py               # 탄소절감량 계산 로직
├── data/
│   ├── items.json          # 품목 데이터베이스 (첨부 파일 참고)
│   ├── carbon_factors.json # 카테고리별 탄소절감 계수 (아래 참고)
│   └── usage_log.json      # 사용자 검색 로그 (자동 생성)
├── requirements.txt
└── .streamlit/
    └── secrets.toml        # Gemini API 키 + 관리자 비밀번호

---

## items.json 구조 (첨부 파일 참고)

각 항목의 필드:
- id: 고유 식별자 (예: styro_001)
- name: 품목 대표 이름
- keywords: 사용자 입력 유사 표현 리스트
- category: 9개 카테고리 중 하나
  (스티로폼 / 유리 / 금속·캔 / 비닐 / 플라스틱 / 종이·종이팩 / 폐의약품 / 전자제품 및 완충재 / 기타)
- skip_questions: 건너뛸 공통 질문 ID 리스트
- extra_questions: 품목 전용 추가 질문 (null이면 공통 트리만 사용)
- note: 환경 설명 텍스트
- steps: 결과 화면의 "정확한 배출 요령" 번호 리스트 (문자열 배열)
  예: ["빨대와 비닐 캡 이물질을 제거하세요.", "물로 깨끗이 헹궈 말립니다.", "차곡차곡 쌓아 배출하세요."]

### extra_questions 구조
현재 방식 (MVP): extra_questions가 공통 트리 앞에 실행됨.
- next: "category_tree" → 추가 질문 후 공통 트리로 진입
- result: "..." → 추가 질문에서 바로 결과 도출

향후 확장 방식 (나중에): questions 배열에 공통(ref)과 품목별 질문을 순서대로 섞어서 정의.

---

## 탄소절감량 계산 (carbon.py)

### carbon_factors.json 구조
카테고리별 1회 올바른 분리배출 시 절감되는 탄소량 (단위: kg CO2e).
아래 값은 나중에 실제 수치로 업데이트할 예정이므로 placeholder로 작성.
업데이트 시 이 JSON 파일만 수정하면 자동 반영되도록 설계.

```json
{
  "스티로폼":   0.0,
  "유리":       0.0,
  "금속·캔":    0.0,
  "비닐":       0.0,
  "플라스틱":   0.0,
  "종이·종이팩": 0.0,
  "폐의약품":   0.0,
  "전자제품 및 완충재":   0.0,
  "기타":       0.0
}
```

### carbon.py 로직
```python
import json
from datetime import date

def get_today_carbon(usage_log: list, carbon_factors: dict) -> float:
    today = date.today().isoformat()  # "2025-04-06"
    total = 0.0
    for entry in usage_log:
        # timestamp가 오늘 날짜인 항목만
        if entry.get("timestamp", "").startswith(today):
            category = entry.get("category", "기타")
            factor = carbon_factors.get(category, 0.0)
            total += factor
    return round(total, 2)
```

홈 화면의 탄소절감량 카드에는 오늘 하루(00:00~현재)의 usage_log를 기반으로
카테고리별 carbon_factors를 합산한 값을 표시.
carbon_factors가 모두 0.0이면 "집계 중..." 또는 "0 kg" 으로 표시.

---

## Decision Tree 로직 (decision_tree.py)

### 스티로폼 트리
Q1. 테이프·송장·스티커가 붙어있나요?
  YES → "제거 후 다음 질문으로" 안내 후 Q2로
  NO  → Q2로
Q2. 음식물·이물질이 묻어있나요?
  YES → Q2-1로
  NO  → Q3으로
Q2-1. 물로 씻으면 제거되나요?
  YES → Q3으로
  NO  → 결과: 일반쓰레기 / 이유: "세척 불가 → 재활용 공정 오염"
Q3. 색상이 있거나 코팅됐나요?
  YES → 결과: 일반쓰레기 / 이유: "색상·코팅 스티로폼은 재생원료 품질 저하로 선별장 반입 거부"
  NO  → 결과: 스티로폼 재활용

### 유리 트리
Q1. 깨진 유리인가요?
  YES → 결과: 일반쓰레기 / 이유: "신문지로 감싸 '깨진 유리' 표기 후 배출. 수거 담당자 안전"
  NO  → Q2로
Q2. 내열유리·도자기·거울인가요?
  YES → 결과: 일반쓰레기 / 이유: "일반 유리와 용해 온도가 달라 함께 재활용 불가"
  NO  → Q3으로
Q3. 내용물을 비웠나요?
  YES → 결과: 유리병 재활용
  NO  → 안내: "내용물을 비운 후 재배출해주세요"

### 금속·캔 트리
Q1. 스프레이·부탄가스 캔인가요?
  YES → Q1-1로 / NO → Q2로
Q1-1. 가스를 완전히 뺐나요?
  YES → 결과: 캔류 재활용
  NO  → 결과: 주의 / 이유: "잔여 가스 → 폭발 위험. 캔에 구멍 뚫어 가스 제거 후 배출"
Q2. 내용물을 완전히 비웠나요?
  YES → Q3으로 / NO → 안내: "내용물을 비운 후 재배출해주세요"
Q3. 다른 재질이 붙어있나요?
  YES → Q3-1로 / NO → 결과: 캔·금속류 재활용
Q3-1. 손으로 분리할 수 있나요?
  YES → 결과: "분리 후 각각 해당 재질로 배출"
  NO  → 결과: 일반쓰레기 / 이유: "분리 불가 복합 재질"

나머지 6개 카테고리 트리는 추후 추가 예정. 확장 가능한 구조로 설계.

---

## 챗봇 동작 흐름

st.session_state로 화면 상태 관리: "home" → "questioning" → "result"

1. [home] 검색창 입력 → 검색 버튼 or 태그 클릭
2. matcher.py keywords 기반 매칭
3. 매칭 성공 → extra_questions 있으면 먼저, 그 후 공통 트리
4. [questioning] Yes/No 카드로 질문 진행 (skip_questions 반영)
5. [result] 결과 표시 + usage_log 저장
6. 매칭 실패 → Gemini fallback (Phase 2) 또는 안내 메시지

---

## Gemini API fallback (hybrid_handler.py) — Phase 2

```python
import google.generativeai as genai
import streamlit as st
import json

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

CATEGORIES = ["스티로폼", "유리", "금속·캔", "비닐", "플라스틱",
              "종이·종이팩", "폐의약품", "전자제품 및 완충재", "기타"]

def classify_category(user_input: str) -> dict:
    prompt = f"""
다음 쓰레기 품목이 아래 카테고리 중 어디에 해당하는지 JSON으로만 답해줘.
카테고리: {', '.join(CATEGORIES)}
품목: {user_input}
응답 형식 (JSON만, 다른 텍스트 없이):
{{"category": "스티로폼", "confidence": "high"}}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json","").replace("```","")
        return json.loads(text)
    except Exception:
        return {"category": None, "confidence": "low"}
```

secrets.toml:
GEMINI_API_KEY = "your-gemini-api-key"
ADMIN_PASSWORD  = "your-admin-password"

---

## usage_log.json 저장

```json
{
  "timestamp": "2025-04-06T12:34:56",
  "user_input": "컵라면 용기",
  "matched_item_id": "styro_001",
  "matched_by": "keyword",
  "category": "스티로폼",
  "final_result": "일반쓰레기",
  "llm_used": false
}
```

---

## UI 디자인 명세 (Streamlit custom CSS 적용)

### 전체 스타일 (모든 화면 공통)

```python
st.markdown("""
<style>
  /* 전체 배경 */
  .stApp { background-color: #F2F2F0; }

  /* 기본 폰트 */
  html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

  /* 네비게이션바 */
  .navbar {
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 40px; background: #FFFFFF;
    border-bottom: 1px solid #E5E5E3;
    position: sticky; top: 0; z-index: 100;
  }
  .navbar-logo { color: #1B4D2E; font-size: 20px; font-weight: 700; }
  .navbar-icons { display: flex; gap: 16px; }

  /* 히어로 헤드라인 */
  .hero-title {
    font-size: 52px; font-weight: 900; line-height: 1.15;
    color: #1B4D2E; margin-bottom: 16px;
  }
  .hero-sub { font-size: 15px; color: #666; line-height: 1.7; }

  /* 검색창 오버라이드 */
  .stTextInput input {
    border-radius: 40px !important; padding: 14px 20px !important;
    font-size: 15px !important; border: 1.5px solid #D0D0CE !important;
  }

  /* 초록 버튼 */
  .stButton > button {
    background-color: #1B4D2E !important; color: white !important;
    border-radius: 40px !important; padding: 12px 28px !important;
    font-size: 15px !important; font-weight: 600 !important;
    border: none !important;
  }
  .stButton > button:hover { background-color: #163D24 !important; }

  /* 카드 */
  .card {
    background: #FFFFFF; border-radius: 16px;
    padding: 28px; margin-bottom: 16px;
  }
  .card-dark {
    background: #1B4D2E; border-radius: 16px;
    padding: 28px; color: white;
  }

  /* HOT ISSUE 태그 */
  .tag {
    display: inline-block; padding: 6px 14px;
    background: #F0F0EE; border-radius: 20px;
    font-size: 13px; color: #333; margin: 4px;
    cursor: pointer;
  }
  .tag:hover { background: #E0E0DE; }

  /* 자주 틀리는 실수 Top 10 번호 */
  .rank-num {
    font-size: 13px; font-weight: 700;
    color: #1B4D2E; margin-right: 8px;
  }

  /* 질문 화면 STEP 뱃지 */
  .step-badge {
    display: inline-block; background: #1B4D2E; color: white;
    border-radius: 20px; padding: 4px 14px;
    font-size: 12px; font-weight: 600; margin-bottom: 8px;
  }
  .process-bg {
    font-size: 80px; font-weight: 900; color: #E8EDE9;
    text-align: center; margin: 0; line-height: 1;
    letter-spacing: 8px;
  }
  .question-title {
    font-size: 42px; font-weight: 900; color: #1B4D2E;
    text-align: center; margin: 16px 0;
  }

  /* 예/아니오 카드 */
  .answer-yes {
    background: #1B4D2E; border-radius: 16px;
    padding: 48px 24px; text-align: center; cursor: pointer;
    color: white;
  }
  .answer-no {
    background: #EEEEED; border-radius: 16px;
    padding: 48px 24px; text-align: center; cursor: pointer;
    color: #555;
  }
  .answer-icon { font-size: 36px; margin-bottom: 12px; }
  .answer-main { font-size: 32px; font-weight: 800; margin-bottom: 8px; }
  .answer-sub  { font-size: 13px; opacity: 0.7; }

  /* 환경 설명 박스 */
  .eco-box {
    background: #F8F8F6; border-radius: 12px; padding: 20px 24px;
    display: flex; gap: 14px; align-items: flex-start;
  }
  .eco-icon {
    background: #E8EDE9; border-radius: 8px;
    width: 36px; height: 36px; display: flex;
    align-items: center; justify-content: center;
    flex-shrink: 0; font-size: 18px;
  }

  /* 결과 화면 */
  .result-card {
    background: white; border-radius: 24px;
    padding: 48px 40px; text-align: center;
    max-width: 700px; margin: 40px auto;
  }
  .result-badge {
    display: inline-block; background: #D4EDDA;
    color: #1B4D2E; border-radius: 20px;
    padding: 6px 16px; font-size: 13px;
    font-weight: 600; margin-bottom: 24px;
  }
  .result-title {
    font-size: 44px; font-weight: 900; color: #1B4D2E;
    line-height: 1.2; margin-bottom: 32px;
  }

  /* 배출 요령 번호 리스트 */
  .steps-card {
    background: #F5F5F3; border-radius: 16px;
    padding: 28px 32px; text-align: left;
  }
  .steps-title { font-size: 16px; font-weight: 700; margin-bottom: 20px; }
  .step-item {
    display: flex; align-items: flex-start;
    gap: 14px; margin-bottom: 16px;
  }
  .step-num {
    background: #1B4D2E; color: white;
    border-radius: 50%; width: 28px; height: 28px;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700; flex-shrink: 0;
  }
  .step-text { font-size: 15px; color: #333; padding-top: 4px; }

  /* 탄소절감량 숫자 */
  .carbon-num {
    font-size: 48px; font-weight: 900;
    color: white; margin: 8px 0;
  }
  .carbon-unit { font-size: 22px; font-weight: 400; }

  /* Streamlit 기본 여백 제거 */
  .block-container { padding-top: 0 !important; padding-bottom: 0 !important; }
  #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)
```

---

### 화면 1 — 홈 (state: "home")

#### 네비게이션바
```python
st.markdown("""
<div class="navbar">
  <span class="navbar-logo">Re:Sort</span>
  <div class="navbar-icons">
    <span>🔍</span>
    <span>👤</span>
  </div>
</div>
""", unsafe_allow_html=True)
```

#### 히어로 섹션
```python
st.markdown("""
<div style="padding: 60px 40px 0;">
  <div class="hero-title">무엇이든 물어보세요.<br>지구의 내일을 위해.</div>
  <div class="hero-sub">
    버리기 어려운 쓰레기, 어떻게 분리배출해야 할까요?<br>
    정확한 가이드를 통해 자원 순환에 동참해 주세요.
  </div>
</div>
""", unsafe_allow_html=True)
```

검색창 + 버튼:
```python
col1, col2 = st.columns([5, 1])
with col1:
    query = st.text_input("", placeholder="예: 배달 음식 용기, 폐건전지, 우유팩", label_visibility="collapsed")
with col2:
    search_btn = st.button("검색", use_container_width=True)
```

#### HOT ISSUE 섹션 (st.columns 2열)
```python
col_left, col_right = st.columns([3, 2])

with col_left:
    # 흰색 카드
    # HOT ISSUE 뱃지 + "지금 가장 많이 찾아보는 품목" 제목
    # usage_log.json에서 오늘 검색 빈도 Top 5 태그로 표시
    # 로그 없으면 하드코딩: ["플라스틱 컵", "치킨 상자", "영수증", "택배 박스"]
    # 각 태그 클릭 시 해당 텍스트로 검색 실행
    pass

with col_right:
    # 짙은 초록 배경 카드
    # 잎사귀 이모지 🌿
    # "오늘 여러분이 줄인 탄소발자국량"
    # "우리의 분리배출로 아낀 탄소 배출량"
    # carbon.py의 get_today_carbon() 호출해서 표시
    # 예: "2,481 kg" (천 단위 쉼표, 소수점 없음)
    # carbon_factors가 모두 0이면 "집계 중..." 표시
    pass
```

#### 자주 틀리는 실수 Top 10 섹션
```python
# 제목 행: "자주 틀리는 실수 Top 10" + "전체보기 →"
# usage_log.json에서 final_result == "일반쓰레기"인 항목 중 user_input 빈도 순
# 로그 없으면 하드코딩:
# ["씻지 않은 음식 용기", "라벨 붙은 페트병", "코팅된 종이 전단지", "깨진 유리 조각"]
# 가로 배열 카드 (st.columns 4열)
# 각 카드: "01 씻지 않은 음식 용기" 형식
```

#### 푸터
```python
st.markdown("""
<div style="padding: 40px; margin-top: 60px; border-top: 1px solid #E5E5E3;">
  <div style="display:flex; justify-content:space-between;">
    <div>
      <div style="color:#1B4D2E; font-weight:700; margin-bottom:8px;">Re:Sort</div>
      <div style="color:#888; font-size:13px;">공공 데이터 기반의 지능형 분리배출 가이드 시스템.<br>환경을 위한 당신의 노력을 응원합니다.</div>
    </div>
    <div style="display:flex; gap:40px; font-size:13px; color:#888;">
      <div><div style="font-weight:600; color:#333; margin-bottom:8px;">RESOURCES</div>
        <div>API Documentation</div><div>Data Sources</div></div>
      <div><div style="font-weight:600; color:#333; margin-bottom:8px;">LEGAL</div>
        <div>Privacy Policy</div><div>Terms of Use</div></div>
    </div>
  </div>
  <div style="margin-top:24px; font-size:11px; color:#AAA;">
    © 2024 RE:SORT ARCHIVE PROJECT. ALL RIGHTS RESERVED.
  </div>
</div>
""", unsafe_allow_html=True)
```

---

### 화면 2 — 질문 (state: "questioning")

```python
# 현재 질문 번호를 st.session_state.step_num으로 관리 (1부터 시작)

st.markdown(f"""
<div style="text-align:center; padding: 40px 20px 0;">
  <div class="process-bg">PROCESS</div>
  <div style="margin-top:-50px;">
    <span class="step-badge">STEP {st.session_state.step_num:02d}</span>
    <div class="question-title">{current_question["text"]}</div>
    <div style="color:#666; font-size:15px; max-width:500px; margin:0 auto 40px;">
      {current_question.get("description", "")}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# 예/아니오 카드 버튼 (st.columns 2열)
col_yes, col_no = st.columns(2)
with col_yes:
    st.markdown("""
    <div class="answer-yes">
      <div class="answer-icon">✓</div>
      <div class="answer-main">예</div>
      <div class="answer-sub">이미 깨끗하게 비웠어요</div>
    </div>
    """, unsafe_allow_html=True)
    yes_btn = st.button("예", key="yes", use_container_width=True)

with col_no:
    st.markdown("""
    <div class="answer-no">
      <div class="answer-icon">✕</div>
      <div class="answer-main">아니오</div>
      <div class="answer-sub">아직 내용물이 남아있어요</div>
    </div>
    """, unsafe_allow_html=True)
    no_btn = st.button("아니오", key="no", use_container_width=True)

# 환경 설명 박스
st.markdown(f"""
<div class="eco-box" style="max-width:600px; margin:32px auto;">
  <div class="eco-icon">💡</div>
  <div>
    <div style="font-weight:600; margin-bottom:4px;">{current_question.get("eco_title","왜 중요한가요?")}</div>
    <div style="font-size:14px; color:#555;">{current_question.get("eco_desc","")}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# 하단 배너
st.markdown("""
<div style="background:#1B4D2E; border-radius:16px; padding:40px 32px; margin-top:40px;
            color:white; font-size:20px; font-weight:700;">
  작은 실천이 만드는 큰 변화
</div>
""", unsafe_allow_html=True)
```

decision_tree의 각 질문 딕셔너리에 아래 필드 추가:
```python
{
  "id": "Q2",
  "text": "내용물이 비워져 있나요?",
  "description": "잔여물이 남아있는 용기는 재활용 품질을 저하시킵니다.",
  "eco_title": "왜 비워야 하나요?",
  "eco_desc": "이물질이 묻은 플라스틱이나 비닐은 다른 깨끗한 자원까지 오염시켜 전체 재활용 공정의 효율을 떨어뜨립니다."
}
```

---

### 화면 3 — 결과 (state: "result")

```python
st.markdown(f"""
<div class="result-card">
  <div class="result-badge">분석 완료: {matched_item["name"]}</div>
  <div class="result-title">{result_text}</div>
</div>
""", unsafe_allow_html=True)

# 다시 검색 버튼
col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    if st.button("↺  다시 검색", use_container_width=True):
        st.session_state.state = "home"
        st.rerun()

# 정확한 배출 요령
steps = matched_item.get("steps", [])
if steps:
    steps_html = "".join([
        f'<div class="step-item"><div class="step-num">{i+1}</div>'
        f'<div class="step-text">{step}</div></div>'
        for i, step in enumerate(steps)
    ])
    st.markdown(f"""
    <div class="steps-card" style="max-width:700px; margin:0 auto 24px;">
      <div class="steps-title">정확한 배출 요령</div>
      {steps_html}
    </div>
    """, unsafe_allow_html=True)

# 환경 설명 note
st.markdown(f"""
<div style="max-width:700px; margin:0 auto; text-align:center;
            color:#888; font-size:13px; padding-bottom:40px;">
  {matched_item.get("note", "")}
</div>
""", unsafe_allow_html=True)
```

---

## 관리자 대시보드 (admin.py)

Streamlit 멀티페이지. /admin URL로 접근. 비밀번호 로그인 후 진입.

표시 내용:
1. 요약 카드 4개: 총 검색 횟수 / 키워드 매칭 성공률 / Gemini fallback 횟수 / 가장 많이 검색된 카테고리
2. 검색 Top 10 바 차트
3. 매칭 실패 목록 테이블 (matched_item_id == null 인 항목)
4. 카테고리별 검색 분포 파이 차트
5. 일별 사용량 추이 라인 차트
6. 전체 로그 테이블 + 날짜 필터 + CSV 다운로드 버튼

---

## 기술 스택

- Python 3.10+
- Streamlit (멀티페이지)
- google-generativeai (Phase 2)
- pandas
- JSON 파일 기반

requirements.txt:
streamlit
google-generativeai
pandas

---

## 개발 순서 (이 순서대로 진행해줘)

1단계: 파일 구조 + requirements.txt + carbon_factors.json 생성
2단계: decision_tree.py — 스티로폼·유리·금속캔 3개 트리 (text/description/eco_title/eco_desc 포함)
3단계: matcher.py — keywords 기반 매칭
4단계: carbon.py — 탄소절감량 계산 함수
5단계: app.py — 홈/질문/결과 3개 화면 + CSS + usage_log 저장
6단계: admin.py — 관리자 대시보드
7단계: 로컬 실행 테스트 (streamlit run app.py)

각 단계마다 확인 후 다음 단계로 넘어갈게.
우선 1단계부터 시작해줘.
