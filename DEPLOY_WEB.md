# Panduan deploy HYDOVA ke web

1. Buat repository GitHub dan unggah file proyek.
2. Pastikan `app.py`, `requirements.txt`, `modules/`, dan `.streamlit/config.toml` ada di root repository.
3. Buka https://share.streamlit.io/, pilih repository, branch, dan `app.py`.
4. Klik Deploy dan tunggu build selesai. Salin URL HTTPS yang diberikan.
5. Uji dari laptop dan Android, termasuk impor data dan unggah berkas GIS.

## Data dan privasi

Jangan unggah data observasi yang bersifat rahasia ke repository publik. Database SQLite lokal tidak otomatis tersinkron ke hosting. Penyimpanan web permanen memerlukan volume persisten atau database eksternal; atur variabel lingkungan `HYDOVA_DB_PATH` jika menggunakan volume file persisten. Batasi akses aplikasi jika data bukan untuk publik.

## Keterbatasan hosting

Paket GIS memakai pustaka native dan dapat membutuhkan penyesuaian dependensi pada hosting. Uji impor GeoTIFF dan Shapefile pada aplikasi yang sudah dideploy. Aplikasi tidak melakukan simulasi hidraulik HEC-RAS 2D.
