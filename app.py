import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from geopy.distance import geodesic
from streamlit_js_eval import get_geolocation
import time
from datetime import datetime, timedelta
import pytz
from modules import *

LAB_LAT = 37.456461 
LAB_LON = 126.952096 
ALLOWED_RADIUS_M = 100 

st.set_page_config(page_title="출결 체크", page_icon="📍", initial_sidebar_state="collapsed")
if 'current_view' not in st.session_state:
    st.session_state['current_view'] = 'main'

def set_view(view_name):
    st.session_state['current_view'] = view_name
    st.rerun()

# --- 다이얼로그 및 헬퍼 함수 ---
if hasattr(st, "dialog"): dlg = st.dialog
else: dlg = st.experimental_dialog

@dlg("조퇴 확인")
def show_early_leave_dialog(name, user_lat, user_lon, distance):
    st.warning("⚠️ 현재 오후 6시 이전입니다. 조퇴하시겠습니까?")
    # 조퇴 사유 입력
    reason = st.text_area(
        "조퇴 사유",
        placeholder="예: 병원 예약, 가족 행사, 개인 사정 등",
        help="조퇴 사유를 간단히 입력해주세요.",
    )
    col_y, col_n = st.columns(2)
    with col_y:
        if st.button("네 (조퇴)"):
            try:
                if not reason or not reason.strip():
                    st.warning("조퇴 사유를 입력해주세요.")
                    st.stop()
                sheet = get_sheet()
                kst = pytz.timezone('Asia/Seoul')
                now = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
                # 조퇴 사유는 기존대로. (스키마상 6번째 컬럼 추정)
                sheet.append_row([now, name, "조퇴", f"{user_lat},{user_lon}", f"{distance:.1f}m", reason.strip()])
                clear_attendance_cache()
                st.success(f"{name}님 {now} 조퇴 기록 완료!")
                st.session_state['force_rerun'] = True 
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                import traceback
                st.code(traceback.format_exc())
    with col_n:
        if st.button("아니오"):
            st.rerun()

@dlg("지각 확인")
def show_late_dialog(name, user_lat, user_lon, distance):
    st.warning("⚠️ 현재 오전 10시 이후입니다. 지각 사유를 작성해주세요.")
    # 지각 사유 입력
    reason = st.text_area(
        "지각 사유",
        placeholder="예: [업무] 외근 복귀, 병원 진료 등",
        help="지각 사유를 입력해주세요. [업무]를 포함하면 근무로 인정됩니다.",
    )
    col_y, col_n = st.columns(2)
    with col_y:
        if st.button("네 (지각 출근)"):
            try:
                if not reason or not reason.strip():
                    st.warning("지각 사유를 입력해주세요.")
                    st.stop()
                sheet = get_sheet()
                kst = pytz.timezone('Asia/Seoul')
                now = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
                # 스키마: 날짜, 이름, 상태, 위치, 거리, 조퇴사유, 지각사유, 결근사유
                # 지각사유는 7번째(index 6)이므로 앞의 조퇴사유(index 5)는 빈값 처리
                sheet.append_row([now, name, "지각", f"{user_lat},{user_lon}", f"{distance:.1f}m", "", reason.strip()])
                clear_attendance_cache()
                st.success(f"{name}님 {now} 지각 기록 완료!")
                st.session_state['force_rerun'] = True 
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                import traceback
                st.code(traceback.format_exc())
    with col_n:
        if st.button("아니오"):
            st.rerun()

@dlg("결근 확인")
def show_absent_dialog(name):
    st.warning("결근 사유를 작성해주세요.")
    reason = st.text_area(
        "결근 사유",
        placeholder="예: 연차, 병가, 예비군 등",
        help="결근 사유를 필수로 입력해주세요.",
    )
    col_y, col_n = st.columns(2)
    with col_y:
        if st.button("네 (결근)"):
            try:
                if not reason or not reason.strip():
                    st.warning("결근 사유를 입력해주세요.")
                    st.stop()
                sheet = get_sheet()
                kst = pytz.timezone('Asia/Seoul')
                now = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
                # 스키마: 날짜, 이름, 상태, 위치, 거리, 조퇴사유, 지각사유, 결근사유
                # 결근사유는 8번째(index 7)
                sheet.append_row([now, name, "결근", "", "", "", "", reason.strip()])
                clear_attendance_cache()
                st.success(f"{name}님 {now} 결근 기록 완료!")
                st.session_state['force_rerun'] = True 
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                import traceback
                st.code(traceback.format_exc())
    with col_n:
        if st.button("취소"):
            st.rerun()

