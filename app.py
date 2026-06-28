import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="에듀테크 수강생 관리 대시보드", layout="wide", page_icon="📊")

# ── 컬럼 정의 ─────────────────────────────────────────────────────────────
STUDENT_COLS = [
    "user_id", "이름", "수강과정", "수강유형", "가입일", "거주지역", "주이용기기",
    "전체커리큘럼수", "완료커리큘럼수", "출석률", "과제제출률", "평균퀴즈점수",
    "최근30일로그인수", "최근로그인경과일", "NPS점수", "결제상태", "이탈여부"
]
VOC_COLS = [
    "ticket_id", "user_id", "이름", "문의일시", "문의채널", "문의유형",
    "문의내용요약", "처리담당자", "처리상태", "처리소요시간(h)", "만족도(1~5)"
]

# ── 데이터 뷰 재구성 ────────────────────────────────────────────────────
def rebuild_views():
    df_s = st.session_state.raw_students.copy()
    df_v = st.session_state.raw_voc.copy()
    df_s.columns = df_s.columns.str.strip()
    df_v.columns = df_v.columns.str.strip()

    merged = df_s.merge(df_v.drop(columns=["이름"], errors="ignore"), on="user_id", how="left")

    # merged_sales.xlsx 저장 (가능한 경우)
    try:
        merged.to_excel("merged_sales.xlsx", index=False)
    except Exception:
        pass

    avail_s = [c for c in STUDENT_COLS if c in merged.columns]
    df_students = merged[avail_s].drop_duplicates(subset="user_id").reset_index(drop=True)

    avail_v = [c for c in VOC_COLS if c != "이름" and c in merged.columns]
    _voc = merged.dropna(subset=["ticket_id"])[avail_v].reset_index(drop=True)
    _voc = _voc.merge(df_students[["user_id", "이름"]], on="user_id", how="left")
    avail_voc = [c for c in VOC_COLS if c in _voc.columns]
    df_voc = _voc[avail_voc].reset_index(drop=True)

    st.session_state.df_students = df_students
    st.session_state.voc_df = df_voc

# ── 초기 데이터 로드 ────────────────────────────────────────────────────
if "raw_students" not in st.session_state:
    df_s = pd.read_excel("더미데이터/edutech_학습자이용데이터.xlsx")
    df_v = pd.read_excel("더미데이터/edutech_VOC문의데이터.xlsx")
    df_s.columns = df_s.columns.str.strip()
    df_v.columns = df_v.columns.str.strip()
    st.session_state.raw_students = df_s
    st.session_state.raw_voc = df_v
    rebuild_views()

df_students = st.session_state.df_students

# ── 외부 API: 오늘의 명언 ────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_quote():
    try:
        r = requests.get("https://zenquotes.io/api/random", timeout=4)
        d = r.json()[0]
        return f'"{d["q"]}" — {d["a"]}'
    except Exception:
        return "오늘도 최선을 다해 수강생을 응원하세요! 💪"

# ── 우선순위 헬퍼 ────────────────────────────────────────────────────────
PRIORITY = {"확인중": (0, "🔴"), "이관됨": (1, "🟡"), "처리완료": (2, "🟢")}

def priority_order(status):
    return PRIORITY.get(status, (3, "⚪"))[0]

def priority_emoji(status):
    return PRIORITY.get(status, (3, "⚪"))[1]

def sort_voc(df):
    df = df.copy()
    df["_ord"] = df["처리상태"].apply(priority_order)
    return df.sort_values("_ord").drop(columns=["_ord"]).reset_index(drop=True)

# ── 타이틀 & 명언 ────────────────────────────────────────────────────────
st.title("📊 에듀테크 수강생 관리 대시보드")

