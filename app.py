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

OFFICE_LAT = 37.456461 
OFFICE_LON = 126.952096 
ALLOWED_RADIUS_M = 100 

# --- 구글 시트 연결 함수 ---
def get_sheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    client = gspread.authorize(credentials)
    sheet_url = st.secrets["private_gsheets_url"]
    return client.open_by_url(sheet_url).sheet1


if hasattr(st, "dialog"):
    dlg = st.dialog
else:
    dlg = st.experimental_dialog

@dlg("조퇴 확인")
def show_early_leave_dialog(name, user_lat, user_lon, distance):
    st.warning("⚠️ 현재 오후 6시 이전입니다. 조퇴하시겠습니까?")
    col_y, col_n = st.columns(2)
    with col_y:
        if st.button("네 (조퇴)"):
            try:
                sheet = get_sheet()
                kst = pytz.timezone('Asia/Seoul')
                now = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
                sheet.append_row([now, name, "조퇴", f"{user_lat},{user_lon}", f"{distance:.1f}m"])
                st.success(f"{name}님 {now} 조퇴 기록 완료!")
                st.session_state['force_rerun'] = True # 메인 화면 갱신 유도
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
    # 3열 그리드로 버튼 배치
    cols = st.columns(3)
    for i, user in enumerate(user_list):
        # '/'를 줄바꿈 문자 '\n'으로 치환하여 표시
        display_name = user.replace("/", "\n")
        with cols[i % 3]:
            # key를 unique하게 설정
            if st.button(display_name, use_container_width=True, key=f"btn_user_select_{i}"):
                st.session_state["selected_name_radio"] = user # 저장 시에는 원본(user) 저장
                st.rerun()

# --- UI 및 로직 ---
st.set_page_config(page_title="출퇴근 체크", page_icon="📍")
st.markdown("""
    <style>
    .responsive-title {
        font-size: clamp(1.2rem, 5vw, 2rem); /* 최소 1.2rem, 화면의 5%, 최대 2rem */
        font-weight: bold;
        white-space: nowrap;      /* 줄바꿈 방지 */
        overflow: hidden;         /* 넘치는 텍스트 숨김 (필요시) */
        text-overflow: ellipsis;  /* 넘치면 ... 표시 (필요시) */
        margin-bottom: 20px;
    }
    /* 라디오 버튼 간격 조정 */
    div[role="radiogroup"] > label {
        margin-bottom: 12px !important;  /* 항목 간 간격 추가 */
        padding: 10px !important;        /* 터치 영역 확대 */
        border-radius: 8px;              /* 시각적 구분감 */
        background-color: #f0f2f6;       /* 연한 배경색 (선택사항) */
    }
    div[role="radiogroup"] > label:hover {
        background-color: #e0e2e6;       /* 호버 효과 */
    }
    /* 버튼 텍스트 줄바꿈 허용 */
    div[data-testid="stButton"] button p {
        white-space: pre-wrap !important;
        line-height: 1.2 !important;
        text-align: center !important;
    }
    </style>
    <div class="responsive-title">📍SCP-LAB 위치 기반 출퇴근 기록</div>
    """, unsafe_allow_html=True)

# 1. 사용자 정보 입력
if "user_names" in st.secrets:
    user_list = st.secrets["user_names"]
else:
    user_list = ["관리자에게 문의하세요(secrets.toml 설정 필요)"]
if "selected_name_radio" not in st.session_state:
    st.session_state["selected_name_radio"] = None
name = st.session_state["selected_name_radio"]
if not name:
    # 이름이 선택되지 않았을 때
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

# 2. 위치 가져오기 (브라우저 GPS)
loc = get_geolocation()
if loc:
    user_lat = loc['coords']['latitude']
    user_lon = loc['coords']['longitude']

    # 거리 계산
    office_point = (OFFICE_LAT, OFFICE_LON)
    user_point = (user_lat, user_lon)
    distance = geodesic(office_point, user_point).meters
    
    st.write(f"현재 위치 감지됨: 연구실과의 거리 **{distance:.1f}m**")
    
    # 반경 체크 및 버튼 표시
    if distance <= ALLOWED_RADIUS_M:
        st.success("✅ 연구실 근처입니다. 출퇴근이 가능합니다.")
        
        col1, col2 = st.columns(2)
        
        # 상태 확인
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
                 # 출근도 안했고 퇴근도 안한 상태 -> 출근 가능
                 if st.button("출근하기 ☀️", key="btn_in_active"):
                    if not name:
                        st.warning("이름을 입력해주세요.")
                    else:
                        try:
                            sheet = get_sheet()
                            kst = pytz.timezone('Asia/Seoul')
                            now_dt = datetime.now(kst)
                            now = now_dt.strftime('%Y-%m-%d %H:%M:%S')

                            # 10시 이후 체크
                            if now_dt.hour >= 10:
                                sheet.append_row([now, name, "지각", f"{user_lat},{user_lon}", f"{distance:.1f}m"])
                                st.warning(f"⚠️ {name}님 10시가 지났습니다. 지각 처리됩니다.")
                            else:
                                sheet.append_row([now, name, "출근", f"{user_lat},{user_lon}", f"{distance:.1f}m"])
                                st.balloons()
                                st.success(f"{name}님 {now} 출근 기록 완료!")
                        except Exception as e: #후에 조종
                            import traceback
                            err_msg = traceback.format_exc()
                            st.code(err_msg, language="bash") 
                            st.stop()  
                        finally:
                            st.session_state['force_rerun'] = True # 메인 화면 갱신 유도
                            time.sleep(1.5)
                            st.rerun()  

        with col2:
            if is_out:
                st.button("출근하기 ☀️", disabled=True, key="btn_in_disabled_out")
                st.info("이미 오늘 퇴근 하셨습니다!")
            else:
                if st.button("퇴근하기 🌙"):
                    if not name:
                        st.warning("이름을 입력해주세요.")
                    else:
                        # 시간 체크; 오후 6시 이전이면 조퇴
                        kst = pytz.timezone('Asia/Seoul')
                        now_dt = datetime.now(kst)
                        if now_dt.hour < 18:
                            show_early_leave_dialog(name, user_lat, user_lon, distance)
                        else:
                            try:
                                sheet = get_sheet()
                                now = now_dt.strftime('%Y-%m-%d %H:%M:%S')
                                sheet.append_row([now, name, "퇴근", f"{user_lat},{user_lon}", f"{distance:.1f}m"])
                                st.success(f"{name}님 {now} 퇴근 기록 완료!")
                            except Exception as e:
                                import traceback
                                err_msg = traceback.format_exc()
                                st.code(err_msg, language="bash") 
                                st.stop() 
                            finally:
                                st.session_state['force_rerun'] = True # 메인 화면 갱신 유도
                                time.sleep(1.5)
                                st.rerun()

    else:
        st.error(f"🚫 연구실 반경 {ALLOWED_RADIUS_M}m 밖입니다. 출퇴근을 기록할 수 없습니다.")
    
    # 지도 표시 (선택 사항)
    df_map = pd.DataFrame({'lat': [user_lat, OFFICE_LAT], 'lon': [user_lon, OFFICE_LON]})
    st.map(df_map, zoom=15)

else:
    st.info("📍 위치 권한을 허용하고 잠시 기다려주세요 (브라우저 새로고침 필요할 수 있음)")

