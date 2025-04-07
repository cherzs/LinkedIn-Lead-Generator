import requests
import os
import logging
from dotenv import load_dotenv
import re

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class EmailValidator:
    """
    Kelas untuk validasi email menggunakan Hunter.io API
    """
    def __init__(self):
        """
        Inisialisasi validator email
        """
        self.api_key = os.getenv('HUNTER_API_KEY')
        
        if not self.api_key:
            logger.warning("HUNTER_API_KEY tidak ditemukan di .env - validasi akan dibatasi")
    
    def is_valid_email_format(self, email):
        """
        Validasi format email menggunakan regex
        
        Args:
            email (str): Alamat email untuk divalidasi
            
        Returns:
            bool: True jika format email valid, False jika tidak
        """
        if not email:
            return False
            
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))
    
    def guess_email(self, name, domain):
        """
        Mencoba menebak alamat email berdasarkan nama dan domain
        
        Args:
            name (str): Nama lengkap
            domain (str): Domain email
            
        Returns:
            list: Daftar kemungkinan alamat email
        """
        if not name or not domain:
            return []
            
        # Bersihkan domain
        domain = domain.lower().strip()
        if domain.startswith('www.'):
            domain = domain[4:]
            
        # Pisahkan nama menjadi first name dan last name
        name_parts = name.strip().split()
        if len(name_parts) < 2:
            return []
            
        first_name = name_parts[0].lower()
        last_name = name_parts[-1].lower()
        
        # Buat daftar format email umum
        email_formats = [
            f"{first_name}@{domain}",
            f"{last_name}@{domain}",
            f"{first_name}.{last_name}@{domain}",
            f"{first_name[0]}{last_name}@{domain}",
            f"{first_name}{last_name[0]}@{domain}",
            f"{first_name}-{last_name}@{domain}",
            f"{first_name}_{last_name}@{domain}",
            f"{first_name}{last_name}@{domain}"
        ]
        
        return email_formats
    
    def validate_with_hunter(self, email):
        """
        Validasi email menggunakan Hunter.io API
        
        Args:
            email (str): Alamat email untuk divalidasi
            
        Returns:
            dict: Hasil validasi email
        """
        if not self.api_key:
            logger.warning("HUNTER_API_KEY tidak ditemukan - tidak dapat memvalidasi dengan Hunter")
            return {
                "valid": self.is_valid_email_format(email),
                "score": 0,
                "source": "format_check_only"
            }
            
        try:
            logger.info(f"Memvalidasi email {email} dengan Hunter.io API")
            url = f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={self.api_key}"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json().get('data', {})
                result = {
                    "valid": data.get('result', '') == 'deliverable',
                    "score": data.get('score', 0),
                    "source": "hunter_api"
                }
                logger.info(f"Hasil validasi {email}: {result}")
                return result
            else:
                logger.error(f"Error saat validasi email dengan Hunter: {response.status_code}")
                return {
                    "valid": self.is_valid_email_format(email),
                    "score": 0,
                    "source": "format_check_fallback"
                }
                
        except Exception as e:
            logger.error(f"Exception saat validasi email dengan Hunter: {e}")
            return {
                "valid": self.is_valid_email_format(email),
                "score": 0,
                "source": "format_check_fallback"
            }
    
    def validate_emails(self, emails):
        """
        Validasi daftar email
        
        Args:
            emails (list): Daftar alamat email untuk divalidasi
            
        Returns:
            dict: Hasil validasi untuk setiap email
        """
        results = {}
        
        for email in emails:
            if not email:
                continue
                
            email = email.strip().lower()
            results[email] = self.validate_with_hunter(email)
            
        return results
    
    def find_company_domain(self, company_name):
        """
        Mencari domain perusahaan menggunakan Hunter.io API
        
        Args:
            company_name (str): Nama perusahaan
            
        Returns:
            str: Domain perusahaan
        """
        if not self.api_key or not company_name:
            return None
            
        try:
            logger.info(f"Mencari domain untuk perusahaan {company_name}")
            url = f"https://api.hunter.io/v2/domain-search?company={company_name}&api_key={self.api_key}"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json().get('data', {})
                domain = data.get('domain')
                logger.info(f"Domain untuk {company_name}: {domain}")
                return domain
            else:
                logger.error(f"Error saat mencari domain perusahaan: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Exception saat mencari domain perusahaan: {e}")
            return None

    def enrich_profile_with_email(self, profile_data):
        """
        Memperkaya data profil dengan email yang valid
        
        Args:
            profile_data (dict): Data profil (harus berisi name dan company)
            
        Returns:
            dict: Data profil yang diperkaya
        """
        # Jika sudah ada email, validasi saja
        if profile_data.get('email'):
            validation_result = self.validate_with_hunter(profile_data['email'])
            profile_data['email_valid'] = validation_result['valid']
            profile_data['email_score'] = validation_result['score']
            return profile_data
            
        # Jika tidak ada email, coba temukan
        if profile_data.get('name') and profile_data.get('company'):
            # Coba temukan domain perusahaan
            company_domain = self.find_company_domain(profile_data['company'])
            
            if company_domain:
                # Tebak kemungkinan email
                possible_emails = self.guess_email(profile_data['name'], company_domain)
                
                # Validasi setiap email yang ditebak
                valid_emails = []
                for email in possible_emails:
                    validation_result = self.validate_with_hunter(email)
                    if validation_result['valid']:
                        valid_emails.append({
                            'email': email,
                            'score': validation_result['score']
                        })
                
                # Urutkan berdasarkan skor
                valid_emails.sort(key=lambda x: x['score'], reverse=True)
                
                # Ambil email dengan skor tertinggi
                if valid_emails:
                    profile_data['email'] = valid_emails[0]['email']
                    profile_data['email_valid'] = True
                    profile_data['email_score'] = valid_emails[0]['score']
                    profile_data['alternative_emails'] = [e['email'] for e in valid_emails[1:3]]  # Simpan 2 alternatif terbaik
        
        return profile_data


# Contoh penggunaan
if __name__ == "__main__":
    validator = EmailValidator()
    
    # Contoh validasi email
    test_email = "john.doe@gmail.com"
    result = validator.validate_with_hunter(test_email)
    print(f"Hasil validasi {test_email}: {result}")
    
    # Contoh memperkaya profil
    test_profile = {
        "name": "John Doe",
        "company": "Google",
        "email": ""
    }
    
    enriched_profile = validator.enrich_profile_with_email(test_profile)
    print(f"Profil yang diperkaya: {enriched_profile}") 