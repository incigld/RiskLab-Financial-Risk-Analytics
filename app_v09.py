
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

st.sidebar.title("RiskLab")
st.sidebar.caption("Financial Risk Analytics")

page = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Credit Risk",
        "Stress Testing",
        "Risk Migration",
        "Portfolio Insights",
        "Early Warning Radar"
    ],
    key="main_navigation"
)

st.title("RiskLab | Credit Risk")
st.caption("Financial Risk Analytics Platform - Demo")

# Tekrarlanabilir ornek portfoy


# RISKLAB - DATA IMPORT

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
                "Eksik sutunlar: " + ", ".join(eksik)
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
                f"{hatali.sum()} satirda eksik "
                "veya gecersiz veri bulundu."
            )
            st.stop()

        if yeni_df.empty:
            st.error("Yuklenen dosya bos.")
            st.stop()

        if yeni_df["Musteri"].duplicated().any():
            st.error("Tekrarlanan Musteri ID bulundu.")
            st.stop()

        df = yeni_df.copy()
        st.sidebar.success(
            f"{len(df)} musteri yuklendi!"
        )

    except Exception as e:
        st.error(f"Dosya okunamadi: {e}")
        st.stop()

st.sidebar.header("Stress Test")

gelir_dususu = st.sidebar.slider(
    "Customer Income Reduction (%)",
    min_value=0,
    max_value=60,
    value=25,
    step=5
)

def risk_hesapla(data, dusus):
    sonuc = data.copy()
    sonuc["DTI"] = (
        sonuc["Aylik_Borc"] /
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

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Customers", len(df))
    col2.metric("Baseline Expected Loss",
                f"{normal_kayip:,.0f} TL")
    col3.metric("Stressed Expected Loss",
                f"{kriz_kayip:,.0f} TL",
                delta=f"{(kriz_kayip / normal_kayip - 1)*100:.1f}%",
                delta_color="inverse")

    risk_sayilari = (
        kriz["Risk"].value_counts()
        .rename_axis("Risk")
        .reset_index(name="Musteri_Sayisi")
    )

    fig = px.bar(
        risk_sayilari,
        x="Risk",
        y="Musteri_Sayisi",
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
                    "CSV Raporunu Indir",
                    display_portfolio.to_csv(index=False).encode("utf-8-sig"),
                    "risklab_rapor.csv",
                    "text/csv"
                )

                st.info(
                    "Bu uygulama sentetik veriler ve "
                    "varsayimsal risk parametreleri kullanir."
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

                st.write("Filtrelenen musteri sayisi:", len(filtreli))

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
                        "Detaylarini incelemek istedigin musteri",
                        filtreli["Musteri"].tolist()
                    )

                    musteri = filtreli[
                        filtreli["Musteri"] == musteri_id
                    ].iloc[0]

                    col1, col2, col3 = st.columns(3)

                    col1.metric("Risk Seviyesi", musteri["Risk"])
                    col2.metric("Borc / Gelir", f'%{musteri["DTI"] * 100:.1f}')
                    col3.metric(
                        "Beklenen Kayip",
                        f'{musteri["Beklenen_Kayip"]:,.0f} TL'
                    )

                    st.subheader("Risk Aciklamasi")

                    if musteri["DTI"] >= 0.50:
                        st.error(
                            "Yuksek risk: Aylik borc odemeleri "
                            "gelirin en az %50'sine esit."
                        )
                    elif musteri["DTI"] >= 0.30:
                        st.warning(
                            "Orta risk: Borc / gelir orani "
                            "%30 ile %50 arasinda."
                        )
                    else:
                        st.success(
                            "Dusuk risk: Borc / gelir orani %30'un altinda."
                        )
                else:
                    st.info("Bu risk seviyesinde musteri bulunamadi.")

  
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
        ],
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

    st.dataframe(
        fragile_df[[
            "Musteri",
            "DTI",
            "Income_Shock_Threshold",
            "Kredi_Bakiyesi"
        ]],
        column_config={
            "Musteri": "Customer ID",
            "DTI": st.column_config.NumberColumn(
                "Debt-to-Income Ratio",
                format="%.2f"
            ),
            "Income_Shock_Threshold": st.column_config.NumberColumn(
                "Additional Income Shock (%)",
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
      