import pandas as pd
import plotly.express as px
import streamlit as st

from src.automotive_analytics.streamlit_data import load_analytics_data

ECO_POWERTRAINS = ["EV", "HEV", "FCEV"]


@st.cache_data
def _data():
    return load_analytics_data()


def _month_options(registration: pd.DataFrame, sales: pd.DataFrame) -> list[tuple[int, int]]:
    registration_months = set(zip(registration["year"], registration["month"]))
    sales_months = set(zip(sales["year"], sales["sales_month"]))
    return sorted(registration_months | sales_months)


def _region_transition(registration: pd.DataFrame, year: int, month: int) -> tuple[pd.DataFrame, str | None]:
    available_months = sorted(set(zip(registration["year"], registration["month"])))
    current_key = (year, month)
    previous_keys = [key for key in available_months if key < current_key]
    previous_key = previous_keys[-1] if previous_keys else None

    current = registration[(registration["year"] == year) & (registration["month"] == month)].copy()
    current["eco_qty"] = current["registered_qty"].where(current["powertrain"].isin(ECO_POWERTRAINS), 0)
    current = current.groupby("region_name", as_index=False).agg(
        registered_qty=("registered_qty", "sum"),
        eco_qty=("eco_qty", "sum"),
    )
    current["eco_share"] = current["eco_qty"] / current["registered_qty"] * 100

    if previous_key is None:
        current["previous_eco_share"] = pd.NA
        current["change_pp"] = pd.NA
        return current, None

    previous = registration[
        (registration["year"] == previous_key[0]) & (registration["month"] == previous_key[1])
    ].copy()
    previous["eco_qty"] = previous["registered_qty"].where(previous["powertrain"].isin(ECO_POWERTRAINS), 0)
    previous = previous.groupby("region_name", as_index=False).agg(
        registered_qty=("registered_qty", "sum"),
        eco_qty=("eco_qty", "sum"),
    )
    previous["previous_eco_share"] = previous["eco_qty"] / previous["registered_qty"] * 100
    result = current.merge(previous[["region_name", "previous_eco_share"]], on="region_name", how="left")
    result["change_pp"] = result["eco_share"] - result["previous_eco_share"]
    return result, f"{previous_key[0]}년 {previous_key[1]}월"


def _sales_mix(sales: pd.DataFrame, year: int, month: int, market: str) -> pd.DataFrame:
    selected = sales[(sales["year"] == year) & (sales["sales_month"] == month)].copy()
    if market != "전체":
        selected = selected[selected["market"] == market]
    mix = selected.groupby("powertrain", as_index=False)["sales_qty"].sum()
    total = mix["sales_qty"].sum()
    mix["sales_share"] = mix["sales_qty"] / total * 100 if total else 0
    return mix


