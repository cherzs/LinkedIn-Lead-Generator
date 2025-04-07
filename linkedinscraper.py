import requests
from bs4 import BeautifulSoup
import time
import os
import random
import logging
import re
from dotenv import load_dotenv

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class LinkedInScraper:
    """
    Kelas untuk scraping data dari LinkedIn menggunakan HTTP requests
    """
    def __init__(self):
        """
        Inisialisasi scraper LinkedIn
        """
        self.username = os.getenv('LINKEDIN_USERNAME')
        self.password = os.getenv('LINKEDIN_PASSWORD')
        self.session = requests.Session()
        self.logged_in = False
        
        # Set daftar User-Agent untuk rotasi
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
        ]
        
        # Rotate user agent
        self.rotate_user_agent()

    def rotate_user_agent(self):
        """
        Rotate user agent for requests
        """
        user_agent = random.choice(self.user_agents)
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })
        logger.info(f"User-Agent diatur ke: {user_agent}")

    def login(self):
        """
        Catatan: LinkedIn memerlukan JavaScript untuk login, 
        sehingga login berbasis requests sederhana tidak akan berfungsi dengan baik.
        Ini adalah contoh implementasi, tetapi untuk produksi mungkin memerlukan pendekatan lain.
        """
        logger.warning("LinkedIn memerlukan JavaScript untuk login. Sebaiknya gunakan API mereka atau cookie yang sudah login.")
        logger.info("Menggunakan pendekatan alternatif untuk pengumpulan data publik tanpa login")
        
        # Set status bahwa kita tidak login
        self.logged_in = False
        return False

    def search_people(self, search_query, number_of_results=10):
        """
        Mencari profil orang di LinkedIn menggunakan web publik
        
        Args:
            search_query (str): Query pencarian
            number_of_results (int): Jumlah hasil yang diinginkan
            
        Returns:
            list: Daftar URL profil yang ditemukan
        """
        # Karena kita tidak dapat melakukan pencarian langsung tanpa login,
        # kita gunakan pendekatan alternatif dengan Google search
        logger.info(f"Mencari profil dengan query: {search_query} (menggunakan Google)")
        
        # Format query untuk Google search untuk LinkedIn profiles
        google_query = f"site:linkedin.com/in/ {search_query}"
        url = f"https://www.google.com/search?q={google_query.replace(' ', '+')}&num=100"
        
        try:
            # Rotate user agent sebelum request
            self.rotate_user_agent()
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Error saat mencari di Google: status code {response.status_code}")
                # Coba cara alternatif
                return self.search_people_alternative(search_query, number_of_results)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ekstrak hasil pencarian dari Google
            profile_urls = []
            
            # Cari semua link hasil pencarian
            search_results = soup.find_all('a')
            
            for link in search_results:
                href = link.get('href', '')
                
                # Cari URL LinkedIn profile di hasil Google
                if '/url?q=' in href and 'linkedin.com/in/' in href:
                    # Ekstrak URL LinkedIn dari parameter Google
                    start_idx = href.find('/url?q=') + 7
                    end_idx = href.find('&', start_idx)
                    
                    if end_idx > start_idx:
                        profile_url = href[start_idx:end_idx]
                        
                        # Pastikan ini adalah URL profil LinkedIn
                        if 'linkedin.com/in/' in profile_url and profile_url not in profile_urls:
                            # Ambil URL profil murni tanpa parameter
                            clean_url = profile_url.split('?')[0]
                            profile_urls.append(clean_url)
                            
                            if len(profile_urls) >= number_of_results:
                                break
            
            # Terkadang kita perlu memeriksa apakah ini benar-benar URL profil LinkedIn
            filtered_profile_urls = []
            for url in profile_urls:
                if 'linkedin.com/in/' in url and '/pub/' not in url:
                    filtered_profile_urls.append(url)
            
            logger.info(f"Berhasil menemukan {len(filtered_profile_urls)} profil dengan Google search")
            
            # Jika tidak menemukan profil yang cukup, coba cara alternatif untuk mendapatkan lebih banyak
            if len(filtered_profile_urls) < number_of_results:
                logger.warning(f"Hanya menemukan {len(filtered_profile_urls)} profil dengan Google search, mencoba cara alternatif...")
                alternative_urls = self.search_people_alternative(search_query, number_of_results - len(filtered_profile_urls))
                
                # Gabungkan hasil dan hilangkan duplikat
                for alt_url in alternative_urls:
                    if alt_url not in filtered_profile_urls:
                        filtered_profile_urls.append(alt_url)
                        
                        if len(filtered_profile_urls) >= number_of_results:
                            break
            
            return filtered_profile_urls[:number_of_results]
            
        except Exception as e:
            logger.error(f"Error saat mencari profil: {e}")
            # Coba cara alternatif
            return self.search_people_alternative(search_query, number_of_results)
    
    def search_people_alternative(self, search_query, number_of_results=10):
        """
        Cara alternatif untuk mencari profil orang jika Google search gagal
        """
        logger.info(f"Mencari profil dengan cara alternatif untuk query: {search_query}")
        
        try:
            # Coba dengan pendekatan pencarian langsung LinkedIn
            # Encode query untuk URL
            encoded_query = search_query.replace(' ', '%20')
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={encoded_query}"
            
            logger.info(f"Mengakses URL pencarian LinkedIn: {search_url}")
            
            # Delay untuk menghindari rate limit
            time.sleep(random.uniform(2, 4))
            
            # Rotate user agent
            self.rotate_user_agent()
            
            # Akses halaman pencarian LinkedIn
            response = self.session.get(search_url, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Error saat mengakses halaman pencarian: status code {response.status_code}")
                
                # Coba pendekatan terakhir - cari dengan query yang lebih spesifik
                return self.search_with_bing(search_query, number_of_results)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Cari elemen yang berisi link profil
            profile_links = []
            search_results = soup.find_all('a')
            
            for link in search_results:
                href = link.get('href', '')
                if '/in/' in href and href.startswith('https://www.linkedin.com/in/') and href not in profile_links:
                    profile_links.append(href)
                    if len(profile_links) >= number_of_results:
                        break
            
            logger.info(f"Ditemukan {len(profile_links)} profil dari pencarian alternatif LinkedIn")
            
            # Jika masih belum menemukan profil, coba dengan Bing
            if len(profile_links) < number_of_results:
                logger.warning("Hasil dari LinkedIn terbatas, mencoba dengan Bing search...")
                bing_results = self.search_with_bing(search_query, number_of_results - len(profile_links))
                
                # Gabungkan hasil dan hilangkan duplikat
                for result in bing_results:
                    if result not in profile_links:
                        profile_links.append(result)
                        
                        if len(profile_links) >= number_of_results:
                            break
            
            return profile_links
            
        except Exception as e:
            logger.error(f"Error saat pencarian alternatif: {e}")
            # Coba pendekatan terakhir dengan Bing
            return self.search_with_bing(search_query, number_of_results)

    def search_with_bing(self, search_query, number_of_results=10):
        """
        Mencoba mencari profil LinkedIn menggunakan Bing search sebagai upaya terakhir
        """
        logger.info(f"Mencari profil LinkedIn dengan Bing search: {search_query}")
        
        try:
            # Format query untuk Bing search 
            bing_query = f"site:linkedin.com/in/ {search_query}"
            url = f"https://www.bing.com/search?q={bing_query.replace(' ', '+')}&count=100"
            
            # Rotate user agent
            self.rotate_user_agent()
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Error saat mengakses Bing search: status code {response.status_code}")
                return self.search_with_duckduckgo(search_query, number_of_results)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ekstrak hasil pencarian dari Bing
            profile_urls = []
            
            # Cari semua link hasil pencarian
            search_results = soup.find_all('a')
            
            for link in search_results:
                href = link.get('href', '')
                
                # Cari URL LinkedIn profile di hasil Bing
                if href and 'linkedin.com/in/' in href and href.startswith('http'):
                    # Pastikan ini adalah URL profil LinkedIn
                    if href not in profile_urls:
                        # Ambil URL profil murni tanpa parameter
                        clean_url = href.split('?')[0]
                        profile_urls.append(clean_url)
                        
                        if len(profile_urls) >= number_of_results:
                            break
            
            logger.info(f"Ditemukan {len(profile_urls)} profil dari Bing search")
            
            # Jika belum mendapatkan cukup profil, coba dengan DuckDuckGo
            if len(profile_urls) < number_of_results:
                logger.warning(f"Hanya menemukan {len(profile_urls)} profil dengan Bing, mencoba DuckDuckGo...")
                ddg_urls = self.search_with_duckduckgo(search_query, number_of_results - len(profile_urls))
                
                # Gabungkan hasil
                for ddg_url in ddg_urls:
                    if ddg_url not in profile_urls:
                        profile_urls.append(ddg_url)
                        
                        if len(profile_urls) >= number_of_results:
                            break
            
            return profile_urls
            
        except Exception as e:
            logger.error(f"Error saat mencari dengan Bing: {e}")
            return self.search_with_duckduckgo(search_query, number_of_results)
    
    def search_with_duckduckgo(self, search_query, number_of_results=10):
        """
        Mencoba mencari profil LinkedIn menggunakan DuckDuckGo sebagai upaya terakhir
        """
        logger.info(f"Mencari profil LinkedIn dengan DuckDuckGo: {search_query}")
        
        try:
            # Format query untuk DuckDuckGo search
            ddg_query = f"site:linkedin.com/in/ {search_query}"
            url = f"https://html.duckduckgo.com/html/?q={ddg_query.replace(' ', '+')}"
            
            # Rotate user agent
            self.rotate_user_agent()
            
            # DuckDuckGo dapat mendeteksi bot lebih mudah, tambahkan headers khusus
            custom_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://duckduckgo.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
            
            response = self.session.get(url, headers=custom_headers, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Error saat mengakses DuckDuckGo: status code {response.status_code}")
                # Coba metode terakhir - Yahoo
                return self.search_with_yandex(search_query, number_of_results)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ekstrak hasil pencarian dari DuckDuckGo
            profile_urls = []
            
            # DuckDuckGo HTML menggunakan struktur yang berbeda
            search_results = soup.find_all('a', {'class': 'result__a'})
            if not search_results:
                search_results = soup.find_all('a')  # Fallback ke semua link
            
            for link in search_results:
                href = link.get('href', '')
                
                # DuckDuckGo kadang menggunakan URL proxy
                if '/ud/' in href:
                    # Ekstrak URL asli dari parameter
                    href_parts = href.split('/ud/')
                    if len(href_parts) > 1:
                        href = href_parts[1]
                
                # Cari URL LinkedIn profile
                if href and 'linkedin.com/in/' in href:
                    # Pastikan ini adalah URL profil LinkedIn
                    if href not in profile_urls:
                        # Ambil URL profil murni tanpa parameter
                        clean_url = href.split('?')[0]
                        profile_urls.append(clean_url)
                        
                        if len(profile_urls) >= number_of_results:
                            break
            
            logger.info(f"Ditemukan {len(profile_urls)} profil dari DuckDuckGo")
            
            # Jika belum cukup, coba metode pencarian terakhir
            if len(profile_urls) < number_of_results:
                yandex_urls = self.search_with_yandex(search_query, number_of_results - len(profile_urls))
                
                # Gabungkan hasil
                for yandex_url in yandex_urls:
                    if yandex_url not in profile_urls:
                        profile_urls.append(yandex_url)
                        if len(profile_urls) >= number_of_results:
                            break
            
            return profile_urls
            
        except Exception as e:
            logger.error(f"Error saat mencari dengan DuckDuckGo: {e}")
            return self.search_with_yandex(search_query, number_of_results)
    
    def search_with_yandex(self, search_query, number_of_results=10):
        """
        Mencoba mencari profil LinkedIn menggunakan Yandex sebagai upaya pencarian terakhir
        """
        logger.info(f"Mencari profil LinkedIn dengan Yandex: {search_query}")
        
        try:
            # Format query untuk Yandex search
            yandex_query = f"site:linkedin.com/in/ {search_query}"
            url = f"https://yandex.com/search/?text={yandex_query.replace(' ', '+')}"
            
            # Rotate user agent
            self.rotate_user_agent()
            
            response = self.session.get(url, timeout=20)  # Yandex bisa jadi lebih lambat
            
            if response.status_code != 200:
                logger.error(f"Error saat mengakses Yandex: status code {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ekstrak hasil pencarian dari Yandex
            profile_urls = []
            
            # Cari semua link hasil pencarian
            search_results = soup.find_all('a')
            
            for link in search_results:
                href = link.get('href', '')
                
                # Cari URL LinkedIn profile
                if href and 'linkedin.com/in/' in href:
                    # Pastikan ini adalah URL profil LinkedIn
                    if href not in profile_urls:
                        # Ambil URL profil murni tanpa parameter
                        clean_url = href.split('?')[0]
                        profile_urls.append(clean_url)
                        
                        if len(profile_urls) >= number_of_results:
                            break
            
            logger.info(f"Ditemukan {len(profile_urls)} profil dari Yandex")
            return profile_urls
            
        except Exception as e:
            logger.error(f"Error saat mencari dengan Yandex: {e}")
            return []
    
    def scrape_profile(self, profile_url):
        """
        Mengekstrak data dari profil LinkedIn
        
        Args:
            profile_url (str): URL profil LinkedIn
            
        Returns:
            dict: Data profil yang diekstrak
        """
        profile_data = {
            "name": "",
            "title": "",
            "location": "",
            "company": "",
            "email": "",
            "profile_url": profile_url
        }
        
        try:
            logger.info(f"Mengakses profil: {profile_url}")
            
            # Delay untuk menghindari pembatasan rate
            time.sleep(random.uniform(2, 5))
            
            # Rotate user agent sebelum request
            self.rotate_user_agent()
            
            # Akses halaman profil
            response = self.session.get(profile_url, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Error saat mengakses profil: status code {response.status_code}")
                return profile_data
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ekstrak informasi - catatan: dalam kasus tanpa login,
            # kita hanya bisa mengambil informasi publik yang terbatas
            
            # Coba ekstrak nama dari title halaman
            title_tag = soup.find('title')
            if title_tag:
                title_parts = title_tag.text.split('|')
                if len(title_parts) > 0:
                    profile_data["name"] = title_parts[0].strip()
            
            # Coba ekstrak judul/profesi dan perusahaan dari meta tags
            meta_desc = soup.find('meta', {'name': 'description'})
            if meta_desc and 'content' in meta_desc.attrs:
                desc = meta_desc['content']
                
                # Biasanya judul/profesi disebutkan di awal meta description
                if '- ' in desc and profile_data['name'] in desc:
                    # Ambil bagian setelah nama dan sebelum tanda '-' lainnya
                    parts = desc.split(profile_data['name'], 1)[1].strip()
                    if parts.startswith('- '):
                        parts = parts[2:]  # Hapus "- " di awal
                    
                    if ' at ' in parts:
                        title_parts = parts.split(' at ', 1)
                        profile_data["title"] = title_parts[0].strip()
                        profile_data["company"] = title_parts[1].split('|')[0].strip()
                    else:
                        profile_data["title"] = parts.split('|')[0].strip()
                
                # Coba ekstrak lokasi
                if '| ' in desc:
                    location_parts = desc.split('| ')
                    if len(location_parts) > 1:
                        profile_data["location"] = location_parts[-1].strip()
            
            # Coba mencari email dalam konten halaman (pendekatan sederhana)
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            email_matches = re.findall(email_pattern, response.text)
            if email_matches:
                # Filter email yang mungkin tidak terkait dengan profil
                valid_email_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
                company_domain = None
                
                if profile_data["company"]:
                    # Ambil domain dari nama perusahaan (hanya perkiraan sederhana)
                    company_words = profile_data["company"].lower().replace(',', '').replace('.', '').split()
                    company_domain = company_words[0] if company_words else None
                
                for email in email_matches:
                    domain = email.split('@')[1]
                    
                    # Prioritaskan email dengan domain perusahaan
                    if company_domain and company_domain in domain:
                        profile_data["email"] = email
                        break
                    # Atau email dari domain populer
                    elif domain in valid_email_domains and not profile_data["email"]:
                        profile_data["email"] = email
                
                # Jika belum menemukan email yang sesuai, ambil yang pertama
                if not profile_data["email"] and email_matches:
                    profile_data["email"] = email_matches[0]
            
            logger.info(f"Berhasil mengekstrak data profil untuk {profile_data['name']}")
            return profile_data
            
        except Exception as e:
            logger.error(f"Error saat mengekstrak data profil {profile_url}: {e}")
            return profile_data
    
    def run_scraper(self, search_query, number_of_results=10):
        """
        Menjalankan seluruh proses scraping
        
        Args:
            search_query (str): Query pencarian
            number_of_results (int): Jumlah hasil yang diinginkan
            
        Returns:
            list: Daftar data profil yang diekstrak
        """
        results = []
        
        try:
            # Cari profil
            profile_urls = self.search_people(search_query, number_of_results)
            
            if not profile_urls:
                logger.warning("Tidak ada profil yang ditemukan.")
                return results
            
            # Scrape profil satu per satu
            for url in profile_urls:
                # Delay acak antara permintaan untuk menghindari pembatasan rate
                time.sleep(random.uniform(3, 6))
                profile_data = self.scrape_profile(url)
                
                if profile_data["name"]:  # Tambahkan hanya jika berhasil mengambil nama
                    results.append(profile_data)
            
            logger.info(f"Berhasil mengekstrak data untuk {len(results)} profil")
            return results
            
        except Exception as e:
            logger.error(f"Error saat menjalankan scraper: {e}")
            return results

    def search_contacts_by_company(self, company_name, number_of_results=10):
        """
        Mencari kontak email berdasarkan nama perusahaan dari berbagai sumber
        
        Args:
            company_name (str): Nama perusahaan untuk dicari
            number_of_results (int): Jumlah hasil yang diinginkan
            
        Returns:
            list: Daftar data profil dengan email yang ditemukan
        """
        logger.info(f"Mencari kontak email untuk perusahaan: {company_name}")
        
        contact_results = []
        
        try:
            # 1. Cari kontak dari situs web perusahaan
            company_emails = self.scrape_company_website_contacts(company_name)
            
            # 2. Cari kontak dari LinkedIn Company Page
            linkedin_company_emails = self.scrape_linkedin_company_page(company_name)
            
            # 3. Cari dari sumber direktori publik
            directory_emails = self.scrape_email_directories(company_name)
            
            # Gabungkan semua hasil
            all_emails = []
            all_emails.extend(company_emails)
            all_emails.extend(linkedin_company_emails)
            all_emails.extend(directory_emails)
            
            # Hapus duplikat
            unique_emails = []
            for email_data in all_emails:
                if email_data['email'] not in [e.get('email') for e in unique_emails]:
                    unique_emails.append(email_data)
            
            logger.info(f"Total kontak unik yang ditemukan: {len(unique_emails)}")
            
            # Batasi jumlah hasil
            return unique_emails[:number_of_results]
            
        except Exception as e:
            logger.error(f"Error saat mencari kontak perusahaan: {e}")
            return contact_results

    def scrape_company_website_contacts(self, company_name):
        """
        Mencoba menemukan kontak email dari website perusahaan
        
        Args:
            company_name (str): Nama perusahaan
            
        Returns:
            list: Daftar data kontak yang ditemukan
        """
        logger.info(f"Mencari kontak dari website perusahaan: {company_name}")
        
        contact_results = []
        
        try:
            # 1. Temukan domain perusahaan dengan Google search
            search_query = f"{company_name} official website"
            url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
            
            # Rotate user agent
            self.rotate_user_agent()
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Error saat mencari website perusahaan: status code {response.status_code}")
                return contact_results
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Cari semua link hasil pencarian
            company_domain = None
            search_results = soup.find_all('a')
            
            for link in search_results:
                href = link.get('href', '')
                
                # Cari URL yang mungkin domain perusahaan (bukan LinkedIn, FB, dll)
                if '/url?q=' in href:
                    start_idx = href.find('/url?q=') + 7
                    end_idx = href.find('&', start_idx)
                    
                    if end_idx > start_idx:
                        result_url = href[start_idx:end_idx]
                        
                        # Filter URL social media dan hasil pencarian umum
                        if not any(domain in result_url for domain in ['linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com', 'google.com', 'youtube.com']):
                            # Ekstrak domain
                            domain_parts = result_url.split('//')
                            if len(domain_parts) > 1:
                                domain = domain_parts[1].split('/')[0]
                                company_domain = domain
                                logger.info(f"Domain perusahaan yang ditemukan: {company_domain}")
                                break
            
            # Jika domain ditemukan, coba akses halaman contact atau about
            if company_domain:
                contact_pages = [
                    f"https://{company_domain}/contact",
                    f"https://{company_domain}/contact-us",
                    f"https://{company_domain}/about",
                    f"https://{company_domain}/about-us",
                    f"https://{company_domain}/team"
                ]
                
                for page_url in contact_pages:
                    try:
                        # Delay
                        time.sleep(random.uniform(1, 3))
                        
                        # Rotate user agent
                        self.rotate_user_agent()
                        
                        response = self.session.get(page_url, timeout=10)
                        
                        if response.status_code == 200:
                            # Cari pola email dalam halaman
                            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                            email_matches = re.findall(email_pattern, response.text)
                            
                            for email in email_matches:
                                # Filter email yang mungkin tidak valid atau tidak terkait
                                if email.endswith(('.png', '.jpg', '.gif')):
                                    continue
                                    
                                # Jika email berisi domain perusahaan, tambahkan ke hasil
                                contact_data = {
                                    "email": email,
                                    "source": f"website ({page_url})",
                                    "company": company_name,
                                    "domain": company_domain
                                }
                                
                                # Coba ekstrak nama dari email
                                if '@' in email:
                                    username = email.split('@')[0]
                                    if '.' in username:
                                        name_parts = username.split('.')
                                        if len(name_parts) == 2:
                                            contact_data["name"] = f"{name_parts[0].capitalize()} {name_parts[1].capitalize()}"
                                
                                contact_results.append(contact_data)
                                
                    except Exception as e:
                        logger.error(f"Error saat akses {page_url}: {e}")
                        continue
            
            return contact_results
            
        except Exception as e:
            logger.error(f"Error saat mencari kontak website: {e}")
            return contact_results

    def scrape_linkedin_company_page(self, company_name):
        """
        Mencari kontak dari LinkedIn company page
        
        Args:
            company_name (str): Nama perusahaan
            
        Returns:
            list: Daftar data kontak yang ditemukan
        """
        logger.info(f"Mencari kontak dari LinkedIn company page: {company_name}")
        
        contact_results = []
        
        try:
            # Format query untuk Google search untuk LinkedIn company page
            search_query = f"site:linkedin.com/company/ {company_name}"
            url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
            
            # Rotate user agent
            self.rotate_user_agent()
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Error saat mencari LinkedIn company page: status code {response.status_code}")
                return contact_results
            
            # Parse hasil pencarian
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Cari URL LinkedIn company page
            company_url = None
            search_results = soup.find_all('a')
            
            for link in search_results:
                href = link.get('href', '')
                
                if '/url?q=' in href and 'linkedin.com/company/' in href:
                    start_idx = href.find('/url?q=') + 7
                    end_idx = href.find('&', start_idx)
                    
                    if end_idx > start_idx:
                        company_url = href[start_idx:end_idx]
                        logger.info(f"LinkedIn company URL: {company_url}")
                        break
            
            # Jika menemukan URL company, cari orang-orang yang terkait dengan perusahaan
            if company_url:
                # Format query untuk mencari karyawan perusahaan
                employee_search = f"{company_name} site:linkedin.com/in/"
                
                # Reuse metode pencarian profil yang ada
                employee_profiles = self.search_people(employee_search, 10)
                
                # Scrape profil untuk mendapatkan data kontak
                for profile_url in employee_profiles:
                    profile_data = self.scrape_profile(profile_url)
                    
                    if profile_data["name"] and (profile_data.get("email") or profile_data.get("company") == company_name):
                        contact_data = {
                            "name": profile_data["name"],
                            "title": profile_data["title"],
                            "company": company_name,
                            "email": profile_data.get("email", ""),
                            "profile_url": profile_url,
                            "source": "linkedin_company"
                        }
                        contact_results.append(contact_data)
            
            return contact_results
            
        except Exception as e:
            logger.error(f"Error saat mencari kontak LinkedIn company: {e}")
            return contact_results

    def scrape_email_directories(self, company_name):
        """
        Mencari kontak email dari direktori email publik seperti Hunter.io, Email-Format, dll.
        Implementasi ini menggunakan pencarian Google untuk menemukan kontak di situs direktori publik.
        
        Args:
            company_name (str): Nama perusahaan
            
        Returns:
            list: Daftar data kontak yang ditemukan
        """
        logger.info(f"Mencari kontak dari direktori email: {company_name}")
        
        contact_results = []
        
        try:
            # Format query untuk mencari email di direktori
            directories = ["hunter.io", "rocketreach.co", "email-format.com", "skrapp.io"]
            
            for directory in directories:
                # Format query
                search_query = f"site:{directory} {company_name} email"
                url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
                
                # Delay
                time.sleep(random.uniform(2, 4))
                
                # Rotate user agent
                self.rotate_user_agent()
                
                response = self.session.get(url, timeout=15)
                
                if response.status_code != 200:
                    logger.error(f"Error saat mencari di {directory}: status code {response.status_code}")
                    continue
                
                # Parse hasil pencarian
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Cari pola email dalam hasil pencarian
                email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                
                # Cari di semua teks dalam halaman hasil pencarian
                page_text = soup.get_text()
                email_matches = re.findall(email_pattern, page_text)
                
                for email in email_matches:
                    # Verifikasi bahwa email berkaitan dengan perusahaan yang dicari
                    # (biasanya email perusahaan menggunakan domain perusahaan)
                    domain = email.split('@')[1]
                    
                    # Cek apakah ada kata-kata perusahaan di domain
                    company_words = company_name.lower().split()
                    if any(word in domain.lower() for word in company_words if len(word) > 3):
                        contact_data = {
                            "email": email,
                            "company": company_name,
                            "domain": domain,
                            "source": f"directory ({directory})"
                        }
                        
                        # Coba ekstrak nama dari email
                        if '@' in email:
                            username = email.split('@')[0]
                            if '.' in username:
                                name_parts = username.split('.')
                                if len(name_parts) == 2:
                                    contact_data["name"] = f"{name_parts[0].capitalize()} {name_parts[1].capitalize()}"
                        
                        # Tambahkan ke hasil jika belum ada
                        if email not in [c.get('email') for c in contact_results]:
                            contact_results.append(contact_data)
            
            return contact_results
            
        except Exception as e:
            logger.error(f"Error saat mencari kontak di direktori: {e}")
            return contact_results

    def run_contact_scraper(self, search_query, is_company=False, number_of_results=10):
        """
        Menjalankan proses scraping kontak, bisa berdasarkan pencarian umum atau spesifik perusahaan
        
        Args:
            search_query (str): Query pencarian atau nama perusahaan
            is_company (bool): True jika mencari berdasarkan perusahaan, False untuk pencarian umum
            number_of_results (int): Jumlah hasil yang diinginkan
            
        Returns:
            list: Daftar data kontak yang diekstrak
        """
        results = []
        
        try:
            if is_company:
                # Jalankan pencarian berdasarkan perusahaan
                company_results = self.search_contacts_by_company(search_query, number_of_results)
                results.extend(company_results)
            else:
                # Jalankan pencarian biasa (reuse metode yang sudah ada)
                profile_urls = self.search_people(search_query, number_of_results)
                
                if not profile_urls:
                    logger.warning("Tidak ada profil yang ditemukan.")
                    return results
                
                # Scrape profil satu per satu
                for url in profile_urls:
                    # Delay acak antara permintaan untuk menghindari pembatasan rate
                    time.sleep(random.uniform(3, 6))
                    profile_data = self.scrape_profile(url)
                    
                    if profile_data["name"]:  # Tambahkan hanya jika berhasil mengambil nama
                        results.append(profile_data)
            
            logger.info(f"Berhasil mengekstrak data untuk {len(results)} kontak")
            return results
            
        except Exception as e:
            logger.error(f"Error saat menjalankan contact scraper: {e}")
            return results


# Contoh penggunaan
if __name__ == "__main__":
    # Inisialisasi scraper
    scraper = LinkedInScraper()
    
    # Jalankan scraper
    results = scraper.run_scraper("software engineer jakarta", 5)
    
    # Tampilkan hasil
    for profile in results:
        print(f"Nama: {profile['name']}")
        print(f"Jabatan: {profile['title']}")
        print(f"Perusahaan: {profile['company']}")
        print(f"Lokasi: {profile['location']}")
        print(f"Email: {profile['email']}")
        print(f"URL: {profile['profile_url']}")
        print("-" * 50) 