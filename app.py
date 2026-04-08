"""
app.py — Re:Sort 분리배출 챗봇 메인 앱
화면 상태: "home" → "questioning" → "result"
"""

import streamlit as st
from datetime import datetime
from pathlib import Path

from matcher import load_items, match_item
from decision_tree import get_tree, get_first_question, process_answer
from carbon import (load_carbon_factors, load_usage_log, save_usage_log,
                    get_today_carbon, format_carbon)

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
# 전체 공통 CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;900&display=swap');

/* ── 기본 리셋 ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.stApp { background-color: #F2F2F0; }
#MainMenu, footer { visibility: hidden; }
[data-testid="collapsedControl"] { visibility: visible !important; }

/* ── 콘텐츠 최대 너비 ── */
.block-container {
    max-width: 1080px !important;
    padding: 0 32px 60px !important;
    margin: 0 auto !important;
}

/* ── 네비게이션바 ── */
.navbar {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0 32px; height: 60px;
    background: #fff; border-bottom: 1px solid #E5E5E3;
    margin: 0 -32px 0;
}
.navbar-logo { color: #1B4D2E; font-size: 18px; font-weight: 900; letter-spacing: -0.3px; }

/* ── 기본 입력창 — 외부 컨테이너 테두리 제거 ── */
[data-testid="stTextInput"] > div,
[data-testid="stTextInput"] > div > div {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
}
.stTextInput input {
    border-radius: 12px !important;
    padding: 13px 18px !important;
    font-size: 15px !important;
    color: #111 !important;
    border: 1.5px solid #D8D8D6 !important;
    background: #fff !important;
    transition: border-color .2s;
    box-shadow: 0 1px 3px rgba(0,0,0,.06) !important;
}
.stTextInput input::placeholder { color: #888 !important; opacity: 1 !important; }
.stTextInput input:focus {
    border-color: #1B4D2E !important;
    box-shadow: 0 0 0 3px rgba(27,77,46,.1) !important;
    outline: none !important;
}

/* ── HOT ISSUE 카드 상단: 제목 영역 ── */
.hot-card-top {
    background: #fff;
    border-radius: 16px 16px 0 0;
    padding: 20px 20px 14px;
    border-left: 1px solid #EBEBEB;
    border-right: 1px solid #EBEBEB;
    border-top: 1px solid #EBEBEB;
}

/* ── HOT ISSUE 카드 하단: 태그 버튼 행 ── */
[data-testid="column"] [data-testid="stHorizontalBlock"] {
    background: #fff !important;
    border-radius: 0 0 16px 16px !important;
    padding: 4px 16px 18px !important;
    margin-top: 0 !important;
    border-left: 1px solid #EBEBEB !important;
    border-right: 1px solid #EBEBEB !important;
    border-bottom: 1px solid #EBEBEB !important;
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    gap: 6px !important;
}

/* ── 태그 컬럼: 내용 너비만큼만 차지 ── */
[data-testid="column"] [data-testid="stHorizontalBlock"] > [data-testid="column"] {
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 0 !important;
    padding: 2px 0 !important;
}

/* ── 태그 버튼: pill 스타일, 텍스트 한 줄 유지 ── */
[data-testid="column"] [data-testid="stHorizontalBlock"] .stButton > button {
    background: #F0F0EE !important;
    color: #333 !important;
    border-radius: 20px !important;
    padding: 5px 12px !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    height: auto !important;
    width: auto !important;
    white-space: nowrap !important;
    box-shadow: none !important;
    transform: none !important;
}
[data-testid="column"] [data-testid="stHorizontalBlock"] .stButton > button:hover {
    background: #E2E2E0 !important;
    transform: none !important;
}

/* ── 기본 버튼 (초록) ── */
.stButton > button {
    background: #1B4D2E !important; color: #fff !important;
    border-radius: 10px !important; border: none !important;
    padding: 11px 20px !important;
    font-size: 14px !important; font-weight: 600 !important;
    transition: background .15s, transform .1s !important;
}
.stButton > button:hover { background: #163D24 !important; transform: translateY(-1px); }
.stButton > button:active { transform: translateY(0); }

/* ── 카드 ── */
.card {
    background: #fff; border-radius: 16px;
    padding: 24px; margin-bottom: 0;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.card-dark {
    background: #1B4D2E; border-radius: 16px;
    padding: 28px; color: #fff;
    box-shadow: 0 2px 8px rgba(27,77,46,.25);
}

/* ── HOT ISSUE 배지 ── */
.hot-badge {
    display: inline-block; background: #E8F5E9; color: #1B4D2E;
    border-radius: 20px; padding: 3px 10px;
    font-size: 11px; font-weight: 700; letter-spacing: .5px;
    margin-bottom: 10px;
}

/* ── 섹션 타이틀 ── */
.section-header {
    display: flex; justify-content: space-between; align-items: center;
    margin: 36px 0 14px;
}
.section-title { font-size: 17px; font-weight: 700; color: #111; }
.section-more  { font-size: 13px; color: #1B4D2E; cursor: pointer; }

/* ── 실수 Top 카드 ── */
.mistake-card {
    background: #fff; border-radius: 12px;
    padding: 16px 14px;
    box-shadow: 0 1px 3px rgba(0,0,0,.05);
    height: 80px;
    display: flex; flex-direction: column;
    justify-content: flex-start;
    margin-bottom: 8px;
}
.rank-num {
    font-size: 11px; font-weight: 800;
    color: #1B4D2E; margin-bottom: 6px;
    line-height: 1;
}
.mistake-text {
    font-size: 13px; color: #333;
    line-height: 1.4;
    word-break: keep-all;
}

/* ── 질문 화면 ── */
.process-bg {
    font-size: 72px; font-weight: 900; color: #EAEDE9;
    text-align: center; line-height: 1; letter-spacing: 6px;
    user-select: none;
}
.step-badge {
    display: inline-block; background: #1B4D2E; color: #fff;
    border-radius: 20px; padding: 4px 14px;
    font-size: 11px; font-weight: 700; letter-spacing: .5px;
}
.question-title {
    font-size: 36px; font-weight: 900; color: #1B4D2E;
    text-align: center; margin: 12px 0 8px; line-height: 1.2;
}
.question-desc {
    font-size: 14px; color: #777; text-align: center;
    max-width: 480px; margin: 0 auto 36px; line-height: 1.6;
}

/* ── eco 박스 ── */
.eco-box {
    background: #F6F8F6; border-radius: 12px;
    padding: 18px 22px; display: flex; gap: 14px; align-items: flex-start;
    max-width: 620px; margin: 28px auto 0;
}
.eco-icon {
    background: #E2EDE4; border-radius: 8px;
    width: 34px; height: 34px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center; font-size: 17px;
}

/* ── 결과 카드 ── */
.result-wrap {
    max-width: 680px; margin: 36px auto 0;
    background: #fff; border-radius: 20px;
    padding: 44px 40px; text-align: center;
    box-shadow: 0 2px 12px rgba(0,0,0,.07);
}
.result-badge {
    display: inline-block; background: #D4EDDA; color: #1B4D2E;
    border-radius: 20px; padding: 5px 14px;
    font-size: 12px; font-weight: 700; margin-bottom: 20px;
}
.result-title {
    font-size: 40px; font-weight: 900; color: #1B4D2E;
    line-height: 1.2; margin-bottom: 0;
}

/* ── 배출 요령 카드 ── */
.steps-card {
    max-width: 680px; margin: 24px auto;
    background: #F5F5F3; border-radius: 14px; padding: 24px 28px;
}
.steps-title { font-size: 15px; font-weight: 700; margin-bottom: 18px; color: #222; }
.step-row { display: flex; align-items: flex-start; gap: 13px; margin-bottom: 14px; }
.step-num {
    background: #1B4D2E; color: #fff;
    border-radius: 50%; width: 26px; height: 26px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700;
}
.step-text { font-size: 14px; color: #333; padding-top: 4px; line-height: 1.5; }

/* ── 탄소 숫자 ── */
.carbon-value { font-size: 42px; font-weight: 900; color: #fff; margin: 6px 0 4px; line-height: 1; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 데이터 로드
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
        "state": "home", "query": "",
        "matched_item": None, "tree": None, "current_q": None,
        "step_num": 1, "guide_message": None,
        "result_text": None, "result_reason": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ──────────────────────────────────────────────
# 헬퍼: 세션 초기화
# ──────────────────────────────────────────────
def reset_session():
    for k in ["state", "query", "matched_item", "tree", "current_q",
              "step_num", "guide_message", "result_text", "result_reason"]:
        if k in st.session_state:
            del st.session_state[k]

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
    extra = matched.get("extra_questions")

    if extra:
        eq = extra[0]
        st.session_state.current_q = {
            "id": eq["id"], "text": eq["question"],
            "description": "", "eco_title": "왜 중요한가요?", "eco_desc": "",
            "_extra_data": eq, "_is_extra": True,
        }
    else:
        tree = get_tree(matched["category"])
        if tree is None:
            st.session_state.result_text   = matched["category"] + " 분리배출"
            st.session_state.result_reason = matched.get("note", "")
            st.session_state.state         = "result"
            append_usage_log(query, matched, st.session_state.result_text)
            return
        first_q = get_first_question(tree, skip)
        if first_q is None:
            st.session_state.result_text   = matched["category"] + " 분리배출"
            st.session_state.result_reason = matched.get("note", "")
            st.session_state.state         = "result"
            append_usage_log(query, matched, st.session_state.result_text)
            return
        st.session_state.tree      = tree
        st.session_state.current_q = first_q

    st.session_state.state         = "questioning"
    st.session_state.step_num      = 1
    st.session_state.guide_message = None

# ──────────────────────────────────────────────
# 헬퍼: 답변 처리
# ──────────────────────────────────────────────
def handle_answer(answer: bool):
    current_q = st.session_state.current_q
    matched   = st.session_state.matched_item
    skip      = matched.get("skip_questions", [])

    if current_q.get("_is_extra"):
        eq     = current_q["_extra_data"]
        branch = eq["yes"] if answer else eq["no"]
        if "result" in branch:
            st.session_state.result_text   = branch["result"]
            st.session_state.result_reason = branch.get("reason", "")
            st.session_state.state         = "result"
            append_usage_log(st.session_state.query, matched, branch["result"])
            return
        if branch.get("next") == "category_tree":
            extra_list = matched.get("extra_questions", [])
            idx = next((i for i, e in enumerate(extra_list) if e["id"] == eq["id"]), -1)
            if idx + 1 < len(extra_list):
                nxt = extra_list[idx + 1]
                st.session_state.current_q = {
                    "id": nxt["id"], "text": nxt["question"],
                    "description": "", "eco_title": "왜 중요한가요?", "eco_desc": "",
                    "_extra_data": nxt, "_is_extra": True,
                }
                st.session_state.step_num += 1
            else:
                tree = get_tree(matched["category"])
                if tree is None:
                    st.session_state.result_text   = matched["category"] + " 분리배출"
                    st.session_state.result_reason = matched.get("note", "")
                    st.session_state.state         = "result"
                    append_usage_log(st.session_state.query, matched, st.session_state.result_text)
                    return
                first_q = get_first_question(tree, skip)
                if first_q is None:
                    st.session_state.result_text   = matched["category"] + " 분리배출"
                    st.session_state.result_reason = matched.get("note", "")
                    st.session_state.state         = "result"
                    append_usage_log(st.session_state.query, matched, st.session_state.result_text)
                    return
                st.session_state.tree          = tree
                st.session_state.current_q     = first_q
                st.session_state.step_num     += 1
                st.session_state.guide_message = None
        return

    outcome = process_answer(st.session_state.tree, current_q["id"], answer, skip)
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

# ──────────────────────────────────────────────
# 공통 네비게이션바
# ──────────────────────────────────────────────
def render_navbar():
    st.markdown("""
    <div class="navbar">
      <span class="navbar-logo">Re:Sort</span>
      <span style="font-size:13px; color:#999;">♻️ 올바른 분리배출 가이드</span>
    </div>
    <div style="height:28px;"></div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
# 화면 1 — 홈
# ══════════════════════════════════════════════
def render_home():
    # 태그 버튼을 작은 회색 pill로 만드는 CSS (홈 전용 오버라이드)
    st.markdown("""
    <style>
    /* 태그 버튼: 작은 회색 pill */
    div[data-testid="stHorizontalBlock"] .stButton > button {
        background: #F0F0EE !important;
        color: #333 !important;
        border-radius: 20px !important;
        padding: 6px 14px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        height: auto !important;
        width: auto !important;
        box-shadow: none !important;
        transform: none !important;
    }
    div[data-testid="stHorizontalBlock"] .stButton > button:hover {
        background: #E2E2E0 !important;
        transform: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    render_navbar()

    # ── 히어로 ──
    st.markdown("""
    <div style="padding: 8px 0 32px;">
      <div style="font-size:46px; font-weight:900; line-height:1.15; color:#1B4D2E; margin-bottom:12px;">
        무엇이든 물어보세요.<br>지구의 내일을 위해.
      </div>
      <div style="font-size:14px; color:#777; line-height:1.7;">
        버리기 어려운 쓰레기, 어떻게 분리배출해야 할까요?<br>
        정확한 가이드를 통해 자원 순환에 동참해 주세요.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 검색창 ──
    st.markdown("""
    <style>
    /* 검색 행: 컬럼 좌우 패딩 제거 → 밑 섹션과 가로 폭 일치 */
    [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] {
        padding-left: 0 !important;
        padding-right: 0 !important;
    }
    [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:first-child {
        padding-right: 10px !important;
    }
    /* 검색 버튼 컬럼: input과 수직 정렬 */
    [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:last-child {
        display: flex !important;
        align-items: flex-end !important;
        padding-left: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    col_input, col_btn = st.columns([6, 1], gap="small")
    with col_input:
        query = st.text_input(
            "품목 검색", placeholder="예: 배달 음식 용기, 폐건전지, 우유팩",
            label_visibility="collapsed", key="home_input",
        )
    with col_btn:
        search_btn = st.button("검색 →", use_container_width=True, key="home_search_btn")

    if search_btn and query:
        run_search(query)
        st.rerun()

    if st.session_state.get("_tag_query"):
        run_search(st.session_state._tag_query)
        st.session_state._tag_query = None
        st.rerun()

    if st.session_state.state == "no_match":
        st.warning(f"**'{st.session_state.query}'** 에 해당하는 품목을 찾지 못했어요. 다른 표현으로 검색해보세요.")
        st.session_state.state = "home"

    st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)

    # ── HOT ISSUE + 탄소 카드 ──
    col_hot, col_carbon = st.columns([3, 2], gap="medium")

    with col_hot:
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

        # 카드 상단: 흰 배경 + 위쪽 둥근 모서리 (태그 행과 테두리 공유)
        st.markdown("""
        <div class="hot-card-top">
          <div class="hot-badge">HOT ISSUE</div>
          <div style="font-size:15px; font-weight:700; color:#111; margin-top:6px;">
            지금 가장 많이 찾아보는 품목
          </div>
        </div>
        """, unsafe_allow_html=True)

        tag_cols = st.columns(len(top5))
        for i, tag in enumerate(top5):
            with tag_cols[i]:
                if st.button(tag, key=f"tag_{i}"):
                    st.session_state._tag_query = tag
                    st.rerun()

    with col_carbon:
        carbon_factors = get_carbon_factors()
        usage_log2     = load_usage_log()
        carbon_val     = get_today_carbon(usage_log2, carbon_factors)
        carbon_str     = format_carbon(carbon_val)
        st.markdown(f"""
        <div class="card-dark" style="min-height:160px;">
          <div style="font-size:22px; margin-bottom:6px;">🌿</div>
          <div style="font-size:12px; opacity:.75; margin-bottom:2px;">오늘 여러분이 줄인 탄소발자국</div>
          <div class="carbon-value">{carbon_str}</div>
          <div style="font-size:12px; opacity:.6;">우리의 분리배출로 아낀 탄소량</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ── 자주 틀리는 실수 Top ──
    st.markdown("""
    <div style="margin:36px 0 14px;">
      <span style="font-size:17px; font-weight:700; color:#111;">자주 틀리는 실수 Top 10</span>
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
        top_mistakes = []

    # 로그가 없거나 일반쓰레기 결과가 없으면 기본값 10개
    if not top_mistakes:
        top_mistakes = [
            "씻지 않은 음식 용기", "라벨 붙은 페트병",
            "코팅된 종이 전단지", "깨진 유리 조각",
            "영수증·감열지", "색상 있는 스티로폼",
            "뚜껑 분리 안 한 페트병", "음식물 묻은 캔",
            "일반 쓰레기봉투에 배터리 배출", "스프레이 캔 가스 미제거",
        ]

    # 5열 × 2행으로 10개 표시, 카드 높이 고정
    cols = st.columns(5, gap="small")
    for i, mistake in enumerate(top_mistakes[:10]):
        with cols[i % 5]:
            st.markdown(f"""
            <div class="mistake-card">
              <div class="rank-num">{i+1:02d}</div>
              <div class="mistake-text">{mistake}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── 푸터 ──
    st.markdown("""
    <div style="margin-top:60px; padding-top:28px; border-top:1px solid #E5E5E3;
                display:flex; justify-content:space-between; align-items:flex-start;">
      <div>
        <div style="font-size:15px; font-weight:700; color:#1B4D2E; margin-bottom:6px;">Re:Sort</div>
        <div style="font-size:12px; color:#AAA; line-height:1.7;">
          공공 데이터 기반의 지능형 분리배출 가이드 시스템.<br>환경을 위한 당신의 노력을 응원합니다.
        </div>
      </div>
      <div style="display:flex; gap:40px; font-size:12px; color:#AAA;">
        <div>
          <div style="font-weight:600; color:#555; margin-bottom:6px;">RESOURCES</div>
          <div>API Documentation</div><div>Data Sources</div>
        </div>
        <div>
          <div style="font-weight:600; color:#555; margin-bottom:6px;">LEGAL</div>
          <div>Privacy Policy</div><div>Terms of Use</div>
        </div>
      </div>
    </div>
    <div style="margin-top:20px; font-size:11px; color:#CCC; padding-bottom:20px;">
      © 2024 RE:SORT ARCHIVE PROJECT. ALL RIGHTS RESERVED.
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
# 화면 2 — 질문
# ══════════════════════════════════════════════
def render_questioning():
    current_q = st.session_state.current_q

    # 질문 화면 전용 CSS: YES(초록 대형) / NO(회색 대형) / 뒤로가기(작은 ghost)
    st.markdown("""
    <style>
    /* YES 버튼: 첫 번째 column */
    [data-testid="column"]:first-child .stButton > button {
        background: #1B4D2E !important;
        color: #fff !important;
        height: 160px !important;
        font-size: 26px !important;
        font-weight: 900 !important;
        border-radius: 18px !important;
        letter-spacing: 1px !important;
    }
    [data-testid="column"]:first-child .stButton > button:hover {
        background: #163D24 !important;
        transform: translateY(-2px) !important;
    }
    /* NO 버튼: 두 번째 column */
    [data-testid="column"]:last-child .stButton > button {
        background: #EEEEED !important;
        color: #444 !important;
        height: 160px !important;
        font-size: 26px !important;
        font-weight: 900 !important;
        border-radius: 18px !important;
    }
    [data-testid="column"]:last-child .stButton > button:hover {
        background: #E2E2E0 !important;
        transform: translateY(-2px) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    render_navbar()

    # 안내 메시지
    if st.session_state.guide_message:
        st.info(f"💡 {st.session_state.guide_message}")
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # PROCESS 배경 + STEP + 질문
    st.markdown(f"""
    <div style="text-align:center; padding: 16px 0 0;">
      <div class="process-bg">PROCESS</div>
      <div style="margin-top:-48px; padding-bottom: 8px;">
        <span class="step-badge">STEP {st.session_state.step_num:02d}</span>
        <div class="question-title">{current_q["text"]}</div>
        <div class="question-desc">{current_q.get("description", "")}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # YES / NO 버튼
    col_yes, col_no = st.columns(2, gap="medium")
    with col_yes:
        if st.button("✓  예", key="yes_btn", use_container_width=True):
            handle_answer(True)
            st.rerun()
    with col_no:
        if st.button("✕  아니오", key="no_btn", use_container_width=True):
            handle_answer(False)
            st.rerun()

    # eco 박스
    eco_title = current_q.get("eco_title", "왜 중요한가요?")
    eco_desc  = current_q.get("eco_desc", "")
    if eco_desc:
        st.markdown(f"""
        <div class="eco-box">
          <div class="eco-icon">💡</div>
          <div>
            <div style="font-size:14px; font-weight:700; margin-bottom:4px;">{eco_title}</div>
            <div style="font-size:13px; color:#555; line-height:1.6;">{eco_desc}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # 처음으로 버튼 (ghost style)
    st.markdown("""
    <div style="height:28px;"></div>
    <style>
    div[data-testid="stVerticalBlock"] > div:last-child .stButton > button {
        background: transparent !important;
        color: #888 !important;
        border: 1px solid #D8D8D6 !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        height: auto !important;
        padding: 8px 20px !important;
        width: auto !important;
        border-radius: 8px !important;
        box-shadow: none !important;
    }
    div[data-testid="stVerticalBlock"] > div:last-child .stButton > button:hover {
        background: #f5f5f3 !important;
        transform: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    _, col_back, _ = st.columns([3, 1, 3])
    with col_back:
        if st.button("← 처음으로", key="back_home", use_container_width=True):
            reset_session()
            st.rerun()

    # 하단 배너
    st.markdown("""
    <div style="background:#1B4D2E; border-radius:14px; padding:32px;
                margin-top:32px; text-align:center;
                color:#fff; font-size:18px; font-weight:700; letter-spacing:.3px;">
      작은 실천이 만드는 큰 변화 🌱
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
# 화면 3 — 결과
# ══════════════════════════════════════════════
def render_result():
    matched     = st.session_state.matched_item
    result_text = st.session_state.result_text
    reason      = st.session_state.result_reason or matched.get("note", "")

    render_navbar()

    # 결과 카드
    st.markdown(f"""
    <div class="result-wrap">
      <div class="result-badge">분석 완료 · {matched["name"]}</div>
      <div class="result-title">{result_text}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # 다시 검색 버튼
    _, col_btn, _ = st.columns([2, 1, 2])
    with col_btn:
        if st.button("↺  다시 검색", use_container_width=True, key="retry_btn"):
            reset_session()
            st.rerun()

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # 배출 요령
    steps = matched.get("steps", [])
    if steps:
        rows_html = "".join(
            f'<div class="step-row">'
            f'<div class="step-num">{i+1}</div>'
            f'<div class="step-text">{s}</div>'
            f'</div>'
            for i, s in enumerate(steps)
        )
        st.markdown(f"""
        <div class="steps-card">
          <div class="steps-title">📋 정확한 배출 요령</div>
          {rows_html}
        </div>
        """, unsafe_allow_html=True)

    # 환경 설명 note
    if reason:
        st.markdown(f"""
        <div style="max-width:680px; margin:16px auto 40px;
                    background:#F6F8F6; border-radius:12px; padding:16px 20px;
                    font-size:13px; color:#666; line-height:1.7;">
          💬 {reason}
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
