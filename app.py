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
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;900&family=Playfair+Display:wght@700;900&family=DM+Sans:wght@400;600;700&display=swap');

/* ── 기본 리셋 ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
html, body { overflow-x: hidden !important; max-width: 100vw !important; }
html::-webkit-scrollbar,
body::-webkit-scrollbar,
*::-webkit-scrollbar { width: 0 !important; display: none !important; }
html { scrollbar-width: none !important; -ms-overflow-style: none !important; }
body { scrollbar-width: none !important; -ms-overflow-style: none !important; }
* { scrollbar-width: none !important; -ms-overflow-style: none !important; }
.stApp { background-color: #EEF4F0; overflow-x: hidden !important; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }

/* ── 콘텐츠 최대 너비 ── */
.block-container {
    max-width: 1080px !important;
    padding: 0 48px 60px !important;
    margin: 0 auto !important;
    overflow-x: hidden !important;
}

/* Streamlit 기본 상단 여백 제거 */
.block-container > div:first-child { padding-top: 0 !important; }
div[data-testid="stAppViewBlockContainer"] { padding-top: 0 !important; }

/* ── 모바일 반응형 ── */
@media (max-width: 768px) {
    /* 기본 레이아웃 */
    .block-container {
        padding: 0 14px 40px !important;
        width: 100% !important;
        max-width: 100% !important;
    }
    /* 히어로 타이틀 */
    .hero-title-wrap div {
        font-size: 28px !important;
        letter-spacing: -0.5px !important;
        line-height: 1.3 !important;
    }
    /* 탄소 카드 세로 배치 */
    .carbon-inner {
        flex-direction: column !important;
        gap: 16px !important;
    }
    .carbon-inner > div:first-child { width: 100% !important; }
    .carbon-inner > div:last-child {
        text-align: left !important;
        width: 100% !important;
    }
    /* 탄소 카드 진행바 100% */
    .carbon-inner > div:last-child > div:nth-child(2) {
        width: 100% !important;
    }
    /* 탄소 숫자 크기 */
    .carbon-inner div[style*="font-size:52px"] {
        font-size: 40px !important;
    }
    /* 실수 카드 2열 */
    .mistake-card {
        height: auto !important;
        min-height: 120px !important;
    }
    /* column 기본 */
    [data-testid="column"] {
        min-width: 0 !important;
        overflow: hidden !important;
    }
    /* 히어로 타이틀 */
    .hero-title-text { font-size: 38px !important; letter-spacing: -1px !important; }
    /* 네비바 */
    .navbar { padding: 0 16px !important; }
    /* 질문 화면 제목 */
    .question-title { font-size: 26px !important; }
}

/* ── 네비게이션바 ── */
.navbar {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0 28px; height: 56px;
    background: rgba(255,255,255,.85);
    backdrop-filter: blur(8px);
    border-radius: 16px;
    box-shadow: 0 2px 12px rgba(27,77,46,.08);
    border: 1px solid rgba(27,77,46,.07);
    margin: 16px 0 0;
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
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    margin-top: 0 !important;
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    gap: 8px !important;
}

