# HYDOVA
**Hydrological Data & Observation Intelligence Platform** — aplikasi akademik Streamlit untuk pengelolaan hujan, analisis frekuensi, estimasi debit metode Rasional, dan pemetaan potensi relatif genangan berbasis DEM.

## Persyaratan
- Windows 10/11, Python 3.10 atau 3.11 (disarankan).
- VS Code.
- Koneksi internet hanya diperlukan untuk instalasi paket / basemap peta.

## Instalasi Windows (PowerShell)
```powershell
cd HYDOVA
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```
Jika PowerShell memblokir aktivasi:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```
Buka URL lokal yang ditampilkan Streamlit (umumnya http://localhost:8501).

### Catatan instalasi GIS di Windows
Rasterio/GeoPandas memiliki dependensi native. Jika instalasi pip gagal, gunakan environment conda-forge:
```powershell
conda create -n hydova python=3.11 -y
conda activate hydova
conda install -c conda-forge streamlit pandas numpy scipy matplotlib openpyxl rasterio geopandas shapely pyproj folium streamlit-folium -y
streamlit run app.py
```

## Struktur proyek
```text
HYDOVA/
├── app.py
├── requirements.txt
├── README.md
├── data/
│   └── hydova.sqlite       # dibuat otomatis
├── modules/
│   ├── __init__.py
│   ├── database.py
│   ├── rainfall.py
│   ├── frequency.py
│   ├── flood.py
│   └── gis.py
└── outputs/                # disiapkan untuk hasil ekspor lanjutan
```

## Memasukkan data
1. Buka **Data Curah Hujan → Input manual** atau **Impor file**.
2. Excel/CSV minimal berisi `date`, `station`, `rainfall_mm`. Alias yang diterima antara lain `tanggal`, `stasiun`, `wilayah`, `curah hujan`, `hujan_mm`.
3. Tanggal harus dapat dibaca Pandas; hujan harus numerik dan tidak negatif.
4. Data disimpan ke SQLite lokal `data/hydova.sqlite`; impor tanggal-stasiun yang sama memperbarui nilainya.
5. Edit/hapus per ID dan reset tersedia di tab Kelola data.

Contoh CSV:
```csv
date,station,rainfall_mm
2020-01-01,Magelang,12.5
2020-01-02,Magelang,0
2020-01-03,Magelang,34
```

## GIS
- DEM: GeoTIFF satu band, CRS terdefinisi.
- Batas: GeoJSON atau ZIP Shapefile (ZIP harus memuat `.shp`, `.shx`, `.dbf`, `.prj`).
- Sungai opsional: GeoJSON atau ZIP Shapefile.
- Batas wilayah diproyeksikan ke CRS metrik (UTM estimasi) bila sumber geografis. DEM direproyeksi jika CRS berbeda.
- Raster keluaran: kelas 0 NoData, 1 rendah, 2 sedang, 3 tinggi.

## Metode dan batasan
- Maksimum tahunan: maksimum observasi harian per tahun kalender dan stasiun terpilih.
- Distribusi frekuensi: Normal, Log Normal, Gumbel, Log Pearson III. Minimal 5 tahun untuk komputasi; disarankan setidaknya 10–30 tahun.
- K-S dan Chi-Square disajikan sebagai pemeriksaan indikatif. K-S p-value biasa tidak dikoreksi untuk parameter yang diestimasi; Chi-Square memerlukan kelas dengan frekuensi harapan memadai dan derajat bebas yang benar.
- Rasional: `Q = 0.278 C I A`, dengan Q m³/s, C tanpa satuan, I mm/jam, A km². Aplikasi memakai `I = R_T / durasi` sebagai pendekatan sederhana, bukan IDF.
- Peta GIS adalah **potensi relatif**, bukan kedalaman/luas genangan aktual. Indeks menggabungkan posisi elevasi relatif, kemiringan, hujan rencana, C, dan durasi. Tidak ada simulasi aliran 2D. Untuk hasil hidraulik gunakan HEC-RAS 2D dengan terrain, mesh, boundary hydrograph, Manning n, kondisi batas, dan kalibrasi.

## Pengujian fitur
1. Input satu baris hujan manual dan periksa Dashboard.
2. Impor CSV contoh; uji tanggal tidak valid dan hujan negatif (harus ditolak).
3. Edit dan hapus baris; tutup/buka ulang aplikasi untuk memeriksa persistensi SQLite.
4. Tambahkan minimal 5 tahun observasi harian untuk satu stasiun, lalu jalankan analisis frekuensi.
5. Uji debit dengan luas 10 km², C 0.6, I 50 mm/jam. Hasil teoritis Q = 83.4 m³/s.
6. Unggah DEM dan batas wilayah nyata dengan CRS. Jalankan GIS untuk beberapa periode ulang; bandingkan perubahan hujan rencana dan peta.
7. Unduh GeoTIFF dan buka di QGIS untuk memeriksa CRS, transform, dan kelas raster.

## Sumber data yang disarankan
Gunakan data resmi/berlisensi yang sesuai dari BIG/Ina-Geoportal, BMKG/pos hujan, dan pemerintah daerah. Tidak ada data observasi atau DEM contoh yang direkayasa disertakan.

---

# HYDOVA lintas perangkat: Windows + Android

## A. Membuka seperti aplikasi desktop di Windows

Cara termudah:
1. Ekstrak ZIP ke folder permanen, misalnya `C:\HYDOVA` (jangan jalankan langsung dari dalam ZIP).
2. Instal Python 3.11 64-bit dari https://www.python.org/downloads/windows/ dan centang **Add Python to PATH**.
3. Klik dua kali `JALANKAN_HYDOVA_WINDOWS.bat`.
4. Pada penggunaan pertama, skrip membuat `.venv` dan memasang paket. Proses pertama dapat memerlukan waktu dan koneksi internet.
5. HYDOVA akan terbuka di jendela aplikasi Microsoft Edge jika tersedia; jika tidak, dibuka di browser default.

Untuk membuka tanpa jendela terminal, klik dua kali `BUKA_HYDOVA.vbs`. Untuk membuat ikon desktop: klik kanan `BUKA_HYDOVA.vbs` → **Show more options** → **Create shortcut**, lalu pindahkan shortcut ke Desktop. Ubah nama shortcut menjadi HYDOVA.

Jika paket GIS gagal dipasang melalui pip, ikuti petunjuk Conda-forge pada bagian instalasi di atas. Komponen GIS (Rasterio/GeoPandas) cukup berat.

## B. Mengakses melalui browser di Windows dan Android

HYDOVA adalah aplikasi web responsif. Setelah dipublikasikan ke hosting, buka alamat HTTPS dari Chrome/Edge pada Windows atau Android. Di Android, pilih menu browser **Tambahkan ke layar utama** / **Install app** jika opsi tersebut tersedia. Ikon pintasan akan muncul seperti aplikasi. Koneksi internet diperlukan untuk akses ke server.

### Publikasi ke Streamlit Community Cloud

1. Buat akun GitHub dan buat repository baru bernama `hydova`.
2. Unggah seluruh isi folder proyek HYDOVA ke repository (jangan unggah `.venv`, file database pribadi, atau `secrets.toml`).
3. Buka https://share.streamlit.io/ dan masuk dengan GitHub.
4. Pilih **Create app**, repository `hydova`, branch `main`, dan file utama `app.py`.
5. Deploy. Setelah selesai, platform memberikan URL HTTPS yang bisa dibuka di Windows dan Android.

**Penting tentang penyimpanan data web:** filesystem dan SQLite pada hosting gratis dapat bersifat sementara/terhapus saat aplikasi dibangun ulang atau tidur. Jangan mengandalkan SQLite lokal di hosting sebagai arsip permanen atau database multi-pengguna. Untuk pemakaian web jangka panjang, arahkan `HYDOVA_DB_PATH` ke volume persisten yang disediakan hosting, atau migrasikan database ke PostgreSQL terkelola. Data desktop tetap tersimpan lokal pada komputer.

## C. Cara akses dari HP saat laptop menjadi server lokal (opsional)

HP dan laptop harus berada pada jaringan Wi-Fi yang sama. Untuk penggunaan LAN, ubah alamat server pada skrip menjadi `0.0.0.0` (bukan `127.0.0.1`), izinkan Python pada Windows Firewall untuk jaringan privat, lalu buka `http://IP-LOKAL-LAPTOP:8501` dari browser HP. Gunakan hanya pada jaringan tepercaya; jangan membuka port ini langsung ke internet.

## Catatan kompatibilitas

- Windows: mode desktop lokal menggunakan browser Edge sebagai jendela aplikasi; launcher disediakan, tetapi file `.exe` native mandiri belum dibundel. Paket GIS memerlukan dependensi native sehingga proses bundling executable perlu diuji khusus pada komputer target.
- Android: didukung melalui browser web responsif dan pintasan layar utama; bukan APK native. Tidak perlu memasang Python di Android.
- Web dan desktop memakai kode analisis yang sama. Database lokal desktop dan database server web terpisah kecuali dikonfigurasi memakai backend penyimpanan bersama.
