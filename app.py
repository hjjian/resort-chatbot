"""
app.py — Re:Sort 분리배출 챗봇 메인 앱
화면 상태: "home" → "questioning" → "result"
"""

import json
import streamlit as st
from datetime import datetime
from pathlib import Path

from matcher import load_items, match_item
from decision_tree import get_tree, get_first_question, process_answer
from carbon import load_carbon_factors, load_usage_log, save_usage_log, get_today_carbon, is_carbon_data_ready, format_carbon

# ──────────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Re:Sort — 분리배출 가이드",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────
# 전체 CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;900&display=swap');

  .stApp { background-color: #F2F2F0; }

  html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

  .navbar {
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 40px; background: #FFFFFF;
    border-bottom: 1px solid #E5E5E3;
    position: sticky; top: 0; z-index: 100;
  }
  .navbar-logo { color: #1B4D2E; font-size: 20px; font-weight: 700; }
  .navbar-icons { display: flex; gap: 16px; }

  .hero-title {
    font-size: 52px; font-weight: 900; line-height: 1.15;
    color: #1B4D2E; margin-bottom: 16px;
  }
  .hero-sub { font-size: 15px; color: #666; line-height: 1.7; }

  .stTextInput input {
    border-radius: 40px !important; padding: 14px 20px !important;
    font-size: 15px !important; border: 1.5px solid #D0D0CE !important;
  }

  .stButton > button {
    background-color: #1B4D2E !important; color: white !important;
    border-radius: 40px !important; padding: 12px 28px !important;
    font-size: 15px !important; font-weight: 600 !important;
    border: none !important;
  }
  .stButton > button:hover { background-color: #163D24 !important; }

  .card {
    background: #FFFFFF; border-radius: 16px;
    padding: 28px; margin-bottom: 16px;
  }
  .card-dark {
    background: #1B4D2E; border-radius: 16px;
    padding: 28px; color: white;
  }

  .tag {
    display: inline-block; padding: 6px 14px;
    background: #F0F0EE; border-radius: 20px;
    font-size: 13px; color: #333; margin: 4px;
    cursor: pointer;
  }
  .tag:hover { background: #E0E0DE; }

  .rank-num {
    font-size: 13px; font-weight: 700;
    color: #1B4D2E; margin-right: 8px;
  }

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

  .carbon-num {
    font-size: 48px; font-weight: 900;
    color: white; margin: 8px 0;
  }
  .carbon-unit { font-size: 22px; font-weight: 400; }

  .block-container { padding-top: 0 !important; padding-bottom: 0 !important; }
  #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 데이터 로드 (캐시)
# ──────────────────────────────────────────────
@st.cache_data
def get_items():
    return load_items()

@st.cache_data
def get_carbon_factors():
    return load_carbon_factors()

# ──────────────────────────────────────────────
# 세션 상태 초기화
# ──────────────────────────────────────────────
def init_session():
    defaults = {
        "state":         "home",
        "query":         "",
        "matched_item":  None,
        "tree":          None,
        "current_q":     None,
        "step_num":      1,
        "guide_message": None,   # 안내 메시지 (action 타입)
        "result_text":   None,
        "result_reason": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ──────────────────────────────────────────────
# 헬퍼: usage_log 저장
# ──────────────────────────────────────────────
def append_usage_log(user_input, matched_item, final_result, llm_used=False):
    log = load_usage_log()
    log.append({
        "timestamp":       datetime.now().isoformat()[:19],
        "user_input":      user_input,
        "matched_item_id": matched_item["id"] if matched_item else None,
        "matched_by":      matched_item.get("matched_by") if matched_item else None,
        "category":        matched_item["category"] if matched_item else None,
        "final_result":    final_result,
        "llm_used":        llm_used,
    })
    save_usage_log(log)

# ──────────────────────────────────────────────
# 헬퍼: 검색 실행
# ──────────────────────────────────────────────
def run_search(query: str):
    query = query.strip()
    if not query:
        return
    items = get_items()
    matched = match_item(query, items)
    st.session_state.query = query

    if matched is None:
        st.session_state.state = "no_match"
        st.session_state.matched_item = None
        return

    st.session_state.matched_item = matched
    skip = matched.get("skip_questions", [])

    # extra_questions가 있으면 먼저 처리
    extra = matched.get("extra_questions")
    if extra:
        eq = extra[0]
        # extra_question을 공통 질문 형식으로 변환
        st.session_state.current_q = {
            "id":          eq["id"],
            "text":        eq["question"],
            "description": "",
            "eco_title":   "왜 중요한가요?",
            "eco_desc":    "",
            "_extra_data": eq,   # 원본 extra_question 데이터 보존
            "_is_extra":   True,
        }
    else:
        tree = get_tree(matched["category"])
        if tree is None:
            # 트리 미구현 카테고리 → 바로 결과(steps)로
            st.session_state.result_text   = matched["category"] + " 분리배출"
            st.session_state.result_reason = matched.get("note", "")
            st.session_state.state         = "result"
            append_usage_log(query, matched, st.session_state.result_text)
            return
        st.session_state.tree      = tree
        first_q = get_first_question(tree, skip)
        if first_q is None:
            st.session_state.result_text   = matched["category"] + " 분리배출"
            st.session_state.result_reason = matched.get("note", "")
            st.session_state.state         = "result"
            append_usage_log(query, matched, st.session_state.result_text)
            return
        st.session_state.current_q = first_q

    st.session_state.state        = "questioning"
    st.session_state.step_num     = 1
    st.session_state.guide_message = None

# ──────────────────────────────────────────────
# 헬퍼: 답변 처리
# ──────────────────────────────────────────────
def handle_answer(answer: bool):
    current_q = st.session_state.current_q
    matched   = st.session_state.matched_item
    skip      = matched.get("skip_questions", [])

    # extra_question 처리
    if current_q.get("_is_extra"):
        eq = current_q["_extra_data"]
        branch = eq["yes"] if answer else eq["no"]

        # 바로 결과
        if "result" in branch:
            st.session_state.result_text   = branch["result"]
            st.session_state.result_reason = branch.get("reason", "")
            st.session_state.state         = "result"
            append_usage_log(st.session_state.query, matched, branch["result"])
            return

        # category_tree로 진입
        if branch.get("next") == "category_tree":
            extra_list = matched.get("extra_questions", [])
            current_idx = next(
                (i for i, eq2 in enumerate(extra_list) if eq2["id"] == eq["id"]), -1
            )
            next_extra_idx = current_idx + 1

            if next_extra_idx < len(extra_list):
                # 다음 extra_question으로
                next_eq = extra_list[next_extra_idx]
                st.session_state.current_q = {
                    "id":          next_eq["id"],
                    "text":        next_eq["question"],
                    "description": "",
                    "eco_title":   "왜 중요한가요?",
                    "eco_desc":    "",
                    "_extra_data": next_eq,
                    "_is_extra":   True,
                }
                st.session_state.step_num += 1
            else:
                # 공통 트리로 진입
                tree = get_tree(matched["category"])
                if tree is None:
                    st.session_state.result_text   = matched["category"] + " 분리배출"
                    st.session_state.result_reason = matched.get("note", "")
                    st.session_state.state         = "result"
                    append_usage_log(st.session_state.query, matched, st.session_state.result_text)
                    return
                st.session_state.tree      = tree
                first_q = get_first_question(tree, skip)
                if first_q is None:
                    st.session_state.result_text   = matched["category"] + " 분리배출"
                    st.session_state.result_reason = matched.get("note", "")
                    st.session_state.state         = "result"
                    append_usage_log(st.session_state.query, matched, st.session_state.result_text)
                    return
                st.session_state.current_q    = first_q
                st.session_state.step_num    += 1
                st.session_state.guide_message = None
        return

    # 공통 트리 처리
    tree = st.session_state.tree
    outcome = process_answer(tree, current_q["id"], answer, skip)

    if outcome["type"] == "result":
        st.session_state.result_text   = outcome["result"]
        st.session_state.result_reason = outcome.get("reason", "")
        st.session_state.state         = "result"
        append_usage_log(st.session_state.query, matched, outcome["result"])

    elif outcome["type"] == "guide":
        st.session_state.guide_message = outcome["message"]
        st.session_state.current_q     = outcome["next_question"]
        st.session_state.step_num     += 1

    elif outcome["type"] == "question":
        st.session_state.guide_message = None
        st.session_state.current_q     = outcome["question"]
        st.session_state.step_num     += 1

# ══════════════════════════════════════════════
# 화면 1 — 홈
# ══════════════════════════════════════════════
def render_home():
    # 네비게이션바
    st.markdown("""
    <div class="navbar">
      <span class="navbar-logo">Re:Sort</span>
      <div class="navbar-icons">
        <span>🔍</span>
        <span>👤</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # 히어로
    st.markdown("""
    <div style="padding: 60px 40px 0;">
      <div class="hero-title">무엇이든 물어보세요.<br>지구의 내일을 위해.</div>
      <div class="hero-sub">
        버리기 어려운 쓰레기, 어떻게 분리배출해야 할까요?<br>
        정확한 가이드를 통해 자원 순환에 동참해 주세요.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # 검색창
    st.markdown("<div style='padding: 24px 40px 0;'>", unsafe_allow_html=True)
    col1, col2 = st.columns([5, 1])
    with col1:
        query = st.text_input(
            "",
            placeholder="예: 배달 음식 용기, 폐건전지, 우유팩",
            label_visibility="collapsed",
            key="home_input",
        )
    with col2:
        search_btn = st.button("검색", use_container_width=True, key="home_search_btn")
    st.markdown("</div>", unsafe_allow_html=True)

    if search_btn and query:
        run_search(query)
        st.rerun()

    # 태그 클릭 처리
    if st.session_state.get("_tag_query"):
        run_search(st.session_state._tag_query)
        st.session_state._tag_query = None
        st.rerun()

    st.markdown("<div style='padding: 0 40px;'>", unsafe_allow_html=True)

    # HOT ISSUE + 탄소절감 카드
    col_left, col_right = st.columns([3, 2])

    with col_left:
        # 오늘 검색 Top 5 태그
        usage_log = load_usage_log()
        if usage_log:
            from collections import Counter
            from datetime import date
            today = date.today().isoformat()
            today_inputs = [
                e["user_input"] for e in usage_log
                if e.get("timestamp", "").startswith(today) and e.get("user_input")
            ]
            top5 = [item for item, _ in Counter(today_inputs).most_common(5)]
        else:
            top5 = ["플라스틱 컵", "치킨 상자", "영수증", "택배 박스", "우유팩"]

        tags_html = "".join(f'<span class="tag">#{t}</span>' for t in top5)
        st.markdown(f"""
        <div class="card">
          <div style="display:inline-block; background:#E8F5E9; color:#1B4D2E;
                      border-radius:20px; padding:4px 12px; font-size:11px;
                      font-weight:700; margin-bottom:12px;">HOT ISSUE</div>
          <div style="font-size:18px; font-weight:700; margin-bottom:16px;">
            지금 가장 많이 찾아보는 품목
          </div>
          <div>{tags_html}</div>
        </div>
        """, unsafe_allow_html=True)

        # 태그 버튼 (클릭 처리용 숨김 버튼)
        tag_cols = st.columns(len(top5))
        for i, tag in enumerate(top5):
            with tag_cols[i]:
                if st.button(tag, key=f"tag_{i}", use_container_width=True):
                    st.session_state._tag_query = tag
                    st.rerun()

    with col_right:
        carbon_factors = get_carbon_factors()
        usage_log      = load_usage_log()
        carbon_val     = get_today_carbon(usage_log, carbon_factors)
        carbon_str     = format_carbon(carbon_val)
        st.markdown(f"""
        <div class="card-dark" style="height:100%;">
          <div style="font-size:28px; margin-bottom:8px;">🌿</div>
          <div style="font-size:13px; opacity:0.8; margin-bottom:4px;">오늘 여러분이 줄인 탄소발자국량</div>
          <div class="carbon-num">{carbon_str}</div>
          <div style="font-size:13px; opacity:0.7; margin-top:8px;">우리의 분리배출로 아낀 탄소 배출량</div>
        </div>
        """, unsafe_allow_html=True)

    # 자주 틀리는 실수 Top 10
    st.markdown("""
    <div style="display:flex; justify-content:space-between; align-items:center;
                margin: 32px 0 16px;">
      <div style="font-size:18px; font-weight:700;">자주 틀리는 실수 Top 10</div>
      <div style="font-size:13px; color:#1B4D2E; cursor:pointer;">전체보기 →</div>
    </div>
    """, unsafe_allow_html=True)

    if usage_log:
        from collections import Counter
        mistakes = [
            e["user_input"] for e in usage_log
            if e.get("final_result") == "일반쓰레기" and e.get("user_input")
        ]
        top_mistakes = [item for item, _ in Counter(mistakes).most_common(10)]
    else:
        top_mistakes = [
            "씻지 않은 음식 용기", "라벨 붙은 페트병",
            "코팅된 종이 전단지", "깨진 유리 조각",
        ]

    # 4열 카드
    chunk = 4
    for row_start in range(0, len(top_mistakes), chunk):
        row_items = top_mistakes[row_start:row_start + chunk]
        cols = st.columns(chunk)
        for i, mistake in enumerate(row_items):
            num = f"{row_start + i + 1:02d}"
            with cols[i]:
                st.markdown(f"""
                <div class="card" style="padding:20px;">
                  <span class="rank-num">{num}</span>{mistake}
                </div>
                """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # 매칭 실패 안내
    if st.session_state.state == "no_match":
        st.warning(f"**'{st.session_state.query}'** 에 해당하는 품목을 찾지 못했어요. 다른 표현으로 검색해보세요.")
        st.session_state.state = "home"

    # 푸터
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


# ══════════════════════════════════════════════
# 화면 2 — 질문
# ══════════════════════════════════════════════
def render_questioning():
    current_q = st.session_state.current_q
    matched   = st.session_state.matched_item

    # 네비게이션바
    st.markdown("""
    <div class="navbar">
      <span class="navbar-logo">Re:Sort</span>
      <div class="navbar-icons"><span>🔍</span><span>👤</span></div>
    </div>
    """, unsafe_allow_html=True)

    # 안내 메시지 (action)
    if st.session_state.guide_message:
        st.info(f"💡 {st.session_state.guide_message}")

    # PROCESS 배경 + 질문
    st.markdown(f"""
    <div style="text-align:center; padding: 40px 20px 0;">
      <div class="process-bg">PROCESS</div>
      <div style="margin-top:-50px;">
        <span class="step-badge">STEP {st.session_state.step_num:02d}</span>
        <div class="question-title">{current_q["text"]}</div>
        <div style="color:#666; font-size:15px; max-width:500px; margin:0 auto 40px;">
          {current_q.get("description", "")}
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # 예 / 아니오 카드
    col_yes, col_no = st.columns(2)
    with col_yes:
        st.markdown("""
        <div class="answer-yes">
          <div class="answer-icon">✓</div>
          <div class="answer-main">예</div>
          <div class="answer-sub">네, 맞아요</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("예", key="yes_btn", use_container_width=True):
            handle_answer(True)
            st.rerun()

    with col_no:
        st.markdown("""
        <div class="answer-no">
          <div class="answer-icon">✕</div>
          <div class="answer-main">아니오</div>
          <div class="answer-sub">아니요, 해당 없어요</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("아니오", key="no_btn", use_container_width=True):
            handle_answer(False)
            st.rerun()

    # 환경 설명 박스
    eco_title = current_q.get("eco_title", "왜 중요한가요?")
    eco_desc  = current_q.get("eco_desc", "")
    if eco_desc:
        st.markdown(f"""
        <div class="eco-box" style="max-width:600px; margin:32px auto;">
          <div class="eco-icon">💡</div>
          <div>
            <div style="font-weight:600; margin-bottom:4px;">{eco_title}</div>
            <div style="font-size:14px; color:#555;">{eco_desc}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # 처음으로 버튼
    st.markdown("<div style='text-align:center; margin-top:16px;'>", unsafe_allow_html=True)
    if st.button("← 처음으로", key="back_home"):
        for k in ["state", "query", "matched_item", "tree", "current_q",
                  "step_num", "guide_message", "result_text", "result_reason"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # 하단 배너
    st.markdown("""
    <div style="background:#1B4D2E; border-radius:16px; padding:40px 32px; margin-top:40px;
                color:white; font-size:20px; font-weight:700;">
      작은 실천이 만드는 큰 변화
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
# 화면 3 — 결과
# ══════════════════════════════════════════════
def render_result():
    matched     = st.session_state.matched_item
    result_text = st.session_state.result_text
    reason      = st.session_state.result_reason or matched.get("note", "")

    # 네비게이션바
    st.markdown("""
    <div class="navbar">
      <span class="navbar-logo">Re:Sort</span>
      <div class="navbar-icons"><span>🔍</span><span>👤</span></div>
    </div>
    """, unsafe_allow_html=True)

    # 결과 카드
    st.markdown(f"""
    <div class="result-card">
      <div class="result-badge">분석 완료: {matched["name"]}</div>
      <div class="result-title">{result_text}</div>
    </div>
    """, unsafe_allow_html=True)

    # 다시 검색 버튼
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("↺  다시 검색", use_container_width=True, key="retry_btn"):
            for k in ["state", "query", "matched_item", "tree", "current_q",
                      "step_num", "guide_message", "result_text", "result_reason"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    # 정확한 배출 요령
    steps = matched.get("steps", [])
    if steps:
        steps_html = "".join([
            f'<div class="step-item">'
            f'<div class="step-num">{i+1}</div>'
            f'<div class="step-text">{step}</div>'
            f'</div>'
            for i, step in enumerate(steps)
        ])
        st.markdown(f"""
        <div class="steps-card" style="max-width:700px; margin:0 auto 24px;">
          <div class="steps-title">정확한 배출 요령</div>
          {steps_html}
        </div>
        """, unsafe_allow_html=True)

    # 이유 / 환경 설명
    if reason:
        st.markdown(f"""
        <div style="max-width:700px; margin:0 auto; text-align:center;
                    color:#888; font-size:13px; padding-bottom:40px;">
          {reason}
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 라우터
# ──────────────────────────────────────────────
state = st.session_state.state

if state in ("home", "no_match"):
    render_home()
elif state == "questioning":
    render_questioning()
elif state == "result":
    render_result()
