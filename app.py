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
