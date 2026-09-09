import pandas as pd
import streamlit as st


def load_analytics_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    connection = st.connection("mydb", type="sql")
    registration = connection.query(
        """
        SELECT year, month, region_name, fuel_name,
               powertrain_name AS powertrain, vehicle_type_name,
               registered_qty
        FROM vw_market_registration_monthly
        """,
        ttl=600,
    )
    sales = connection.query(
        """
        SELECT year, sales_month, market, category, model_family,
               powertrain, sales_qty
        FROM vw_hyundai_sales_monthly
        """,
        ttl=600,
    )
    return registration, sales