def _powertrain_mix_by_market(sales: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    selected = sales[(sales["year"] == year) & (sales["sales_month"] == month)]
    mix = selected.groupby(["market", "powertrain"], as_index=False)["sales_qty"].sum()
    totals = mix.groupby("market")["sales_qty"].transform("sum")
    mix["sales_share"] = mix["sales_qty"] / totals * 100
    return mix


def render_dashboard():
    try:
        registration, sales = _data()
    except Exception as error:
        st.error("DB 연결 또는 분석 view를 확인하세요.")
        st.code(str(error))
        st.stop()

    st.title("친환경차 전환 모니터링")
    st.caption("지역별 시장 전환 속도와 현대차 판매 포트폴리오를 같은 기준월로 확인합니다.")

    month_options = _month_options(registration, sales)
    selected_date = st.sidebar.selectbox(
        "분석 기준월",
        month_options,
        index=len(month_options) - 1,
        format_func=lambda value: f"{value[0]}년 {value[1]}월",
    )
    year, month = selected_date
    market = st.sidebar.selectbox("현대차 시장", ["전체", "Domestic", "Export"])

    market_slice = registration[(registration["year"] == year) & (registration["month"] == month)]
    sales_slice = sales[(sales["year"] == year) & (sales["sales_month"] == month)]
    if market != "전체":
        sales_slice = sales_slice[sales_slice["market"] == market]

    total_market = int(market_slice["registered_qty"].sum())
    eco_market = int(market_slice[market_slice["powertrain"].isin(ECO_POWERTRAINS)]["registered_qty"].sum())
    total_sales = int(sales_slice["sales_qty"].sum())
    eco_sales = int(sales_slice[sales_slice["powertrain"].isin(ECO_POWERTRAINS)]["sales_qty"].sum())
    region_transition, previous_label = _region_transition(registration, year, month)
    fastest_region = None
    if previous_label is not None:
        changeable = region_transition.dropna(subset=["change_pp"])
        if not changeable.empty:
            fastest_region = changeable.sort_values("change_pp", ascending=False).iloc[0]

    metric_columns = st.columns(4)
    metric_columns[0].metric("시장 등록대수", f"{total_market:,}대")
    metric_columns[1].metric("시장 친환경차 비중", f"{eco_market / total_market * 100:.1f}%" if total_market else "-")
    metric_columns[2].metric("현대차 친환경 판매 구성", f"{eco_sales / total_sales * 100:.1f}%" if total_sales else "-")
    metric_columns[3].metric(
        "전환 상승폭 1위 지역",
        fastest_region["region_name"] if fastest_region is not None else "비교 불가",
        f"+{fastest_region['change_pp']:.1f}%p" if fastest_region is not None else None,
    )

    st.subheader("1. 어느 지역에서 친환경차 전환이 빠른가?")
    if previous_label is None:
        st.info("이전 기준월이 없어 전환 속도를 계산할 수 없습니다.")
    else:
        st.caption(f"전월({previous_label}) 대비 친환경차 등록 비중의 증감폭입니다. 양수일수록 전환이 빨라진 지역입니다.")
        left, right = st.columns(2)
        with left:
            change_chart = region_transition.sort_values("change_pp", ascending=False)
            st.plotly_chart(
                px.bar(change_chart, x="region_name", y="change_pp", color="change_pp", color_continuous_scale="RdYlGn", title="지역별 전월 대비 전환 속도(%p)"),
                use_container_width=True,
            )
        with right:
            st.plotly_chart(
                px.scatter(region_transition, x="eco_share", y="change_pp", size="registered_qty", hover_name="region_name", labels={"eco_share": "현재 친환경차 비중(%)", "change_pp": "전월 대비 증감(%p)"}, title="현재 비중과 전환 속도"),
                use_container_width=True,
            )
        region_table = region_transition.sort_values("change_pp", ascending=False).rename(
            columns={"region_name": "지역", "registered_qty": "시장 등록대수", "eco_share": "현재 친환경차 비중(%)", "previous_eco_share": "이전 친환경차 비중(%)", "change_pp": "전월 대비 증감(%p)"}
        )
        st.dataframe(region_table[["지역", "시장 등록대수", "현재 친환경차 비중(%)", "이전 친환경차 비중(%)", "전월 대비 증감(%p)"]].round(1), use_container_width=True, hide_index=True)

    st.subheader("2. 지역 시장과 현대차 판매 구성은 어떻게 맞물리는가?")
    st.caption("현대차 원천 판매 데이터에는 지역 정보가 없어, 지역별 시장 비중과 선택한 현대차 시장의 전체 판매 구성을 별도로 비교합니다. 이는 지역별 현대차 점유율이 아닙니다.")
    national_market_eco = eco_market / total_market * 100 if total_market else 0
    hyundai_eco = eco_sales / total_sales * 100 if total_sales else 0
    comparison = region_transition[["region_name", "eco_share"]].copy()
    comparison["hyundai_eco_share"] = hyundai_eco
    comparison["market_level"] = comparison["eco_share"].map(lambda value: "시장 전환 상위" if value >= national_market_eco else "시장 전환 하위")
    comparison = comparison.sort_values("eco_share", ascending=False).rename(columns={"region_name": "지역", "eco_share": "지역 시장 친환경차 비중(%)", "hyundai_eco_share": "현대차 친환경 판매 구성(%)", "market_level": "시장 위치"})
    st.dataframe(comparison.round(1), use_container_width=True, hide_index=True)
    st.plotly_chart(px.bar(comparison, x="지역", y=["지역 시장 친환경차 비중(%)", "현대차 친환경 판매 구성(%)"], barmode="group", title="지역 시장 비중과 현대차 판매 구성 참고 비교", labels={"value": "비중(%)", "variable": "구분"}), use_container_width=True)

    st.subheader("3. 국내와 수출의 대응 방향은 다른가?")
    market_mix = _powertrain_mix_by_market(sales, year, month)
    left, right = st.columns(2)
    with left:
        st.plotly_chart(px.bar(market_mix, x="market", y="sales_share", color="powertrain", barmode="stack", title="국내·수출 파워트레인 판매 구성", labels={"sales_share": "판매 구성(%)", "market": "판매시장"}), use_container_width=True)
    with right:
        model_mix = sales[(sales["year"] == year) & (sales["sales_month"] == month)]
        top_models = model_mix.groupby(["market", "model_family"], as_index=False)["sales_qty"].sum()
        top_models = top_models.sort_values(["market", "sales_qty"], ascending=[True, False]).groupby("market").head(5)
        st.plotly_chart(px.bar(top_models, x="sales_qty", y="model_family", color="market", facet_col="market", orientation="h", title="국내·수출 판매 상위 모델", labels={"sales_qty": "판매대수", "model_family": "모델 패밀리"}), use_container_width=True)

    selected_mix = _sales_mix(sales, year, month, market)
    st.caption(f"현재 선택 시장: {market}. 친환경차 구성은 EV·HEV·FCEV 판매 비중의 합입니다.")
    st.dataframe(selected_mix.rename(columns={"powertrain": "파워트레인", "sales_qty": "판매대수", "sales_share": "판매 구성(%)"}).round(1), use_container_width=True, hide_index=True)
