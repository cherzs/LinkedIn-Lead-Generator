#!/usr/bin/env python3
import os
from linkedin_scraper import Person, actions
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import time
import sys

# Menggunakan path ChromeDriver yang sudah kita ekstrak
chromedriver_path = os.getenv("CHROMEDRIVER", os.path.join(os.getcwd(), "drivers/chromedriver-linux64/chromedriver"))
print(f"Using ChromeDriver at: {chromedriver_path}")

# Inisiasi driver dengan path yang benar
service = Service(executable_path=chromedriver_path)
driver = webdriver.Chrome(service=service)

# Terima profile_url jika diberikan sebagai argumen
profile_url = None
if len(sys.argv) > 1:
    profile_url = sys.argv[1]

try:
    print("Membuka LinkedIn.com...")
    driver.get("https://www.linkedin.com/login")
    print(f"Title: {driver.title}")
    
    # Login otomatis
    email = input("Masukkan email LinkedIn Anda: ")
    password = input("Masukkan password LinkedIn Anda: ")
    actions.login(driver, email, password)
    
    # Cek apakah login berhasil
    if "feed" in driver.current_url or "checkpoint" in driver.current_url:
        print("Login berhasil!")
        
        # Jika URL profil diberikan sebagai argumen, langsung scrape
        if profile_url:
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
            print("\nBerhasil login ke LinkedIn. Browser akan tetap terbuka untuk mempertahankan sesi.")
            print("Anda sekarang dapat menggunakan aplikasi web untuk scraping profil LinkedIn.")
    else:
        print("Sepertinya login belum berhasil.")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    # Tunggu input pengguna sebelum keluar
    input("\nTekan Enter untuk keluar dan menutup browser...")
    driver.quit() 