@dlg("출결 인원 선택")
def show_name_selection_dialog(user_list):
    st.write("본인의 이름을 터치해주세요.")
    cols = st.columns(3)
    for i, user in enumerate(user_list):
        display_name = user.replace("/", "\n")
        with cols[i % 3]:
            if st.button(display_name, use_container_width=True, key=f"btn_user_select_{i}"):
                st.session_state["selected_name_radio"] = user 
                st.rerun()

# --- 출결 기록 확인 페이지 ---
def view_records_page():
    st.markdown("""
    <style>
    div[data-testid="stButton"] button {
        width: 100%;
    }
    th, td {
        white-space: pre-wrap !important; 
        vertical-align: top !important;
        font-size: 0.9rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("📋 출결 현황")

    try:
        with st.spinner("데이터를 불러오는 중입니다..."):
            sheet = get_sheet()
            data = get_cached_records(sheet)
        
        if data and len(data) > 1:
            headers = data[0]
            df = pd.DataFrame(data[1:], columns=headers)
            
            col_ts = headers[0] # 날짜시간
            col_name = headers[1] # 이름
            col_type = headers[2] # 비고/유형 (출근/퇴근 등)
            df['dt'] = pd.to_datetime(df[col_ts], errors='coerce')
            df = df.dropna(subset=['dt'])
            
            kst = pytz.timezone('Asia/Seoul')
            now_kst = datetime.now(kst)
            today = now_kst.date()
            # 이번 달 데이터만 가져옴
            mask_month = (df['dt'].dt.year == today.year) & (df['dt'].dt.month == today.month)
            month_df = df[mask_month].copy().sort_values('dt')
            
            week_days_kor = ["월", "화", "수", "목", "금", "토", "일"]
            today_str = f"{today.month}.{today.day} ({week_days_kor[today.weekday()]})"
            summary_list = []
            users = month_df[col_name].unique()
            
            for user in users:
                user_rows = month_df[month_df[col_name] == user]
                user_rows['date_only'] = user_rows['dt'].dt.date
                dates = user_rows['date_only'].unique()
                
                present_days_cnt = len(dates) # 출석 일수
                late_cnt = 0
                early_leave_cnt = 0
                total_duration = 0
                duration_cnt = 0
                for d in dates:
                    day_recs = user_rows[user_rows['date_only'] == d]
                    types = day_recs[col_type].unique()
                    
                    if "지각" in types: 
                        # 지각 사유에 [업무]가 포함되어 있으면 카운트 제외
                        is_late_count = True
                        if "지각 사유" in day_recs.columns:
                             # 해당 날짜의 지각 기록 중 하나라도 [업무]가 있으면 제외 (보통 하루 1건)
                             reasons = day_recs[day_recs[col_type] == "지각"]["지각 사유"].fillna("").astype(str)
                             for r in reasons:
                                 if "[업무]" in r:
                                     is_late_count = False
                                     break
                        if is_late_count:
                            late_cnt += 1

                    if "조퇴" in types: 
                        # 조퇴 사유에 [업무]가 포함되어 있으면 카운트 제외
                        is_early_count = True
                        if "조퇴 사유" in day_recs.columns:
                             reasons = day_recs[day_recs[col_type] == "조퇴"]["조퇴 사유"].fillna("").astype(str)
                             for r in reasons:
                                 if "[업무]" in r:
                                     is_early_count = False
                                     break
                        if is_early_count:
                            early_leave_cnt += 1
                    
                    ins = day_recs[day_recs[col_type].isin(["출근", "지각"])]
                    outs = day_recs[day_recs[col_type].isin(["퇴근", "조퇴"])]
                    
                    start_time = ins['dt'].min() if not ins.empty else None
                    end_time = outs['dt'].max() if not outs.empty else None
                    
                    if start_time and end_time:
                         diff = (end_time - start_time).total_seconds()
                         total_duration += diff
                         duration_cnt += 1
                
                avg_time = (total_duration / 3600 / duration_cnt) if duration_cnt > 0 else 0
                summary_text = (
                    f"출근: {present_days_cnt}일\n"
                    f"지각: {late_cnt}회\n"
                    f"조퇴: {early_leave_cnt}회\n"
                    f"평균: {avg_time:.1f}h"
                )
                
                row_data = {"이름": user, "월간 요약": summary_text}
                
                day_recs_today = user_rows[user_rows['date_only'] == today]
                cell_text = ""
                
                if not day_recs_today.empty:
                    ins = day_recs_today[day_recs_today[col_type].isin(["출근", "지각"])]
                    start_time = ins['dt'].min() if not ins.empty else None
                    
                    outs = day_recs_today[day_recs_today[col_type].isin(["퇴근", "조퇴"])]
                    end_time = outs['dt'].max() if not outs.empty else None
                    
                    lines = []
                    # 시간
                    s_str = start_time.strftime("%H:%M:%S") if start_time else ""
                    e_str = end_time.strftime("%H:%M:%S") if end_time else ""
                    
                    if s_str: lines.append(f"출근: {s_str}")
                    if e_str: lines.append(f"퇴근: {e_str}")
                    
                    # 태그
                    types = day_recs_today[col_type].unique()
                    tags = []
                    if "지각" in types: tags.append("지각")
                    if "조퇴" in types: tags.append("조퇴")
                    if tags: lines.append(f"[{', '.join(tags)}]")
                    
                    # 근무 시간
                    if start_time and end_time:
                         diff = (end_time - start_time).total_seconds()
                         hours = diff / 3600
                         lines.append(f"시간: 약 {hours:.1f}h")
                    
                    # 사유
                    if "조퇴 사유" in day_recs_today.columns:
                        reasons = day_recs_today[day_recs_today[col_type] == "조퇴"]["조퇴 사유"].dropna().unique()
                        for r in reasons:
                            if r and str(r).strip():
                                lines.append(f"사유: {r}")
                    
                    cell_text = "\n".join(lines)
                
                row_data[today_str] = cell_text
                summary_list.append(row_data)

            if summary_list:
                res_df = pd.DataFrame(summary_list)
                # 컬럼 순서 지정
                cols = ["이름", "월간 요약", today_str]
                final_cols = [c for c in cols if c in res_df.columns]
                res_df = res_df[final_cols]
                
                # HTML 테이블 생성
                html = "<table style='width:100%; border-collapse: collapse; font-size: 0.9em;'>"
                html += "<thead><tr style='background-color: transparent; border-bottom: 2px solid #ddd;'>"
                for col in final_cols:
                    html += f"<th style='padding: 8px; text-align: left; white-space: nowrap;'>{col}</th>"
                html += "</tr></thead>"
                html += "<tbody>"
                for _, row in res_df.iterrows():
                    html += "<tr style='border-bottom: 1px solid #eee;'>"
                    for col in final_cols:
                        val = row[col] if pd.notna(row[col]) else ""
                        val_str = str(val)
                        if "지각" in val_str:
                            val_str = val_str.replace("지각", "<span style='color: #d9534f; font-weight:bold;'>지각</span>")
                        if "조퇴" in val_str:
                            val_str = val_str.replace("조퇴", "<span style='color: #f0ad4e; font-weight:bold;'>조퇴</span>")
                        if "결근" in val_str:
                             val_str = val_str.replace("결근", "<span style='color: red; font-weight:bold;'>결근</span>")

                        val_html = val_str.replace("\n", "<br>")
                        html += f"<td style='padding: 8px; vertical-align: top; line-height: 1.4;'>{val_html}</td>"
                    html += "</tr>"
                html += "</tbody></table>"
                
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.info("이번 주 표시할 기록이 없습니다.")

            if st.button("🔄 새로고침"):
                clear_attendance_cache()
                st.rerun()

        else:
            st.info("데이터가 없습니다.")
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        # 디버깅용
        # import traceback
        # st.code(traceback.format_exc())

    st.divider()
    if st.button("🏠 메인 화면으로 이동"):
        set_view('main')

# --- 메인 출결체크 페이지 ---
def view_main_page():
    st.markdown("""
        <style>
        .responsive-title {
            font-size: clamp(1.2rem, 5vw, 2rem);
            font-weight: bold;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-bottom: 20px;
        }
        div[role="radiogroup"] > label {
            margin-bottom: 12px !important;
            padding: 10px !important;
            border-radius: 8px;
            background-color: #f0f2f6;
        }
        div[role="radiogroup"] > label:hover {
            background-color: #e0e2e6;
        }
        div[data-testid="stButton"] button p {
            white-space: pre-wrap !important;
            line-height: 1.2 !important;
            text-align: center !important;
        }
        </style>
        <div class="responsive-title">📍SCP-LAB 위치 기반 출퇴근 기록</div>
        """, unsafe_allow_html=True)

    # 페이지 이동 버튼
    if st.button("📋 전체 기록 보기", use_container_width=True):
        set_view('records')

    # 사용자 정보 확인
    if "user_names" in st.secrets:
        user_list = st.secrets["user_names"]
    else:
        user_list = ["관리자에게 문의하세요"]
    
    if "selected_name_radio" not in st.session_state:
        st.session_state["selected_name_radio"] = None
    name = st.session_state["selected_name_radio"]

    if not name:
        st.info("본인을 선택해주세요 🔽")
        if st.button("사용자 선택", use_container_width=True, type="primary"):
            show_name_selection_dialog(user_list)
    else:
        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button("🔄", help="사용자 변경"):
                show_name_selection_dialog(user_list)
        with c2:
            st.success(f"**{name}**님 안녕하세요! 👋")
        
        # 결근 버튼 (위치 무관)
        if st.button("🙅 결근 통보 (위치 무관)", use_container_width=True):
            show_absent_dialog(name)

    # 위치 확인 및 출결 로직
    loc = get_geolocation()
    if loc and 'coords' in loc:
        user_lat = loc['coords']['latitude']
        user_lon = loc['coords']['longitude']
        office_point = (LAB_LAT, LAB_LON)
        user_point = (user_lat, user_lon)
        distance = geodesic(office_point, user_point).meters
        
        st.write(f"현재 위치 감지됨: 연구실과의 거리 **{distance:.1f}m**")
        
        if distance <= ALLOWED_RADIUS_M:
            st.success("✅ 연구실 근처입니다. 출퇴근이 가능합니다.")
            col1, col2 = st.columns(2)
            
            is_in = check_is_clocked_in(get_sheet(), name)
            is_out = check_is_clocked_out(get_sheet(), name)

            with col1:
                if is_in:
                    st.button("출근하기 ☀️", disabled=True, key="btn_in_disabled")
                    st.info("이미 오늘 출근 기록이 있습니다.")
                elif is_out:
                    st.button("출근하기 ☀️", disabled=True, key="btn_in_disabled_out")
                    st.info("이미 오늘 퇴근 기록이 있습니다.")
                else:
                    if st.button("출근하기 ☀️", key="btn_in_active"):
                        if not name:
                            st.warning("이름을 입력해주세요.")
                        else:
                            try:
                                kst = pytz.timezone('Asia/Seoul')
                                now_dt = datetime.now(kst)
                                now = now_dt.strftime('%Y-%m-%d %H:%M:%S')
                                if now_dt.hour >= 10:
                                    # 지각 시 팝업 띄우기
                                    show_late_dialog(name, user_lat, user_lon, distance)
                                else:
                                    sheet = get_sheet()
                                    sheet.append_row([now, name, "출근", f"{user_lat},{user_lon}", f"{distance:.1f}m"])
                                    clear_attendance_cache()
                                    st.balloons()
                                    st.success(f"{name}님 {now} 출근 기록 완료!")
                                    st.session_state['force_rerun'] = True
                                    time.sleep(1.5)
                                    st.rerun()
                            except Exception as e:
                                import traceback
                                st.code(traceback.format_exc())
                                st.stop()
                            finally:
                                st.session_state['force_rerun'] = True
                                time.sleep(1.5)
                                st.rerun()

            with col2:
                if is_out:
                    st.button("퇴근하기 🌙", disabled=True, key="btn_out_disabled")
                    st.info("이미 오늘 퇴근 하셨습니다!")
                else:
                    if st.button("퇴근하기 🌙"):
                        if not name:
                            st.warning("이름을 입력해주세요.")
                        else:
                            kst = pytz.timezone('Asia/Seoul')
                            now_dt = datetime.now(kst)
                            if now_dt.hour < 18:
                                show_early_leave_dialog(name, user_lat, user_lon, distance)
                            else:
                                try:
                                    sheet = get_sheet()
                                    now = now_dt.strftime('%Y-%m-%d %H:%M:%S')
                                    sheet.append_row([now, name, "퇴근", f"{user_lat},{user_lon}", f"{distance:.1f}m"])
                                    clear_attendance_cache()
                                    st.success(f"{name}님 {now} 퇴근 기록 완료!")
                                except Exception as e:
                                    import traceback
                                    st.code(traceback.format_exc())
                                    st.stop()
                                finally:
                                    st.session_state['force_rerun'] = True
                                    time.sleep(1.5)
                                    st.rerun()
        else:
            st.error(f"🚫 연구실 반경 {ALLOWED_RADIUS_M}m 밖입니다. 출퇴근을 기록할 수 없습니다.")
        
        df_map = pd.DataFrame({'lat': [user_lat, LAB_LAT], 'lon': [user_lon, LAB_LON]})
        st.map(df_map, zoom=15)
    elif loc and 'error' in loc:
        st.error(f"⚠️ 위치 정보를 불러오지 못했습니다: {loc['error']}\n브라우저 '위치 권한'을 허용했는지 확인해주세요.")
    else:
        st.info("📍 위치 권한을 허용하고 잠시 기다려주세요 (브라우저 새로고침 필요할 수 있음)")

# --- 라우팅 로직 ---
if st.session_state['current_view'] == 'records':
    view_records_page()
else:
    view_main_page()

