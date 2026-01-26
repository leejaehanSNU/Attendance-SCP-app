import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from geopy.distance import geodesic
from streamlit_js_eval import get_geolocation
import time
from datetime import datetime
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
    </style>
    """, unsafe_allow_html=True)
    
    st.title("📋 출퇴근 기록 확인")

    try:
        with st.spinner("데이터를 불러오는 중입니다..."):
            sheet = get_sheet()
            data = get_cached_records(sheet)
        if data:
            headers = data[0]
            rows = data[1:]
            df = pd.DataFrame(rows, columns=headers)
            if "날짜시간" in df.columns:
                df = df.sort_values(by="날짜시간", ascending=False)
            
            if st.button("🔄 새로고침"):
                clear_attendance_cache()
                st.rerun()
            
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("표시할 기록이 없습니다.")
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")

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

    # 위치 확인 및 출결 로직
    loc = get_geolocation()
    if loc:
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
                                sheet = get_sheet()
                                kst = pytz.timezone('Asia/Seoul')
                                now_dt = datetime.now(kst)
                                now = now_dt.strftime('%Y-%m-%d %H:%M:%S')
                                if now_dt.hour >= 10:
                                    sheet.append_row([now, name, "지각", f"{user_lat},{user_lon}", f"{distance:.1f}m"])
                                    clear_attendance_cache()
                                    st.warning(f"⚠️ {name}님 10시가 지났습니다. 지각 처리됩니다.")
                                else:
                                    sheet.append_row([now, name, "출근", f"{user_lat},{user_lon}", f"{distance:.1f}m"])
                                    clear_attendance_cache()
                                    st.balloons()
                                    st.success(f"{name}님 {now} 출근 기록 완료!")
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
    else:
        st.info("📍 위치 권한을 허용하고 잠시 기다려주세요 (브라우저 새로고침 필요할 수 있음)")

# --- 라우팅 로직 ---
if st.session_state['current_view'] == 'records':
    view_records_page()
else:
    view_main_page()

