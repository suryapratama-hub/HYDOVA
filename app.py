# HYDOVA — Hydrological Data & Observation Intelligence Platform
# Versi mandiri: seluruh fungsi utama berada dalam satu file app.py.
# Jalankan: python -m streamlit run app.py

import io
import json
import math
import sqlite3
import tempfile
import zipfile
import requests
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Dependensi opsional GIS. Menu lain tetap dapat digunakan jika GIS belum terpasang.
try:
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.mask import mask
    from rasterio.features import geometry_mask
    from rasterio.transform import xy
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    import geopandas as gpd
    from shapely.geometry import mapping
    from shapely.ops import unary_union
    import folium
    from streamlit_folium import st_folium
    GIS_AVAILABLE = True
    GIS_IMPORT_ERROR = None
except Exception as _gis_error:
    GIS_AVAILABLE = False
    GIS_IMPORT_ERROR = str(_gis_error)

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False


# -------------------------------------------------------------------
# KONFIGURASI DASAR
# -------------------------------------------------------------------
st.set_page_config(
    page_title="HYDOVA | Hydrological Intelligence",
    page_icon="🌧️",
    layout="wide",
)

DB_PATH = Path(__file__).with_name("hydova.db")
RETURN_PERIODS = [2, 5, 10, 25, 50, 100]

# Palet visualisasi bertema hujan dan air
plt.rcParams["figure.facecolor"] = "#f4fbff"
plt.rcParams["axes.facecolor"] = "#f4fbff"
plt.rcParams["text.color"] = "#123047"
plt.rcParams["axes.labelcolor"] = "#31566d"
plt.rcParams["xtick.color"] = "#527286"
plt.rcParams["ytick.color"] = "#527286"
plt.rcParams["axes.edgecolor"] = "#c8e0ec"
plt.rcParams["axes.prop_cycle"] = plt.cycler(color=["#168aad", "#20a4c7", "#52b6cf", "#2a6f97"])

st.markdown("""
<style>
:root {
  --rain-950:#06283d; --rain-900:#083650; --rain-800:#0b4964;
  --rain-700:#126782; --rain-600:#168aad; --rain-500:#20a4c7;
  --rain-300:#8ed3e6; --rain-200:#c6eaf3; --rain-100:#e8f7fb;
  --mist:#f2f9fc; --paper:#ffffff; --ink:#123047; --muted:#5c7889;
  --line:#d6e8ef; --aqua:#dff5f7;
}
.stApp,.main {background:linear-gradient(145deg,#f4fbff 0%,#eef7fb 48%,#f8fcfd 100%);color:var(--ink)}
.block-container {padding-top:1.35rem;padding-bottom:2.4rem;max-width:1500px}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#06283d 0%,#083e59 52%,#0b5871 100%)}
[data-testid="stSidebar"] * {color:#eaf8fc}
[data-testid="stSidebar"] hr {border-color:rgba(198,234,243,.2)}
[data-testid="stSidebar"] [data-testid="stRadio"]>label {display:none}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {gap:7px}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"]>label {
  min-height:46px;padding:5px 12px;border-radius:12px;
  background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.035);
  transition:all .18s ease;
}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"]>label:hover {
  background:rgba(142,211,230,.15);border-color:rgba(142,211,230,.3)
}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"]>label:has(input:checked) {
  background:linear-gradient(100deg,#168aad,#20a4c7);border:1px solid #8ed3e6;
  box-shadow:0 5px 16px rgba(0,0,0,.15)
}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"]>label p {color:#f2fbfd;font-weight:650}
.hydova-hero {
  position:relative;overflow:hidden;padding:25px 30px;margin:0 0 22px;border-radius:22px;
  color:#fff;background:linear-gradient(115deg,#06283d 0%,#0b5871 52%,#168aad 100%);
  box-shadow:0 12px 30px rgba(8,54,80,.16);border:1px solid rgba(255,255,255,.22)
}
.hydova-hero:after {
  content:"";position:absolute;right:-55px;top:-115px;width:330px;height:330px;border-radius:50%;
  background:radial-gradient(circle,rgba(198,234,243,.23) 0 34%,rgba(142,211,230,.10) 35% 55%,transparent 56%);
  pointer-events:none
}
.hydova-hero:before {
  content:"";position:absolute;right:90px;bottom:-110px;width:250px;height:170px;border-radius:50%;
  background:rgba(142,211,230,.13);filter:blur(2px);pointer-events:none
}
.hydova-hero-inner {position:relative;z-index:1;display:flex;align-items:center;gap:17px}
.hydova-mark {width:58px;height:58px;display:flex;align-items:center;justify-content:center;
  border-radius:17px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.25);font-size:31px}
.hydova-title {font-size:2.15rem;line-height:1.05;font-weight:850;color:#fff;letter-spacing:.045em}
.hydova-sub {font-size:.92rem;color:#d8f2f8;margin-top:6px;letter-spacing:.015em}
.hydova-tag {display:inline-block;margin-top:12px;padding:4px 10px;border-radius:30px;
  background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.22);
  color:#e8f7fb;font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
h1,h2,h3,h4,h5,h6 {color:var(--rain-950)}
.stMarkdown,.stText,label,p {color:var(--ink)}
[data-testid="stHeader"] {background:rgba(242,249,252,.78)}
[data-testid="stMetric"] {
  background:linear-gradient(155deg,#fff 0%,#f0faff 100%);padding:17px 18px;
  border:1px solid var(--line);border-top:4px solid var(--rain-500);border-radius:16px;
  box-shadow:0 5px 18px rgba(8,54,80,.055)
}
[data-testid="stMetricLabel"] {color:var(--muted)!important;font-weight:650}
[data-testid="stMetricValue"] {color:var(--rain-950)!important;font-weight:800}
[data-testid="stMetricDelta"] {color:var(--rain-700)!important}
hr {border-color:var(--line)}
.stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"] button {
  background:linear-gradient(105deg,#0b6b89,#168aad);color:white;border:1px solid #168aad;
  border-radius:11px;font-weight:700;min-height:42px;padding:0 17px;
  box-shadow:0 4px 12px rgba(22,138,173,.13);transition:all .18s ease
}
.stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stFormSubmitButton"] button:hover {
  background:linear-gradient(105deg,#084c69,#0b7899);color:white;border-color:#0b7899;
  transform:translateY(-1px);box-shadow:0 7px 16px rgba(22,138,173,.2)
}
.stButton>button:focus,.stDownloadButton>button:focus {outline:2px solid var(--rain-300);outline-offset:2px}
input,textarea,[data-baseweb="select"]>div {
  background:#fff!important;border-color:#c8e0ec!important;border-radius:10px!important
}
[data-baseweb="tab-list"] {background:#e3f2f7;border:1px solid #d2e9f1;border-radius:13px;padding:5px;gap:5px}
[data-baseweb="tab"] {border-radius:9px;color:#31566d}
[data-baseweb="tab"][aria-selected="true"] {background:#fff;color:#0b7899;box-shadow:0 2px 8px rgba(8,54,80,.08)}
[data-testid="stDataFrame"],[data-testid="stTable"] {border:1px solid var(--line);border-radius:12px;overflow:hidden}
[data-testid="stFileUploader"] {background:rgba(255,255,255,.7);border:1px dashed #9bcddd;border-radius:14px;padding:8px}
[data-testid="stAlert"] {border-radius:12px;border:1px solid var(--line)}
[data-testid="stExpander"] {background:rgba(255,255,255,.72);border:1px solid var(--line);border-radius:12px}
[data-testid="stPlotlyChart"],.stPyplot {background:#f4fbff;border-radius:14px}
[data-testid="stProgress"]>div>div {background:linear-gradient(90deg,#168aad,#8ed3e6)}
.hydova-section-note {padding:12px 15px;border-radius:12px;background:#e7f6fa;border-left:4px solid #20a4c7;color:#31566d}
@media(max-width:768px) {
  .block-container {padding:.8rem .8rem 2rem}
  .hydova-hero {padding:19px 18px;border-radius:17px}
  .hydova-title {font-size:1.75rem}
  .hydova-sub {font-size:.8rem}
  .hydova-mark {width:48px;height:48px;font-size:25px}
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# DATABASE — aman dipanggil berulang kali
# -------------------------------------------------------------------
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rainfall (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                station TEXT NOT NULL,
                rainfall_mm REAL NOT NULL CHECK(rainfall_mm >= 0),
                UNIQUE(date, station)
            )
        """)
        conn.commit()


