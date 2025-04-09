#!/usr/bin/env python3
import os
from linkedin_scraper import Person, actions
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import time

# Menggunakan path ChromeDriver yang sudah kita ekstrak
chromedriver_path = os.getenv("CHROMEDRIVER", os.path.join(os.getcwd(), "drivers/chromedriver-linux64/chromedriver"))
print(f"Using ChromeDriver at: {chromedriver_path}")

# Inisiasi driver dengan path yang benar
service = Service(executable_path=chromedriver_path)
driver = webdriver.Chrome(service=service)

# Opsi login: otomatis atau manual
login_mode = input("Pilih mode login (1: Otomatis, 2: Manual): ")

try:
    print("Membuka LinkedIn.com...")
    driver.get("https://www.linkedin.com/login")
    print(f"Title: {driver.title}")
    
    if login_mode == "1":
        # Login otomatis
        email = input("Masukkan email LinkedIn Anda: ")
        password = input("Masukkan password LinkedIn Anda: ")
        actions.login(driver, email, password)
    else:
        # Login manual
        print("\nSilakan login secara manual di browser yang terbuka.")
        print("Anda memiliki 60 detik untuk login...")
        time.sleep(60)  # Beri waktu 60 detik untuk login manual
    
    # Cek apakah login berhasil
    if "feed" in driver.current_url or "checkpoint" in driver.current_url:
        print("Login berhasil!")
        
        # Tanya apakah ingin scrape profil
        scrape_profile = input("\nApakah Anda ingin scrape profil? (y/n): ")
        if scrape_profile.lower() == 'y':
            profile_url = input("Masukkan URL profil LinkedIn yang ingin di-scrape: ")
            print(f"\nMemulai scraping profil: {profile_url}")
            person = Person(profile_url, driver=driver, close_on_complete=False)
            print(f"Nama: {person.name}")
            if hasattr(person, 'about') and person.about:
                print(f"Tentang: {person.about}")
            if hasattr(person, 'experiences') and person.experiences:
                print(f"Jumlah pengalaman: {len(person.experiences)}")
            if hasattr(person, 'educations') and person.educations:
                print(f"Jumlah pendidikan: {len(person.educations)}")
    else:
        print("Sepertinya login belum berhasil.")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    # Tunggu input pengguna sebelum keluar
    input("\nTekan Enter untuk keluar dan menutup browser...")
    driver.quit() 