"""
admin.py — Re:Sort 관리자 대시보드
streamlit run admin.py 또는 멀티페이지: pages/admin.py
"""

import json
import streamlit as st
import pandas as pd
from datetime import datetime, date
from collections import Counter
from pathlib import Path

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

    display_cols = ["timestamp", "nickname", "user_input", "matched_item_id",
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
# 7. 품목 데이터 관리 (Google Sheets)
# ══════════════════════════════════════════════
st.markdown('<div class="section-title">🗂️ 품목 데이터 관리</div>', unsafe_allow_html=True)

try:
    sheet_id = st.secrets.get("GSHEET_ID", "")
    if sheet_id:
        sheets_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit#gid=0"
        st.markdown(f"""
        <div style="background:#E8F5E9;border-radius:12px;padding:20px 24px;
                    display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
          <div>
            <div style="font-size:14px;font-weight:700;color:#1B4D2E;">📊 Google Sheets에서 품목 편집</div>
            <div style="font-size:12px;color:#555;margin-top:4px;line-height:1.6;">
              Sheets의 <b>items</b> 탭에서 품목을 추가·수정·삭제하세요.<br>
              변경 후 앱에 <b>5분 이내</b> 자동 반영됩니다.
            </div>
          </div>
          <a href="{sheets_url}" target="_blank"
             style="background:#1B4D2E;color:#fff;border-radius:8px;
                    padding:10px 22px;font-size:14px;font-weight:600;
                    text-decoration:none;white-space:nowrap;">
            Sheets 열기 →
          </a>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("GSHEET_ID secrets가 설정되지 않았습니다.")
except Exception:
    st.info("Google Sheets 연동 설정을 확인해주세요.")


# ══════════════════════════════════════════════
# 8. AI 추론 입력 검수 (A 전략)
# ══════════════════════════════════════════════
st.markdown('<div class="section-title">🤖 AI 추론 입력 검수</div>', unsafe_allow_html=True)

st.markdown(
    '<div style="background:#E8F5E9;border-radius:12px;padding:16px 20px;margin-bottom:16px;' +
    'font-size:13px;color:#1B4D2E;line-height:1.7;">' +
    '키워드 매칭에 실패해 AI가 카테고리를 추론한 입력 목록이에요.<br>' +
    '자주 등장하는 입력은 구글 시트 items 탭에 키워드로 추가하면 다음부터 정확하게 매칭돼요.' +
    '</div>',
    unsafe_allow_html=True
)

@st.cache_data(ttl=30)
def get_ai_inferred() -> pd.DataFrame:
    try:
        import gspread
        from carbon import _get_workbook
        sh = _get_workbook()
        if not sh:
            return pd.DataFrame()
        try:
            ws = sh.worksheet("ai_inferred")
            records = ws.get_all_records()
            if not records:
                return pd.DataFrame()
            return pd.DataFrame(records)
        except gspread.WorksheetNotFound:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

inferred_df = get_ai_inferred()

if len(inferred_df) > 0:
    if "added_to_items" in inferred_df.columns:
        pending = inferred_df[inferred_df["added_to_items"] != "True"].copy()
    else:
        pending = inferred_df.copy()

    if len(pending) > 0:
        freq = (
            pending.groupby(["user_input", "inferred_category", "confidence"])
            .size()
            .reset_index(name="횟수")
            .sort_values("횟수", ascending=False)
            .reset_index(drop=True)
        )
        st.markdown(f"**미검수 항목 {len(freq)}건** (동일 입력 중복 제거)")
        st.dataframe(freq, use_container_width=True)
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        st.info("💡 위 목록에서 자주 등장하는 항목을 구글 시트 items 탭에 키워드로 직접 추가해주세요.")

        sheets_url = ""
        try:
            sheet_id = st.secrets.get("GSHEET_ID", "")
            if sheet_id:
                sheets_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit#gid=0"
        except Exception:
            pass

        col_a, col_b = st.columns([1, 3])
        with col_a:
            if sheets_url:
                st.markdown(
                    f'<a href="{sheets_url}" target="_blank" ' +
                    'style="display:inline-block;background:#1B4D2E;color:#fff;' +
                    'border-radius:8px;padding:10px 20px;font-size:13px;' +
                    'font-weight:600;text-decoration:none;">Sheets 열기 →</a>',
                    unsafe_allow_html=True
                )
        with col_b:
            if st.button("✅ 전체 검수 완료 처리", key="mark_all_reviewed"):
                try:
                    from carbon import _get_workbook
                    sh = _get_workbook()
                    ws = sh.worksheet("ai_inferred")
                    all_vals = ws.get_all_values()
                    header = all_vals[0] if all_vals else []
                    if "added_to_items" in header:
                        col_idx = header.index("added_to_items") + 1
                        updates = [
                            {"range": f"{chr(64 + col_idx)}{row_i}", "values": [["True"]]}
                            for row_i in range(2, len(all_vals) + 1)
                        ]
                        if updates:
                            ws.batch_update(updates)
                    st.success("완료 처리됐어요! 새로고침하면 목록이 비워져요.")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"처리 실패: {e}")
    else:
        st.success("미검수 항목이 없어요.")
else:
    st.info("AI 추론 데이터가 아직 없어요. 키워드 매칭 실패 검색이 발생하면 여기에 쌓여요.")


# ──────────────────────────────────────────────
# 로그아웃
# ──────────────────────────────────────────────
st.markdown("<br><br>", unsafe_allow_html=True)
_, col_logout, _ = st.columns([4, 1, 4])
with col_logout:
    if st.button("로그아웃", use_container_width=True, key="logout_btn"):
        st.session_state.admin_authenticated = False
        st.rerun()
