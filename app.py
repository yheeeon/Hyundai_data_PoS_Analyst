import streamlit as st
from dashboard import render_dashboard

# 페이지 설정
st.set_page_config(
    page_title="자동차 등록 현황 대시보드",
    layout="wide",
    initial_sidebar_state="collapsed"  # 사이드바 기본 숨김
)

# 모듈 import
def main():
    render_dashboard()

if __name__ == "__main__":
    main()