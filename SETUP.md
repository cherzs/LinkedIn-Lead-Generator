# Panduan Setup LinkedIn Lead Generator

Dokumen ini berisi panduan langkah demi langkah untuk mengatur dan menggunakan LinkedIn Lead Generator.

## 1. Instalasi

### 1.1. Prasyarat

Pastikan Anda telah menginstal:
- Python 3.8 atau lebih baru
- Google Chrome
- ChromeDriver yang sesuai dengan versi Chrome Anda

### 1.2. Clone Repositori dan Instal Dependencies

```bash
# Clone repositori
git clone https://github.com/username/linkedin-lead-generator.git
cd linkedin-lead-generator

# Instal dependencies
pip install -r requirements.txt
```

## 2. Konfigurasi

### 2.1. Setup file .env

1. Duplikat file `.env.example` menjadi `.env`:
   ```bash
   # Windows
   copy .env.example .env
   
   # MacOS/Linux
   cp .env.example .env
   ```

2. Edit file `.env` dengan informasi Anda:
   ```
   LINKEDIN_USERNAME=email_linkedin_anda@example.com
   LINKEDIN_PASSWORD=password_linkedin_anda
   CHROME_DRIVER_PATH=C:\\Users\\zhafr\\Downloads\\chromedriver_win32\\chromedriver.exe
   ```

### 2.2. Setup Hunter.io API (Opsional)

Untuk validasi email:

1. Daftar akun di [Hunter.io](https://hunter.io/)
2. Dapatkan API key dari dashboard Hunter.io
3. Tambahkan ke file `.env`:
   ```
   HUNTER_API_KEY=hunter_api_key_anda
   ```

### 2.3. Setup Google Sheets API (Opsional)

Untuk mengekspor data ke Google Sheets:

1. Buka [Google Cloud Console](https://console.cloud.google.com/)
2. Buat project baru
3. Aktifkan Google Sheets API dan Google Drive API
4. Buat Service Account dan download file JSON credentials
5. Simpan file credentials sebagai `credentials.json` di direktori utama proyek
6. Buat spreadsheet baru di Google Sheets dan bagikan dengan email service account
7. Salin ID spreadsheet dari URL dan tambahkan ke file `.env`:
   ```
   GOOGLE_SHEETS_ID=id_spreadsheet_anda
   ```

## 3. Menggunakan Aplikasi

### 3.1. Contoh Perintah Dasar

```bash
# Cari 10 profil Software Engineer di Jakarta
python app.py --search "software engineer jakarta" --count 10
```

### 3.2. Validasi Email

```bash
# Cari dan validasi email
python app.py --search "software engineer jakarta" --count 10 --validate
```

### 3.3. Ekspor Hasil

```bash
# Ekspor ke file CSV
python app.py --search "software engineer jakarta" --count 10 --export-csv --output hasil.csv

# Ekspor ke Google Sheets
python app.py --search "software engineer jakarta" --count 10 --export-sheets
```

### 3.4. Kombinasi Opsi

```bash
# Cari, validasi, dan ekspor ke Google Sheets dan CSV
python app.py --search "software engineer jakarta" --count 10 --validate --export-sheets --export-csv
```

## 4. Pemecahan Masalah

### 4.1. Masalah ChromeDriver

Jika Anda melihat error seperti "session not created: This version of ChromeDriver only supports Chrome version XX":

1. Periksa versi Chrome Anda dengan membuka `chrome://version/` di browser
2. Download versi ChromeDriver yang sesuai dari [situs resmi](https://sites.google.com/chromium.org/driver/)
3. Perbarui path di file `.env`

### 4.2. Masalah Login LinkedIn

Jika aplikasi gagal login ke LinkedIn:

1. Pastikan kredensial di file `.env` benar
2. Edit file `linkedinscraper.py` dan hapus komentar pada baris:
   ```python
   # chrome_options.add_argument("--headless")
   ```
   untuk melihat proses login secara visual dan debug

### 4.3. Rate Limiting

Jika Anda melihat error terkait pembatasan permintaan:

1. Kurangi jumlah profil yang dicari dengan opsi `--count`
2. Tingkatkan waktu jeda antara permintaan dengan mengedit nilai random di file `linkedinscraper.py`

## 5. Tips

- Gunakan query pencarian yang spesifik untuk mendapatkan hasil yang lebih relevan
- Eksperimen dengan pencarian yang berbeda untuk menemukan prospek yang paling sesuai
- LinkedIn membatasi jumlah halaman yang dapat dilihat. Saat menggunakan jumlah `--count` yang besar, semua hasil mungkin tidak dapat diakses
- Nonaktifkan validasi email jika Anda tidak memerlukan informasi email yang tervalidasi
- Ekspor ke Google Sheets sangat berguna untuk kolaborasi tim 