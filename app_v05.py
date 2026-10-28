
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(
    page_title="RiskLab",
    page_icon="📊",
    layout="wide"
)

st.title("RiskLab | Credit Risk")
st.caption("Financial Risk Analytics Platform - Demo")

# Tekrarlanabilir ornek portfoy


# RISKLAB - DATA IMPORT

st.sidebar.header("Portfolio Data")

uploaded_file = st.sidebar.file_uploader(
    "Musteri dosyasi yukle",
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
    "Musteri gelir dususu (%)",
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

normal_kayip = normal["Beklenen_Kayip"].sum()
kriz_kayip = kriz["Beklenen_Kayip"].sum()

col1, col2, col3 = st.columns(3)

col1.metric("Toplam Musteri", len(df))
col2.metric("Normal Beklenen Kayip",
            f"{normal_kayip:,.0f} TL")
col3.metric("Kriz Beklenen Kayip",
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
    title="Kredi Riski Dagilimi",
    color="Risk"
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Musteri Portfoyu")
st.dataframe(
    kriz,
    use_container_width=True,
    hide_index=True
)

st.download_button(
    "CSV Raporunu Indir",
    kriz.to_csv(index=False).encode("utf-8-sig"),
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

risk_secimi = st.selectbox(
    "Risk seviyesini filtrele",
    ["Tumu", "Dusuk", "Orta", "Yuksek"]
)

if risk_secimi == "Tumu":
    filtreli = kriz.copy()
else:
    filtreli = kriz[kriz["Risk"] == risk_secimi].copy()

st.write("Filtrelenen musteri sayisi:", len(filtreli))

st.dataframe(
    filtreli.sort_values("Beklenen_Kayip", ascending=False),
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

# RISKLAB v0.5 - RISK MIGRATION

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

st.metric("Riski Artan Musteri Sayisi", int(kotulesen))

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
        "x": "Kriz Sonrasi Risk",
        "y": "Normal Risk",
        "color": "Musteri"
    },
    title="Risk Gecis Matrisi",
    aspect="auto"
)

st.plotly_chart(fig_gecis, use_container_width=True)

st.subheader("Musteri Risk Degisimleri")

st.dataframe(
    karsilastirma[
        ["Musteri", "Normal_Risk", "Kriz_Risk"]
    ],
    hide_index=True,
    use_container_width=True
)