/* ── 태그 컬럼: 내용 너비만큼만 차지 ── */
[data-testid="column"] [data-testid="stHorizontalBlock"] > [data-testid="column"] {
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 0 !important;
    padding: 2px 0 !important;
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
.carbon-value { font-size: 42px; font-weight: 700; color: #fff; margin: 6px 0 4px; line-height: 1; font-family: 'DM Sans', sans-serif; letter-spacing: -1px; }
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
        "nickname": "",
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
        "nickname":        st.session_state.get("nickname", ""),
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
    if not query or not isinstance(query, str):
        return
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
    is_home = st.session_state.get("state", "home") in ("home", "no_match")
    nav_label = "Home" if is_home else "Guide"
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;
                padding:18px 0;border-bottom:1px solid rgba(0,0,0,.07);margin-bottom:0;">
      <span style="font-size:17px;font-weight:800;color:#1a1a1a;letter-spacing:-0.5px;">Re:Sort</span>
      <span style="font-size:13px;font-weight:600;color:#1a1a1a;
                   border-bottom:2px solid #1a1a1a;padding-bottom:1px;cursor:pointer;">{nav_label}</span>
    </div>
    """, unsafe_allow_html=True)

def render_home():
    st.markdown("""
    <style>
    .stApp { background: #F0F0EE !important; }
    /* 기본 버튼 — 질문화면용 초록 */
    .stButton > button {
        background: #1B4D2E !important; color: #fff !important;
        border-radius: 10px !important; border: none !important;
        padding: 11px 20px !important; font-size: 14px !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover { background: #163D24 !important; }
    /* 홈 태그 버튼 */
    .tag-area .stButton > button {
        background: #fff !important; color: #333 !important;
        border: 1.5px solid rgba(0,0,0,.12) !important;
        border-radius: 999px !important; padding: 7px 18px !important;
        font-size: 13px !important; font-weight: 500 !important;
        height: auto !important; width: auto !important;
        box-shadow: 0 1px 4px rgba(0,0,0,.05) !important;
        white-space: nowrap !important;
    }
    .tag-area .stButton > button:hover {
        background: #1a1a1a !important; color: #fff !important;
        border-color: #1a1a1a !important;
    }
    /* 컬럼 투명 */
    div[data-testid="column"] > div[data-testid="stVerticalBlock"] {
        background: transparent !important;
        box-shadow: none !important; border: none !important; padding: 0 !important;
    }
    /* 실수 카드 hover */
    .mistake-card { transition: transform .15s, box-shadow .15s; }
    .mistake-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,.1) !important; }
    </style>
    """, unsafe_allow_html=True)

    render_navbar()

    # ── 히어로 제목 + 닉네임 + 검색창 통합 ──
    st.markdown("""
    <style>
    /* 검색 영역 전체 */
    .search-section {
        max-width: 520px;
        margin: 28px auto 0;
    }
    /* 공통 input 스타일 */
    .search-section .stTextInput > div,
    .search-section .stTextInput > div > div {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
        padding: 0 !important;
    }
    /* 닉네임 */
    .nickname-wrap .stTextInput input {
        border-radius: 12px !important;
        border: 1.5px solid rgba(0,0,0,.1) !important;
        background: #fff !important;
        padding: 12px 18px !important;
        font-size: 14px !important;
        color: #222 !important;
        box-shadow: none !important;
    }
    .nickname-wrap .stTextInput input:focus {
        border-color: #1B4D2E !important;
        box-shadow: 0 0 0 3px rgba(27,77,46,.08) !important;
        outline: none !important;
    }
    /* 검색창 */
    .search-wrap .stTextInput input {
        border-radius: 999px !important;
        border: 1.5px solid rgba(0,0,0,.09) !important;
        background: #fff !important;
        box-shadow: 0 2px 16px rgba(0,0,0,.07) !important;
        padding: 14px 22px !important;
        font-size: 15px !important;
        color: #222 !important;
    }
    .search-wrap .stTextInput input::placeholder { color: #bbb !important; }
    .search-wrap .stTextInput input:focus {
        border-color: #1B4D2E !important;
        box-shadow: 0 0 0 3px rgba(27,77,46,.1) !important;
        outline: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 제목
    st.markdown("""
    <div style="text-align:center;margin:20px 0 24px;">
      <div style="font-size:40px;font-weight:900;line-height:1.25;color:#1a1a1a;
                  letter-spacing:-1px;font-family:'Noto Sans KR',sans-serif;">
        지속 가능한 미래를 위한<br>
        <span style="color:#1B4D2E;">똑똑한 분리배출</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # 닉네임 + 검색창
    st.markdown('<div class="search-section">', unsafe_allow_html=True)
    st.markdown('<div class="nickname-wrap">', unsafe_allow_html=True)
    nickname_input = st.text_input(
        "닉네임", placeholder="닉네임을 입력해주세요 (필수)",
        label_visibility="collapsed", key="nickname_input",
    )
    if nickname_input:
        st.session_state.nickname = nickname_input.strip()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    st.markdown('<div class="search-wrap">', unsafe_allow_html=True)
    query = st.text_input(
        "검색", placeholder="어떤 품목을 버리시나요? (Enter로 검색)",
        label_visibility="collapsed", key="home_input",
    )
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    if query and query != st.session_state.get("_last_query", ""):
        if not st.session_state.get("nickname", "").strip():
            st.warning("닉네임을 먼저 입력해주세요.")
        else:
            st.session_state["_last_query"] = query
            run_search(query)
            st.rerun()

    # query param으로 태그 클릭 처리
    params = st.query_params
    if "q" in params:
        tag_query = params["q"]
        st.query_params.clear()
        if tag_query and isinstance(tag_query, str):
            run_search(tag_query)
            st.rerun()

    if st.session_state.state == "no_match":
        _, cw, _ = st.columns([0.3, 5, 0.3])
        with cw:
            st.warning(f"**'{st.session_state.query}'** 에 해당하는 품목을 찾지 못했어요.")
        st.session_state.state = "home"

    # ── 인기 태그 ──
    DEFAULT_TAGS = ["플라스틱 컵", "배달 용기", "알루미늄 캔", "종이팩"]
    usage_log = load_usage_log()
    if usage_log:
        from collections import Counter
        from datetime import date
        today = date.today().isoformat()
        # 오늘 top4 — 실제 품목 검색(matched_item_id 있는 것)만 카운팅
        today_inputs = [
            e["user_input"] for e in usage_log
            if e.get("timestamp", "").startswith(today)
            and e.get("user_input")
            and e.get("matched_item_id")
        ]
        top4 = [item for item, _ in Counter(today_inputs).most_common(4)]
        # 오늘 데이터 4개 미만이면 전체 기간 top으로 채움
        if len(top4) < 4:
            all_inputs = [e["user_input"] for e in usage_log
                          if e.get("user_input") and e.get("matched_item_id")]
            for item, _ in Counter(all_inputs).most_common(20):
                if item not in top4:
                    top4.append(item)
                if len(top4) == 4:
                    break
        # 그래도 부족하면 기본값으로 채움
        for tag in DEFAULT_TAGS:
            if len(top4) == 4:
                break
            if tag not in top4:
                top4.append(tag)
    else:
        top4 = DEFAULT_TAGS

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # ── 인기 태그 버튼 (중앙 정렬) ──
    tag_html = "".join([
        f'<a href="?q={tag}" target="_self" style="'
        f'display:inline-block;background:#fff;color:#444;'
        f'border:1.5px solid rgba(0,0,0,.1);border-radius:999px;'
        f'padding:7px 18px;font-size:13px;font-weight:500;'
        f'text-decoration:none;white-space:nowrap;'
        f'box-shadow:0 1px 4px rgba(0,0,0,.06);'
        f'transition:background .15s,color .15s;'
        f'">{tag}</a>'
        for tag in top4
    ])
    st.markdown(f"""
    <div style="display:flex;justify-content:center;align-items:center;
                gap:8px;flex-wrap:wrap;margin-top:4px;">
      <span style="font-size:12px;color:#999;font-weight:500;white-space:nowrap;">인기 검색어</span>
      {tag_html}
    </div>
    """, unsafe_allow_html=True)



    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

    # ── 탄소 카드 + 사용자 현황 ──
    carbon_factors = get_carbon_factors()
    usage_log2 = load_usage_log()
    carbon_val = get_today_carbon(usage_log2, carbon_factors)
    carbon_str = format_carbon(carbon_val)
    num_str = carbon_str.replace(' kg', '')

    # 사용자 현황 Top5 계산
    from collections import Counter
    nickname_counts = Counter(
        e.get("nickname", "") for e in usage_log2
        if e.get("nickname", "").strip() and e.get("matched_item_id")
    )
    top5_users = nickname_counts.most_common(5)

    # Top5 HTML
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    users_rows = ""
    for idx, (name, cnt) in enumerate(top5_users):
        users_rows += f"""
        <div style="display:flex;align-items:center;justify-content:space-between;
                    padding:7px 0;border-bottom:1px solid rgba(0,0,0,.06);">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:14px;">{medals[idx]}</span>
            <span style="font-size:13px;font-weight:600;color:#1a1a1a;">{name}</span>
          </div>
          <span style="font-size:12px;color:#888;font-weight:500;">{cnt}회</span>
        </div>
        """
    if not top5_users:
        users_rows = '<div style="font-size:13px;color:#aaa;text-align:center;padding:16px 0;">아직 데이터가 없어요</div>'

    col_carbon, col_users = st.columns([1, 1], gap="medium")

    with col_carbon:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1a3a2a 0%,#1B4D2E 60%,#2a6640 100%);
                    border-radius:20px;padding:20px 18px;height:100%;
                    box-shadow:0 4px 16px rgba(27,77,46,.2);">
          <div style="display:inline-flex;align-items:center;gap:5px;
                      background:rgba(255,255,255,.15);border-radius:999px;
                      padding:3px 10px;margin-bottom:10px;">
            <span style="width:5px;height:5px;background:#4ade80;border-radius:50%;display:inline-block;"></span>
            <span style="font-size:10px;color:rgba(255,255,255,.8);font-weight:600;letter-spacing:.5px;">TODAY'S IMPACT</span>
          </div>
          <div style="font-size:11px;color:rgba(255,255,255,.6);margin-bottom:4px;">오늘 줄인 탄소발자국</div>
          <div style="font-size:36px;font-weight:900;color:#fff;letter-spacing:-1px;line-height:1;
                      font-family:'DM Sans',sans-serif;">
            {num_str}<span style="font-size:16px;font-weight:600;color:rgba(255,255,255,.6);margin-left:4px;">kg</span>
          </div>
          <div style="margin-top:14px;">
            <div style="width:100%;height:4px;background:rgba(255,255,255,.15);border-radius:999px;overflow:hidden;">
              <div style="width:84%;height:100%;background:#4ade80;border-radius:999px;"></div>
            </div>
            <div style="font-size:11px;color:rgba(255,255,255,.5);margin-top:5px;">월간 목표 84%</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col_users:
        st.markdown(f"""
        <div style="background:#fff;border-radius:20px;padding:20px 18px;height:100%;
                    border:1px solid rgba(0,0,0,.07);box-shadow:0 2px 8px rgba(0,0,0,.05);">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:12px;">
            <span style="font-size:13px;font-weight:700;color:#1a1a1a;">🏆 검색 TOP 5</span>
            <span style="font-size:10px;color:#aaa;background:#f5f5f3;border-radius:999px;padding:2px 8px;">실시간</span>
          </div>
          {users_rows}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

    # ── 자주 틀리는 실수 Top 10 ──
    st.markdown("""
    <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:20px;">
      <div>
        <div style="font-size:22px;font-weight:800;color:#1a1a1a;letter-spacing:-0.5px;">자주 틀리는 실수 Top 10</div>
        <div style="font-size:13px;color:#999;margin-top:4px;">가장 많은 사용자들이 헷갈려 하는 분리배출 사례</div>
      </div>

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

    if not top_mistakes:
        top_mistakes = [
            "씻지 않은 음식 용기", "라벨 붙은 페트병",
            "코팅된 종이 전단지", "깨진 유리 조각",
            "영수증·감열지", "색상 있는 스티로폼",
            "뚜껑 분리 안 한 페트병", "음식물 묻은 캔",
            "일반 쓰레기봉투에 배터리 배출", "스프레이 캔 가스 미제거",
        ]

    icons = ["🍕","☕","🧊","📄","🧾","🎨","🍶","🥫","🔋","💨"]
    descs = [
        "종이가 아닌 종량제봉투로 버려야 합니다.",
        "몸체는 종이, 뚜껑은 플라스틱으로 분리하세요.",
        "고흡수성 시 백은 전용 수거함에 배출하세요.",
        "비닐 코팅된 종이는 재활용이 불가능합니다.",
        "감열지는 재활용 불가, 일반쓰레기로 배출하세요.",
        "유색 스티로폼은 재활용이 불가능합니다.",
        "뚜껑을 분리 후 각각 배출하세요.",
        "음식물을 깨끗이 씻어서 배출하세요.",
        "약국이나 보건소의 전용 수거함을 이용하세요.",
        "가스를 완전히 제거 후 배출하세요.",
    ]

    mistakes_html = ""
    for i, mistake in enumerate(top_mistakes[:10]):
        is_top3 = i < 3
        mistakes_html += f"""
        <div style="background:#fff;border-radius:16px;padding:18px 20px;
                    margin-bottom:10px;border:1px solid rgba(0,0,0,.06);
                    display:flex;align-items:center;gap:16px;">
          <div style="background:{'#1a1a1a' if is_top3 else '#f0f0ee'};
                      color:{'#fff' if is_top3 else '#888'};
                      border-radius:10px;padding:6px 10px;
                      font-size:12px;font-weight:800;flex-shrink:0;min-width:36px;text-align:center;">{i+1:02d}</div>
          <div style="flex:1;min-width:0;">
            <div style="font-size:15px;font-weight:700;color:#1a1a1a;margin-bottom:3px;word-break:keep-all;">{mistake}</div>
            <div style="font-size:12px;color:#999;line-height:1.5;word-break:keep-all;">{descs[i]}</div>
          </div>
          <div style="font-size:22px;flex-shrink:0;">{icons[i]}</div>
        </div>
        """
    st.markdown(mistakes_html, unsafe_allow_html=True)

    # ── 내 검색 기록 ──
    st.markdown("<div style='height:56px;'></div>", unsafe_allow_html=True)
    nickname = st.session_state.get("nickname", "").strip()
    if nickname:
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:20px;">
          <div>
            <div style="font-size:22px;font-weight:800;color:#1a1a1a;letter-spacing:-0.5px;">
              {nickname}님의 검색 기록
            </div>
            <div style="font-size:13px;color:#999;margin-top:4px;">최근 10건</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        my_log = load_usage_log()
        my_entries = [
            e for e in my_log
            if e.get("nickname", "") == nickname
        ][-10:][::-1]  # 최근 10건, 최신순

        if my_entries:
            for entry in my_entries:
                ts = entry.get("timestamp", "")[:16].replace("T", " ")
                user_input = entry.get("user_input", "")
                final_result = entry.get("final_result", "")
                category = entry.get("category", "")
                is_recycled = "종량제" not in str(final_result) and "반납" not in str(final_result)
                result_color = "#1B4D2E" if is_recycled else "#888"
                result_bg = "#E8F5E9" if is_recycled else "#F5F5F3"
                st.markdown(f"""
                <div style="background:#fff;border-radius:14px;padding:16px 20px;
                            margin-bottom:10px;border:1px solid rgba(0,0,0,.06);
                            display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                  <div>
                    <div style="font-size:15px;font-weight:700;color:#1a1a1a;margin-bottom:4px;">{user_input}</div>
                    <div style="font-size:12px;color:#aaa;">{ts} · {category}</div>
                  </div>
                  <div style="background:{result_bg};color:{result_color};
                              border-radius:8px;padding:5px 12px;
                              font-size:13px;font-weight:700;white-space:nowrap;">
                    {final_result}
                  </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#fff;border-radius:14px;padding:24px;text-align:center;
                        color:#aaa;font-size:14px;">
              아직 검색 기록이 없어요. 첫 검색을 시작해보세요! 🌿
            </div>
            """, unsafe_allow_html=True)

    # ── 푸터 ──
    st.markdown("""
    <div style="margin-top:80px;padding:28px 0;border-top:1px solid rgba(0,0,0,.07);
                display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
      <div style="font-size:12px;color:#999;">© 2026 Re:Sort. 버릴래말래.</div>
      <div style="display:flex;gap:24px;font-size:12px;color:#999;">
        <span>Privacy</span><span>Terms</span>
        <a href="mailto:hjeong326@korea.ac.kr" style="color:#999;text-decoration:none;">Contact</a>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_questioning():
    current_q = st.session_state.current_q

    st.markdown("""
    <style>
    .stApp { background: #F0F4F0 !important; }
    /* YES 카드 버튼 */
    [data-testid="column"]:first-child .stButton > button {
        background: #fff !important;
        color: #1B4D2E !important;
        height: 120px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        border-radius: 20px !important;
        border: 2px solid #1B4D2E !important;
        box-shadow: 0 2px 12px rgba(27,77,46,.1) !important;
        transition: all .15s !important;
    }
    [data-testid="column"]:first-child .stButton > button:hover {
        background: #1B4D2E !important;
        color: #fff !important;
        transform: translateY(-2px) !important;
    }
    /* NO 카드 버튼 */
    [data-testid="column"]:last-child .stButton > button {
        background: #fff !important;
        color: #666 !important;
        height: 120px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        border-radius: 20px !important;
        border: 2px solid #E0E0DE !important;
        box-shadow: 0 2px 12px rgba(0,0,0,.05) !important;
    }
    [data-testid="column"]:last-child .stButton > button:hover {
        background: #f5f5f3 !important;
        transform: translateY(-2px) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    render_navbar()

    # 안내 메시지
    if st.session_state.guide_message:
        _, cg, _ = st.columns([1, 4, 1])
        with cg:
            st.info(f"💡 {st.session_state.guide_message}")
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # STEP 배지 + 질문
    desc = current_q.get("description", "")
    st.markdown(f"""
    <div style="text-align:center;padding:48px 0 32px;">
      <div style="display:inline-block;background:#1B4D2E;color:#fff;
                  border-radius:999px;padding:4px 16px;font-size:11px;
                  font-weight:700;letter-spacing:1px;margin-bottom:20px;">
        ● STEP {st.session_state.step_num:02d}
      </div>
      <div style="font-size:clamp(22px,5vw,36px);font-weight:900;color:#1a1a1a;
                  line-height:1.25;letter-spacing:-1px;word-break:keep-all;">
        {current_q["text"]}
      </div>
      {"<div style='font-size:14px;color:#888;margin-top:12px;line-height:1.6;word-break:keep-all;max-width:480px;margin-left:auto;margin-right:auto;'>" + desc + "</div>" if desc else ""}
    </div>
    """, unsafe_allow_html=True)

    # YES / NO 카드 버튼
    _, col_btns, _ = st.columns([1, 4, 1])
    with col_btns:
        col_yes, col_no = st.columns(2, gap="medium")
        with col_yes:
            if st.button("✓  네, 했어요\n\n다음 단계로 이동", key="yes_btn", use_container_width=True):
                handle_answer(True)
                st.rerun()
        with col_no:
            if st.button("✕  아직이요\n\n가이드 확인하기", key="no_btn", use_container_width=True):
                handle_answer(False)
                st.rerun()

    # 분리배출 팁 박스
    eco_title = current_q.get("eco_title", "")
    eco_desc  = current_q.get("eco_desc", "")
    if eco_desc:
        st.markdown(f"""
        <div style="max-width:560px;margin:32px auto 0;
                    background:#fff;border-radius:16px;padding:20px 24px;
                    display:flex;gap:16px;align-items:flex-start;
                    box-shadow:0 1px 8px rgba(0,0,0,.06);">
          <div style="background:#E8F5E9;border-radius:10px;width:40px;height:40px;
                      flex-shrink:0;display:flex;align-items:center;justify-content:center;
                      font-size:18px;">♻️</div>
          <div>
            <div style="font-size:11px;font-weight:700;color:#1B4D2E;
                        letter-spacing:.8px;margin-bottom:6px;">분리배출 팁</div>
            <div style="font-size:13px;color:#555;line-height:1.6;">{eco_desc}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # 처음으로 버튼
    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
    _, col_back, _ = st.columns([2, 1, 2])
    with col_back:
        st.markdown("""
        <style>
        [data-testid="column"]:nth-child(2) .stButton > button {
            background: transparent !important;
            color: #aaa !important;
            border: 1px solid #ddd !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            height: auto !important;
            padding: 9px 20px !important;
            border-radius: 8px !important;
            box-shadow: none !important;
        }
        [data-testid="column"]:nth-child(2) .stButton > button:hover {
            background: #f5f5f3 !important;
            transform: none !important;
        }
        </style>
        """, unsafe_allow_html=True)
        if st.button("← 처음으로", key="back_home", use_container_width=True):
            reset_session()
            st.rerun()


# ══════════════════════════════════════════════
# 화면 3 — 결과
# ══════════════════════════════════════════════
def render_result():
    matched     = st.session_state.matched_item
    result_text = st.session_state.result_text
    reason      = st.session_state.result_reason or matched.get("note", "")
    steps       = matched.get("steps", [])

    st.markdown("""
    <style>
    .stApp { background: #F0F4F0 !important; }
    @media (max-width: 768px) {
        /* 결과 카드 패딩 축소 */
        div[style*="max-width:480px"] {
            padding: 28px 20px !important;
        }
        /* 결과 제목 크기 */
        div[style*="font-size:24px"] {
            font-size: 20px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    render_navbar()

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # 분석 완료 배지
    st.markdown(f"""
    <div style="text-align:center;margin-bottom:8px;">
      <span style="display:inline-flex;align-items:center;gap:6px;
                   font-size:13px;font-weight:600;color:#1B4D2E;">
        ✅ 분석완료: {matched["name"]}
      </span>
    </div>
    """, unsafe_allow_html=True)

    # 결과 카드
    st.markdown(f"""
    <div style="max-width:480px;margin:0 auto;
                background:#fff;border-radius:24px;padding:40px 32px;
                text-align:center;box-shadow:0 2px 16px rgba(0,0,0,.07);">
      <div style="background:#E8F5E9;border-radius:16px;width:64px;height:64px;
                  display:flex;align-items:center;justify-content:center;
                  margin:0 auto 20px;font-size:28px;">♻️</div>
      <div style="font-size:24px;font-weight:900;color:#1a1a1a;
                  line-height:1.3;margin-bottom:8px;word-break:keep-all;">
        {result_text}
      </div>
      {"<div style='font-size:13px;color:#888;line-height:1.6;word-break:keep-all;'>" + reason.split('.')[0] + ".</div>" if reason else ""}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

    # IMPACT NOTE
    if reason:
        st.markdown(f"""
        <div style="max-width:480px;margin:0 auto 20px;
                    background:#fff;border-radius:16px;padding:20px 24px;">
          <div style="font-size:11px;font-weight:700;color:#1B4D2E;
                      letter-spacing:.8px;margin-bottom:8px;">🌿 IMPACT NOTE</div>
          <div style="font-size:13px;color:#555;line-height:1.7;">{reason}</div>
        </div>
        """, unsafe_allow_html=True)

    # 정확한 배출 요령
    if steps:
        rows_html = "".join(
            f'<li style="font-size:13px;color:#444;line-height:1.8;margin-bottom:4px;">{s}</li>'
            for s in steps
        )
        st.markdown(f"""
        <div style="max-width:480px;margin:0 auto 24px;
                    background:#fff;border-radius:16px;padding:20px 24px;">
          <div style="font-size:11px;font-weight:700;color:#1B4D2E;
                      letter-spacing:.8px;margin-bottom:12px;">💡 정확한 배출 요령</div>
          <ul style="margin:0;padding-left:18px;">{rows_html}</ul>
        </div>
        """, unsafe_allow_html=True)

    # 버튼
    _, col_btn, _ = st.columns([1, 2, 1])
    with col_btn:
        st.markdown("""
        <style>
        [data-testid="column"]:nth-child(2) .stButton > button {
            border-radius: 12px !important;
            height: 48px !important;
            font-size: 15px !important;
            font-weight: 700 !important;
        }
        [data-testid="column"]:nth-child(2) .stButton > button:last-child {
            background: #f0f0ee !important;
            color: #555 !important;
            border: none !important;
            margin-top: 8px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        if st.button("🔍  다시 검색", use_container_width=True, key="retry_btn"):
            reset_session()
            st.rerun()
        if st.button("홈으로 돌아가기", use_container_width=True, key="home_btn"):
            reset_session()
            st.rerun()

    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)




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
