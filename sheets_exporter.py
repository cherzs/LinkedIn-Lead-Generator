import os
import logging
import pandas as pd
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account
from gspread_dataframe import set_with_dataframe
import time

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class SheetsExporter:
    """
    Kelas untuk mengekspor data ke Google Sheets
    """
    def __init__(self, credentials_file='credentials.json'):
        """
        Inisialisasi exporter Google Sheets
        
        Args:
            credentials_file (str): Path ke file credentials JSON
        """
        self.credentials_file = credentials_file
        self.sheet_id = os.getenv('GOOGLE_SHEETS_ID')
        
        # Cek apakah file kredensial ada
        if not os.path.exists(credentials_file):
            logger.warning(f"File kredensial {credentials_file} tidak ditemukan")
            logger.info("Untuk mengaktifkan ekspor ke Sheets, ikuti petunjuk di README untuk menyiapkan API Google Sheets")
        
        if not self.sheet_id:
            logger.warning("GOOGLE_SHEETS_ID tidak ditemukan di .env")
    
    def authenticate(self):
        """
        Autentikasi ke Google Sheets API
        
        Returns:
            gspread.Client: Klien gspread yang sudah diautentikasi
        """
        try:
            # Definisikan scope yang diperlukan
            scope = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Autentikasi menggunakan service account
            credentials = Credentials.from_service_account_file(
                self.credentials_file, 
                scopes=scope
            )
            
            # Buat klien gspread
            client = gspread.authorize(credentials)
            logger.info("Autentikasi ke Google Sheets berhasil")
            return client
            
        except Exception as e:
            logger.error(f"Error saat autentikasi ke Google Sheets: {e}")
            return None
    
    def export_profiles(self, profile_data_list, worksheet_name='Leads'):
        """
        Ekspor data profil ke Google Sheets
        
        Args:
            profile_data_list (list): Daftar data profil
            worksheet_name (str): Nama worksheet
            
        Returns:
            bool: True jika ekspor berhasil, False jika gagal
        """
        if not profile_data_list:
            logger.warning("Tidak ada data profil untuk diekspor")
            return False
            
        if not os.path.exists(self.credentials_file) or not self.sheet_id:
            logger.error("File kredensial atau ID spreadsheet tidak ada")
            return False
            
        try:
            client = self.authenticate()
            if not client:
                return False
                
            # Buka spreadsheet
            spreadsheet = client.open_by_key(self.sheet_id)
            
            # Cek apakah worksheet ada, jika tidak, buat baru
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
                logger.info(f"Menggunakan worksheet yang sudah ada: {worksheet_name}")
            except gspread.exceptions.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=20)
                logger.info(f"Membuat worksheet baru: {worksheet_name}")
            
            # Konversi data ke DataFrame
            df = pd.DataFrame(profile_data_list)
            
            # Normalisasi kolom - pastikan semua profil memiliki kolom yang sama
            all_columns = set()
            for profile in profile_data_list:
                all_columns.update(profile.keys())
            
            for profile in profile_data_list:
                for column in all_columns:
                    if column not in profile:
                        profile[column] = ""
            
            # Urutkan kolom untuk konsistensi
            columns = sorted(list(all_columns))
            
            # Prioritaskan kolom penting untuk tampil lebih dulu
            important_columns = ['name', 'title', 'company', 'location', 'email', 'email_valid', 'email_score', 'profile_url']
            for col in reversed(important_columns):
                if col in columns:
                    columns.remove(col)
                    columns.insert(0, col)
            
            # Buat DataFrame baru dengan kolom yang diurutkan
            df = pd.DataFrame(profile_data_list, columns=columns)
            
            # Hapus data yang sudah ada di worksheet
            worksheet.clear()
            
            # Ekspor DataFrame ke worksheet
            set_with_dataframe(worksheet, df)
            
            # Format header
            header_format = {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
            }
            
            # Format header
            header_cells = f"A1:{chr(65 + len(columns) - 1)}1"
            worksheet.format(header_cells, {"textFormat": {"bold": True}})
            
            # Auto-resize kolom (tidak tersedia di API, harus dilakukan secara manual)
            
            logger.info(f"Berhasil mengekspor {len(profile_data_list)} profil ke Google Sheets")
            
            # Return URL ke spreadsheet
            return True
            
        except Exception as e:
            logger.error(f"Error saat mengekspor ke Google Sheets: {e}")
            return False
    
    def get_spreadsheet_url(self):
        """
        Mendapatkan URL spreadsheet
        
        Returns:
            str: URL spreadsheet
        """
        return f"https://docs.google.com/spreadsheets/d/{self.sheet_id}"

    def export_to_csv(self, profile_data_list, filename='leads_export.csv'):
        """
        Ekspor data profil ke file CSV
        
        Args:
            profile_data_list (list): Daftar data profil
            filename (str): Nama file CSV
            
        Returns:
            bool: True jika ekspor berhasil, False jika gagal
        """
        if not profile_data_list:
            logger.warning("Tidak ada data profil untuk diekspor")
            return False
            
        try:
            # Konversi data ke DataFrame
            df = pd.DataFrame(profile_data_list)
            
            # Normalisasi kolom - pastikan semua profil memiliki kolom yang sama
            all_columns = set()
            for profile in profile_data_list:
                all_columns.update(profile.keys())
            
            for profile in profile_data_list:
                for column in all_columns:
                    if column not in profile:
                        profile[column] = ""
            
            # Urutkan kolom untuk konsistensi
            columns = sorted(list(all_columns))
            
            # Prioritaskan kolom penting untuk tampil lebih dulu
            important_columns = ['name', 'title', 'company', 'location', 'email', 'email_valid', 'email_score', 'profile_url']
            for col in reversed(important_columns):
                if col in columns:
                    columns.remove(col)
                    columns.insert(0, col)
            
            # Buat DataFrame baru dengan kolom yang diurutkan
            df = pd.DataFrame(profile_data_list, columns=columns)
            
            # Ekspor ke CSV
            df.to_csv(filename, index=False)
            
            logger.info(f"Berhasil mengekspor {len(profile_data_list)} profil ke {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saat mengekspor ke CSV: {e}")
            return False


# Contoh penggunaan
if __name__ == "__main__":
    # Contoh data profil
    test_profiles = [
        {
            "name": "John Doe",
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco, CA",
            "email": "john.doe@gmail.com",
            "email_valid": True,
            "profile_url": "https://linkedin.com/in/johndoe"
        },
        {
            "name": "Jane Smith",
            "title": "Data Scientist",
            "company": "Microsoft",
            "location": "Seattle, WA",
            "email": "jane.smith@microsoft.com",
            "email_valid": True,
            "profile_url": "https://linkedin.com/in/janesmith"
        }
    ]
    
    # Ekspor ke CSV
    exporter = SheetsExporter()
    exporter.export_to_csv(test_profiles) 