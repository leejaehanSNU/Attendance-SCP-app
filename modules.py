import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz

# --- 구글 시트 연결 함수 ---
@st.cache_resource
def get_sheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    client = gspread.authorize(credentials)
    sheet_url = st.secrets["private_gsheets_url"]
    return client.open_by_url(sheet_url).sheet1

# TTL을 10초로 설정하여 API 호출 최소화
# _sheet_obj: 인자 이름 앞에 언더바(_)를 붙이면 hash 계산에서 제외되어 캐싱 키 생성 시 무시됨
@st.cache_data(ttl=10)
def get_cached_records(_sheet_obj):
    return _sheet_obj.get_all_values()

def clear_attendance_cache():
    """출퇴근 기록이 갱신되었을 때 캐시를 강제로 비우는 함수"""
    get_cached_records.clear()

def check_is_clocked_in(sheet, name):
    """ 특정 사용자가 오늘 날짜(KST 기준)에 '출근' 기록을 남겼는지 확인하는 함수 """
    try:
        # 캐싱된 함수 사용
        all_records = get_cached_records(sheet)
        kst = pytz.timezone('Asia/Seoul')
        today_date = datetime.now(kst).strftime('%Y-%m-%d')
        for row in all_records:
            # row 구조: [timestamp, name, type, lat,lon, distance]
            if len(row) < 3: continue
            timestamp_str = row[0]
            record_name = row[1]
            record_type = row[2]
            if timestamp_str.startswith(today_date) and record_name == name and record_type in ["출근", "지각"]:
                return True
        return False
    except Exception as e:
        print(f"Error checking attendance: {e}")
        return False


def check_is_clocked_out(sheet, name):
    """ 특정 사용자가 오늘 날짜(KST 기준)에 '퇴근' 또는 '조퇴' 기록을 남겼는지 확인하는 함수 """
    try:
        all_records = get_cached_records(sheet)
        kst = pytz.timezone('Asia/Seoul')
        today_date = datetime.now(kst).strftime('%Y-%m-%d')
        for row in all_records:
            if len(row) < 3:
                continue
            timestamp_str = row[0]
            record_name = row[1]
            record_type = row[2]
            if timestamp_str.startswith(today_date) and record_name == name and record_type in ["퇴근", "조퇴"]:
                return True
        return False
    except Exception as e:
        print(f"Error checking clocked out: {e}")
        return False

def check_is_absent_today(sheet, name):
    """ 특정 사용자가 오늘 날짜(KST 기준)에 '결근' 기록을 남겼는지 확인하는 함수 """
    try:
        all_records = get_cached_records(sheet)
        kst = pytz.timezone('Asia/Seoul')
        today_date = datetime.now(kst).strftime('%Y-%m-%d')
        for row in all_records:
            if len(row) < 3:
                continue
            timestamp_str = row[0]
            record_name = row[1]
            record_type = row[2]
            if timestamp_str.startswith(today_date) and record_name == name and record_type == "결근":
                return True
        return False
    except Exception as e:
        print(f"Error checking absent: {e}")
        return False
