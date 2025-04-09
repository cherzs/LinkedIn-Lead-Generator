#!/usr/bin/env python3
import os
import platform
import json
import requests
from linkedin_scraper import Person, actions
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import sys
import traceback
from datetime import datetime

print("=== LinkedIn Profile Scraper ===")
print(f"Python version: {sys.version}")

# Detect the operating system and select the appropriate ChromeDriver
system = platform.system()
if system == "Windows":
    chromedriver_path = os.getenv("CHROMEDRIVER", os.path.join(os.getcwd(), "drivers/chromedriver-win64/chromedriver.exe"))
elif system == "Linux":
    chromedriver_path = os.getenv("CHROMEDRIVER", os.path.join(os.getcwd(), "drivers/chromedriver-linux64/chromedriver"))
else:  # For macOS
    chromedriver_path = os.getenv("CHROMEDRIVER", os.path.join(os.getcwd(), "drivers/chromedriver-mac64/chromedriver"))

print(f"Operating System: {system}")
print(f"Using ChromeDriver at: {chromedriver_path}")

# Check if ChromeDriver exists
if not os.path.exists(chromedriver_path):
    print(f"ERROR: ChromeDriver not found at {chromedriver_path}")
    print("Drivers folder contains: ")
    drivers_dir = os.path.dirname(chromedriver_path)
    if os.path.exists(drivers_dir):
        print(os.listdir(drivers_dir))
    else:
        print(f"Folder {drivers_dir} not found")
    sys.exit(1)
else:
    print(f"ChromeDriver found: {chromedriver_path}")

