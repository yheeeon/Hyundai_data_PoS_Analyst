from pathlib import Path

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent

from src.automotive_analytics.streamlit_data import load_analytics_data


@st.cache_data
def _data():
    return load_analytics_data()


def render_dashboard():
    try:
        registration, sales = _data()
    except Exception as error:
        st.error("DB 연결 또는 분석 view를 확인하세요.")
        st.code(str(error))
        st.stop()
    st.title("자동차 시장과 현대차 포트폴리오")
    st.caption("시장 등록 규모와 현대차 판매 포트폴리오를 같은 기준월로 비교합니다.")

    years = sorted(set(registration["year"]) | set(sales["year"]))
    year = st.sidebar.selectbox("분석 연도", years, index=len(years) - 1)
    months = sorted(registration.loc[registration.year == year, "month"].unique())
    month = st.sidebar.selectbox("분석 월", months, index=len(months) - 1)
    market = st.sidebar.selectbox("현대차 시장", ["전체", "Domestic", "Export"])

    market_slice = registration[(registration.year == year) & (registration.month == month)]
    sales_slice = sales[(sales.year == year) & (sales.sales_month == month)]
    if market != "전체":
        sales_slice = sales_slice[sales_slice.market == market]

    total_market = int(market_slice.registered_qty.sum())
    total_sales = int(sales_slice.sales_qty.sum())
    eco_market = int(market_slice[market_slice.powertrain.isin(["EV", "HEV", "FCEV"])].registered_qty.sum())
    st.metric("시장 등록대수", f"{total_market:,}대")
    st.metric("현대차 판매량", f"{total_sales:,}대")
    st.metric("친환경 파워트레인 비중", f"{eco_market / total_market * 100:.1f}%" if total_market else "-")

    left, right = st.columns(2)
    with left:
        region = market_slice.groupby("region_name", as_index=False)["registered_qty"].sum().sort_values("registered_qty", ascending=False)
        st.plotly_chart(px.bar(region, x="region_name", y="registered_qty", title="지역별 시장 등록대수"), use_container_width=True)
    with right:
        mix = sales_slice.groupby("model_family", as_index=False)["sales_qty"].sum().sort_values("sales_qty", ascending=False).head(15)
        st.plotly_chart(px.bar(mix, x="sales_qty", y="model_family", orientation="h", title="현대차 모델 패밀리 판매량"), use_container_width=True)

    st.subheader("파워트레인 기회 영역")
    market_mix = market_slice.groupby("powertrain", as_index=False)["registered_qty"].sum().rename(columns={"registered_qty": "market_qty"})
    sales_mix = sales_slice.groupby("powertrain", as_index=False)["sales_qty"].sum()
    opportunity = market_mix.merge(sales_mix, on="powertrain", how="outer").fillna(0)
    opportunity["market_share"] = opportunity.market_qty / opportunity.market_qty.sum() * 100
    opportunity["hyundai_share"] = opportunity.sales_qty / opportunity.sales_qty.sum() * 100 if opportunity.sales_qty.sum() else 0
    opportunity["share_gap"] = (opportunity.market_share - opportunity.hyundai_share).round(1)
    st.dataframe(opportunity.sort_values("share_gap", ascending=False), use_container_width=True, hide_index=True)