def read_rainfall():
    with get_connection() as conn:
        df = pd.read_sql_query(
            "SELECT id, date, station, rainfall_mm FROM rainfall ORDER BY date",
            conn,
        )
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["rainfall_mm"] = pd.to_numeric(df["rainfall_mm"], errors="coerce")
        df = df.dropna(subset=["date", "station", "rainfall_mm"])
    return df


def insert_rainfall(df):
    required = {"date", "station", "rainfall_mm"}
    if not required.issubset(df.columns):
        raise ValueError("Kolom wajib: date, station, rainfall_mm.")
    rows = []
    for _, row in df.iterrows():
        dt = pd.to_datetime(row["date"], errors="coerce")
        station = str(row["station"]).strip()
        rain = pd.to_numeric(row["rainfall_mm"], errors="coerce")
        if pd.isna(dt) or not station or pd.isna(rain) or float(rain) < 0:
            continue
        rows.append((dt.strftime("%Y-%m-%d"), station, float(rain)))
    if not rows:
        raise ValueError("Tidak ada baris data yang valid untuk disimpan.")
    with get_connection() as conn:
        conn.executemany("""
            INSERT INTO rainfall(date, station, rainfall_mm)
            VALUES (?, ?, ?)
            ON CONFLICT(date, station) DO UPDATE SET rainfall_mm=excluded.rainfall_mm
        """, rows)
        conn.commit()
    return len(rows)


def update_rainfall(record_id, dt, station, rainfall):
    with get_connection() as conn:
        conn.execute(
            "UPDATE rainfall SET date=?, station=?, rainfall_mm=? WHERE id=?",
            (pd.Timestamp(dt).strftime("%Y-%m-%d"), station, float(rainfall), int(record_id)),
        )
        conn.commit()