# Function to notify the backend API about login status
def notify_login_status(status):
    try:
        print(f"\nSending login status ({status}) to backend...")
        api_url = "http://localhost:5000/api/linkedin/login"
        retries = 5  # Increase retry count
        success = False
        
        # Save to file first as the main fallback
        try:
            status_data = {
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "url": driver.current_url if 'driver' in globals() else "",
                "source": "test_scraper_direct"
            }
            
            with open("linkedin_login_status.json", "w") as f:
                json.dump(status_data, f)
            print("Login status saved to file as the primary method.")
        except Exception as e:
            print(f"Failed to save status to file: {str(e)}")
        
        for attempt in range(retries):
            try:
                # Use more comprehensive payload
                payload = {
                    "login_method": "manual", 
                    "status": status,
                    "timestamp": datetime.now().isoformat(),
                    "source": "test_scraper",
                    "url": driver.current_url if 'driver' in globals() else ""
                }
                
                print(f"Sending payload: {payload}")
                response = requests.post(
                    api_url,
                    json=payload,
                    timeout=10  # Add timeout
                )
                
                print(f"Status code: {response.status_code}")
                print(f"Response: {response.text}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    print(f"Login status successfully sent to backend: {status}")
                    print(f"Response from server: {response_data}")
                    success = True
                    break
                else:
                    print(f"Attempt {attempt+1}: Failed to send login status to backend, code: {response.status_code}")
                    print(f"Response: {response.text}")
            except Exception as err:
                print(f"Attempt {attempt+1}: Error while sending login status: {str(err)}")
                time.sleep(2)  # Add wait time between retries
        
        if not success:
            print("Failed to send login status after several attempts.")
            # Try all alternative endpoints
            try:
                # Method 1: Using manual-update endpoint
                alt_url = "http://localhost:5000/api/linkedin/manual-update"
                alt_response = requests.post(
                    alt_url,
                    json={"status": status, "message": "Updated from test_scraper fallback method"},
                    timeout=10
                )
                if alt_response.status_code == 200:
                    print("Successfully used manual-update endpoint as an alternative!")
                    return
            except Exception as e:
                print(f"Alternative 1 failed: {str(e)}")
                
            try:
                # Method 2: Using force-login endpoint
                alt_url = "http://localhost:5000/api/linkedin/force-login"
                alt_response = requests.post(
                    alt_url,
                    json={"status": status},
                    timeout=10
                )
                if alt_response.status_code == 200:
                    print("Successfully used force-login endpoint as an alternative!")
                    return
            except Exception as e:
                print(f"Alternative 2 failed: {str(e)}")
    except Exception as e:
        print(f"Error in notify_login_status function: {str(e)}")

# Initialize driver with the correct path
try:
    print("\nAttempting to initialize WebDriver...")
    service = Service(executable_path=chromedriver_path)
    
    # Configure Chrome options
    options = Options()
    options.add_argument("--start-maximized")  # Start with maximized window
    options.add_argument("--disable-extensions")  # Disable extensions
    options.add_experimental_option("excludeSwitches", ["enable-automation"])  # Hide automation info
    options.add_experimental_option('useAutomationExtension', False)
    
    # Add debugging options
    print("Creating WebDriver instance...")
    driver = webdriver.Chrome(service=service, options=options)
    print("WebDriver created successfully!")
except Exception as e:
    print(f"ERROR creating WebDriver: {str(e)}")
    print("Error details:")
    traceback.print_exc()
    sys.exit(1)

# Accept profile_url if provided as an argument
profile_url = None
if len(sys.argv) > 1:
    profile_url = sys.argv[1]
    print(f"Profile URL to scrape: {profile_url}")

try:
    print("\nOpening LinkedIn.com...")
    driver.get("https://www.linkedin.com/login")
    print(f"Page title: {driver.title}")
    
    # Automatic login
    print("\n" + "="*50)
    print("ENTER LINKEDIN CREDENTIALS")
    print("="*50)
    print("IMPORTANT: If you see error messages about TensorFlow or delegate, IGNORE them.")
    print("These error messages come from Chrome and are not serious issues.\n")
    
    email = input(">> Enter your LinkedIn email: ")
    password = input(">> Enter your LinkedIn password: ")
    
    print("\nAttempting login...")
    actions.login(driver, email, password)
    
    # Check if login was successful
    print(f"Current URL after login: {driver.current_url}")
    if "feed" in driver.current_url or "checkpoint" in driver.current_url:
        print("Login successful!")
        
        # Notify backend that login was successful
        notify_login_status(True)
        
        # Display alternative URL to update status if automatic method fails
        print("\nIf login status doesn't change in the web application, please visit the following URL:")
        print("http://localhost:5000/api/linkedin/set-logged-in")
        print("The above URL will manually update the LinkedIn login status.")
        
        # If profile URL was provided as an argument, scrape immediately
        if profile_url:
            print(f"\nStarting profile scraping: {profile_url}")
            person = Person(profile_url, driver=driver, close_on_complete=False)
            print(f"Name: {person.name}")
            if hasattr(person, 'about') and person.about:
                print(f"About: {person.about}")
            if hasattr(person, 'experiences') and person.experiences:
                print(f"Number of experiences: {len(person.experiences)}")
            if hasattr(person, 'educations') and person.educations:
                print(f"Number of educations: {len(person.educations)}")
            
            # Try to send profile data to backend
            try:
                profile_data = {
                    "name": person.name,
                    "about": person.about if hasattr(person, 'about') and person.about else "",
                    "experiences": len(person.experiences) if hasattr(person, 'experiences') else 0,
                    "educations": len(person.educations) if hasattr(person, 'educations') else 0,
                    "source_url": profile_url
                }
                
                print("\nSending profile data to backend...")
                api_url = "http://localhost:5000/api/linkedin/scrape-profile"
                response = requests.post(
                    api_url,
                    json={"profile_data": profile_data, "use_existing_session": True, "profile_url": profile_url},
                    timeout=10
                )
                
                if response.status_code == 200:
                    print("Profile data successfully sent to backend")
                else:
                    print(f"Failed to send profile data: {response.status_code}")
            except Exception as e:
                print(f"Error while sending profile data: {str(e)}")
        else:
            print("\nSuccessfully logged in to LinkedIn. Browser will remain open to maintain the session.")
            print("You can now use the web application to scrape LinkedIn profiles.")
    else:
        print("It seems login was not successful.")
        notify_login_status(False)
        
except Exception as e:
    print(f"Error: {e}")
    print("Error details:")
    traceback.print_exc()
    notify_login_status(False)
finally:
    # Keep browser open during the session
    # If login was successful, leave window open
    if "feed" in driver.current_url or "checkpoint" in driver.current_url:
        print("\nLogin session successful. Browser will remain open.")
        print("You can use the web application to scrape LinkedIn profiles.")
        print("Do not close this browser window to keep the session active.")
        
        # Display message and wait for user to manually close browser
        while True:
            try:
                # Check if browser is still open
                driver.current_url
                # Wait 10 seconds before checking again
                time.sleep(10)
            except:
                # Browser has been closed
                break
    else:
        # If login failed, wait a few seconds then close
        print("\nLogin was not successful. Browser will close in 10 seconds...")
        time.sleep(10)
        driver.quit() 