st.markdown(
    f"""
    <div style="
        background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%);
        border-left: 5px solid #5ba3d9;
        border-radius: 8px;
        padding: 16px 22px;
        margin: 8px 0 16px 0;
    ">
        <span style="font-size: 1.05rem; color: #e8f4fd; font-style: italic; line-height: 1.6;">
            💬 {get_quote()}
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.divider()

# ── KPI 지표 ─────────────────────────────────────────────────────────────
total = len(df_students)
completion_rate = (
    df_students["완료커리큘럼수"] >= df_students["전체커리큘럼수"]
).mean() * 100 if "완료커리큘럼수" in df_students.columns else 0
avg_attend = df_students["출석률"].mean() * 100 if "출석률" in df_students.columns else 0
churn_rate = (df_students["이탈여부"] == "Y").mean() * 100 if "이탈여부" in df_students.columns else 0

cnt_gov = int((df_students["수강유형"] == "국비지원").sum()) if "수강유형" in df_students.columns else 0
cnt_job = int((df_students["수강유형"] == "취업연계형").sum()) if "수강유형" in df_students.columns else 0
cnt_gen = int((df_students["수강유형"] == "일반결제형").sum()) if "수강유형" in df_students.columns else 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("총 수강생", f"{total}명")
    st.caption(f"국비지원 {cnt_gov}명  |  취업연계형 {cnt_job}명  |  일반결제형 {cnt_gen}명")
with kpi2:
    st.metric("수료율", f"{completion_rate:.1f}%")
with kpi3:
    st.metric("평균 출석률", f"{avg_attend:.1f}%")
with kpi4:
    st.metric("이탈률", f"{churn_rate:.1f}%")

st.divider()

# ── 메인 레이아웃 ─────────────────────────────────────────────────────────
left, right = st.columns([1, 1.3], gap="large")

# ── 좌측: 수강생 목록 ─────────────────────────────────────────────────────
with left:
    st.subheader("수강생 목록")

    # 수강생 데이터 업로드
    with st.expander("📂 수강생 데이터 교체"):
        st.caption("현재 수강생 데이터를 새 엑셀 파일로 교체합니다.")
        up_s = st.file_uploader(
            "수강생 엑셀 파일 (.xlsx)",
            type=["xlsx", "xls"],
            key="up_student",
        )
        if up_s:
            try:
                df_new_s = pd.read_excel(up_s)
                df_new_s.columns = df_new_s.columns.str.strip()
                required_s = {"user_id", "이름", "수강과정", "수강유형", "출석률", "이탈여부"}
                missing_s = required_s - set(df_new_s.columns)
                if missing_s:
                    st.error(f"필수 컬럼 누락: {', '.join(missing_s)}")
                else:
                    st.session_state.raw_students = df_new_s
                    rebuild_views()
                    st.success(f"수강생 데이터 업데이트 완료! ({len(df_new_s)}명)")
                    st.rerun()
            except Exception as e:
                st.error(f"파일 오류: {e}")

    # 필터
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        courses = ["전체"] + sorted(df_students["수강과정"].unique()) if "수강과정" in df_students.columns else ["전체"]
        sel_course = st.selectbox("과정", courses)
    with fc2:
        types = ["전체"] + sorted(df_students["수강유형"].unique()) if "수강유형" in df_students.columns else ["전체"]
        sel_type = st.selectbox("수강유형", types)
    with fc3:
        sel_status = st.selectbox("이탈여부", ["전체", "Y (이탈)", "N (정상)"])

    filtered = df_students.copy()
    if sel_course != "전체":
        filtered = filtered[filtered["수강과정"] == sel_course]
    if sel_type != "전체":
        filtered = filtered[filtered["수강유형"] == sel_type]
    if sel_status == "Y (이탈)":
        filtered = filtered[filtered["이탈여부"] == "Y"]
    elif sel_status == "N (정상)":
        filtered = filtered[filtered["이탈여부"] == "N"]

    display_df = filtered[["user_id", "이름", "수강과정", "수강유형", "출석률", "이탈여부"]].copy()
    if "출석률" in display_df.columns:
        display_df["출석률"] = (display_df["출석률"] * 100).round(1).astype(str) + "%"
    st.caption("행을 클릭하면 우측 VOC 대시보드에 반영됩니다.")
    selection = st.dataframe(
        display_df.reset_index(drop=True),
        use_container_width=True,
        height=340,
        on_select="rerun",
        selection_mode="single-row",
        key="student_table",
    )
    selected_rows = selection.selection.rows
    sel_name = filtered.iloc[selected_rows[0]]["이름"] if selected_rows else None

# ── 우측: VOC 대시보드 ────────────────────────────────────────────────────
with right:
    st.subheader("VOC 대시보드")

    # VOC 데이터 업로드
    with st.expander("📂 VOC 데이터 교체"):
        st.caption("현재 VOC 데이터를 새 엑셀 파일로 교체합니다.")
        up_v = st.file_uploader(
            "VOC 엑셀 파일 (.xlsx)",
            type=["xlsx", "xls"],
            key="up_voc",
        )
        if up_v:
            try:
                df_new_v = pd.read_excel(up_v)
                df_new_v.columns = df_new_v.columns.str.strip()
                required_v = {"ticket_id", "user_id", "처리상태", "만족도(1~5)"}
                missing_v = required_v - set(df_new_v.columns)
                if missing_v:
                    st.error(f"필수 컬럼 누락: {', '.join(missing_v)}")
                else:
                    st.session_state.raw_voc = df_new_v
                    rebuild_views()
                    st.success(f"VOC 데이터 업데이트 완료! ({len(df_new_v)}건)")
                    st.rerun()
            except Exception as e:
                st.error(f"파일 오류: {e}")

    # 인수인계 규칙 가이드
    with st.expander("❕ 인수인계 규칙 가이드"):
        st.markdown(
            "🔴 **확인중** — 미처리, 즉시 대응 필요  \n"
            "🟡 **이관됨** — 타 팀 처리 진행 중  \n"
            "🟢 **처리완료** — 종결된 VOC  \n"
            "🗑️ **만족도 3 초과**일 경우에만 삭제 가능"
        )

    # 전체 보기 토글
    if "show_all" not in st.session_state:
        st.session_state.show_all = False
    if st.button("📋 전체 VOC 보기"):
        st.session_state.show_all = not st.session_state.show_all

    voc_df = st.session_state.voc_df

    if st.session_state.show_all:
        display_voc = sort_voc(voc_df)
        st.caption(f"전체 VOC {len(display_voc)}건 — 우선순위 자동 정렬")
    elif sel_name:
        uid = df_students[df_students["이름"] == sel_name]["user_id"].values[0]
        display_voc = sort_voc(voc_df[voc_df["user_id"] == uid])
        st.caption(f"{sel_name} 님의 VOC {len(display_voc)}건")
    else:
        display_voc = pd.DataFrame()
        st.info("좌측 표에서 수강생 행을 클릭하거나 **전체 VOC 보기**를 클릭하세요.")

    if not display_voc.empty:
        delete_ticket = None
        for _, row in display_voc.iterrows():
            emoji = priority_emoji(row["처리상태"])
            sat_raw = row["만족도(1~5)"]
            if pd.isna(sat_raw):
                sat_num = None
                can_delete = False
            else:
                sat_num = float(sat_raw)
                can_delete = sat_num > 3
            sat_text = f"{sat_num:.0f}점" if sat_num is not None else "미입력"

            st.markdown("---")
            header_col, btn_col = st.columns([6, 1])
            with header_col:
                st.markdown(
                    f"{emoji} **{row['처리상태']}**　|　"
                    f"📣 {row['문의채널']}　|　🏷️ {row['문의유형']}"
                )
            with btn_col:
                if can_delete:
                    if st.button("🗑️", key=f"del_{row['ticket_id']}", help="VOC 삭제"):
                        delete_ticket = row["ticket_id"]

            st.write(f"📝 {row['문의내용요약']}")
            hours = row["처리소요시간(h)"]
            time_text = f"{hours:.0f}h" if pd.notna(hours) else "진행중"
            st.caption(
                f"담당자: **{row['처리담당자']}**　|　만족도: {sat_text}　|　처리시간: {time_text}"
            )

        if delete_ticket is not None:
            st.session_state.voc_df = st.session_state.voc_df[
                st.session_state.voc_df["ticket_id"] != delete_ticket
            ].reset_index(drop=True)
            st.rerun()
