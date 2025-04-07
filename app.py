import os
import logging
import argparse
import time
from dotenv import load_dotenv

from linkedinscraper import LinkedInScraper
from email_validator import EmailValidator
from sheets_exporter import SheetsExporter

# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("leadgen.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def parse_arguments():
    """
    Parse command line arguments
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='LinkedIn Lead Generation Tool')
    
    parser.add_argument('--search', type=str, help='Query pencarian LinkedIn (contoh: "software engineer jakarta")')
    parser.add_argument('--company', type=str, help='Nama perusahaan untuk mencari kontak (contoh: "Google Indonesia")')
    parser.add_argument('--count', type=int, default=10, help='Jumlah profil yang akan diambil (default: 10)')
    parser.add_argument('--validate', action='store_true', help='Validasi email yang ditemukan')
    parser.add_argument('--export-sheets', action='store_true', help='Ekspor hasil ke Google Sheets')
    parser.add_argument('--export-csv', action='store_true', help='Ekspor hasil ke file CSV')
    parser.add_argument('--output', type=str, default='leads_export.csv', help='Nama file output untuk CSV (default: leads_export.csv)')
    
    return parser.parse_args()

def main():
    """
    Fungsi utama program
    """
    # Parse command line arguments
    args = parse_arguments()
    
    # Cek argumen yang diperlukan
    if not args.search and not args.company:
        logger.error("Argumen --search atau --company diperlukan")
        print("Gunakan --search untuk menentukan query pencarian LinkedIn atau --company untuk mencari berdasarkan nama perusahaan")
        return
    
    try:
        # Inisialisasi LinkedIn scraper
        linkedin_scraper = LinkedInScraper()
        
        # Jalankan scraper berdasarkan jenis pencarian
        if args.company:
            logger.info(f"Memulai pencarian kontak untuk perusahaan: {args.company}")
            profile_results = linkedin_scraper.run_contact_scraper(args.company, is_company=True, number_of_results=args.count)
        else:
            logger.info(f"Memulai scraping dengan query: {args.search}")
            profile_results = linkedin_scraper.run_scraper(args.search, args.count)
        
        if not profile_results:
            logger.warning("Tidak ada profil atau kontak yang ditemukan atau terjadi kesalahan")
            return
            
        logger.info(f"Berhasil mendapatkan {len(profile_results)} profil/kontak")
        
        # Validasi dan perkaya data email
        if args.validate:
            logger.info("Memvalidasi email...")
            email_validator = EmailValidator()
            
            for profile in profile_results:
                enriched_profile = email_validator.enrich_profile_with_email(profile)
                profile.update(enriched_profile)
                
            logger.info("Validasi email selesai")
        
        # Ekspor hasil
        if args.export_csv:
            logger.info(f"Mengekspor ke CSV: {args.output}")
            exporter = SheetsExporter()
            if exporter.export_to_csv(profile_results, args.output):
                logger.info(f"Data berhasil diekspor ke {args.output}")
                
        if args.export_sheets:
            logger.info("Mengekspor ke Google Sheets...")
            exporter = SheetsExporter()
            if exporter.export_profiles(profile_results):
                logger.info(f"Data berhasil diekspor ke Google Sheets: {exporter.get_spreadsheet_url()}")
        
        # Tampilkan hasil
        logger.info("Hasil scraping:")
        for i, profile in enumerate(profile_results, 1):
            print(f"\nProfil {i}:")
            print(f"Nama: {profile.get('name', '')}")
            print(f"Jabatan: {profile.get('title', '')}")
            print(f"Perusahaan: {profile.get('company', '')}")
            print(f"Lokasi: {profile.get('location', '')}")
            print(f"Email: {profile.get('email', '')}")
            if 'email_valid' in profile:
                print(f"Email Valid: {'Ya' if profile.get('email_valid') else 'Tidak'}")
            if 'email_score' in profile:
                print(f"Skor Email: {profile.get('email_score', 0)}")
            print(f"URL: {profile.get('profile_url', '')}")
            
        logger.info("Proses selesai")
    
    except KeyboardInterrupt:
        logger.info("Proses dihentikan oleh pengguna")
    except Exception as e:
        logger.error(f"Terjadi kesalahan: {e}")
        raise

if __name__ == "__main__":
    main() 