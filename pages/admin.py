"""
admin.py — Re:Sort 관리자 대시보드
streamlit run admin.py 또는 멀티페이지: pages/admin.py
"""

import json
import base64
import requests
import streamlit as st
import pandas as pd
from datetime import datetime, date
from collections import Counter
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from carbon import load_usage_log

# ──────────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Re:Sort Admin",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;900&display=swap');
  .stApp { background-color: #F2F2F0; }
  html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

  .admin-navbar {
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 40px; background: #1B4D2E;
    margin-bottom: 32px;
  }
  .admin-navbar-logo { color: white; font-size: 18px; font-weight: 700; }
  .admin-navbar-sub  { color: rgba(255,255,255,0.7); font-size: 13px; }

  .metric-card {
    background: white; border-radius: 16px;
    padding: 24px 28px; margin-bottom: 16px;
  }
  .metric-label { font-size: 13px; color: #888; margin-bottom: 6px; }
  .metric-value { font-size: 36px; font-weight: 900; color: #1B4D2E; }
  .metric-sub   { font-size: 12px; color: #AAA; margin-top: 4px; }

  .section-title {
    font-size: 18px; font-weight: 700;
    color: #1B4D2E; margin: 32px 0 16px;
  }

  .stButton > button {
    background-color: #1B4D2E !important; color: white !important;
    border-radius: 40px !important; padding: 10px 24px !important;
    font-size: 14px !important; font-weight: 600 !important;
    border: none !important;
  }
  #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 로그인
# ──────────────────────────────────────────────
def check_password() -> bool:
    if st.session_state.get("admin_authenticated"):
        return True

    st.markdown("""
    <div style="max-width:400px; margin:120px auto; background:white;
                border-radius:20px; padding:48px 40px; text-align:center;">
      <div style="font-size:24px; font-weight:900; color:#1B4D2E; margin-bottom:8px;">
        Re:Sort Admin
      </div>
      <div style="font-size:13px; color:#888; margin-bottom:32px;">
        관리자 전용 페이지입니다.
      </div>
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        pw = st.text_input("비밀번호", type="password", key="admin_pw_input")
        if st.button("로그인", use_container_width=True):
            try:
                correct = st.secrets.get("ADMIN_PASSWORD", "admin")
            except Exception:
                correct = "admin"
            if pw == correct:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
    return False

if not check_password():
    st.stop()

# ──────────────────────────────────────────────
# 네비게이션바
# ──────────────────────────────────────────────
st.markdown("""
<div class="admin-navbar">
  <div>
    <div class="admin-navbar-logo">Re:Sort Admin</div>
    <div class="admin-navbar-sub">분리배출 가이드 관리자 대시보드</div>
  </div>
  <div style="color:rgba(255,255,255,0.7); font-size:13px;">
    ⚙️ 관리자 모드
  </div>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 데이터 로드
# ──────────────────────────────────────────────
@st.cache_data(ttl=30)
def get_log() -> pd.DataFrame:
    raw = load_usage_log()
    if not raw:
        return pd.DataFrame(columns=[
            "timestamp", "user_input", "matched_item_id",
            "matched_by", "category", "final_result", "llm_used"
        ])
    df = pd.DataFrame(raw)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["date"] = df["timestamp"].dt.date
    return df

df = get_log()
has_data = len(df) > 0

# ──────────────────────────────────────────────
# 1. 요약 카드 4개
# ──────────────────────────────────────────────
st.markdown('<div class="section-title">📊 요약</div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)

total = len(df)
keyword_ok = int((df["matched_by"] != "llm").sum()) if has_data else 0
match_rate = f"{keyword_ok / total * 100:.1f}%" if total > 0 else "—"
llm_count = int(df["llm_used"].sum()) if has_data and "llm_used" in df.columns else 0
top_cat = df["category"].value_counts().idxmax() if has_data and "category" in df.columns and not df["category"].isna().all() else "—"

for col, label, value, sub in [
    (c1, "총 검색 횟수",         f"{total:,}",   "누적 전체"),
    (c2, "키워드 매칭 성공률",    match_rate,     f"{keyword_ok:,}건 성공"),
    (c3, "Gemini fallback 횟수", f"{llm_count:,}", "LLM 사용"),
    (c4, "가장 많이 검색된 카테고리", top_cat,    "누적 1위"),
]:
    with col:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
          <div class="metric-sub">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 2. 검색 Top 10 바 차트
# ──────────────────────────────────────────────
st.markdown('<div class="section-title">🔍 검색 Top 10</div>', unsafe_allow_html=True)

if has_data and "user_input" in df.columns:
    top10 = (
        df["user_input"].dropna()
        .value_counts()
        .head(10)
        .reset_index()
    )
    top10.columns = ["품목", "검색 횟수"]
    st.bar_chart(top10.set_index("품목"), height=300)
else:
    st.info("검색 데이터가 없습니다.")

# ──────────────────────────────────────────────
# 3. 매칭 실패 목록
# ──────────────────────────────────────────────
st.markdown('<div class="section-title">❌ 매칭 실패 목록</div>', unsafe_allow_html=True)

if has_data and "matched_item_id" in df.columns:
    failed = df[df["matched_item_id"].isna()][["timestamp", "user_input", "final_result"]].copy()
    failed["timestamp"] = failed["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    if len(failed) > 0:
        st.dataframe(failed.reset_index(drop=True), use_container_width=True)
    else:
        st.success("매칭 실패 항목이 없습니다.")
else:
    st.info("데이터가 없습니다.")

# ──────────────────────────────────────────────
# 4. 카테고리별 검색 분포 파이 차트
# ──────────────────────────────────────────────
st.markdown('<div class="section-title">🥧 카테고리별 검색 분포</div>', unsafe_allow_html=True)

if has_data and "category" in df.columns:
    cat_counts = df["category"].dropna().value_counts().reset_index()
    cat_counts.columns = ["카테고리", "검색 횟수"]
    # Streamlit 기본 차트는 파이 미지원 → 바 차트로 대체
    st.bar_chart(cat_counts.set_index("카테고리"), height=280)
else:
    st.info("카테고리 데이터가 없습니다.")

# ──────────────────────────────────────────────
# 5. 일별 사용량 추이 라인 차트
# ──────────────────────────────────────────────
st.markdown('<div class="section-title">📈 일별 사용량 추이</div>', unsafe_allow_html=True)

if has_data and "date" in df.columns:
    daily = df.groupby("date").size().reset_index(name="검색 횟수")
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.set_index("date").sort_index()
    st.line_chart(daily, height=280)
else:
    st.info("일별 데이터가 없습니다.")

# ──────────────────────────────────────────────
# 6. 전체 로그 테이블 + 날짜 필터 + CSV 다운로드
# ──────────────────────────────────────────────
st.markdown('<div class="section-title">📋 전체 로그</div>', unsafe_allow_html=True)

col_f1, col_f2, col_f3 = st.columns([2, 2, 3])

with col_f1:
    date_from = st.date_input(
        "시작일",
        value=df["date"].min() if has_data and "date" in df.columns else date.today(),
        key="filter_from",
    )
with col_f2:
    date_to = st.date_input(
        "종료일",
        value=date.today(),
        key="filter_to",
    )
with col_f3:
    cat_options = ["전체"] + (sorted(df["category"].dropna().unique().tolist()) if has_data else [])
    selected_cat = st.selectbox("카테고리 필터", cat_options, key="filter_cat")

# 필터 적용
if has_data:
    mask = (df["date"] >= date_from) & (df["date"] <= date_to)
    filtered = df[mask].copy()
    if selected_cat != "전체":
        filtered = filtered[filtered["category"] == selected_cat]

    display_cols = ["timestamp", "user_input", "matched_item_id",
                    "matched_by", "category", "final_result", "llm_used"]
    display_cols = [c for c in display_cols if c in filtered.columns]
    filtered_display = filtered[display_cols].copy()
    filtered_display["timestamp"] = filtered_display["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    st.dataframe(filtered_display.reset_index(drop=True), use_container_width=True)

    # CSV 다운로드
    csv = filtered_display.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="⬇ CSV 다운로드",
        data=csv,
        file_name=f"resort_log_{date_from}_{date_to}.csv",
        mime="text/csv",
        key="csv_download",
    )
else:
    st.info("로그 데이터가 없습니다.")

# ══════════════════════════════════════════════
# 7. items.json 편집기
# ══════════════════════════════════════════════
st.markdown('<div class="section-title">🗂️ 품목 데이터 편집 (items.json)</div>', unsafe_allow_html=True)

ITEMS_PATH = Path(__file__).parent.parent / "data" / "items.json"

def load_items_raw():
    with open(ITEMS_PATH, encoding="utf-8") as f:
        return json.load(f)

def save_items_raw(data):
    """로컬 저장 + GitHub API로 push (Streamlit Cloud 환경)"""
    content_str = json.dumps(data, ensure_ascii=False, indent=2)

    # 로컬에도 저장 (로컬 실행 시 반영)
    with open(ITEMS_PATH, "w", encoding="utf-8") as f:
        f.write(content_str)

    # GitHub API로 push
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        repo  = st.secrets.get("GITHUB_REPO", "")
        if not token or not repo:
            return  # secrets 없으면 로컬 저장만

        api_url = f"https://api.github.com/repos/{repo}/contents/data/items.json"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

        # 현재 파일의 sha 가져오기 (업데이트에 필요)
        res = requests.get(api_url, headers=headers)
        sha = res.json().get("sha", "") if res.status_code == 200 else ""

        # 파일 업데이트
        payload = {
            "message": "admin: items.json 업데이트",
            "content": base64.b64encode(content_str.encode("utf-8")).decode("utf-8"),
            "sha": sha,
        }
        put_res = requests.put(api_url, headers=headers, json=payload)
        if put_res.status_code in (200, 201):
            st.toast("✅ GitHub에 저장되었습니다!", icon="🎉")
        else:
            st.warning(f"GitHub 저장 실패: {put_res.status_code}")
    except Exception as e:
        st.warning(f"GitHub 연동 오류: {e}")

def items_to_df(items):
    rows = []
    for item in items:
        rows.append({
            "id":              item.get("id", ""),
            "name":            item.get("name", ""),
            "category":        item.get("category", ""),
            "keywords":        ", ".join(item.get("keywords", [])),
            "skip_questions":  ", ".join(item.get("skip_questions", [])),
            "steps":           " | ".join(item.get("steps", [])),
            "note":            item.get("note", ""),
        })
    return pd.DataFrame(rows)

def df_to_items(df, original_items):
    """편집된 DataFrame을 items 리스트로 변환. extra_questions는 원본에서 유지."""
    original_map = {i["id"]: i for i in original_items}
    result = []
    for _, row in df.iterrows():
        item_id = str(row["id"]).strip()
        orig = original_map.get(item_id, {})
        result.append({
            "id":              item_id,
            "name":            str(row["name"]).strip(),
            "keywords":        [k.strip() for k in str(row["keywords"]).split(",") if k.strip()],
            "category":        str(row["category"]).strip(),
            "skip_questions":  [s.strip() for s in str(row["skip_questions"]).split(",") if s.strip()],
            "extra_questions": orig.get("extra_questions", None),
            "steps":           [s.strip() for s in str(row["steps"]).split("|") if s.strip()],
            "note":            str(row["note"]).strip(),
        })
    return result

# 카테고리 목록
CATEGORIES = ["스티로폼", "유리", "금속·캔", "플라스틱", "종이·종이팩", "비닐", "전자제품", "폐의약품", "기타"]

items_data = load_items_raw()
items_list = items_data["items"]

tab_list, tab_add = st.tabs(["📋 항목 목록 / 수정", "➕ 새 항목 추가"])

# ── 탭 1: 목록 보기 + 인라인 수정 ──
with tab_list:
    st.markdown("<div style='font-size:13px; color:#888; margin-bottom:12px;'>셀을 클릭해서 직접 수정할 수 있어요. 수정 후 <b>저장</b> 버튼을 눌러주세요.<br>• keywords: 쉼표로 구분 &nbsp;|&nbsp; steps: | (파이프)로 구분 &nbsp;|&nbsp; skip_questions: 쉼표로 구분</div>", unsafe_allow_html=True)

    # 카테고리 필터
    col_cat_f, col_search_f = st.columns([2, 3])
    with col_cat_f:
        filter_cat = st.selectbox("카테고리 필터", ["전체"] + CATEGORIES, key="item_filter_cat")
    with col_search_f:
        filter_kw = st.text_input("이름/키워드 검색", placeholder="예: 우유팩", key="item_filter_kw")

    filtered_items = items_list
    if filter_cat != "전체":
        filtered_items = [i for i in filtered_items if i["category"] == filter_cat]
    if filter_kw.strip():
        kw = filter_kw.strip().lower()
        filtered_items = [
            i for i in filtered_items
            if kw in i["name"].lower() or any(kw in k.lower() for k in i["keywords"])
        ]

    st.markdown(f"<div style='font-size:13px; color:#1B4D2E; margin-bottom:8px; font-weight:600;'>총 {len(filtered_items)}개 항목</div>", unsafe_allow_html=True)

    if filtered_items:
        edit_df = items_to_df(filtered_items)
        edited = st.data_editor(
            edit_df,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "id":             st.column_config.TextColumn("ID", width="small"),
                "name":           st.column_config.TextColumn("품목명", width="medium"),
                "category":       st.column_config.SelectboxColumn("카테고리", options=CATEGORIES, width="small"),
                "keywords":       st.column_config.TextColumn("키워드 (쉼표 구분)", width="large"),
                "skip_questions": st.column_config.TextColumn("skip_questions", width="small"),
                "steps":          st.column_config.TextColumn("배출 요령 (| 구분)", width="large"),
                "note":           st.column_config.TextColumn("note", width="large"),
            },
            key="items_editor",
        )

        col_save, col_del = st.columns([2, 5])
        with col_save:
            if st.button("💾 변경사항 저장", key="save_items", use_container_width=True):
                # 수정된 항목 반영 (필터링 안 된 항목은 유지)
                edited_ids = set(edited["id"].tolist())
                unchanged = [i for i in items_list if i["id"] not in edited_ids]
                updated   = df_to_items(edited, items_list)
                items_data["items"] = unchanged + updated
                save_items_raw(items_data)
                st.cache_data.clear()
                st.success(f"✅ {len(updated)}개 항목이 저장되었습니다!")
                st.rerun()

# ── 탭 2: 새 항목 추가 ──
with tab_add:
    st.markdown("<div style='font-size:13px; color:#888; margin-bottom:16px;'>새로운 품목을 추가해요.</div>", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        new_name     = st.text_input("품목명 *", placeholder="예: 컵라면 용기", key="new_name")
        new_category = st.selectbox("카테고리 *", CATEGORIES, key="new_category")
        new_keywords = st.text_input("키워드 (쉼표 구분) *", placeholder="예: 컵라면, 라면용기, 즉석라면 컵", key="new_keywords")
        new_skip     = st.text_input("skip_questions (쉼표 구분)", placeholder="예: Q1", key="new_skip")
    with col_b:
        new_steps    = st.text_area("배출 요령 (한 줄에 하나씩)", placeholder="내용물을 비우세요.\n물로 헹구세요.\n스티로폼 수거함에 배출하세요.", height=120, key="new_steps")
        new_note     = st.text_area("환경 설명 (note)", placeholder="왜 이렇게 배출해야 하는지 간단히 설명해주세요.", height=80, key="new_note")

    # ID 자동 생성 미리보기
    if new_category and new_name:
        cat_prefix_map = {
            "스티로폼": "styro", "유리": "glass", "금속·캔": "metal",
            "플라스틱": "plastic", "종이·종이팩": "paper", "비닐": "vinyl",
            "전자제품": "elec", "폐의약품": "medi", "기타": "etc"
        }
        prefix = cat_prefix_map.get(new_category, "item")
        existing_ids = [i["id"] for i in items_list if i["id"].startswith(prefix)]
        next_num = len(existing_ids) + 1
        auto_id = f"{prefix}_{next_num:03d}"
        st.markdown(f"<div style='font-size:13px; color:#1B4D2E;'>자동 생성 ID: <b>{auto_id}</b></div>", unsafe_allow_html=True)

    if st.button("➕ 항목 추가", key="add_item_btn"):
        if not new_name.strip() or not new_keywords.strip():
            st.error("품목명과 키워드는 필수입니다.")
        else:
            new_item = {
                "id":              auto_id,
                "name":            new_name.strip(),
                "keywords":        [k.strip() for k in new_keywords.split(",") if k.strip()],
                "category":        new_category,
                "skip_questions":  [s.strip() for s in new_skip.split(",") if s.strip()],
                "extra_questions": None,
                "steps":           [s.strip() for s in new_steps.strip().split("\n") if s.strip()],
                "note":            new_note.strip(),
            }
            items_data["items"].append(new_item)
            save_items_raw(items_data)
            st.cache_data.clear()
            st.success(f"✅ '{new_name}' 항목이 추가되었습니다! (ID: {auto_id})")
            st.rerun()

# ──────────────────────────────────────────────
# 로그아웃
# ──────────────────────────────────────────────
st.markdown("<br><br>", unsafe_allow_html=True)
_, col_logout, _ = st.columns([4, 1, 4])
with col_logout:
    if st.button("로그아웃", use_container_width=True, key="logout_btn"):
        st.session_state.admin_authenticated = False
        st.rerun()
