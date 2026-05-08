"""
app.py — Re:Sort 분리배출 챗봇 메인 앱
화면 상태: "home" → "questioning" → "result"
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from pathlib import Path

from matcher import load_items, match_item
from decision_tree import get_tree, get_first_question, process_answer
from carbon import (load_carbon_factors, load_usage_log, save_usage_log,
                    get_today_carbon, format_carbon, load_items_from_sheets)

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
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&display=swap');
  @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

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
@st.cache_data(ttl=300)  # 5분 캐시
def get_items():
    return load_items_from_sheets()

def get_items_and_fill_ids():
    """캐시 없이 호출 — 빈 id를 Sheets에 채워주는 사이드이펙트 포함."""
    items = load_items_from_sheets()
    st.cache_data.clear()   # 캐시 갱신해서 다음 get_items()도 최신 반영
    return items

@st.cache_data(ttl=60)
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

    # 세션 첫 시작 시 한 번만 — 빈 id를 Sheets에 채워줌
    if "ids_filled" not in st.session_state:
        get_items_and_fill_ids()
        st.session_state["ids_filled"] = True

init_session()

def scroll_to_top(_key: str):
    components.html(
        """
        <script>
        const scrollTop = () => {
          const doc = window.parent.document;
          const targets = [
            doc.scrollingElement,
            doc.documentElement,
            doc.body,
            doc.querySelector('[data-testid="stAppViewContainer"]'),
            doc.querySelector('section.main'),
            doc.querySelector('main')
          ].filter(Boolean);
          targets.forEach((el) => {
            try { el.scrollTo({ top: 0, left: 0, behavior: 'instant' }); }
            catch (_) { el.scrollTop = 0; el.scrollLeft = 0; }
          });
        };
        requestAnimationFrame(scrollTop);
        setTimeout(scrollTop, 50);
        setTimeout(scrollTop, 250);
        </script>
        """,
        height=0,
        width=0,
        scrolling=False,
    )

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
            st.session_state.result_text   = ("일반쓰레기 배출" if matched["category"] == "일반쓰레기" else matched["category"] + " 분리배출")
            st.session_state.result_reason = matched.get("note", "")
            st.session_state.state         = "result"
            append_usage_log(query, matched, st.session_state.result_text)
            return
        first_q = get_first_question(tree, skip)
        if first_q is None:
            st.session_state.result_text   = ("일반쓰레기 배출" if matched["category"] == "일반쓰레기" else matched["category"] + " 분리배출")
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
                    st.session_state.result_text   = ("일반쓰레기 배출" if matched["category"] == "일반쓰레기" else matched["category"] + " 분리배출")
                    st.session_state.result_reason = matched.get("note", "")
                    st.session_state.state         = "result"
                    append_usage_log(st.session_state.query, matched, st.session_state.result_text)
                    return
                first_q = get_first_question(tree, skip)
                if first_q is None:
                    st.session_state.result_text   = ("일반쓰레기 배출" if matched["category"] == "일반쓰레기" else matched["category"] + " 분리배출")
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

    # ── 제목 + 닉네임 + 검색창 ──
    st.markdown("""
    <style>
    /* 입력창 간격 최소화 */
    [data-testid="stVerticalBlock"] > [data-testid="element-container"] {
        margin-bottom: -12px !important;
    }
    .stTextInput { margin-bottom: 0 !important; }
    .stTextInput input {
        border-radius: 12px !important;
        border: 1.5px solid rgba(0,0,0,.1) !important;
        background: #fff !important;
        padding: 12px 18px !important;
        font-size: 14px !important;
        color: #222 !important;
        box-shadow: none !important;
    }
    .stTextInput input:focus {
        border-color: #1B4D2E !important;
        box-shadow: 0 0 0 3px rgba(27,77,46,.08) !important;
        outline: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center;margin:35px 0 40px;">
      <div style="font-size:35px;font-weight:900;line-height:1.3;color:#1a1a1a;
                  letter-spacing:-0.5px;font-family:'Pretendard','Noto Sans KR',sans-serif;">
        지속 가능한 미래를 위한<br>
        <span style="color:#1B4D2E;">똑똑한 분리배출</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    nickname_input = st.text_input(
        "닉네임", placeholder="닉네임을 입력해주세요 (필수)",
        label_visibility="collapsed", key="nickname_input",
    )
    if nickname_input:
        st.session_state.nickname = nickname_input.strip()

    query = st.text_input(
        "검색", placeholder="어떤 품목을 버리시나요? (Enter로 검색)",
        label_visibility="collapsed", key="home_input",
    )
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
    DEFAULT_TAGS = ["플라스틱 컵", "배달 용기", "알루미늄 캔"]
    usage_log = load_usage_log()
    if usage_log:
        from collections import Counter
        from datetime import date
        today = date.today().isoformat()
        today_inputs = [
            e["user_input"] for e in usage_log
            if e.get("timestamp", "").startswith(today)
            and e.get("user_input")
            and e.get("matched_item_id")
            and e.get("user_input") != e.get("nickname", "")
        ]
        top3 = [item for item, _ in Counter(today_inputs).most_common(3)]
        if len(top3) < 3:
            all_inputs = [e["user_input"] for e in usage_log
                          if e.get("user_input")
                          and e.get("matched_item_id")
                          and e.get("user_input") != e.get("nickname", "")]
            for item, _ in Counter(all_inputs).most_common(20):
                if item not in top3:
                    top3.append(item)
                if len(top3) == 3:
                    break
        for tag in DEFAULT_TAGS:
            if len(top3) == 3:
                break
            if tag not in top3:
                top3.append(tag)
    else:
        top3 = DEFAULT_TAGS

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # ── 인기 태그 버튼 (한 줄, nowrap) ──
    tag_html = "".join([
        f'<a href="?q={tag}" target="_self" style="'
        f'display:inline-block;background:#fff;color:#444;'
        f'border:1.5px solid rgba(0,0,0,.1);border-radius:999px;'
        f'padding:6px 14px;font-size:12px;font-weight:500;'
        f'text-decoration:none;white-space:nowrap;'
        f'box-shadow:0 1px 4px rgba(0,0,0,.06);'
        f'flex-shrink:0;'
        f'">{tag}</a>'
        for tag in top3
    ])
    st.markdown(f"""
    <div style="display:flex;justify-content:center;align-items:center;
                gap:6px;flex-wrap:nowrap;overflow:hidden;">
      <span style="font-size:11px;color:#999;font-weight:500;white-space:nowrap;flex-shrink:0;">인기 검색어</span>
      {tag_html}
    </div>
    """, unsafe_allow_html=True)



    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

    # ── 탄소 카드 + 사용자 현황 ──
    carbon_factors = get_carbon_factors()
    usage_log2 = load_usage_log()
    carbon_val = get_today_carbon(usage_log2, carbon_factors)
    carbon_str = format_carbon(carbon_val)
    num_str = carbon_str.replace(' kg', '')

    # 주간 목표: 100 kg
    WEEKLY_GOAL = 100.0
    from datetime import date as _date, timedelta as _timedelta
    _today = _date.today()
    _week_start = _today - _timedelta(days=_today.weekday())  # 이번 주 월요일
    weekly_carbon = sum(
        carbon_factors.get(e.get("category", "기타"), 0.0)
        for e in usage_log2
        if str(e.get("timestamp", ""))[:10] >= _week_start.isoformat()
    )
    goal_pct = min(int(weekly_carbon / WEEKLY_GOAL * 100), 100)
    goal_str = f"{weekly_carbon:.1f} / {int(WEEKLY_GOAL)} kg"

    # 사용자 현황 — 날짜별 중복 제거 (하루 1회로 제한)
    from collections import defaultdict
    user_dates = defaultdict(set)
    for e in usage_log2:
        nick = e.get("nickname", "").strip()
        ts = str(e.get("timestamp", ""))[:10]  # "2026-05-06"
        if nick and ts:
            user_dates[nick].add(ts)
    nickname_counts = {nick: len(dates) for nick, dates in user_dates.items()}

    # 동점자 묶어서 순위 그룹 만들기
    rank_groups = []  # [{"rank": 1, "count": 20, "names": [...], "cnt": 5}]
    if nickname_counts:
        sorted_users = sorted(nickname_counts.items(), key=lambda x: -x[1])
        rank = 1
        i = 0
        while i < len(sorted_users) and rank <= 3:
            cnt = sorted_users[i][1]
            group_names = []
            while i < len(sorted_users) and sorted_users[i][1] == cnt:
                group_names.append(sorted_users[i][0])
                i += 1
            rank_groups.append({"rank": rank, "names": group_names, "cnt": cnt})
            rank += 1

    # 슬라이드 데이터 — 순위별 슬라이드 생성
    slides_data = []
    medals = ["🥇", "🥈", "🥉"]
    for g in rank_groups:
        medal = medals[g["rank"] - 1] if g["rank"] <= 5 else f"{g['rank']}위"
        total = len(g["names"])
        for si, name in enumerate(g["names"]):
            slides_data.append({
                "medal": medal,
                "name": name,
                "cnt": g["cnt"],
                "label": f"{si+1}/{total}" if total > 1 else "",
            })

    # users_rows — CSS animation으로 슬라이드 (JS 없이)
    if slides_data:
        n = len(slides_data)
        slide_dur = 3  # 슬라이드당 3초
        total_dur = n * slide_dur
        # 각 슬라이드의 keyframe 애니메이션 계산
        style_parts = []
        slide_parts = []
        for si, s in enumerate(slides_data):
            lbl = f'<span style="font-size:9px;color:#aaa;margin-left:4px;">{s["label"]}</span>' if s["label"] else ""
            # 각 슬라이드가 보이는 구간 계산
            start_pct = (si * slide_dur / total_dur) * 100
            end_pct = ((si + 1) * slide_dur / total_dur) * 100
            # fade 없이 즉시 전환 (마지막 슬라이드는 100%까지 유지)
            kf = f"usr{si}"
            is_last = (si == n - 1)
            if is_last:
                style_parts.append(
                    f"@keyframes {kf} {{"
                    f"0%{{opacity:0;}} "
                    f"{max(0,start_pct-0.1):.1f}%{{opacity:0;}} "
                    f"{start_pct:.1f}%{{opacity:1;}} "
                    f"100%{{opacity:1;}}"
                    f"}}"
                )
            else:
                style_parts.append(
                    f"@keyframes {kf} {{"
                    f"0%{{opacity:0;}} "
                    f"{max(0,start_pct-0.1):.1f}%{{opacity:0;}} "
                    f"{start_pct:.1f}%{{opacity:1;}} "
                    f"{end_pct:.1f}%{{opacity:1;}} "
                    f"{end_pct+0.1:.1f}%{{opacity:0;}} "
                    f"100%{{opacity:0;}}"
                    f"}}"
                )
            delay = 0
            slide_parts.append(
                f'<div style="position:absolute;top:0;left:0;right:0;text-align:center;padding:8px 0;'
                f'opacity:{"1" if si==0 else "0"};'
                f'animation:{kf} {total_dur}s linear infinite;">'
                f'<div style="font-size:18px;margin-bottom:4px;">{s["medal"]}{lbl}</div>'
                f'<div style="font-size:14px;font-weight:700;color:#1a1a1a;margin-bottom:2px;">{s["name"]}</div>'
                f'<div style="font-size:11px;color:#888;">{s["cnt"]}일 참여</div>'
                f'</div>'
            )
        style_str = "<style>" + " ".join(style_parts) + "</style>"
        users_rows = (
            style_str +
            f'<div style="position:relative;height:80px;">' +
            "".join(slide_parts) +
            f'</div>'
        )
    else:
        users_rows = '<div style="font-size:13px;color:#aaa;text-align:center;padding:16px 0;">아직 데이터가 없어요</div>'  

    st.markdown(f"""
    <div style="display:flex;gap:12px;align-items:stretch;">
      <!-- 탄소 카드 -->
      <div style="flex:1;min-width:0;background:linear-gradient(135deg,#1a3a2a 0%,#1B4D2E 60%,#2a6640 100%);
                  border-radius:20px;padding:18px 16px;
                  box-shadow:0 4px 16px rgba(27,77,46,.2);">
        <div style="display:inline-flex;align-items:center;gap:5px;
                    background:rgba(255,255,255,.15);border-radius:999px;
                    padding:3px 10px;margin-bottom:10px;">
          <span style="width:5px;height:5px;background:#4ade80;border-radius:50%;display:inline-block;"></span>
          <span style="font-size:9px;color:rgba(255,255,255,.8);font-weight:600;letter-spacing:.5px;">TODAY'S IMPACT</span>
        </div>
        <div style="font-size:11px;color:rgba(255,255,255,.6);margin-bottom:4px;">오늘 줄인 탄소발자국</div>
        <div style="font-size:30px;font-weight:900;color:#fff;letter-spacing:-1px;line-height:1;
                    font-family:'DM Sans',sans-serif;">
          {num_str}<span style="font-size:14px;font-weight:600;color:rgba(255,255,255,.6);margin-left:3px;">kg</span>
        </div>
        <div style="margin-top:12px;">
          <div style="width:100%;height:4px;background:rgba(255,255,255,.15);border-radius:999px;overflow:hidden;">
            <div style="width:{goal_pct}%;height:100%;background:#4ade80;border-radius:999px;"></div>
          </div>
          <div style="font-size:10px;color:rgba(255,255,255,.5);margin-top:4px;">주간 목표 {goal_pct}% ({goal_str})</div>
        </div>
      </div>
      <!-- 사용자 현황 -->
      <div style="flex:1;min-width:0;background:#fff;border-radius:20px;padding:18px 16px;
                  border:1px solid rgba(0,0,0,.07);box-shadow:0 2px 8px rgba(0,0,0,.05);">
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;">
          <span style="font-size:12px;font-weight:700;color:#1a1a1a;">사용자 TOP 3</span>
          <span style="font-size:9px;color:#aaa;background:#f5f5f3;border-radius:999px;padding:2px 7px;">실시간</span>
        </div>
        {users_rows}
      </div>
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
            "우유팩", "분리배출 마크가 없는 비닐",
            "약국 조제 알약", "유리 약병",
            "특수용기 폐의약품 (연고 등)", "스티로폼 완충재 (전자제품 포장용)",
            "플라스틱 빨대", "음식물 묻은 스티로폼 상자",
            "물약, 시럽", "샴푸/바디워시 용기 펌프",
        ]

    icons = ["","","","","","","","","",""]
    descs = [
        "내용물을 비우고 물로 헹군 뒤 종이팩으로 배출하세요.",
        "비닐류로 분리배출하세요.",
        "포장을 개봉하지 않고 그대로 폐의약품 수거함에 배출하세요.",
        "내용물은 다른 용기에 옮겨 담아 폐의약품 수거함으로, 빈 유리병은 헹군 뒤 유리병으로 배출하세요.",
        "종이박스 등 포장재 제거 후 내용물이 들어 있는 용기째 폐의약품 수거함에 배출하세요.",
        "가급적 제품 구입처로 반납해주세요.",
        "일반쓰레기(종량제)로 배출하세요.",
        "일반쓰레기(종량제)로 배출하세요.",
        "용기째 밀봉하여 폐의약품 수거함에 배출하세요.",
        "펌프는 일반쓰레기로, 빈 통은 플라스틱류로 배출하세요.",
    ]

    mistakes_html = ""
    for i, mistake in enumerate(top_mistakes[:10]):
        is_top3 = i < 3
        bg_color = "#1a1a1a" if is_top3 else "#f0f0ee"
        txt_color = "#fff" if is_top3 else "#888"
        desc_html = descs[i].replace("\n", "<br>")
        num = f"{i+1:02d}"
        mistakes_html += (
            f'<div style="background:#fff;border-radius:16px;padding:18px 20px;' +
            f'margin-bottom:10px;border:1px solid rgba(0,0,0,.06);' +
            f'display:flex;align-items:center;gap:16px;">' +
            f'<div style="background:{bg_color};color:{txt_color};' +
            f'border-radius:10px;padding:6px 10px;' +
            f'font-size:12px;font-weight:800;flex-shrink:0;min-width:36px;text-align:center;">{num}</div>' +
            f'<div style="flex:1;min-width:0;">' +
            f'<div style="font-size:15px;font-weight:700;color:#1a1a1a;margin-bottom:3px;word-break:keep-all;">{mistake}</div>' +
            f'<div style="font-size:12px;color:#999;line-height:1.5;word-break:keep-all;">{desc_html}</div>' +
            f'</div>' +
            f'<div style="font-size:22px;flex-shrink:0;">{icons[i]}</div>' +
            f'</div>'
        )
    st.markdown(mistakes_html, unsafe_allow_html=True)

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
    scroll_to_top(f"scroll_question_{current_q.get('id', 'q')}_{st.session_state.step_num}")

    st.markdown("""
    <style>
    html,
    body,
    #root,
    .stApp,
    main,
    .stMain,
    [data-testid="stMain"],
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    .block-container {
        background: #F0F4F0 !important;
    }
    html,
    body,
    #root {
        min-height: 100% !important;
    }
    .stApp,
    main,
    .stMain,
    [data-testid="stMain"],
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    .block-container {
        min-height: 100vh !important;
        min-height: 100svh !important;
    }
    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        background: #F0F4F0;
        z-index: 0;
        pointer-events: none;
    }
    .stApp > * {
        position: relative;
        z-index: 1;
    }
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
        st.markdown("""
        <style>
        @media (max-width: 768px) {
            [data-testid="stHorizontalBlock"]:has(#answer-row-marker) {
                width: 100% !important;
                max-width: 100% !important;
                overflow: visible !important;
            }
            [data-testid="stHorizontalBlock"]:has(#answer-row-marker) + [data-testid="stHorizontalBlock"] {
                display: grid !important;
                grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) !important;
                gap: 10px !important;
                width: 100% !important;
                max-width: 100% !important;
                overflow: hidden !important;
            }
            [data-testid="stHorizontalBlock"]:has(#answer-row-marker) + [data-testid="stHorizontalBlock"] > [data-testid="column"] {
                width: 100% !important;
                min-width: 0 !important;
                max-width: 100% !important;
            }
            [data-testid="stHorizontalBlock"]:has(#answer-row-marker) + [data-testid="stHorizontalBlock"] .stButton > button {
                height: 88px !important;
                min-height: 88px !important;
                width: 100% !important;
                max-width: 100% !important;
                font-size: 17px !important;
                border-radius: 16px !important;
                padding: 10px 8px !important;
                white-space: normal !important;
            }
        }
        </style>
        <span id="answer-row-marker"></span>
        """, unsafe_allow_html=True)
        col_yes, col_no = st.columns(2, gap="small")
        with col_yes:
            if st.button("예", key="yes_btn", use_container_width=True):
                handle_answer(True)
                st.rerun()
        with col_no:
            if st.button("아니오", key="no_btn", use_container_width=True):
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
    scroll_to_top("scroll_result")

    st.markdown("""
    <style>
    html,
    body,
    #root,
    .stApp,
    main,
    .stMain,
    [data-testid="stMain"],
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    .block-container {
        background: #F0F4F0 !important;
    }
    html,
    body,
    #root {
        min-height: 100% !important;
    }
    .stApp,
    main,
    .stMain,
    [data-testid="stMain"],
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    .block-container {
        min-height: 100vh !important;
        min-height: 100svh !important;
    }
    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        background: #F0F4F0;
        z-index: 0;
        pointer-events: none;
    }
    .stApp > * {
        position: relative;
        z-index: 1;
    }
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
        if st.button("다시 검색", use_container_width=True, key="retry_btn"):
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