def delete_rainfall(record_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM rainfall WHERE id=?", (int(record_id),))
        conn.commit()


def reset_rainfall():
    with get_connection() as conn:
        conn.execute("DELETE FROM rainfall")
        conn.commit()


# -------------------------------------------------------------------
# PENGOLAHAN DATA HUJAN
# -------------------------------------------------------------------
def validate_rainfall(raw):
    aliases = {
        "tanggal": "date", "date": "date", "datetime": "date",
        "stasiun": "station", "nama stasiun": "station", "wilayah": "station",
        "station": "station", "rain station": "station",
        "curah hujan": "rainfall_mm", "curah hujan (mm)": "rainfall_mm",
        "rainfall": "rainfall_mm", "rainfall_mm": "rainfall_mm",
        "rainfall (mm)": "rainfall_mm", "hujan (mm)": "rainfall_mm",
    }
    df = raw.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    rename = {}
    for col in df.columns:
        normalized = " ".join(col.replace("_", " ").split())
        if normalized in aliases:
            rename[col] = aliases[normalized]
    df = df.rename(columns=rename)
    missing = {"date", "station", "rainfall_mm"} - set(df.columns)
    if missing:
        return pd.DataFrame(), [
            "Kolom tidak ditemukan: " + ", ".join(sorted(missing))
            + ". Gunakan tanggal/date, stasiun/station, curah hujan/rainfall_mm."
        ]
    df = df[["date", "station", "rainfall_mm"]].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["station"] = df["station"].astype(str).str.strip()
    df["rainfall_mm"] = pd.to_numeric(df["rainfall_mm"], errors="coerce")
    invalid = (
        df["date"].isna() | df["station"].isin(["", "nan", "None"])
        | df["rainfall_mm"].isna() | (df["rainfall_mm"] < 0)
    )
    errors = []
    if invalid.any():
        errors.append(f"{int(invalid.sum())} baris tidak valid akan diabaikan.")
    clean = df.loc[~invalid].copy()
    clean["date"] = clean["date"].dt.strftime("%Y-%m-%d")
    clean = clean.drop_duplicates(["date", "station"], keep="last")
    if clean.empty:
        errors.append("Tidak ada data valid.")
    return clean, errors


def annual_maxima(df, station):
    if df.empty:
        return pd.Series(dtype=float)
    subset = df.copy()
    if station != "Semua stasiun":
        subset = subset[subset["station"] == station]
    if subset.empty:
        return pd.Series(dtype=float)
    subset["year"] = pd.to_datetime(subset["date"]).dt.year
    return subset.groupby("year")["rainfall_mm"].max().sort_index()


# -------------------------------------------------------------------
# ANALISIS FREKUENSI
# -------------------------------------------------------------------
def calculate_frequency(values, distribution):
    if not SCIPY_AVAILABLE:
        raise RuntimeError("SciPy belum terpasang. Jalankan: python -m pip install scipy")
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 5:
        raise ValueError("Minimal 5 tahun data maksimum tahunan diperlukan; lebih baik 10–30 tahun.")
    if np.any(x < 0):
        raise ValueError("Data hujan tidak boleh negatif.")
    if np.std(x, ddof=1) == 0:
        raise ValueError("Semua data maksimum tahunan sama; distribusi tidak dapat dihitung.")
    params = {}
    rows = []

    if distribution == "Normal":
        mu, sd = stats.norm.fit(x)
        params = {"Rata-rata": float(mu), "Simpangan baku": float(sd)}
        dist = stats.norm(loc=mu, scale=sd)
    elif distribution == "Log Normal":
        if np.any(x <= 0):
            raise ValueError("Log Normal membutuhkan data hujan lebih besar dari 0.")
        shape, loc, scale = stats.lognorm.fit(x, floc=0)
        params = {"Bentuk (sigma log)": float(shape), "Skala": float(scale)}
        dist = stats.lognorm(s=shape, loc=loc, scale=scale)
    elif distribution == "Gumbel":
        loc, scale = stats.gumbel_r.fit(x)
        params = {"Lokasi": float(loc), "Skala": float(scale)}
        dist = stats.gumbel_r(loc=loc, scale=scale)
    elif distribution == "Log Pearson III":
        if np.any(x <= 0):
            raise ValueError("Log Pearson III membutuhkan data hujan lebih besar dari 0.")
        lx = np.log10(x)
        shape, loc, scale = stats.pearson3.fit(lx)
        params = {"Rata-rata log": float(np.mean(lx)),
                  "Simpangan baku log": float(np.std(lx, ddof=1)),
                  "Koefisien kemencengan log": float(stats.skew(lx, bias=False))}
        log_dist = stats.pearson3(skew=shape, loc=loc, scale=scale)
        dist = None
    else:
        raise ValueError("Distribusi tidak dikenal.")

    for t in RETURN_PERIODS:
        p = 1.0 - 1.0 / t
        if distribution == "Log Pearson III":
            quantile = float(10 ** log_dist.ppf(p))
        else:
            quantile = float(dist.ppf(p))
        rows.append({"Periode ulang (tahun)": t, "Peluang tidak terlampaui": p,
                     "Hujan rencana (mm)": quantile})
    return params, pd.DataFrame(rows)


def goodness_of_fit(values, distribution):
    if not SCIPY_AVAILABLE:
        return {"Status": "SciPy tidak tersedia"}
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 5:
        return {"Status": "Minimal 5 data diperlukan"}
    try:
        if distribution == "Normal":
            pars = stats.norm.fit(x); cdf = lambda z: stats.norm.cdf(z, *pars)
        elif distribution == "Log Normal":
            if np.any(x <= 0): return {"Status": "Data harus > 0 untuk Log Normal"}
            pars = stats.lognorm.fit(x, floc=0); cdf = lambda z: stats.lognorm.cdf(z, *pars)
        elif distribution == "Gumbel":
            pars = stats.gumbel_r.fit(x); cdf = lambda z: stats.gumbel_r.cdf(z, *pars)
        else:
            if np.any(x <= 0): return {"Status": "Data harus > 0 untuk Log Pearson III"}
            pars = stats.pearson3.fit(np.log10(x))
            cdf = lambda z: stats.pearson3.cdf(np.log10(z), *pars)
        ks = stats.kstest(x, cdf)
        return {"K-S statistik": float(ks.statistic),
                "K-S p-value (indikatif)": float(ks.pvalue),
                "Catatan": "P-value K-S standar bersifat indikatif karena parameter distribusi diestimasi dari sampel."}
    except Exception as exc:
        return {"Status": f"Uji tidak dapat dihitung: {exc}"}


# -------------------------------------------------------------------
# DEBIT BANJIR — METODE RASIONAL
# -------------------------------------------------------------------
def rational_method(area_km2, runoff_c, intensity_mm_hr):
    return 0.278 * float(runoff_c) * float(intensity_mm_hr) * float(area_km2)


def rational_table(area, runoff, frequency_table, duration):
    result = frequency_table.copy()
    result["Intensitas (mm/jam)"] = result["Hujan rencana (mm)"] / float(duration)
    result["Debit (m³/det)"] = result["Intensitas (mm/jam)"].apply(
        lambda i: rational_method(area, runoff, i)
    )
    return result


# -------------------------------------------------------------------
# GIS UTILITIES
# -------------------------------------------------------------------
def read_vector_upload(uploaded):
    if not GIS_AVAILABLE:
        raise RuntimeError("Dependensi GIS belum tersedia.")
    suffix = Path(uploaded.name).suffix.lower()
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / uploaded.name
        path.write_bytes(uploaded.getvalue())
        if suffix == ".zip":
            with zipfile.ZipFile(path) as zf:
                zf.extractall(Path(td) / "shape")
            shp_files = list((Path(td) / "shape").rglob("*.shp"))
            if not shp_files:
                raise ValueError("ZIP tidak berisi file .shp.")
            gdf = gpd.read_file(shp_files[0])
        else:
            gdf = gpd.read_file(path)
    if gdf.empty:
        raise ValueError("Layer batas tidak memiliki fitur.")
    if gdf.crs is None:
        raise ValueError("CRS batas wilayah tidak diketahui. Tetapkan CRS pada data sumber.")
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    gdf["geometry"] = gdf.geometry.buffer(0)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
    if gdf.empty:
        raise ValueError("Tidak ditemukan geometri batas yang valid.")
    return gdf


def analyze_dem_upload(dem_upload, boundary_upload, rain_depth, period, duration, runoff):
    if not GIS_AVAILABLE:
        raise RuntimeError("GIS belum siap. Pasang dependensi pada requirements.txt.")
    boundary = read_vector_upload(boundary_upload)
    with MemoryFile(dem_upload.getvalue()) as memfile:
        with memfile.open() as src:
            if src.crs is None:
                raise ValueError("CRS DEM tidak diketahui.")
            boundary = boundary.to_crs(src.crs)
            geoms = [mapping(g) for g in boundary.geometry if g is not None and not g.is_empty]
            if not geoms:
                raise ValueError("Batas wilayah tidak memiliki poligon valid.")
            clipped, transform = mask(src, geoms, crop=True, filled=False)
            elev = clipped[0].astype("float64")
            valid = ~np.ma.getmaskarray(clipped[0]) & np.isfinite(elev)
            if valid.sum() < 9:
                raise ValueError("Area DEM valid terlalu kecil untuk analisis kemiringan.")
            elev_data = np.where(valid, elev, np.nan)
            dx = abs(src.res[0]); dy = abs(src.res[1])
            gy, gx = np.gradient(np.nan_to_num(elev_data, nan=float(np.nanmedian(elev_data))), dy, dx)
            slope = np.degrees(np.arctan(np.sqrt(gx**2 + gy**2)))
            zmin, zmax = np.nanpercentile(elev_data[valid], [5, 95])
            if zmax <= zmin:
                raise ValueError("Rentang elevasi DEM tidak memadai.")
            low_relief = 1 - np.clip((elev_data - zmin) / (zmax - zmin), 0, 1)
            slope_factor = 1 - np.clip(slope / 45.0, 0, 1)
            rain_factor = np.clip(float(rain_depth) / 300.0, 0, 1)
            index = (0.45 * low_relief + 0.35 * slope_factor + 0.20 * rain_factor) * 100
            index[~valid] = np.nan
            classes = np.zeros(index.shape, dtype=np.uint8)
            classes[valid & (index < 35)] = 1
            classes[valid & (index >= 35) & (index < 65)] = 2
            classes[valid & (index >= 65)] = 3
            pixel_area = abs(transform.a * transform.e - transform.b * transform.d)
            areas = {
                1: float((classes == 1).sum() * pixel_area / 1_000_000),
                2: float((classes == 2).sum() * pixel_area / 1_000_000),
                3: float((classes == 3).sum() * pixel_area / 1_000_000),
            }
            profile = src.profile.copy()
            profile.update(driver="GTiff", height=classes.shape[0], width=classes.shape[1],
                           count=1, dtype="uint8", transform=transform, nodata=0,
                           compress="lzw")
            out = io.BytesIO()
            with MemoryFile() as out_mem:
                with out_mem.open(**profile) as dst:
                    dst.write(classes, 1)
                out.write(out_mem.read())
            # Untuk tampilan peta, buat layer batas dalam koordinat geografis.
            boundary_wgs = boundary.to_crs("EPSG:4326")
            bounds = boundary_wgs.total_bounds
            center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
            result = {
                "classes": classes, "transform": transform, "crs": src.crs,
                "areas": areas, "geojson": json.loads(boundary_wgs.to_json()),
                "center": center, "rain_depth": float(rain_depth),
                "period": int(period), "duration": float(duration),
                "runoff": float(runoff), "geotiff": out.getvalue(),
            }
            return result


def make_folium_map(result, rivers_upload=None):
    """Peta batas wilayah dengan basemap OpenStreetMap tanpa API key CARTO."""
    m = folium.Map(
        location=result["center"],
        zoom_start=11,
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        max_zoom=19,
        control_scale=True,
    )
    folium.GeoJson(
        result["geojson"],
        name="Batas wilayah",
        style_function=lambda _: {
            "color": "#c83e2b", "weight": 2, "fillColor": "#e3a52b",
            "fillOpacity": 0.06,
        },
    ).add_to(m)
    bounds = result["geojson"]
    try:
        layer = folium.GeoJson(bounds)
        m.fit_bounds(layer.get_bounds())
    except Exception:
        pass
    folium.LayerControl(collapsed=True).add_to(m)
    return m


# -------------------------------------------------------------------
# GIS OTOMATIS BERBASIS API ONLINE
# -------------------------------------------------------------------
GEOB_API = "https://www.geoboundaries.org/api/current/gbOpen/IDN/{adm}/"
OPEN_METEO_ELEVATION = "https://api.open-meteo.com/v1/elevation"
OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"


@st.cache_data(ttl=60 * 60 * 24 * 14, show_spinner=False)
def fetch_geoboundaries(adm_level):
    """Ambil batas administrasi Indonesia dari geoBoundaries (cache 14 hari)."""
    if adm_level not in ("ADM1", "ADM2"):
        raise ValueError("Level administrasi tidak didukung.")
    meta_response = requests.get(GEOB_API.format(adm=adm_level), timeout=45)
    meta_response.raise_for_status()
    metadata = meta_response.json()
    geojson_url = metadata.get("simplifiedGeometryGeoJSON") or metadata.get("gjDownloadURL")
    if not geojson_url:
        raise RuntimeError(f"Tautan GeoJSON {adm_level} tidak tersedia dari geoBoundaries.")
    geo_response = requests.get(geojson_url, timeout=120)
    geo_response.raise_for_status()
    if len(geo_response.content) < 100:
        raise RuntimeError("File batas wilayah yang diterima kosong atau tidak lengkap.")
    gdf = gpd.read_file(io.BytesIO(geo_response.content))
    if gdf.empty:
        raise RuntimeError(f"Data batas {adm_level} kosong.")
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    else:
        gdf = gdf.to_crs("EPSG:4326")
    name_col = next((c for c in ["shapeName", "NAME_1", "NAME_2", "name", "NAME"] if c in gdf.columns), None)
    if name_col is None:
        raise RuntimeError("Kolom nama wilayah tidak ditemukan pada data batas geoBoundaries.")
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    gdf["_hydova_name"] = gdf[name_col].astype(str).str.strip()
    gdf = gdf[gdf["_hydova_name"] != ""].copy()
    return gdf, metadata


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def fetch_elevation_points(latitudes, longitudes):
    """Ambil elevasi Copernicus DEM GLO-90, maksimal 100 titik per request."""
    lats = list(latitudes)
    lons = list(longitudes)
    if len(lats) != len(lons):
        raise ValueError("Daftar koordinat lintang dan bujur tidak sama panjang.")
    values = []
    for start in range(0, len(lats), 100):
        batch_lat = lats[start:start + 100]
        batch_lon = lons[start:start + 100]
        response = requests.get(
            OPEN_METEO_ELEVATION,
            params={"latitude": ",".join(f"{v:.5f}" for v in batch_lat),
                    "longitude": ",".join(f"{v:.5f}" for v in batch_lon)},
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        values.extend(result.get("elevation", []))
    if len(values) != len(lats):
        raise RuntimeError("Jumlah data elevasi yang diterima tidak sesuai jumlah titik.")
    return [float(v) if v is not None else float("nan") for v in values]


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def fetch_historical_rain(lat, lon, start_date, end_date):
    """Ambil jumlah hujan harian ERA5/reanalisis Open-Meteo untuk titik pusat wilayah."""
    response = requests.get(
        OPEN_METEO_ARCHIVE,
        params={
            "latitude": float(lat), "longitude": float(lon),
            "start_date": str(start_date), "end_date": str(end_date),
            "daily": "precipitation_sum", "timezone": "Asia/Jakarta",
        },
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    daily = payload.get("daily", {})
    dates = daily.get("time", [])
    rain = daily.get("precipitation_sum", [])
    if not dates or not rain:
        raise RuntimeError("API tidak mengembalikan data curah hujan untuk periode tersebut.")
    frame = pd.DataFrame({"Tanggal": pd.to_datetime(dates), "Hujan (mm)": rain})
    frame["Hujan (mm)"] = pd.to_numeric(frame["Hujan (mm)"], errors="coerce")
    frame = frame.dropna(subset=["Hujan (mm)"])
    if frame.empty:
        raise RuntimeError("Data curah hujan dari API tidak memiliki nilai valid.")
    return frame, payload.get("timezone", "Asia/Jakarta"), payload.get("latitude", lat), payload.get("longitude", lon)


def create_analysis_grid(polygon, rows=12, cols=12, max_points=64):
    """Buat titik sampling merata di dalam poligon, bukan hanya mengambil sisi awal grid."""
    minx, miny, maxx, maxy = polygon.bounds
    if maxx <= minx or maxy <= miny:
        raise ValueError("Batas wilayah tidak memiliki rentang koordinat yang valid.")

    from shapely.geometry import Point
    points = []
    for r, lat in enumerate(np.linspace(miny, maxy, rows)):
        for c, lon in enumerate(np.linspace(minx, maxx, cols)):
            point = Point(float(lon), float(lat))
            if polygon.covers(point):
                points.append({
                    "row": r, "col": c,
                    "latitude": float(lat), "longitude": float(lon),
                })

    # Jika jumlah titik lebih banyak dari batas, pilih indeks yang tersebar merata.
    if len(points) > max_points:
        selected = np.linspace(0, len(points) - 1, max_points, dtype=int)
        points = [points[i] for i in selected]

    # Untuk poligon kecil atau sempit, gunakan titik dari triangulasi.
    if len(points) < 3:
        from shapely.ops import triangulate
        candidates = []
        for tri in triangulate(polygon):
            candidate = tri.representative_point()
            if polygon.covers(candidate):
                candidates.append(candidate)
        representative = polygon.representative_point()
        candidates.append(representative)
        unique = []
        seen = set()
        for p in candidates:
            key = (round(p.x, 8), round(p.y, 8))
            if key not in seen:
                seen.add(key)
                unique.append(p)
        if len(unique) > max_points:
            idx = np.linspace(0, len(unique) - 1, max_points, dtype=int)
            unique = [unique[i] for i in idx]
        points = [
            {"row": i, "col": 0, "latitude": float(p.y), "longitude": float(p.x)}
            for i, p in enumerate(unique)
        ]

    if len(points) < 3:
        raise ValueError("Wilayah terlalu kecil untuk menghasilkan minimal tiga titik sampling.")
    return points


def calculate_relative_index(points, elevations, rainfall_total):
    """Hitung indeks screening relatif dari elevasi, relief lokal, dan hujan."""
    if len(points) != len(elevations):
        raise ValueError("Jumlah titik dan data elevasi tidak sama.")

    frame = pd.DataFrame(points).copy()
    frame["Elevasi (m)"] = pd.to_numeric(pd.Series(elevations), errors="coerce").to_numpy()
    frame = frame.replace([np.inf, -np.inf], np.nan)
    frame = frame.dropna(subset=["latitude", "longitude", "Elevasi (m)"]).reset_index(drop=True)
    if len(frame) < 3:
        raise ValueError("Titik elevasi valid kurang dari tiga; indeks tidak dapat dihitung.")

    z = frame["Elevasi (m)"].to_numpy(dtype=float)
    emin, emax = float(np.min(z)), float(np.max(z))
    if emax - emin < 0.01:
        low_elevation = np.full(len(frame), 0.5)
    else:
        low_elevation = 1.0 - np.clip((z - emin) / (emax - emin), 0, 1)

    # Jarak antar titik dikoreksi terhadap lintang agar tidak memakai derajat mentah.
    lat = frame["latitude"].to_numpy(dtype=float)
    lon = frame["longitude"].to_numpy(dtype=float)
    coords_m = np.column_stack((
        lon * 111320.0 * np.cos(np.radians(lat)),
        lat * 110574.0,
    ))
    relief = np.zeros(len(frame), dtype=float)
    for i in range(len(frame)):
        distances = np.sqrt(((coords_m - coords_m[i]) ** 2).sum(axis=1))
        distances[i] = np.inf
        nearest = np.argsort(distances)[:min(4, len(frame) - 1)]
        nearest = [j for j in nearest if distances[j] > 0]
        if nearest:
            gradients = [abs(z[j] - z[i]) / max(1.0, distances[j]) for j in nearest]
            relief[i] = float(np.mean(gradients))

    flat_factor = 1.0 - np.clip(relief / 0.15, 0, 1)
    rain_factor = float(np.clip(float(rainfall_total) / 300.0, 0, 1))
    frame["Relief lokal (m/m)"] = relief
    frame["Hujan periode (mm)"] = float(rainfall_total)
    frame["Indeks potensi relatif"] = (
        0.40 * low_elevation + 0.35 * flat_factor + 0.25 * rain_factor
    ) * 100
    frame["Kelas relatif"] = pd.cut(
        frame["Indeks potensi relatif"],
        bins=[-0.001, 35, 65, 100.001],
        labels=["Rendah", "Sedang", "Tinggi"],
        include_lowest=True,
    ).astype(str)
    return frame


def make_index_geotiff(samples, polygon, width=240, height=240):
    """Ekspor raster interpolasi indeks titik; hasil adalah visualisasi screening, bukan DEM."""
    if not GIS_AVAILABLE:
        raise RuntimeError("Dependensi rasterio/geopandas belum tersedia.")
    try:
        from scipy.interpolate import griddata
    except Exception as exc:
        raise RuntimeError("SciPy diperlukan untuk interpolasi GeoTIFF. Jalankan pip install scipy.") from exc
    from rasterio.transform import from_bounds
    from rasterio.features import geometry_mask as raster_geometry_mask
    from shapely.geometry import mapping
    minx, miny, maxx, maxy = polygon.bounds
    transform = from_bounds(minx, miny, maxx, maxy, width, height)
    xs = minx + (np.arange(width) + 0.5) * ((maxx - minx) / width)
    ys = maxy - (np.arange(height) + 0.5) * ((maxy - miny) / height)
    grid_x, grid_y = np.meshgrid(xs, ys)
    clean_samples = samples.dropna(subset=["longitude", "latitude", "Indeks potensi relatif"]).copy()
    clean_samples = clean_samples.drop_duplicates(subset=["longitude", "latitude"])
    coords = clean_samples[["longitude", "latitude"]].to_numpy(dtype=float)
    vals = clean_samples["Indeks potensi relatif"].to_numpy(dtype=float)
    if len(coords) < 1:
        raise ValueError("Tidak ada titik valid untuk membuat GeoTIFF.")
    method = "linear" if len(coords) >= 3 else "nearest"
    try:
        grid = griddata(coords, vals, (grid_x, grid_y), method=method)
    except Exception:
        grid = griddata(coords, vals, (grid_x, grid_y), method="nearest")
    nearest = griddata(coords, vals, (grid_x, grid_y), method="nearest")
    grid = np.where(np.isfinite(grid), grid, nearest)
    inside = raster_geometry_mask([mapping(polygon)], out_shape=(height, width),
                                  transform=transform, invert=True)
    grid = np.where(inside & np.isfinite(grid), grid, -9999).astype("float32")
    output = io.BytesIO()
    profile = {
        "driver": "GTiff", "height": height, "width": width, "count": 1,
        "dtype": "float32", "crs": "EPSG:4326", "transform": transform,
        "nodata": -9999.0, "compress": "lzw",
    }
    with rasterio.io.MemoryFile() as memfile:
        with memfile.open(**profile) as dst:
            dst.write(grid, 1)
            dst.set_band_description(1, "Interpolated relative susceptibility screening index 0-100")
        output.write(memfile.read())
    return output.getvalue()


def make_index_area_geojson(selected_boundary, samples, rows=28, cols=28):
    """Buat zona area berwarna dari interpolasi indeks titik secara vektorisasi."""
    from shapely.geometry import box, mapping
    from scipy.interpolate import griddata

    clean = samples.dropna(
        subset=["longitude", "latitude", "Indeks potensi relatif"]
    ).drop_duplicates(subset=["longitude", "latitude"]).copy()
    if len(clean) < 3:
        raise ValueError("Minimal tiga titik valid diperlukan untuk membentuk area indeks.")
    if selected_boundary is None or selected_boundary.is_empty:
        raise ValueError("Geometri batas wilayah kosong.")

    minx, miny, maxx, maxy = selected_boundary.bounds
    if maxx <= minx or maxy <= miny:
        raise ValueError("Batas wilayah tidak memiliki luas yang valid.")

    coords = clean[["longitude", "latitude"]].to_numpy(dtype=float)
    values = clean["Indeks potensi relatif"].to_numpy(dtype=float)

    # Hitung nilai seluruh titik tengah grid sekaligus (jauh lebih cepat).
    dx = (maxx - minx) / cols
    dy = (maxy - miny) / rows
    x_centers = minx + (np.arange(cols) + 0.5) * dx
    y_centers = miny + (np.arange(rows) + 0.5) * dy
    grid_x, grid_y = np.meshgrid(x_centers, y_centers)
    try:
        grid_values = griddata(coords, values, (grid_x, grid_y), method="linear")
    except Exception:
        grid_values = np.full(grid_x.shape, np.nan, dtype=float)
    nearest = griddata(coords, values, (grid_x, grid_y), method="nearest")
    grid_values = np.where(np.isfinite(grid_values), grid_values, nearest)
    grid_values = np.clip(grid_values, 0, 100)

    features = []
    for r in range(rows):
        y0, y1 = miny + r * dy, miny + (r + 1) * dy
        for c in range(cols):
            x0, x1 = minx + c * dx, minx + (c + 1) * dx
            cell = box(x0, y0, x1, y1).intersection(selected_boundary)
            if cell.is_empty or cell.area <= 0:
                continue
            value = float(grid_values[r, c])
            kelas = "Rendah" if value <= 35 else ("Sedang" if value <= 65 else "Tinggi")
            features.append({
                "type": "Feature",
                "properties": {"indeks": round(value, 2), "kelas": kelas},
                "geometry": mapping(cell),
            })

    if not features:
        raise ValueError("Tidak ada sel grid yang beririsan dengan batas wilayah.")
    return {"type": "FeatureCollection", "features": features}


def summarize_index_area_km2(selected_boundary, samples):
    """Hitung luas setiap kelas area dengan luas geodesik (km²), bukan jumlah titik."""
    from shapely.geometry import shape
    from pyproj import Geod

    area_geojson = make_index_area_geojson(selected_boundary, samples)
    geod = Geod(ellps="WGS84")
    totals = {"Rendah": 0.0, "Sedang": 0.0, "Tinggi": 0.0}

    for feature in area_geojson["features"]:
        kelas = feature["properties"].get("kelas")
        if kelas not in totals:
            continue
        geom = shape(feature["geometry"])
        # Geod menghitung luas di permukaan ellipsoid bumi dari koordinat lon/lat.
        area_m2, _ = geod.geometry_area_perimeter(geom)
        totals[kelas] += abs(float(area_m2))

    return {kelas: luas_m2 / 1_000_000 for kelas, luas_m2 in totals.items()}


def folium_auto_map(selected_boundary, samples):
    """Tampilkan zona area hasil interpolasi; titik sampling tidak ditampilkan."""
    if selected_boundary is None or selected_boundary.is_empty:
        raise ValueError("Geometri batas wilayah kosong.")
    if samples.empty:
        raise ValueError("Tidak ada data sampling yang dapat dipetakan.")

    geom_json = json.loads(gpd.GeoSeries([selected_boundary], crs="EPSG:4326").to_json())
    area_json = make_index_area_geojson(selected_boundary, samples)
    center_point = selected_boundary.representative_point()
    fmap = folium.Map(
        location=[center_point.y, center_point.x], zoom_start=11,
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        max_zoom=19, control_scale=True, prefer_canvas=True,
    )

    area_colors = {"Rendah": "#2d8a57", "Sedang": "#e0a52b", "Tinggi": "#c83e2b"}
    area_layer = folium.FeatureGroup(name="Zona indeks potensi relatif", show=True)
    folium.GeoJson(
        area_json,
        style_function=lambda feature: {
            "color": area_colors.get(feature["properties"].get("kelas"), "#808080"),
            "weight": 0.15,
            "fillColor": area_colors.get(feature["properties"].get("kelas"), "#808080"),
            "fillOpacity": 0.48,
        },
        highlight_function=lambda feature: {"weight": 1.2, "color": "#202020", "fillOpacity": 0.68},
        tooltip=folium.GeoJsonTooltip(
            fields=["kelas", "indeks"],
            aliases=["Kelas area:", "Indeks relatif:"],
            localize=True, sticky=True,
        ),
        name="Zona indeks",
    ).add_to(area_layer)
    area_layer.add_to(fmap)

    folium.GeoJson(
        geom_json, name="Batas administrasi",
        style_function=lambda _: {"color": "#c83e2b", "weight": 3, "fillOpacity": 0},
        tooltip="Batas wilayah terpilih",
    ).add_to(fmap)

    legend_html = """
    <div style="position: fixed; bottom: 28px; left: 18px; z-index: 9999;
                background: white; padding: 10px 12px; border: 1px solid #777;
                border-radius: 6px; font-size: 12px; box-shadow: 0 1px 5px #7778;">
      <b>Indeks potensi relatif</b><br>
      <span style="color:#2d8a57">&#9632;</span> Rendah (0–35)<br>
      <span style="color:#e0a52b">&#9632;</span> Sedang (35–65)<br>
      <span style="color:#c83e2b">&#9632;</span> Tinggi (65–100)
    </div>"""
    fmap.get_root().html.add_child(folium.Element(legend_html))
    minx, miny, maxx, maxy = selected_boundary.bounds
    fmap.fit_bounds([[miny, minx], [maxy, maxx]], padding=(25, 25))
    folium.LayerControl(collapsed=True).add_to(fmap)
    return fmap


# -------------------------------------------------------------------
# SESSION STATE: hanya untuk hasil/non-widget. Jangan mengubah key widget.
# -------------------------------------------------------------------
DEFAULT_STATE = {
    "confirm_reset": False,
    "gis_result": None,
    "gis_auto_result": None,
    "freq_result": None,
}
for _key, _value in DEFAULT_STATE.items():
    if _key not in st.session_state:
        st.session_state[_key] = _value


# -------------------------------------------------------------------
# NAVIGASI
# -------------------------------------------------------------------
init_db()
data = read_rainfall()
stations = sorted(data["station"].dropna().astype(str).unique().tolist()) if not data.empty else []

with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:12px;padding:8px 4px 18px;
    border-bottom:1px solid rgba(198,234,243,.2)">
      <div style="font-size:28px;background:linear-gradient(145deg,#168aad,#20a4c7);padding:10px;border-radius:14px;box-shadow:0 5px 16px #001b2b55">🌧️</div>
      <div><div style="font-size:1.38rem;font-weight:850;color:#ffffff;letter-spacing:.05em">HYDOVA</div>
      <div style="font-size:.76rem;color:#bfe7f1">Hydrological Intelligence</div></div>
    </div>
    <div style="color:#8ed3e6;font-size:.72rem;font-weight:800;letter-spacing:.13em;padding:16px 8px 7px">NAVIGASI UTAMA</div>
    """, unsafe_allow_html=True)
    page_labels = ["Dashboard", "Analisis Frekuensi", "Debit Banjir",
                   "GIS & Potensi Genangan", "Panduan"]
    page = st.radio("NAVIGASI", page_labels, label_visibility="collapsed", key="main_navigation")
    st.markdown("""
    <div style="border-top:1px solid rgba(198,234,243,.2);margin-top:18px;padding:16px 8px;
    color:#b7dce7;font-size:.77rem;line-height:1.8"><b style="color:#fff">Cakupan wilayah</b><br>Seluruh Indonesia
    <br><br><span style="color:#8ed3e6">●</span> Build 2.0 · Academic project</div>
    """, unsafe_allow_html=True)

st.markdown(
    '<div class="hydova-hero"><div class="hydova-hero-inner">'
    '<div class="hydova-mark">🌧️</div><div>'
    '<div class="hydova-title">HYDOVA</div>'
    '<div class="hydova-sub">Hydrological Data &amp; Observation Intelligence Platform</div>'
    '<div class="hydova-tag">Rainfall · Runoff · Spatial Insight</div>'
    '</div></div></div>',
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# DASHBOARD — pengelolaan hujan terintegrasi
# -------------------------------------------------------------------
if page == "Dashboard":
    st.subheader("Dashboard pemantauan hidrologi")
    st.caption("Pemantauan dan pengelolaan data curah hujan untuk stasiun atau wilayah di seluruh Indonesia.")

    n = len(data)
    maxrain = float(data["rainfall_mm"].max()) if n else 0.0
    avg = float(data["rainfall_mm"].mean()) if n else 0.0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Data observasi", f"{n:,}")
    c2.metric("Stasiun/wilayah", f"{len(stations)}")
    c3.metric("Hujan maksimum", f"{maxrain:.1f} mm")
    c4.metric("Rata-rata hujan", f"{avg:.1f} mm")
    st.divider()

    tab_summary, tab_input, tab_import, tab_manage = st.tabs(
        ["Ringkasan", "Input Data", "Impor File", "Kelola Data"]
    )

    with tab_summary:
        if data.empty:
            st.info("Belum ada data observasi. Tambahkan melalui tab Input Data atau Impor File.")
        else:
            left, right = st.columns([1.5, 1])
            with left:
                st.markdown("#### Riwayat curah hujan")
                daily = data.groupby("date", as_index=False)["rainfall_mm"].mean()
                fig, ax = plt.subplots(figsize=(9, 3))
                ax.plot(daily["date"], daily["rainfall_mm"], linewidth=1.6)
                ax.set_ylabel("Curah hujan (mm)")
                ax.grid(alpha=0.2)
                fig.autofmt_xdate()
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)
            with right:
                st.markdown("#### Statistik ringkas")
                st.dataframe(data["rainfall_mm"].describe().rename("mm").to_frame(),
                             use_container_width=True)
            st.markdown("#### Maksimum tahunan")
            annual_station = st.selectbox(
                "Pilih stasiun untuk maksimum tahunan",
                ["Semua stasiun"] + stations,
                key="dash_annual_station",
            )
            annual_values = annual_maxima(data, annual_station)
            if not annual_values.empty:
                st.bar_chart(annual_values)
            st.caption("Untuk analisis frekuensi desain, gunakan seri maksimum tahunan dari satu stasiun yang representatif.")
            st.markdown("#### Data observasi terbaru")
            st.dataframe(data.sort_values("date", ascending=False).head(20),
                         use_container_width=True, hide_index=True)

    with tab_input:
        st.markdown("#### Input curah hujan secara manual")
        with st.form("manual_rainfall_form", clear_on_submit=True):
            a, b, c = st.columns(3)
            input_date = a.date_input("Tanggal", value=date.today(), key="manual_date_input")
            input_station = b.text_input("Nama stasiun / wilayah",
                                         placeholder="Contoh: Stasiun Hujan Magelang",
                                         key="manual_station_input")
            input_rain = c.number_input("Curah hujan (mm)", min_value=0.0,
                                        step=1.0, key="manual_rain_input")
            submitted = st.form_submit_button("Simpan observasi", type="primary")
        if submitted:
            if not input_station.strip():
                st.error("Nama stasiun atau wilayah wajib diisi.")
            else:
                try:
                    insert_rainfall(pd.DataFrame([{
                        "date": input_date, "station": input_station.strip(),
                        "rainfall_mm": input_rain,
                    }]))
                    st.success("Observasi berhasil disimpan.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Gagal menyimpan data: {exc}")

    with tab_import:
        st.markdown("#### Impor data dari Excel atau CSV")
        st.caption("Kolom yang dibutuhkan: tanggal/date, stasiun/station, dan curah hujan/rainfall_mm.")
        uploaded = st.file_uploader("Pilih file Excel atau CSV", type=["xlsx", "xls", "csv"],
                                    key="dashboard_rain_import")
        if uploaded is not None:
            try:
                raw = (pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv")
                       else pd.read_excel(uploaded))
                cleaned, warnings = validate_rainfall(raw)
                for warning in warnings:
                    st.warning(warning)
                if not cleaned.empty:
                    st.success(f"{len(cleaned)} baris valid.")
                    st.dataframe(cleaned.head(15), use_container_width=True, hide_index=True)
                    if st.button("Simpan data impor", type="primary", key="save_rain_import"):
                        saved = insert_rainfall(cleaned)
                        st.success(f"{saved} baris berhasil disimpan/diperbarui.")
                        st.rerun()
            except Exception as exc:
                st.error(f"Gagal membaca file: {exc}")

    with tab_manage:
        st.markdown("#### Edit, hapus, dan unduh data")
        current = read_rainfall()
        if current.empty:
            st.info("Belum ada data untuk dikelola.")
        else:
            st.dataframe(current, use_container_width=True, hide_index=True)
            record_ids = current["id"].astype(int).tolist()
            selected_id = st.selectbox("Pilih ID data", record_ids, key="manage_selected_id")
            selected_record = current.loc[current["id"] == selected_id].iloc[0]
            with st.form("edit_rainfall_form"):
                edit_date = st.date_input("Tanggal", value=pd.Timestamp(selected_record["date"]).date())
                edit_station = st.text_input("Stasiun / wilayah", value=str(selected_record["station"]))
                edit_rain = st.number_input("Curah hujan (mm)", min_value=0.0,
                                            value=float(selected_record["rainfall_mm"]))
                edit_submit = st.form_submit_button("Simpan perubahan")
            if edit_submit:
                if not edit_station.strip():
                    st.error("Nama stasiun wajib diisi.")
                else:
                    try:
                        update_rainfall(selected_id, edit_date, edit_station.strip(), edit_rain)
                        st.success("Data berhasil diperbarui.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Gagal memperbarui data: {exc}")

            if st.button("Hapus ID terpilih", key="delete_selected_rainfall"):
                delete_rainfall(selected_id)
                st.success("Data berhasil dihapus.")
                st.rerun()

            export_data = current.drop(columns=["id"]).copy()
            st.download_button("Unduh CSV", export_data.to_csv(index=False).encode("utf-8"),
                               "hydova_rainfall.csv", "text/csv")
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                export_data.to_excel(writer, index=False)
            st.download_button("Unduh Excel", excel_buffer.getvalue(), "hydova_rainfall.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.divider()
        if st.button("Reset seluruh data hujan", key="open_reset_confirmation"):
            st.session_state["confirm_reset"] = True
        if st.session_state["confirm_reset"]:
            st.warning("Konfirmasi: seluruh observasi curah hujan akan dihapus permanen.")
            col_yes, col_no = st.columns(2)
            if col_yes.button("Ya, hapus seluruh data", type="primary", key="confirm_reset_yes"):
                reset_rainfall()
                st.session_state["confirm_reset"] = False
                st.success("Seluruh data hujan telah dihapus.")
                st.rerun()
            if col_no.button("Batal", key="confirm_reset_no"):
                st.session_state["confirm_reset"] = False
                st.rerun()


# -------------------------------------------------------------------
# ANALISIS FREKUENSI
# -------------------------------------------------------------------
elif page == "Analisis Frekuensi":
    st.subheader("Analisis frekuensi hujan")
    if data.empty:
        st.warning("Masukkan data hujan terlebih dahulu melalui Dashboard.")
    else:
        freq_station_widget = st.selectbox("Stasiun analisis", stations, key="freq_station_widget")
        freq_distribution_widget = st.selectbox(
            "Distribusi", ["Normal", "Log Normal", "Gumbel", "Log Pearson III"],
            key="freq_distribution_widget",
        )
        annual = annual_maxima(data, freq_station_widget)
        st.write(f"Jumlah tahun tersedia: **{len(annual)}**")
        if not annual.empty:
            st.dataframe(annual.rename("Maksimum tahunan (mm)").to_frame(),
                         use_container_width=True)
        if st.button("Hitung hujan rencana", type="primary", key="calculate_frequency_button"):
            try:
                params, table = calculate_frequency(annual.values, freq_distribution_widget)
                # Hasil disimpan pada satu key non-widget; tidak mengubah key widget.
                st.session_state["freq_result"] = {
                    "station": freq_station_widget,
                    "distribution": freq_distribution_widget,
                    "params": params,
                    "table": table,
                    "annual_values": annual.values.tolist(),
                }
            except Exception as exc:
                st.error(f"Perhitungan gagal: {exc}")

        freq_result = st.session_state.get("freq_result")
        if (freq_result is not None
                and freq_result["station"] == freq_station_widget
                and freq_result["distribution"] == freq_distribution_widget):
            st.markdown("#### Parameter distribusi")
            st.json(freq_result["params"])
            st.dataframe(freq_result["table"], use_container_width=True, hide_index=True)
            fig, ax = plt.subplots(figsize=(8, 3.5))
            ax.plot(freq_result["table"]["Periode ulang (tahun)"],
                    freq_result["table"]["Hujan rencana (mm)"], marker="o")
            ax.set_xlabel("Periode ulang (tahun)")
            ax.set_ylabel("Hujan rencana (mm)")
            ax.grid(alpha=0.25)
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
            st.markdown("#### Uji kesesuaian")
            st.json(goodness_of_fit(annual.values, freq_distribution_widget))
            st.caption("Uji K-S menggunakan parameter hasil estimasi sampel; p-value standar bersifat indikatif.")
        elif freq_result is not None:
            st.info("Pilihan stasiun atau distribusi berubah. Tekan Hitung hujan rencana untuk memperbarui hasil.")


# -------------------------------------------------------------------
# DEBIT BANJIR
# -------------------------------------------------------------------
elif page == "Debit Banjir":
    st.subheader("Estimasi debit banjir rencana — Metode Rasional")
    st.caption("Q = 0,278 × C × I × A; Q (m³/det), C (-), I (mm/jam), A (km²).")
    a, b, c = st.columns(3)
    area = a.number_input("Luas DAS (km²)", min_value=0.001, value=10.0, step=0.5,
                          key="flood_area")
    runoff = b.number_input("Koefisien limpasan C", min_value=0.0, max_value=1.0,
                             value=0.6, step=0.05, key="flood_runoff")
    duration = c.number_input("Durasi hujan / waktu konsentrasi (jam)", min_value=0.1,
                              value=1.0, step=0.1, key="flood_duration")
    if data.empty:
        st.info("Tambahkan data hujan melalui Dashboard untuk menghitung hujan rencana.")
    else:
        flood_station = st.selectbox("Stasiun sumber hujan", stations, key="flood_station_widget")
        flood_distribution = st.selectbox(
            "Distribusi frekuensi", ["Gumbel", "Log Pearson III", "Normal", "Log Normal"],
            key="flood_distribution_widget",
        )
        flood_annual = annual_maxima(data, flood_station)
        try:
            _, depths = calculate_frequency(flood_annual.values, flood_distribution)
            qtable = rational_table(area, runoff, depths, duration)
            st.dataframe(qtable, use_container_width=True, hide_index=True)
            fig, ax = plt.subplots(figsize=(8, 3))
            ax.plot(qtable["Periode ulang (tahun)"], qtable["Debit (m³/det)"], marker="o")
            ax.set_xlabel("Periode ulang (tahun)")
            ax.set_ylabel("Debit (m³/det)")
            ax.grid(alpha=0.25)
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
            last = qtable.iloc[-1]
            st.success(f"Debit Q{int(last['Periode ulang (tahun)'])} = {last['Debit (m³/det)']:.3f} m³/det")
            st.caption("Intensitas dihitung dari hujan rencana dibagi durasi yang dimasukkan; ini pendekatan sederhana, bukan kurva IDF.")
        except Exception as exc:
            st.error(f"Belum dapat menghitung: {exc}")


# -------------------------------------------------------------------
# GIS & POTENSI GENANGAN
# -------------------------------------------------------------------
elif page == "GIS & Potensi Genangan":
    st.subheader("Peta otomatis Indonesia — potensi relatif genangan")
    st.caption("Pilih wilayah. HYDOVA mengambil batas administrasi, elevasi, dan hujan historis melalui internet.")
    st.warning("Hasil merupakan indeks screening relatif, bukan kedalaman genangan, bukan peta bahaya resmi, dan bukan pengganti simulasi hidraulik.")

    if not GIS_AVAILABLE:
        st.error("Komponen GIS belum tersedia. Pasang dependensi dengan perintah berikut:")
        st.code("python -m pip install requests geopandas shapely pyproj folium streamlit-folium")
        st.caption(f"Rincian impor GIS: {GIS_IMPORT_ERROR}")
    else:
        try:
            with st.spinner("Mengambil daftar provinsi Indonesia dari geoBoundaries..."):
                adm1_gdf, adm1_meta = fetch_geoboundaries("ADM1")
            province_names = sorted(adm1_gdf["_hydova_name"].dropna().unique().tolist())
            if not province_names:
                raise RuntimeError("Daftar provinsi dari sumber batas administrasi kosong.")

            selected_province_name = st.selectbox(
                "Provinsi", province_names, key="gis_auto_province"
            )
            province_rows = adm1_gdf[adm1_gdf["_hydova_name"] == selected_province_name]
            province_geom = unary_union(list(province_rows.geometry))

            with st.spinner("Mengambil daftar kabupaten/kota dari geoBoundaries..."):
                adm2_gdf, adm2_meta = fetch_geoboundaries("ADM2")
            # Hubungkan ADM2 ke provinsi secara spasial; tidak bergantung pada nama parent.
            province_adm2_mask = adm2_gdf.geometry.intersects(province_geom)
            local_adm2 = adm2_gdf.loc[province_adm2_mask].copy()
            local_names = sorted(local_adm2["_hydova_name"].dropna().unique().tolist())
            area_options = ["Seluruh provinsi"] + local_names
            selected_area_name = st.selectbox(
                "Kabupaten/Kota", area_options, key="gis_auto_regency"
            )

            c1, c2 = st.columns(2)
            default_end = date.today() - pd.Timedelta(days=7)
            default_start = default_end - pd.Timedelta(days=29)
            with c1:
                rain_start = st.date_input("Awal data hujan historis", value=default_start,
                                           key="gis_auto_rain_start")
            with c2:
                rain_end = st.date_input("Akhir data hujan historis", value=default_end,
                                         key="gis_auto_rain_end")
            st.caption("Periode historis dibatasi sampai beberapa hari sebelum hari ini untuk mengurangi risiko data reanalisis yang belum tersedia.")

            if rain_start >= rain_end:
                st.error("Tanggal awal harus lebih dahulu daripada tanggal akhir.")
            else:
                run_auto_gis = st.button("Buat peta otomatis", type="primary", key="run_auto_gis_button")
                if run_auto_gis:
                    if selected_area_name == "Seluruh provinsi":
                        chosen_geom = province_geom
                        chosen_area_label = selected_province_name
                    else:
                        area_rows = local_adm2[local_adm2["_hydova_name"] == selected_area_name]
                        if area_rows.empty:
                            st.error("Geometri kabupaten/kota tidak ditemukan untuk pilihan tersebut.")
                            chosen_geom = None
                        else:
                            chosen_geom = unary_union(list(area_rows.geometry))
                            chosen_area_label = f"{selected_area_name}, {selected_province_name}"
                    if chosen_geom is not None:
                        try:
                            points = create_analysis_grid(chosen_geom, rows=12, cols=12, max_points=64)
                            if len(points) < 3:
                                raise ValueError("Wilayah terlalu kecil untuk menghasilkan titik sampling yang cukup.")
                            latitudes = [p["latitude"] for p in points]
                            longitudes = [p["longitude"] for p in points]
                            with st.spinner(f"Mengambil data elevasi Copernicus DEM untuk {len(points)} titik..."):
                                elevations = fetch_elevation_points(latitudes, longitudes)
                            valid_pairs = [
                                (point, elevation)
                                for point, elevation in zip(points, elevations)
                                if elevation is not None and np.isfinite(float(elevation))
                            ]
                            if len(valid_pairs) < 3:
                                raise ValueError(
                                    "Data elevasi valid kurang dari tiga titik. "
                                    "Periksa koneksi atau cakupan DEM pada wilayah tersebut."
                                )
                            points = [item[0] for item in valid_pairs]
                            elevations = [item[1] for item in valid_pairs]
                            centroid = chosen_geom.representative_point()
                            with st.spinner("Mengambil curah hujan historis dari Open-Meteo..."):
                                rain_frame, rain_timezone, api_lat, api_lon = fetch_historical_rain(
                                    centroid.y, centroid.x, rain_start.isoformat(), rain_end.isoformat()
                                )
                            rain_total = float(rain_frame["Hujan (mm)"].sum())
                            samples = calculate_relative_index(points, elevations, rain_total)
                            fmap = folium_auto_map(chosen_geom, samples)
                            geotiff_bytes = make_index_geotiff(samples, chosen_geom)
                            st.session_state["gis_auto_result"] = {
                                "province": selected_province_name,
                                "area": chosen_area_label,
                                "boundary_geom": chosen_geom,
                                "samples": samples,
                                "rain": rain_frame,
                                "rain_total": rain_total,
                                "start": rain_start.isoformat(),
                                "end": rain_end.isoformat(),
                                "map_html": fmap.get_root().render(),
                                "map_type": "area_interpolasi_v2",
                                "geotiff": geotiff_bytes,
                                "boundary_year": adm2_meta.get("boundaryYearRepresented", "tidak diketahui"),
                                "boundary_source": adm2_meta.get("boundarySource", "geoBoundaries"),
                                "boundary_license": adm2_meta.get("boundaryLicense", "lihat metadata geoBoundaries"),
                                "rain_lat": api_lat,
                                "rain_lon": api_lon,
                            }
                            st.success("Peta otomatis berhasil dibuat dari data online.")
                        except Exception as exc:
                            st.error(f"Pembuatan peta otomatis gagal: {exc}")
                            st.info("Periksa koneksi internet, lalu coba kembali. HYDOVA tidak akan mengganti data yang gagal diunduh dengan data buatan.")

            auto_result = st.session_state.get("gis_auto_result")
            # Hapus HTML peta lama yang masih tersimpan di session_state.
            # Versi sebelumnya menyimpan tile CARTO; mengganti fungsi saja tidak
            # otomatis mengganti HTML yang sudah telanjur tersimpan.
            if auto_result is not None:
                _old_map_html = str(auto_result.get("map_html", "")).lower()
                _old_map_type = auto_result.get("map_type")
                if (_old_map_type != "area_interpolasi_v2"
                        or "carto.com" in _old_map_html
                        or "basemaps" in _old_map_html):
                    st.session_state["gis_auto_result"] = None
                    auto_result = None
                    st.info("Tampilan peta diperbarui menjadi zona area. Klik 'Buat peta otomatis' untuk membangun ulang peta dengan tampilan area.")
            if auto_result is not None:
                st.divider()
                st.markdown(f"#### Hasil: {auto_result['area']}")
                sdata = auto_result["samples"]
                low_count = int((sdata["Kelas relatif"] == "Rendah").sum())
                med_count = int((sdata["Kelas relatif"] == "Sedang").sum())
                high_count = int((sdata["Kelas relatif"] == "Tinggi").sum())
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Sampel pembentuk area", f"{len(sdata)}")
                m2.metric("Hujan akumulasi", f"{auto_result['rain_total']:.1f} mm")
                m3.metric("Elevasi rata-rata", f"{sdata['Elevasi (m)'].mean():.1f} m")
                m4.metric("Titik kelas tinggi", f"{high_count}")
                st.markdown("#### Peta indeks potensi relatif")
                # Tampilkan HTML folium hasil pembuatan otomatis; tanpa unggah file pengguna.
                from streamlit.components.v1 import html as st_html
                st_html(auto_result["map_html"], height=600, scrolling=False)
                st.markdown("#### Ringkasan luas kelas area")
                try:
                    class_area_km2 = summarize_index_area_km2(auto_result["boundary_geom"], sdata)
                    class_summary = pd.DataFrame({
                        "Kelas": ["Rendah", "Sedang", "Tinggi"],
                        "Luas area (km²)": [
                            class_area_km2["Rendah"],
                            class_area_km2["Sedang"],
                            class_area_km2["Tinggi"],
                        ],
                    })
                    class_summary["Luas area (km²)"] = class_summary["Luas area (km²)"].round(2)
                    st.dataframe(class_summary, use_container_width=True, hide_index=True)
                    st.bar_chart(class_summary.set_index("Kelas"))
                    st.caption(
                        "Luas dihitung dari poligon zona hasil interpolasi menggunakan luas geodesik WGS84, "
                        "bukan dari jumlah titik sampling."
                    )
                except Exception as area_exc:
                    st.warning(f"Luas area per kelas belum dapat dihitung: {area_exc}")
                st.markdown("#### Data curah hujan historis yang diunduh")
                st.write(f"Periode: {auto_result['start']} sampai {auto_result['end']}")
                st.dataframe(auto_result["rain"], use_container_width=True, hide_index=True)
                st.download_button(
                    "Unduh titik analisis (CSV)",
                    sdata.to_csv(index=False).encode("utf-8"),
                    "HYDOVA_titik_indeks_potensi.csv", "text/csv",
                )
                st.download_button(
                    "Unduh raster indeks interpolasi (GeoTIFF)",
                    auto_result["geotiff"],
                    "HYDOVA_indeks_potensi_interpolasi.tif", "image/tiff",
                )
                st.download_button(
                    "Unduh data hujan historis (CSV)",
                    auto_result["rain"].to_csv(index=False).encode("utf-8"),
                    "HYDOVA_hujan_historis.csv", "text/csv",
                )
                st.caption(
                    f"Sumber batas: geoBoundaries, tahun data {auto_result['boundary_year']}; "
                    f"sumber utama: {auto_result['boundary_source']}. Lisensi: {auto_result['boundary_license']}. "
                    "Elevasi: Copernicus DEM GLO-90 melalui Open-Meteo. Hujan: reanalisis historis Open-Meteo pada titik representatif wilayah."
                )
                st.info(
                    "Interpretasi: titik sampling menunjukkan indeks screening relatif dari elevasi, relief lokal, dan akumulasi hujan periode terpilih. "
                    "GeoTIFF merupakan interpolasi visual dari titik sampling, bukan pengukuran kontinu atau model genangan tervalidasi. "
                    "Curah hujan diambil pada satu titik representatif wilayah dan diterapkan sebagai faktor hujan regional. "
                    "Untuk penentuan kedalaman/genangan aktual diperlukan data hidrologi-hidraulik terkalibrasi dan survei lapangan."
                )
        except Exception as exc:
            st.error(f"Tidak dapat memuat pilihan wilayah Indonesia: {exc}")
            st.caption("Sumber batas: geoBoundaries API (gbOpen). Pastikan komputer tersambung ke internet.")


# -------------------------------------------------------------------
# PANDUAN
# -------------------------------------------------------------------
elif page == "Panduan":
    st.subheader("Panduan penggunaan & metodologi")
    st.markdown("""
### 1. Format data hujan
File Excel/CSV harus memiliki tiga kolom berikut. Nama alternatif Bahasa Indonesia juga diterima.

| date | station | rainfall_mm |
|---|---|---:|
| 2020-01-01 | Stasiun Magelang | 12.5 |
| 2020-01-02 | Stasiun Magelang | 0 |

Satu baris adalah satu observasi harian pada satu stasiun. Jika tanggal dan stasiun sama, data yang baru akan memperbarui data lama.

### 2. Analisis frekuensi
Data harian diringkas menjadi maksimum untuk setiap tahun kalender dan stasiun. Aplikasi mensyaratkan minimal 5 tahun untuk komputasi; 10–30 tahun atau lebih sangat dianjurkan untuk analisis desain. Distribusi yang tersedia: Normal, Log Normal, Gumbel, dan Log Pearson III.

### 3. Debit banjir
Metode Rasional: **Q = 0,278 × C × I × A**. Intensitas dalam aplikasi dihitung sebagai hujan rencana dibagi durasi/waktu konsentrasi. Untuk perencanaan, gunakan kurva IDF lokal dan periksa kesesuaian metode terhadap karakteristik DAS.

### 4. GIS dan peta otomatis
Pilih provinsi dan kabupaten/kota. HYDOVA mengambil batas administrasi dari geoBoundaries, elevasi Copernicus DEM GLO-90 melalui Open-Meteo, dan hujan historis reanalisis Open-Meteo. Pengguna tidak perlu mengunggah DEM atau shapefile.

Peta menampilkan zona area hasil interpolasi indeks screening relatif berdasarkan elevasi, relief lokal, dan akumulasi hujan periode terpilih. Titik sampling digunakan sebagai masukan perhitungan dan tidak ditampilkan sebagai marker pada peta. Data hujan yang diambil dari satu titik representatif wilayah menjadi faktor regional, bukan pengukuran hujan di setiap titik peta.

**Peringatan ilmiah:** indeks ini bukan kedalaman genangan, bukan peta bahaya resmi, dan tidak menggantikan pemodelan hidraulik 1D/2D. Periksa sumber, tahun, resolusi, lisensi, dan keterbatasan data.

### 5. Cakupan Indonesia
Pilihan batas provinsi dan kabupaten/kota diambil online dari geoBoundaries. Data hujan observasi tetap dapat dimasukkan untuk stasiun mana pun di Indonesia melalui Dashboard. Untuk analisis GIS otomatis, gunakan koneksi internet aktif. Data Open-Meteo bersifat reanalisis/model, bukan data pengamatan langsung BMKG.

### 6. Perbaikan kestabilan aplikasi
- Key widget dipisahkan dari key penyimpanan hasil analisis.
- Hasil analisis frekuensi disimpan dalam `freq_result`, bukan mengubah `freq_station_widget`.
- Database dibuat otomatis saat aplikasi pertama dijalankan.
- Kesalahan impor data dan perhitungan ditangani dengan pesan yang lebih jelas.
""")

st.caption("HYDOVA · Academic project · Hydrological Data & Observation Intelligence Platform")
