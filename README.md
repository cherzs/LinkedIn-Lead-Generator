# LinkedIn Lead Generator

Alat untuk mengumpulkan dan memvalidasi data kontak dari LinkedIn untuk tujuan Lead Generation.

## Fitur

- **Web Scraping Berbasis HTTP**: Mengekstrak profil pengguna dari LinkedIn menggunakan teknik scraping ringan tanpa perlu browser.
- **Validasi Email**: Memvalidasi alamat email yang ditemukan dan memperkirakan alamat email potensial menggunakan Hunter.io API.
- **Ekspor Data**: Ekspor hasil ke Google Sheets atau CSV untuk integrasi mudah dengan alur kerja bisnis.

## Persiapan

### Prasyarat

- Python 3.8 atau lebih baru
- Akun LinkedIn (opsional)
- API Key dari Hunter.io (opsional, untuk validasi email)
- Kredensial Google Sheets API (opsional, untuk ekspor ke Google Sheets)

### Instalasi

1. Clone repositori ini:
   ```
   git clone https://github.com/username/linkedin-lead-generator.git
   cd linkedin-lead-generator
   ```

2. Instal dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Siapkan file konfigurasi:
   - Duplikat file `.env.example` menjadi `.env`
   - Edit `.env` dengan kredensial dan konfigurasi Anda

### Konfigurasi

1. **Kredensial LinkedIn** (opsional):
   - Tambahkan username dan password LinkedIn Anda di file `.env`:
     ```
     LINKEDIN_USERNAME=youremail@gmail.com
     LINKEDIN_PASSWORD=yourpassword
     ```
   - Catatan: Versi saat ini menggunakan pencarian Google untuk menemukan profil LinkedIn tanpa login.

2. **API Key Hunter.io** (opsional, untuk validasi email):
   - Daftar akun di [Hunter.io](https://hunter.io/)
   - Dapatkan API key dan tambahkan ke file `.env`:
     ```
     HUNTER_API_KEY=your_hunter_api_key
     ```

3. **Kredensial Google Sheets API** (opsional, untuk ekspor ke Google Sheets):
   - Ikuti [petunjuk resmi Google](https://developers.google.com/sheets/api/quickstart/python) untuk membuat kredensial
   - Simpan file kredensial sebagai `credentials.json` di direktori utama proyek
   - Tambahkan ID spreadsheet ke file `.env`:
     ```
     GOOGLE_SHEETS_ID=your_google_sheets_id
     ```

## Penggunaan

### Perintah Dasar

```bash
python app.py --search "software engineer jakarta" --count 10
```

### Opsi-opsi Perintah

- `--search`: Query pencarian LinkedIn (wajib)
- `--count`: Jumlah profil yang akan diambil (default: 10)
- `--validate`: Validasi email yang ditemukan menggunakan Hunter.io
- `--export-sheets`: Ekspor hasil ke Google Sheets
- `--export-csv`: Ekspor hasil ke file CSV
- `--output`: Nama file output untuk CSV (default: leads_export.csv)

### Contoh

1. Cari 20 profil dan validasi email:
   ```bash
   python app.py --search "product manager jakarta" --count 20 --validate
   ```

2. Cari 10 profil dan ekspor ke CSV:
   ```bash
   python app.py --search "data scientist jakarta" --count 10 --export-csv --output data_scientists.csv
   ```

3. Cari 15 profil, validasi email, dan ekspor ke Google Sheets:
   ```bash
   python app.py --search "marketing manager jakarta" --count 15 --validate --export-sheets
   ```

## Pertimbangan Etika dan Hukum

- Gunakan alat ini dengan bijak dan patuhi Ketentuan Layanan situs yang di-scrape
- Pastikan untuk memberikan jeda waktu antar permintaan untuk menghindari pembatasan atau pemblokiran
- Simpan data yang dikumpulkan sesuai dengan peraturan privasi data (GDPR, dll.)
- Hanya gunakan alat ini untuk keperluan bisnis yang sah

## Pemecahan Masalah

### Masalah Rate Limiting

Jika Anda melihat error terkait pembatasan permintaan:

1. Kurangi jumlah profil yang dicari dengan opsi `--count`
2. Tingkatkan waktu jeda antara permintaan dengan mengedit nilai random di file `linkedinscraper.py`
3. Gunakan proxy atau VPN untuk menghindari pembatasan IP (tidak disediakan dalam alat ini)

### Akurasi Data

Data yang diekstrak dari halaman publik LinkedIn mungkin kurang lengkap dibandingkan profil lengkap:

1. Jalankan dengan opsi `--validate` untuk mencoba memperkaya data dengan informasi tambahan
2. Gunakan alat ini sebagai langkah awal untuk pengumpulan lead, dan lakukan validasi manual untuk data kritis

## Lisensi

Proyek ini dilisensikan di bawah lisensi MIT - lihat file [LICENSE](LICENSE) untuk detail. 