import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from geopy.distance import geodesic
from streamlit_js_eval import get_geolocation
import time
from datetime import datetime
import pytz

# --- 설정 (회사 위치 및 반경) ---
OFFICE_LAT = 37.456461  # 예: 강남역 위도 (수정 필요)
OFFICE_LON = 126.952096 # 예: 강남역 경도 (수정 필요)
ALLOWED_RADIUS_M = 100 # 허용 반경 (미터)

# --- 구글 시트 연결 함수 ---
def get_sheet():
    # Streamlit Secrets에서 인증 정보 로드
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    client = gspread.authorize(credentials)
    # 시트 이름 혹은 URL로 열기 (secrets에 sheet_url 저장 권장)
    sheet_url = st.secrets["private_gsheets_url"]
    return client.open_by_url(sheet_url).sheet1

# --- UI 및 로직 ---
st.set_page_config(page_title="출퇴근 체크", page_icon="📍")
st.markdown("## 📍 위치 기반 출퇴근 기록")

# 1. 사용자 정보 입력
name = st.text_input("이름을 입력하세요", placeholder="예: 홍길동")

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
    
    # 지도 표시 (선택 사항)
    df_map = pd.DataFrame({'lat': [user_lat, OFFICE_LAT], 'lon': [user_lon, OFFICE_LON]})
    st.map(df_map, zoom=15)

    # 3. 반경 체크 및 버튼 표시
    if distance <= ALLOWED_RADIUS_M:
        st.success("✅ 연구실 근처입니다. 출퇴근이 가능합니다.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("출근하기 ☀️"):
                if not name:
                    st.warning("이름을 입력해주세요.")
                else:
                    try:
                        sheet = get_sheet()
                        kst = pytz.timezone('Asia/Seoul')
                        now = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
                        sheet.append_row([now, name, "출근", f"{user_lat},{user_lon}", f"{distance:.1f}m"])
                        st.balloons()
                        st.success(f"{name}님 {now} 출근 기록 완료!")
                    except Exception as e:
                        st.error(f"오류 발생: {e}")

        with col2:
            if st.button("퇴근하기 🌙"):
                if not name:
                    st.warning("이름을 입력해주세요.")
                else:
                    try:
                        sheet = get_sheet()
                        kst = pytz.timezone('Asia/Seoul')
                        now = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
                        sheet.append_row([now, name, "퇴근", f"{user_lat},{user_lon}", f"{distance:.1f}m"])
                        st.success(f"{name}님 {now} 퇴근 기록 완료!")
                    except Exception as e:
                        st.error(f"오류 발생: {e}")
    else:
        st.error(f"🚫 연구실 반경 {ALLOWED_RADIUS_M}m 밖입니다. 출퇴근을 기록할 수 없습니다.")
else:
    st.info("📍 위치 권한을 허용하고 잠시 기다려주세요 (브라우저 새로고침 필요할 수 있음)")

