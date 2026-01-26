import streamlit as st
import pandas as pd
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules import get_sheet

st.set_page_config(page_title="출퇴근 기록 확인", page_icon="📋")
st.title("📋 출퇴근 기록 확인")

try:
    with st.spinner("데이터를 불러오는 중입니다..."):
        sheet = get_sheet()
        data = sheet.get_all_values()
    if data:
        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)
        if "날짜시간" in df.columns:
            df = df.sort_values(by="날짜시간", ascending=False)
        if st.button("🔄 새로고침"):
            st.rerun()
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("표시할 기록이 없습니다.")
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")

# 메인으로 돌아가기 버튼 (사이드바가 자동으로 생기지만 직관적인 이동을 위해)
st.divider()
if st.button("🏠 메인 화면으로 이동"):
    st.switch_page("app.py")
