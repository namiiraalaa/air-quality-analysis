from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Air Quality Explorer", page_icon="🌫️", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "main_data.csv.gz"

@st.cache_data
def load_data(path):
    df = pd.read_csv(path, parse_dates=["datetime"])
    df["station"] = df["station"].astype(str)
    return df

st.title("🌫️ Air Quality Explorer — Beijing")
st.caption("Eksplorasi PM2.5 dan kondisi cuaca di 12 stasiun pemantauan, Maret 2013–Februari 2017.")
if not DATA_PATH.exists():
    st.error(f"File data tidak ditemukan: {DATA_PATH}. Letakkan main_data.csv.gz di folder dashboard.")
    st.stop()

df = load_data(DATA_PATH)
if df.empty:
    st.warning("Dataset tidak berisi baris.")
    st.stop()

min_date = df["datetime"].min().date()
max_date = df["datetime"].max().date()

with st.sidebar:
    st.header("Filter")
    stations = sorted(df["station"].dropna().unique().tolist())
    selected_stations = st.multiselect("Stasiun", stations, default=stations)
    date_range = st.date_input("Rentang tanggal", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    st.caption("Missing value pengukuran tidak diimputasi. Metrik dihitung dari observasi valid.")

if not selected_stations:
    st.info("Pilih setidaknya satu stasiun pada filter.")
    st.stop()
if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Pilih tanggal mulai dan tanggal akhir.")
    st.stop()

start_date, end_date = date_range
filtered = df[
    df["station"].isin(selected_stations)
    & (df["datetime"].dt.date >= start_date)
    & (df["datetime"].dt.date <= end_date)
].copy()
if filtered.empty:
    st.warning("Tidak ada data pada kombinasi filter tersebut.")
    st.stop()

valid_pm = filtered["PM2.5"].dropna()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Rata-rata PM2.5", f"{valid_pm.mean():.1f} µg/m³" if len(valid_pm) else "N/A")
c2.metric("Median PM2.5", f"{valid_pm.median():.1f} µg/m³" if len(valid_pm) else "N/A")
c3.metric("Observasi PM2.5 valid", f"{len(valid_pm):,}")
c4.metric("Stasiun dipilih", f"{filtered['station'].nunique()}")

st.divider()
left, right = st.columns(2)
with left:
    station_avg = (filtered.groupby("station", as_index=False)["PM2.5"]
                   .mean().dropna().sort_values("PM2.5", ascending=True))
    fig_station = px.bar(
        station_avg, x="PM2.5", y="station", orientation="h",
        title="Rata-rata PM2.5 per stasiun",
        labels={"PM2.5": "Rata-rata PM2.5 (µg/m³)", "station": "Stasiun"},
        color="PM2.5", color_continuous_scale="OrRd"
    )
    fig_station.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(fig_station, use_container_width=True)

with right:
    hourly = (filtered.dropna(subset=["PM2.5"])
              .assign(month_start=lambda x: x["datetime"].dt.to_period("M").dt.to_timestamp())
              .groupby("month_start", as_index=False)["PM2.5"].mean())
    fig_trend = px.line(
        hourly, x="month_start", y="PM2.5", markers=True,
        title="Tren bulanan PM2.5",
        labels={"month_start": "Bulan", "PM2.5": "Rata-rata PM2.5 (µg/m³)"}
    )
    fig_trend.update_layout(margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(fig_trend, use_container_width=True)

st.subheader("Hubungan PM2.5 dengan kondisi cuaca")
weather_col = st.selectbox("Variabel cuaca", ["TEMP", "RAIN", "WSPM", "PRES", "DEWP"])
scatter_df = filtered.dropna(subset=["PM2.5", weather_col])
if scatter_df.empty:
    st.info("Tidak ada pasangan observasi valid untuk variabel yang dipilih.")
else:
    fig_scatter = px.scatter(
        scatter_df.sample(min(5000, len(scatter_df)), random_state=42),
        x=weather_col, y="PM2.5", color="station",
        opacity=0.45, render_mode="webgl",
        title=f"PM2.5 dan {weather_col} (sampel maksimal 5.000 titik)",
        labels={"PM2.5": "PM2.5 (µg/m³)", weather_col: weather_col}
    )
    fig_scatter.update_layout(margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(fig_scatter, use_container_width=True)
    st.caption("Grafik menunjukkan asosiasi visual, bukan hubungan sebab-akibat.")

with st.expander("Lihat data hasil filter"):
    st.dataframe(filtered.sort_values("datetime", ascending=False), use_container_width=True, height=350)
    st.download_button(
        "Unduh data hasil filter (CSV)",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="air_quality_filtered.csv",
        mime="text/csv"
    )

st.caption("Sumber: Air Quality Dataset (PRSA). Dataset historis Beijing, 2013–2017. Kategori dan statistik tidak dimaksudkan sebagai diagnosis atau peringatan kesehatan resmi.")
