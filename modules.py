from datetime import datetime
import pytz

def check_is_clocked_in(sheet, name):
    """ 특정 사용자가 오늘 날짜(KST 기준)에 '출근' 기록을 남겼는지 확인하는 함수 """
    try:
        all_records = sheet.get_all_values()
        kst = pytz.timezone('Asia/Seoul')
        today_date = datetime.now(kst).strftime('%Y-%m-%d')
        for row in all_records:
            # row 구조: [timestamp, name, type, lat,lon, distance]
            # ['2023-10-27 09:00:00', '홍길동', '출근', ...]
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
        all_records = sheet.get_all_values()
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
