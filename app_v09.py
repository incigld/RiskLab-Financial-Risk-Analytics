
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(
    page_title="RiskLab | Financial Risk Analytics",
    page_icon="📊",
    layout="wide",
    menu_items={
        "About": "RiskLab — Financial Risk Analytics & Simulation Platform. Credit risk analysis, income shock simulations and early warning indicators."
    }
)

st.markdown("""
<style>
    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        font-size: 17px;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label p {
        font-size: 17px !important;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# RISKLAB v0.6 - NAVIGATION

st.sidebar.markdown("## ◈ RiskLab")
st.sidebar.caption("FINANCIAL RISK ANALYTICS")
st.sidebar.divider()

navigation_groups = {
    "DASHBOARD": [
        "Overview"
    ],
    "RISK ANALYTICS": [
        "Credit Risk",
        "Stress Testing",
        "Risk Migration",
        "Portfolio Insights",
        "Early Warning Radar"
    ],
    "DECISION SUPPORT": [
        "Risk Mitigation Simulator",
        "What-If Scenario Builder"

    ]
}

page_icons = {
    "Overview": ":material/dashboard: Overview",
    "Credit Risk": ":material/account_balance: Credit Risk",
    "Stress Testing": ":material/monitoring: Stress Testing",
    "Risk Migration": ":material/swap_horiz: Risk Migration",
    "Portfolio Insights": ":material/pie_chart: Portfolio Insights",
    "Early Warning Radar": ":material/notification_important: Early Warning Radar",
    "Risk Mitigation Simulator": ":material/tune: Risk Mitigation Simulator",
    "What-If Scenario Builder": ":material/compare_arrows: What-If Scenario Builder"

}

if "selected_page" not in st.session_state:
    st.session_state.selected_page = "Overview"

for group_name, group_pages in navigation_groups.items():
    st.sidebar.caption(group_name)

    for page_name in group_pages:
        is_active = st.session_state.selected_page == page_name

        if st.sidebar.button(
            page_icons[page_name],
            key=f"nav_button_{page_name}",
            use_container_width=True,
            type="primary" if is_active else "secondary"
        ):
            st.session_state.selected_page = page_name
            st.rerun()

page = st.session_state.selected_page

st.title("RiskLab | Credit Risk")
st.caption("Financial Risk Analytics Platform - Demo")

# Sample Portfolio Generation

# Data Import

st.sidebar.header("Portfolio Data")

uploaded_file = st.sidebar.file_uploader(
    "Upload Customer Portfolio",
    type=["csv", "xlsx"],
    key="risklab_portfolio_upload"
)

# Ornek portfoy
rng = np.random.default_rng(42)
n = 1000

df = pd.DataFrame({
    "Musteri": range(1, n + 1),
    "Gelir": rng.integers(20000, 150000, n),
    "Aylik_Borc": rng.integers(2000, 65000, n),
    "Kredi_Bakiyesi": rng.integers(10000, 500000, n)
})

if uploaded_file is not None:
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            yeni_df = pd.read_csv(uploaded_file)
        else:
            yeni_df = pd.read_excel(uploaded_file)

        gerekli = [
            "Musteri", "Gelir",
            "Aylik_Borc", "Kredi_Bakiyesi"
        ]

        eksik = [
            sutun for sutun in gerekli
            if sutun not in yeni_df.columns
        ]

        if eksik:
            st.error(
                "Missing columns: " + ", ".join(eksik)
            )
            st.stop()

        for sutun in [
            "Gelir", "Aylik_Borc", "Kredi_Bakiyesi"
        ]:
            yeni_df[sutun] = pd.to_numeric(
                yeni_df[sutun], errors="coerce"
            )

        hatali = (
            yeni_df[gerekli].isna().any(axis=1)
            | (yeni_df["Gelir"] <= 0)
            | (yeni_df["Aylik_Borc"] < 0)
            | (yeni_df["Kredi_Bakiyesi"] < 0)
        )

        if hatali.any():
            st.error(
                f"{hatali.sum()} rows contain missing "
                "or invalid data."
            )
            st.stop()

        if yeni_df.empty:
            st.error("Uploaded file is empty.")
            st.stop()

        if yeni_df["Musteri"].duplicated().any():
            st.error("Duplicate Customer IDs found.")
            st.stop()

        df = yeni_df.copy()
        st.sidebar.success(
            f"{len(df)} customers uploaded successfully!"
        )

    except Exception as e:
        st.error(f"Unable to read file: {e}")
        st.stop()

st.sidebar.header("Stress Test")

gelir_dususu = st.sidebar.slider(
    "Customer Income Reduction (%)",
    min_value=0,
    max_value=60,
    value=25,
    step=5
)

def risk_hesapla(data, dusus, taksit_degisim=0):
    sonuc = data.copy()
    sonuc["DTI"] = (
        (sonuc["Aylik_Borc"] * (1 + taksit_degisim / 100)) /
        (sonuc["Gelir"] * (1 - dusus / 100))
    )

    sonuc["Risk"] = np.select(
        [sonuc["DTI"] < 0.30, sonuc["DTI"] < 0.50],
        ["Dusuk", "Orta"],
        default="Yuksek"
    )

    sonuc["PD"] = sonuc["Risk"].map({
        "Dusuk": 0.02,
        "Orta": 0.08,
        "Yuksek": 0.20
    })

    sonuc["Beklenen_Kayip"] = (
        sonuc["PD"] *
        0.45 *
        sonuc["Kredi_Bakiyesi"]
    )

    return sonuc

normal = risk_hesapla(df, 0)
kriz = risk_hesapla(df, gelir_dususu)
kriz["Income_Shock_Threshold"] = (
    (1 - kriz["DTI"] / 0.50) * 100
).clip(lower=0)

kriz["Early_Warning"] = (
    (kriz["DTI"] < 0.50) &
    (kriz["Income_Shock_Threshold"] <= 10)
)

fragile_customers = kriz["Early_Warning"].sum()

fragile_exposure = kriz.loc[
    kriz["Early_Warning"], "Kredi_Bakiyesi"
].sum()

total_exposure = kriz["Kredi_Bakiyesi"].sum()

fragile_exposure_ratio = (
    fragile_exposure / total_exposure * 100
    if total_exposure > 0 else 0
)

normal_kayip = normal["Beklenen_Kayip"].sum()
kriz_kayip = kriz["Beklenen_Kayip"].sum()
# RISKLAB v0.6 - OVERVIEW

if page == "Overview":
    st.header("Portfolio Overview")
    st.caption("Key portfolio indicators")

    toplam_kredi = df["Kredi_Bakiyesi"].sum()
    
    el_rate = (kriz_kayip / toplam_kredi * 100) if toplam_kredi > 0 else 0

    yuksek_riskli = (
        kriz["Risk"] == "Yuksek"
    ).sum()

    col1, col2 = st.columns(2)

    with col1.container(border=True):
        st.metric("Total Exposure", f"{toplam_kredi:,.0f} TL")

    with col2.container(border=True):
        st.metric("High Risk Customers", int(yuksek_riskli))

    col3, col4 = st.columns(2)

    with col3.container(border=True):
        st.metric("Expected Loss", f"{kriz_kayip:,.0f} TL")

    with col4.container(border=True):
        st.metric("Expected Loss Rate", f"{el_rate:.2f}%")

if page == "Stress Testing":
    st.header("Stress Testing")
    
    loss_delta_pct = (
        (kriz_kayip / normal_kayip - 1) * 100
        if normal_kayip > 0 else 0
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Customers", len(df))
    col2.metric("Baseline Expected Loss",
                f"{normal_kayip:,.0f} TL")
    col3.metric("Stressed Expected Loss",
                f"{kriz_kayip:,.0f} TL",
                delta=f"{loss_delta_pct:.1f}%",
                delta_color="inverse")

    risk_sayilari = (
        kriz["Risk"].value_counts()
        .rename_axis("Risk")
        .reset_index(name="Number of Customers")
    )

    risk_sayilari["Risk"] = risk_sayilari["Risk"].replace({
        "Dusuk": "Low",
        "Orta": "Medium",
        "Yuksek": "High"
    })

    fig = px.bar(
        risk_sayilari,
        x="Risk",
        y="Number of Customers",
        title="Credit Risk Distribution",
        color="Risk"
    )

    st.plotly_chart(fig, use_container_width=True)

if page == "Credit Risk":


                st.subheader("Customer Portfolio")

                display_portfolio = kriz.rename(columns={
                    "Musteri": "Customer ID",
                    "Gelir": "Monthly Income",
                    "Aylik_Borc": "Monthly Debt",
                    "Kredi_Bakiyesi": "Credit Exposure",
                    "Risk": "Risk Level",
                    "Beklenen_Kayip": "Expected Loss"
                })

                display_portfolio["Risk Level"] = display_portfolio["Risk Level"].replace({
                    "Dusuk": "Low",
                    "Orta": "Medium",
                    "Yuksek": "High"
                })

                st.dataframe(
                    display_portfolio,
                    use_container_width=True,
                    hide_index=True
                )
                st.download_button(
                    "Download CSV Report",
                    display_portfolio.to_csv(index=False).encode("utf-8-sig"),
                    "risklab_rapor.csv",
                    "text/csv"
                )

                st.info(
                    "This application uses synthetic data and "
                    "assumed risk parameters."
                )

                # RISKLAB - CUSTOMER RISK INVESTIGATION

                st.divider()
                st.header("Customer Risk Investigation")

                risk_labels = {
                    "All": "Tumu",
                    "Low": "Dusuk",
                    "Medium": "Orta",
                    "High": "Yuksek"
                }

                selected_risk = st.selectbox(
                    "Filter by Risk Level",
                    list(risk_labels.keys())
                )

                risk_secimi = risk_labels[selected_risk]

                if risk_secimi == "Tumu":
                    filtreli = kriz.copy()
                else:
                    filtreli = kriz[kriz["Risk"] == risk_secimi].copy()

                st.write("Filtered Customer Count:", len(filtreli))

                filtered_display = filtreli.sort_values(
                    "Beklenen_Kayip", ascending=False
                ).rename(columns={
                    "Musteri": "Customer ID",
                    "Gelir": "Monthly Income",
                    "Aylik_Borc": "Monthly Debt",
                    "Kredi_Bakiyesi": "Credit Exposure",
                    "Risk": "Risk Level",
                    "Beklenen_Kayip": "Expected Loss"
                })

                filtered_display["Risk Level"] = filtered_display["Risk Level"].replace({
                    "Dusuk": "Low",
                    "Orta": "Medium",
                    "Yuksek": "High"
                })

                st.dataframe(
                    filtered_display,
                    use_container_width=True,
                    hide_index=True
                )

                if not filtreli.empty:
                    musteri_id = st.selectbox(
                        "Select a Customer to View Details",
                        filtreli["Musteri"].tolist()
                    )

                    musteri = filtreli[
                        filtreli["Musteri"] == musteri_id
                    ].iloc[0]

                    col1, col2, col3 = st.columns(3)

                    risk_english = {
                        "Dusuk": "Low",
                        "Orta": "Medium",
                        "Yuksek": "High"
                    }

                    col1.metric("Risk Level", risk_english[musteri["Risk"]])
                    col2.metric("Debt-to-Income Ratio", f'{musteri["DTI"] * 100:.1f}%')
                    col3.metric(
                        "Expected Loss",
                        f'{musteri["Beklenen_Kayip"]:,.0f} TL'
                    )

                    st.subheader("Risk Assessment")

                    if musteri["DTI"] >= 0.50:
                        st.error(
                            "High Risk: Monthly debt payments account "
                            "for at least 50% of monthly income."
                        )
                    elif musteri["DTI"] >= 0.30:
                        st.warning(
                            "Medium Risk: The debt-to-income ratio "
                            "is between 30% and 50%."
                        )
                    else:
                        st.success(
                            "Low Risk: The debt-to-income ratio "
                            "is below 30%."
                        )
                else:
                    st.info("No customers found in the selected risk category.")

  
if page == "Risk Migration":

    st.divider()
    st.header("Risk Migration Analysis")

    karsilastirma = pd.DataFrame({
        "Musteri": df["Musteri"],
        "Normal_Risk": normal["Risk"],
        "Kriz_Risk": kriz["Risk"]
    })

    risk_sirasi = {
        "Dusuk": 1,
        "Orta": 2,
        "Yuksek": 3
    }

    karsilastirma["Normal_Puan"] = (
        karsilastirma["Normal_Risk"].map(risk_sirasi)
    )

    karsilastirma["Kriz_Puan"] = (
        karsilastirma["Kriz_Risk"].map(risk_sirasi)
    )

    kotulesen = (
        karsilastirma["Kriz_Puan"]
        > karsilastirma["Normal_Puan"]
    ).sum()

    st.metric(
        "Customers with Increased Risk",
        int(kotulesen)
    )

    gecis_tablosu = pd.crosstab(
        karsilastirma["Normal_Risk"],
        karsilastirma["Kriz_Risk"]
    )

    riskler = ["Dusuk", "Orta", "Yuksek"]

    gecis_tablosu = gecis_tablosu.reindex(
        index=riskler,
        columns=riskler,
        fill_value=0
    )

    gecis_tablosu = gecis_tablosu.rename(
        index={"Dusuk": "Low", "Orta": "Medium", "Yuksek": "High"},
        columns={"Dusuk": "Low", "Orta": "Medium", "Yuksek": "High"}
    )

    fig_gecis = px.imshow(
        gecis_tablosu,
        text_auto=True,
        labels={
            "x": "Risk After Stress",
            "y": "Risk Before Stress",
            "color": "Customers"
        },
        title="Risk Migration Matrix",
        aspect="auto"
    )

    st.plotly_chart(
        fig_gecis,
        use_container_width=True
    )

    st.subheader("Customer Risk Changes")

    st.dataframe(
        karsilastirma[
            ["Musteri", "Normal_Risk", "Kriz_Risk"]
        ].replace({
            "Dusuk": "Low",
            "Orta": "Medium",
            "Yuksek": "High"
        }).rename(columns={
            "Musteri": "Customer ID",
            "Normal_Risk": "Baseline Risk",
            "Kriz_Risk": "Stressed Risk"
        }),
        hide_index=True,
        use_container_width=True
    )

if page == "Portfolio Insights":

                st.header("Portfolio Insights")
                st.caption("Credit exposure and risk concentration")

                toplam_kredi = kriz["Kredi_Bakiyesi"].sum()

                top_10_exposure = kriz["Kredi_Bakiyesi"].nlargest(10).sum()
                top_10_concentration = (top_10_exposure / toplam_kredi * 100) if toplam_kredi > 0 else 0

                yuksek_risk_kredi = kriz.loc[
                    kriz["Risk"] == "Yuksek",
                    "Kredi_Bakiyesi"
                ].sum()

                yogunlasma = (
                    yuksek_risk_kredi / toplam_kredi * 100
                    if toplam_kredi > 0 else 0
                )

                col1, col2 = st.columns(2)

                col1.metric("Total Credit Exposure", f"{toplam_kredi:,.0f} TL")
                col2.metric("High Risk Exposure", f"{yuksek_risk_kredi:,.0f} TL")

                col3, col4 = st.columns(2)

                col3.metric("High Risk Concentration", f"{yogunlasma:.1f}%")
                col4.metric("Top 10 Concentration", f"{top_10_concentration:.2f}%")

                st.subheader("Top 10 Largest Credit Exposures")

                top_10_customers = kriz.nlargest(10, "Kredi_Bakiyesi")


                top_10_display = top_10_customers[
                    ["Musteri", "Kredi_Bakiyesi", "Risk"]
                ].rename(columns={
                    "Musteri": "Customer ID",
                    "Kredi_Bakiyesi": "Credit Exposure",
                    "Risk": "Risk Level"
                })

                top_10_display["Risk Level"] = top_10_display["Risk Level"].replace({
                    "Dusuk": "Low",
                    "Orta": "Medium",
                    "Yuksek": "High"
                })

                st.dataframe(
                    top_10_display,
                    use_container_width=True,
                    hide_index=True
                )

                st.subheader("Top 10 Highest Expected Loss")

                top_10_loss = kriz.nlargest(10, "Beklenen_Kayip")

                top_10_loss_display = top_10_loss[
                    ["Musteri", "Kredi_Bakiyesi", "Risk", "Beklenen_Kayip"]
                ].rename(columns={
                    "Musteri": "Customer ID",
                    "Kredi_Bakiyesi": "Credit Exposure",
                    "Risk": "Risk Level",
                    "Beklenen_Kayip": "Expected Loss"
                })

                top_10_loss_display["Risk Level"] = top_10_loss_display["Risk Level"].replace({
                    "Dusuk": "Low",
                    "Orta": "Medium",
                    "Yuksek": "High"
                })

                st.dataframe(
                    top_10_loss_display,
                    use_container_width=True,
                    hide_index=True
                )            

                common_customers = set(top_10_customers["Musteri"]) & set(top_10_loss["Musteri"])

                insight_col1, insight_col2 = st.columns(2, gap="medium")

                with insight_col1:
                    with st.container(border=True):
                        st.metric(
                            "Customers in Both Top 10 Lists",
                            len(common_customers)
                        )

                top_10_loss_total = top_10_loss["Beklenen_Kayip"].sum()
                top_10_loss_share = (top_10_loss_total / kriz_kayip * 100) if kriz_kayip > 0 else 0

                with insight_col2:
                    with st.container(border=True):
                        st.metric(
                            "Top 10 Expected Loss Share",
                            f"{top_10_loss_share:.2f}%"
                        )

                loss_share_data = pd.DataFrame({
                    "Segment": ["Top 10 Customers", "Remaining Portfolio"],
                    "Expected Loss": [
                        top_10_loss_total,
                        kriz_kayip - top_10_loss_total
                    ]
                })

                fig_loss_share = px.pie(
                    loss_share_data,
                    names="Segment",
                    values="Expected Loss",
                    title="Expected Loss Concentration",
                    hole=0.55
                )

                fig_loss_share.update_layout(
                    height=350,
                    margin=dict(l=10, r=10, t=60, b=10),
                    legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center")
                )

                chart_col1, chart_col2 = st.columns(2, gap="large")

                risk_exposure = (
                    kriz.groupby("Risk")["Kredi_Bakiyesi"]
                    .sum()
                    .reindex(["Dusuk", "Orta", "Yuksek"], fill_value=0)
                    .reset_index()
                )

                risk_exposure["Risk"] = risk_exposure["Risk"].replace({
                    "Dusuk": "Low",
                    "Orta": "Medium",
                    "Yuksek": "High"
                })

                fig_exposure = px.pie(
                    risk_exposure,
                    names="Risk",
                    values="Kredi_Bakiyesi",
                    title="Credit Exposure by Risk Segment",
                    hole=0.5
                )

                fig_exposure.update_layout(
                    height=350,
                    margin=dict(l=10, r=10, t=60, b=10),
                    legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center")
                )

                with chart_col1:
                    with st.container(border=True):
                        st.plotly_chart(fig_exposure, use_container_width=True)

                with chart_col2:
                    with st.container(border=True):
                        st.plotly_chart(fig_loss_share, use_container_width=True)

if page == "Early Warning Radar":
    st.header("Early Warning Radar")
    st.caption("Identify customers vulnerable to further income shocks.")

    warning_threshold = st.slider(
        "Early Warning Threshold — Additional Income Shock (%)",
        min_value=1,
        max_value=30,
        value=10,
        step=1
    )

    warning_mask = (
        (kriz["DTI"] < 0.50) &
        (kriz["Income_Shock_Threshold"] <= warning_threshold)
    )

    fragile_customers = warning_mask.sum()

    fragile_exposure = kriz.loc[
        warning_mask, "Kredi_Bakiyesi"
    ].sum()

    fragile_exposure_ratio = (
        fragile_exposure / total_exposure * 100
        if total_exposure > 0 else 0
    )

    st.divider()

    col1, col2, col3 = st.columns(3, gap="large")

    with col1:
        with st.container(border=True):
            st.metric(
                "Fragile Customers",
                f"{fragile_customers:,}"
            )

    with col2:
        with st.container(border=True):
            st.metric(
                "Fragile Credit Exposure",
                f"{fragile_exposure:,.0f}"
            )

    with col3:
        with st.container(border=True):
            st.metric(
                "Fragile Exposure Ratio",
                f"{fragile_exposure_ratio:.2f}%"
            ) 

    st.subheader("Customers on Early Warning")

    fragile_df = kriz.loc[warning_mask].copy()

    fragile_df = fragile_df.sort_values(
        "Income_Shock_Threshold",
        ascending=True
    )

    def warning_severity(threshold):
        if threshold <= 3:
            return "Critical"
        elif threshold <= 7:
            return "High Alert"
        else:
            return "Watchlist"

    fragile_df["Warning_Severity"] = fragile_df[
        "Income_Shock_Threshold"
    ].apply(warning_severity)

    critical_customers = (fragile_df["Warning_Severity"] == "Critical").sum()

    st.warning(
        f"Critical Alert: {critical_customers} customers "
        "are within a 3% additional income shock "
        "of the high-risk threshold."
    )

    st.dataframe(
        fragile_df[[
            "Musteri",
            "Warning_Severity",
            "DTI",
            "Income_Shock_Threshold",
            "Kredi_Bakiyesi"
        ]],
        column_config={
            "Musteri": "Customer ID",
            "Warning_Severity": "Warning Severity",
            "DTI": st.column_config.NumberColumn(
                "Debt-to-Income Ratio",
                format="%.2f"
            ),
           "Income_Shock_Threshold": st.column_config.ProgressColumn(
                "Additional Income Shock (%)",
                min_value=0,
                max_value=30,
                format="%.2f%%"
            ),
                        "Kredi_Bakiyesi": st.column_config.NumberColumn(
                "Credit Exposure",
                format="%.0f"
            )
        },
        width="stretch",
        hide_index=True
    )
    
if page == "Risk Mitigation Simulator":
    st.header("Risk Mitigation Simulator")

    st.caption(
        "Simulate credit risk mitigation strategies "
        "and evaluate their impact on portfolio risk."
    )

    st.subheader("Payment Restructuring Scenario")

    restructuring_strategy = st.radio(
        "Restructuring Strategy",
        ["Portfolio-wide", "Targeted High-Risk"],
        horizontal=True
    )

    if restructuring_strategy == "Targeted High-Risk":
        st.info(
            "Targeted Strategy: Payment reductions are applied "
            "only to customers classified as High Risk "
            "before restructuring. Medium- and Low-Risk "
            "customers remain unchanged."
        )
    else:
        st.info(
            "Portfolio-wide Strategy: Payment reductions "
            "are applied equally to all customers, "
            "regardless of their risk classification."
        )

    payment_reduction = st.slider(
        "Monthly Payment Reduction (%)",
        min_value=0,
        max_value=50,
        value=0,
        step=5
    )

    if restructuring_strategy == "Targeted High-Risk":
        reduction_rate = (
            (kriz["Risk"] == "Yuksek").astype(float)
            * payment_reduction / 100
        )
    else:
        reduction_rate = payment_reduction / 100

    simulated_payment = (
        kriz["Aylik_Borc"] * (1 - reduction_rate)
    )

    if restructuring_strategy == "Targeted High-Risk":
        targeted_customers = (kriz["Risk"] == "Yuksek").sum()
    else:
        targeted_customers = len(kriz)

    st.metric(
        "Customers Targeted",
        f"{targeted_customers:,}"
    )

    simulated_dti = simulated_payment / (
        kriz["Gelir"] * (1 - gelir_dususu / 100)
    )

    st.subheader("DTI Comparison")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Current Average DTI",
            f"{kriz['DTI'].mean() * 100:.2f}%"
        )

    with col2:
        st.metric(
            "Restructured Average DTI",
            f"{simulated_dti.mean() * 100:.2f}%",
            delta=f"{(simulated_dti.mean() - kriz['DTI'].mean()) * 100:.2f} pp",
            delta_color="inverse"
        )

    simulated_risk = simulated_dti.apply(
        lambda dti: "Dusuk" if dti < 0.30
        else "Orta" if dti < 0.50
        else "Yuksek"
    )

    simulated_pd = simulated_risk.map({
        "Dusuk": 0.02,
        "Orta": 0.08,
        "Yuksek": 0.20
    })

    before_expected_loss = kriz["Beklenen_Kayip"].sum()

    after_expected_loss = (
        simulated_pd * 0.45 * kriz["Kredi_Bakiyesi"]
    ).sum()

    improved_customers = (
        (kriz["Risk"] == "Yuksek") &
        (simulated_risk != "Yuksek")
    ).sum()

    st.metric(
        "High-Risk Customers Improved",
        f"{improved_customers:,}",
        help="Number of customers moving from High Risk to Medium or Low Risk after payment restructuring."
    )

    high_to_medium = (
        (kriz["Risk"] == "Yuksek") &
        (simulated_risk == "Orta")
    ).sum()

    high_to_low = (
        (kriz["Risk"] == "Yuksek") &
        (simulated_risk == "Dusuk")
    ).sum()

    st.subheader("Risk Migration After Restructuring")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("High → Medium", f"{high_to_medium:,}")

    with col2:
        st.metric("High → Low", f"{high_to_low:,}")

    original_monthly_payment = kriz["Aylik_Borc"].sum()

    restructured_monthly_payment = simulated_payment.sum()

    monthly_cashflow_reduction = (
        original_monthly_payment - restructured_monthly_payment
    )

    st.subheader("Expected Loss Impact")

    st.caption(
        "Model-implied expected loss comparison based on "
        "illustrative DTI-to-PD assumptions. "
        "Payment restructuring does not guarantee an "
        "equivalent reduction in actual default risk."
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Before Expected Loss",
        f"{before_expected_loss:,.0f} TL"
    )

    col2.metric(
        "After Expected Loss",
        f"{after_expected_loss:,.0f} TL"
    )

    loss_change_pct = (
        (after_expected_loss / before_expected_loss - 1) * 100
        if before_expected_loss > 0 else 0
    )

    col3.metric(
        "Expected Loss Change",
        f"{loss_change_pct:+.2f}%"
    )

    st.caption(
        "Illustrative expected loss based on assumed PD and LGD. "
        "This does not represent a validated forecast of actual credit losses."
    )

    st.subheader("Restructuring Financial Impact")

    st.metric(
        "Monthly Cash Flow Reduction",
        f"{monthly_cashflow_reduction:,.0f} TL"
    )

    cashflow_per_improved_customer = (
        monthly_cashflow_reduction / improved_customers
        if improved_customers > 0 else 0
    )

    st.metric(
        "Monthly Cash Flow Reduction per Improved Customer",
        f"{cashflow_per_improved_customer:,.0f} TL"
    )

    st.subheader("Restructuring Strategy Comparison")

    portfolio_dti = (
        kriz["DTI"] * (1 - payment_reduction / 100)
    )

    targeted_dti = kriz["DTI"].copy()

    targeted_dti.loc[kriz["Risk"] == "Yuksek"] *= (
        1 - payment_reduction / 100
    )

    portfolio_improved = (
        (kriz["Risk"] == "Yuksek") &
        (portfolio_dti < 0.50)
    ).sum()

    targeted_improved = (
        (kriz["Risk"] == "Yuksek") &
        (targeted_dti < 0.50)
    ).sum()

    portfolio_cashflow_reduction = (
        kriz["Aylik_Borc"].sum() * payment_reduction / 100
    )

    targeted_cashflow_reduction = (
        kriz.loc[
            kriz["Risk"] == "Yuksek", "Aylik_Borc"
        ].sum() * payment_reduction / 100
    )

    comparison_df = pd.DataFrame({
        "Strategy": [
            "Portfolio-wide",
            "Targeted High-Risk"
        ],
        "Customers Targeted": [
            len(kriz),
            (kriz["Risk"] == "Yuksek").sum()
        ],
        "Improved Customers": [
            portfolio_improved,
            targeted_improved
        ],
        "Monthly Cash Flow Reduction (TL)": [
            portfolio_cashflow_reduction,
            targeted_cashflow_reduction
        ]
        
    })

    st.dataframe(
        comparison_df,
        hide_index=True,
        width="stretch"
    )   

    st.subheader("Automated Strategy Assessment")

    if portfolio_improved == 0 and targeted_improved == 0:
        st.info(
            "No high-risk customers move to a lower risk "
            "category under the selected payment reduction."
        )

    elif (
        portfolio_improved == targeted_improved
        and targeted_cashflow_reduction < portfolio_cashflow_reduction
    ):
        st.success(
            "Targeted High-Risk restructuring achieves "
            "the same number of high-risk customer improvements "
            "with a lower monthly cash flow reduction "
            "than Portfolio-wide restructuring."
        )

    else:
        st.info(
            "Review the strategy comparison table to assess "
            "the trade-off between risk classification "
            "improvements and monthly cash flow reduction."
        )

    st.subheader("Strategy Efficiency Analysis")

    portfolio_efficiency = (
        portfolio_improved / (portfolio_cashflow_reduction / 1_000_000)
        if portfolio_cashflow_reduction > 0 else 0
    )

    targeted_efficiency = (
        targeted_improved / (targeted_cashflow_reduction / 1_000_000)
        if targeted_cashflow_reduction > 0 else 0
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Portfolio-wide Efficiency",
            f"{portfolio_efficiency:.2f}"
        )

    with col2:
        st.metric(
            "Targeted Efficiency",
            f"{targeted_efficiency:.2f}"
        )

    st.caption(
        "Customers moving out of the High-Risk category "
        "per 1 million TL of monthly cash flow reduction. "
        "This is not a measure of profitability or actual credit loss reduction."
    )  

    st.subheader("Decision Summary")

    if portfolio_improved == 0 and targeted_improved == 0:
        st.info(
            "Decision: Neither strategy improves the "
            "High-Risk classification under this scenario."
        )

    elif targeted_efficiency > portfolio_efficiency:
        st.success(
            "Scenario Assessment: Targeted High-Risk "
            "restructuring is more efficient under the "
            "selected assumptions, achieving more "
            "classification improvements per 1 million TL "
            "of monthly cash flow reduction."
        )

    else:
        st.info(
            "Scenario Assessment: No clear efficiency "
            "advantage is identified between the strategies."
        )

    st.caption(
        "Decision-support simulation only. Results are based "
        "on illustrative DTI thresholds and synthetic data. "
        "Changes in risk classification do not establish "
        "changes in actual default probability. "
        "Loan maturity, interest costs and economic "
        "restructuring costs are not modeled."
    )


if page == "What-If Scenario Builder":
    st.header("Scenario Comparison Lab")
    st.caption(
        "Compare alternative economic scenarios "
        "and evaluate their impact on credit risk."
    )

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Scenario A")
        income_a = st.slider(
            "Income Reduction A (%)", 0, 60, 15, 5
        )
        payment_a = st.slider(
            "Monthly Payment Change A (%)", -50, 50, 5, 5
        )

    with col_b:
        st.subheader("Scenario B")
        income_b = st.slider(
            "Income Reduction B (%)", 0, 60, 35, 5
        )
        payment_b = st.slider(
            "Monthly Payment Change B (%)", -50, 50, 15, 5
        )

    baseline = risk_hesapla(df, 0, 0)
    scenario_a = risk_hesapla(df, income_a, payment_a)
    scenario_b = risk_hesapla(df, income_b, payment_b)

    st.subheader("Scenario Comparison")

    comparison = pd.DataFrame({
        "Scenario": ["Baseline", "Scenario A", "Scenario B"],
        "High-Risk Customers": [
            (baseline["Risk"] == "Yuksek").sum(),
            (scenario_a["Risk"] == "Yuksek").sum(),
            (scenario_b["Risk"] == "Yuksek").sum()
        ],
        "Expected Loss (TL)": [
            baseline["Beklenen_Kayip"].sum(),
            scenario_a["Beklenen_Kayip"].sum(),
            scenario_b["Beklenen_Kayip"].sum()
        ]
    })

    st.dataframe(comparison, hide_index=True, width="stretch")

    st.subheader("Risk Migration Comparison")

    risk_order = {"Dusuk": 0, "Orta": 1, "Yuksek": 2}

    baseline_level = baseline["Risk"].map(risk_order)

    migration_data = []

    for name, scenario in [
        ("Scenario A", scenario_a),
        ("Scenario B", scenario_b)
    ]:
        scenario_level = scenario["Risk"].map(risk_order)

        migration_data.append({
            "Scenario": name,
            "Risk Increased": (scenario_level > baseline_level).sum(),
            "Risk Decreased": (scenario_level < baseline_level).sum(),
            "Unchanged": (scenario_level == baseline_level).sum()
        })

    st.dataframe(
        pd.DataFrame(migration_data),
        hide_index=True,
        width="stretch"
    )

    migration_chart = pd.DataFrame(migration_data).set_index("Scenario")

    st.bar_chart(
        migration_chart[["Risk Increased", "Risk Decreased"]],
        x_label="Scenario",
        y_label="Number of Customers"
    )


    st.divider()
    st.subheader("Reverse Stress Testing")

    st.caption(
        "Identify the income shock required to reach "
        "a selected High-Risk portfolio threshold."
    )

    target_high_risk = st.slider(
        "Target High-Risk Customer Ratio (%)",
        min_value=10,
        max_value=100,
        value=40,
        step=5
    )
 
    required_shock = None

    for shock in range(0, 61):
        stressed = risk_hesapla(df, shock, 0)

        high_risk_ratio = (
            (stressed["Risk"] == "Yuksek").mean() * 100
        )

        if high_risk_ratio >= target_high_risk:
            required_shock = shock
            break

    if required_shock == 0:
        st.info(
            "The selected High-Risk threshold is already "
            "reached under baseline conditions. "
            "No additional income shock is required."
        )

    elif required_shock is not None:
        st.metric(
            "Required Income Reduction",
            f"{required_shock}%"
        )

        st.success(
            f"A {required_shock}% income reduction is sufficient "
            f"to reach or exceed the selected "
            f"{target_high_risk}% High-Risk customer threshold."
        )
    else:
        st.warning(
            "The selected High-Risk threshold is not reached "
            "within the tested income reduction range of 0–60%."
        )

    shock_results = []

    for shock in range(0, 61):
        stressed = risk_hesapla(df, shock, 0)

        shock_results.append({
            "Income Reduction (%)": shock,
            "High-Risk Customers (%)": (
                (stressed["Risk"] == "Yuksek").mean() * 100
            ),
            "Target Threshold (%)": target_high_risk
        })

    shock_chart = pd.DataFrame(shock_results).set_index(
        "Income Reduction (%)"
    )

    st.line_chart(
        shock_chart,
        x_label="Income Reduction (%)",
        y_label="High-Risk Customers (%)"
    )
