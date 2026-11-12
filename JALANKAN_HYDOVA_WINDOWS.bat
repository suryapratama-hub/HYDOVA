@echo off
setlocal
cd /d "%~dp0"
title HYDOVA - Hydrological Intelligence

where py >nul 2>nul
if errorlevel 1 (
  echo Python tidak ditemukan. Instal Python 3.11 dari https://www.python.org/downloads/windows/
  echo Centang pilihan Add Python to PATH saat instalasi.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Membuat lingkungan Python HYDOVA...
  py -3.11 -m venv .venv
  if errorlevel 1 goto :error
)

echo Memeriksa paket HYDOVA...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo Menjalankan HYDOVA...
start "HYDOVA Server" /min cmd /c "cd /d "%~dp0" ^&^& .venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501"
timeout /t 5 /nobreak >nul

where msedge >nul 2>nul
if not errorlevel 1 (
  start "" msedge --app=http://localhost:8501
) else (
  start "" http://localhost:8501
)
echo.
echo HYDOVA berjalan di http://localhost:8501
 echo Tutup jendela server HYDOVA untuk menghentikan aplikasi.
exit /b 0

:error
echo.
echo Instalasi atau proses menjalankan HYDOVA gagal.
echo Untuk masalah paket GIS, lihat bagian instalasi Conda pada README.md.
pause
exit /b 1
