#!/usr/bin/env python3
import os
import json
import logging
import argparse
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime
import re
import csv
import tempfile
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import subprocess
import platform

# Import LinkedIn scraper
from linkedin_scraper import Person, actions
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("leadgen.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("leadgen")

# Get environment variables
from dotenv import load_dotenv
load_dotenv()

# Flask App setup
app = Flask(__name__)
CORS(app)

# Data storage paths
LEADS_FILE = "leads_data.json"

# Store the LinkedIn driver globally for reuse
linkedin_driver = None
linkedin_login_status = {
    "logged_in": False,
    "timestamp": None,
    "message": "Not logged in"
}

# Helper functions
def load_leads():
    """Load leads from JSON file"""
    try:
        if os.path.exists(LEADS_FILE):
            with open(LEADS_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Error loading leads: {str(e)}")
        return []

def save_leads(leads):
    """Save leads to JSON file"""
    try:
        with open(LEADS_FILE, 'w') as f:
            json.dump(leads, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving leads: {str(e)}")
        return False

def generate_lead_id(leads):
    """Generate a new unique ID for a lead"""
    if not leads:
        return 1
    ids = [lead.get("id") for lead in leads if lead.get("id")]
    if not ids:
        return 1
    return max(ids) + 1

def clean_leads_data(leads):
    """Clean and normalize leads data"""
    cleaned_leads = []
    for lead in leads:
        # Normalize company names (capitalize first letter of each word)
        if lead.get("company"):
            lead["company"] = re.sub(r'\s+', ' ', lead["company"].strip())
            lead["company"] = ' '.join([word.capitalize() for word in lead["company"].split()])
        
        # Ensure all fields exist
        for field in ["name", "title", "company", "location", "email", "emails", "source_url"]:
            if field not in lead:
                if field == "emails":
                    lead[field] = []
                else:
                    lead[field] = ""
                    
        # Add single email to emails array if not already present
        if lead.get("email") and lead["email"] not in lead.get("emails", []):
            if not lead.get("emails"):
                lead["emails"] = []
            lead["emails"].append(lead["email"])
                
        cleaned_leads.append(lead)
    
    return cleaned_leads

def extract_profile_data(soup, url):
    """Extract profile data from a webpage"""
    # Basic profile structure
    profile = {
        "name": "",
        "title": "",
        "company": "",
        "location": "",
        "email": "",
        "emails": [],
        "source_url": url
    }
    
    # Extract name - look for common heading patterns
    name_tags = soup.select('h1, .name, .profile-name, [class*="name"], [id*="name"]')
    if name_tags:
        profile["name"] = name_tags[0].get_text().strip()
    
    # Extract title - look for elements that might contain job titles
    title_tags = soup.select('.title, .job-title, .profession, [class*="title"], [class*="position"]')
    if title_tags:
        profile["title"] = title_tags[0].get_text().strip()
    
    # Extract company - look for elements that might contain company info
    company_tags = soup.select('.company, .organization, [class*="company"], [class*="organization"]')
    if company_tags:
        profile["company"] = company_tags[0].get_text().strip()
    
    # Extract location - look for location elements
    location_tags = soup.select('.location, [class*="location"], address')
    if location_tags:
        profile["location"] = location_tags[0].get_text().strip()
    
    # Extract email - look for email patterns
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    found_emails = re.findall(email_regex, str(soup))
    if found_emails:
        profile["email"] = found_emails[0]
        profile["emails"] = list(set(found_emails))  # Remove duplicates
    
    return profile

def setup_chrome_driver():
    """Setup and return a Chrome WebDriver instance"""
    # Detect operating system and select appropriate ChromeDriver
    system = platform.system()
    logger.info(f"Detected OS: {system}")
    
    if system == "Windows":
        chromedriver_path = os.getenv("CHROMEDRIVER", os.path.join(os.getcwd(), "drivers/chromedriver-win64/chromedriver.exe"))
    elif system == "Linux":
        chromedriver_path = os.getenv("CHROMEDRIVER", os.path.join(os.getcwd(), "drivers/chromedriver-linux64/chromedriver"))
    else:  # For macOS
        chromedriver_path = os.getenv("CHROMEDRIVER", os.path.join(os.getcwd(), "drivers/chromedriver-mac64/chromedriver"))
    
    logger.info(f"Using ChromeDriver at: {chromedriver_path}")
    
    # Set Chrome options to ensure browser is visible
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--start-maximized")  # Start maximized
    chrome_options.add_argument("--disable-extensions")  # Disable extensions
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])  # Hide automation info
    chrome_options.add_experimental_option('useAutomationExtension', False)
    # Make sure headless mode is NOT enabled
    # chrome_options.add_argument("--headless")  # Comment this out to see the browser
    
    logger.info("Starting Chrome with visible UI")
    service = Service(executable_path=chromedriver_path)
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_linkedin_profile(profile_url, login_method="manual", email=None, password=None, use_existing_session=True):
    """Scrape a LinkedIn profile using Selenium"""
    global linkedin_driver, linkedin_login_status
    
    try:
        # Check if we already have a logged-in session
        if use_existing_session and linkedin_driver:
            # Verify existing driver session status
            try:
                current_url = linkedin_driver.current_url
                # Check if driver is still active and on a LinkedIn page
                if any(domain in current_url for domain in ["linkedin.com/feed", "linkedin.com/checkpoint", "linkedin.com/in", "linkedin.com/mynetwork"]):
                    driver = linkedin_driver
                    linkedin_login_status["logged_in"] = True  # Make sure login status is updated
                    logger.info(f"Using existing LinkedIn session (URL: {current_url})")
                else:
                    # Browser active but not on a page requiring login
                    logger.warning(f"Existing driver found but URL doesn't indicate login: {current_url}")
                    driver = linkedin_driver  # Still use existing driver
            except Exception as e:
                # Driver not active or error, create a new one
                logger.warning(f"Error checking existing driver: {str(e)}")
                driver = setup_chrome_driver()
                linkedin_login_status["logged_in"] = False
        else:
            # Setup a new driver
            driver = setup_chrome_driver()
            
            # Login to LinkedIn
            logger.info("Opening LinkedIn.com...")
            driver.get("https://www.linkedin.com/login")
            
            if login_method == "automatic" and email and password:
                # Login automatically
                logger.info("Attempting automatic login")
                actions.login(driver, email, password)
            else:
                # Login manually
                logger.info("Waiting for manual login")
                logger.info("Please login to LinkedIn in the opened browser window")
                # Wait for a moment to allow the login page to open
                time.sleep(60)
            
            # Check if login was successful
            if "feed" in driver.current_url or "checkpoint" in driver.current_url:
                logger.info("Login successful")
                
                # Update global variables
                if linkedin_driver:
                    try:
                        linkedin_driver.quit()
                    except:
                        pass
                linkedin_driver = driver
                linkedin_login_status = {
                    "logged_in": True,
                    "timestamp": datetime.now().isoformat(),
                    "message": "Logged in automatically"
                }
            else:
                logger.error("Login unsuccessful")
                driver.quit()
                return {"success": False, "error": "Login to LinkedIn failed. Please check credentials or try manual login."}
        
        # Scrape the profile
        logger.info(f"Starting profile scraping: {profile_url}")
        
        try:
            # Navigate to profile URL
            driver.get(profile_url)
            time.sleep(3)  # Wait for a moment to allow the page to load
            
            # Check if redirected to login page (indicating session expired)
            if "login" in driver.current_url:
                logger.error("Redirected to login page - session expired")
                linkedin_login_status["logged_in"] = False
                return {"success": False, "error": "LinkedIn session expired. Please login again."}
            
            # Check if page not found or rate limited
            if "page-not-found" in driver.current_url or driver.title == "Profile Unavailable":
                logger.error(f"Profile not found or unavailable: {profile_url}")
                return {"success": False, "error": f"LinkedIn profile not found or not available: {profile_url}"}
            
            try:
                # Try to scrape profile with safe method
                logger.info("Attempting to scrape profile with modified Person class")
                
                try:
                    # Use direct Selenium scraping instead of library
                    logger.info("Scraping profile directly with Selenium")
                    
                    # Extra wait to ensure the page is fully loaded
                    time.sleep(5)
                    
                    # Initialize profile_data before use
                    profile_data = {
                        "name": "",
                        "job_title": "",
                        "company": "",
                        "location": "",
                        "about": "",
                        "experiences": 0,
                        "educations": 0
                    }
                    
                    # Extract data from page
                    try:
                        name_element = driver.find_element(By.XPATH, "//h1")
                        profile_data["name"] = name_element.text if name_element else "Unknown"
                        logger.info(f"Name successfully extracted: {profile_data['name']}")
                    except Exception as e:
                        logger.error(f"Error extracting name: {str(e)}")
                    
                    # Extract job title/position
                    try:
                        title_selectors = [
                            "//div[contains(@class, 'text-body-medium')]",
                            "//div[contains(@class, 'pv-text-details__left-panel')]/div",
                            "//*[contains(@class, 'pv-text-details__left-panel')]//h2",
                            "//div[contains(@class, 'ph5')]/div[contains(@class, 'mt2')]//div[contains(@class, 'text-body-medium')]"
                        ]
                        
                        for selector in title_selectors:
                            try:
                                elements = driver.find_elements(By.XPATH, selector)
                                for element in elements:
                                    if element and element.text.strip():
                                        profile_data["job_title"] = element.text.strip()
                                        logger.info(f"Job title successfully extracted: {profile_data['job_title']}")
                                        break
                                if profile_data["job_title"]:
                                    break
                            except Exception as sel_err:
                                logger.debug(f"Error with selector {selector}: {str(sel_err)}")
                    except Exception as e:
                        logger.error(f"Error extracting job title: {str(e)}")
                    
                    # Extract current company
                    try:
                        company_selectors = [
                            "//div[contains(@class, 'pv-entity__company-details')]/div",
                            "//span[contains(@class, 'pv-entity__secondary-title')]",
                            "//a[contains(@href, '/company/')]",
                            "//div[contains(@class, 'inline-show-more-text')]/span"
                        ]
                        
                        for selector in company_selectors:
                            try:
                                elements = driver.find_elements(By.XPATH, selector)
                                for element in elements:
                                    if element and element.text.strip():
                                        profile_data["company"] = element.text.strip()
                                        logger.info(f"Company successfully extracted: {profile_data['company']}")
                                        break
                                if profile_data["company"]:
                                    break
                            except Exception as sel_err:
                                logger.debug(f"Error with company selector {selector}: {str(sel_err)}")
                    except Exception as e:
                        logger.error(f"Error extracting company: {str(e)}")
                    
                    # Extract company from job title if not found
                    if not profile_data["company"] and " at " in profile_data.get("job_title", ""):
                        parts = profile_data["job_title"].split(" at ", 1)
                        profile_data["company"] = parts[1].strip() if len(parts) > 1 else ""
                        logger.info(f"Company extracted from job title: {profile_data['company']}")
                    
                    # Count experiences
                    try:
                        exp_elements = driver.find_elements(By.XPATH, "//section[contains(@class,'experience')]//li")
                        profile_data["experiences"] = len(exp_elements) if exp_elements else 0
                    except Exception as e:
                        logger.error(f"Error extracting experiences: {str(e)}")
                    
                    # Count educations
                    try:
                        edu_elements = driver.find_elements(By.XPATH, "//section[contains(@class,'education')]//li")
                        profile_data["educations"] = len(edu_elements) if edu_elements else 0
                    except Exception as e:
                        logger.error(f"Error extracting educations: {str(e)}")
                    
                    # Extract About section
                    try:
                        # Try to find about section with various selectors
                        about_selectors = [
                            "//section[contains(@class, 'about')]//div[contains(@class, 'display-flex')]//span",
                            "//section[.//span[text()='About' or text()='Tentang']]//div[contains(@class, 'display-flex')]//span",
                            "//section[contains(@id, 'about')]//div[contains(@class, 'inline-show-more-text')]",
                            "//section[.//span[text()='About' or text()='Tentang']]//p",
                            "//div[contains(@class, 'about-section')]//p"
                        ]
                        
                        for selector in about_selectors:
                            try:
                                # Try to click "see more" if present to see full text
                                try:
                                    see_more_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'see more') or contains(text(), 'lihat selengkapnya')]")
                                    for button in see_more_buttons:
                                        if button.is_displayed():
                                            driver.execute_script("arguments[0].click();", button)
                                            time.sleep(1)
                                except Exception as see_more_err:
                                    logger.debug(f"Error clicking 'see more': {str(see_more_err)}")
                                
                                # Find about element and get its text
                                elements = driver.find_elements(By.XPATH, selector)
                                about_text = ""
                                for element in elements:
                                    if element and element.text.strip():
                                        about_text += element.text.strip() + " "
                                
                                if about_text:
                                    profile_data["about"] = about_text.strip()
                                    logger.info(f"About section successfully extracted: {profile_data['about'][:50]}...")
                                    break
                            except Exception as sel_err:
                                logger.debug(f"Error with about selector {selector}: {str(sel_err)}")
                    except Exception as e:
                        logger.error(f"Error extracting about section: {str(e)}")
                    
                    # Take screenshot for debugging
                    try:
                        screenshot_path = f"profile_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        driver.save_screenshot(screenshot_path)
                        logger.info(f"Screenshot saved: {screenshot_path}")
                    except Exception as e:
                        logger.error(f"Error saving screenshot: {str(e)}")
                    
                    # Send data to scrape-profile endpoint
                    try:
                        api_url = "http://localhost:5000/api/linkedin/scrape-profile"
                        response = requests.post(
                            api_url,
                            json={"profile_data": profile_data, "use_existing_session": True, "profile_url": profile_url},
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            logger.info("Profile data successfully sent to backend")
                        else:
                            logger.error(f"Failed to send profile data: {response.status_code}")
                    except Exception as e:
                        logger.error(f"Error sending profile data: {str(e)}")
                except Exception as scrape_e:
                    logger.error(f"Error during direct Selenium scraping: {str(scrape_e)}")
                    
                    # Initialize empty Person object
                    person = type('Person', (), {})()
                    person.name = ""
                    person.about = ""
                    person.location = ""
                    person.experiences = []
                    person.educations = []
                    person.company = ""
                    
                    # Try alternative approach - basic scraping for minimal data
                    try:
                        # Get name
                        try:
                            name_elem = driver.find_element(By.TAG_NAME, "h1")
                            person.name = name_elem.text if name_elem else ""
                        except:
                            logger.warning("Failed to extract name with basic fallback method")
                    except Exception as basic_error:
                        logger.error(f"Basic extraction failed too: {str(basic_error)}")
                
                # Create lead from scraped profile
                lead = {
                    "name": profile_data.get("name", ""),
                    "title": profile_data.get("job_title", ""),
                    "company": profile_data.get("company", ""),
                    "location": profile_data.get("location", ""),
                    "email": "",  # LinkedIn doesn't expose email
                    "emails": [],
                    "source_url": profile_url,
                    "about": profile_data.get("about", ""),
                    "experiences": profile_data.get("experiences", 0),
                    "educations": profile_data.get("educations", 0)
                }
                
                return {"success": True, "lead": lead}
            except Exception as scrape_error:
                logger.error(f"Error during profile scraping: {str(scrape_error)}")
                # Check if problem is login-related
                if "login" in driver.current_url:
                    linkedin_login_status["logged_in"] = False
                    return {"success": False, "error": "LinkedIn session expired. Please login again."}
                return {"success": False, "error": f"Failed to retrieve profile data: {str(scrape_error)}"}
            
        except Exception as scrape_error:
            logger.error(f"Error during profile scraping: {str(scrape_error)}")
            # Check if problem is login-related
            if "login" in driver.current_url:
                linkedin_login_status["logged_in"] = False
                return {"success": False, "error": "LinkedIn session expired. Please login again."}
            return {"success": False, "error": f"Failed to retrieve profile data: {str(scrape_error)}"}
            
    except Exception as e:
        logger.error(f"Error scraping LinkedIn profile: {str(e)}")
        try:
            if not use_existing_session or not linkedin_login_status["logged_in"]:
                driver.quit()
        except:
            pass
        return {"success": False, "error": str(e)}

# API Routes
@app.route('/')
def index():
    """API root endpoint"""
    return jsonify({
        'status': 'online',
        'message': 'LinkedIn Lead Generator API',
        'endpoints': [
            '/api/leads',
            '/api/leads/<id>',
            '/api/linkedin/scrape-profile',
            '/api/clean-data',
            '/api/export/csv',
            '/api/status'
        ]
    })

@app.route('/api/leads', methods=['GET'])
def get_leads():
    """Get all leads"""
    leads = load_leads()
    return jsonify(leads)

@app.route('/api/leads/<int:lead_id>', methods=['GET'])
def get_lead(lead_id):
    """Get a specific lead by ID"""
    leads = load_leads()
    lead = next((lead for lead in leads if lead.get("id") == lead_id), None)
    if lead:
        return jsonify(lead)
    return jsonify({"error": "Lead not found"}), 404

@app.route('/api/leads', methods=['POST'])
def add_lead():
    """Add a new lead"""
    try:
        lead_data = request.json
        leads = load_leads()
        
        # Generate ID for new lead
        lead_data["id"] = generate_lead_id(leads)
        
        # Clean the lead data
        lead_data = clean_leads_data([lead_data])[0]
        
        leads.append(lead_data)
        save_leads(leads)
        
        return jsonify({"success": True, "lead": lead_data})
    except Exception as e:
        logger.error(f"Error adding lead: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/<int:lead_id>', methods=['PUT'])
def update_lead(lead_id):
    """Update a lead"""
    try:
        lead_data = request.json
        leads = load_leads()
        
        lead_index = next((index for index, lead in enumerate(leads) if lead.get("id") == lead_id), None)
        if lead_index is None:
            return jsonify({"error": "Lead not found"}), 404
        
        # Preserve ID
        lead_data["id"] = lead_id
        
        # Clean the lead data
        lead_data = clean_leads_data([lead_data])[0]
        
        leads[lead_index] = lead_data
        save_leads(leads)
        
        return jsonify({"success": True, "lead": lead_data})
    except Exception as e:
        logger.error(f"Error updating lead: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/<int:lead_id>', methods=['DELETE'])
def delete_lead(lead_id):
    """Delete a lead"""
    try:
        leads = load_leads()
        
        lead_index = next((index for index, lead in enumerate(leads) if lead.get("id") == lead_id), None)
        if lead_index is None:
            return jsonify({"error": "Lead not found"}), 404
        
        removed_lead = leads.pop(lead_index)
        save_leads(leads)
        
        return jsonify({"success": True, "lead": removed_lead})
    except Exception as e:
        logger.error(f"Error deleting lead: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/linkedin/login', methods=['POST'])
def linkedin_login():
    """Login to LinkedIn and keep session for later use"""
    global linkedin_driver, linkedin_login_status
    
    try:
        data = request.json
        login_method = data.get('login_method', 'manual')  # 'manual' or 'automatic'
        email = data.get('email')
        password = data.get('password')
        
        # Check if test_scraper.py is sending login status only
        if 'status' in data:
            # Update login status based on notification from test_scraper.py
            login_status = data.get('status', False)
            timestamp = data.get('timestamp', datetime.now().isoformat())
            
            # Log more detailed response
            logger.info(f"Received login status update from test_scraper.py: {login_status}")
            logger.info(f"Full payload: {data}")
            
            linkedin_login_status = {
                "logged_in": login_status,
                "timestamp": timestamp,
                "message": "Login status updated from test_scraper.py"
            }
            
            # Actively verify driver also if exists
            if linkedin_driver:
                try:
                    current_url = linkedin_driver.current_url
                    if any(domain in current_url for domain in ["linkedin.com/feed", "linkedin.com/checkpoint", "linkedin.com/in", "linkedin.com/mynetwork"]):
                        # URL indicates user is already logged in
                        if not login_status:
                            logger.info(f"Driver shows user is logged in (URL: {current_url}) but received status is False. Overriding.")
                            login_status = True
                            linkedin_login_status["logged_in"] = True
                            linkedin_login_status["message"] = "Login confirmed by URL check"
                except Exception as e:
                    logger.error(f"Error checking driver status: {str(e)}")
            
            return jsonify({
                "success": True, 
                "status": "login_status_updated",
                "logged_in": linkedin_login_status["logged_in"],
                "message": f"LinkedIn login status updated: {'Logged in' if linkedin_login_status['logged_in'] else 'Not logged in'}"
            })
        
        # Normal login process if not notification from test_scraper.py
        # If there's already an active session, close it
        if linkedin_driver:
            try:
                linkedin_driver.quit()
            except:
                pass
        
        # Setup a new driver
        driver = setup_chrome_driver()
        
        # Open LinkedIn login page
        logger.info("Opening LinkedIn.com...")
        driver.get("https://www.linkedin.com/login")
        
        login_result = {"success": False, "message": "Login failed"}
        
        if login_method == "automatic" and email and password:
            # Login automatically
            logger.info("Attempting automatic login")
            actions.login(driver, email, password)
            
            # Check if login was successful
            time.sleep(5)  # Wait a moment for login to complete
            if "feed" in driver.current_url or "checkpoint" in driver.current_url:
                linkedin_driver = driver
                linkedin_login_status = {
                    "logged_in": True,
                    "timestamp": datetime.now().isoformat(),
                    "message": "Logged in automatically"
                }
                login_result = {"success": True, "message": "Automatic login successful"}
            else:
                driver.quit()
                login_result = {"success": False, "message": "Automatic login failed. Please check your credentials."}
        else:
            # Manual login mode
            # Return immediately so the user can see the browser and login
            linkedin_driver = driver
            linkedin_login_status = {
                "logged_in": False,
                "timestamp": datetime.now().isoformat(),
                "message": "Waiting for manual login"
            }
            return jsonify({
                "success": True, 
                "status": "waiting_for_login",
                "message": "Browser opened for manual login. Please login within 60 seconds."
            })
        
        return jsonify(login_result)
    
    except Exception as e:
        logger.error(f"Error during LinkedIn login: {str(e)}")
        if 'driver' in locals():
            try:
                driver.quit()
            except:
                pass
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/linkedin/login-status', methods=['GET'])
def check_login_status():
    """Check if user is logged in to LinkedIn without opening a new browser"""
    global linkedin_driver, linkedin_login_status
    
    # Only check existing driver status, don't create a new one
    if linkedin_driver:
        # Check if user has completed manual login
        try:
            current_url = linkedin_driver.current_url
            if any(domain in current_url for domain in ["linkedin.com/feed", "linkedin.com/checkpoint", "linkedin.com/in", "linkedin.com/mynetwork"]):
                # If browser looks like still logged in but status not updated
                if not linkedin_login_status["logged_in"]:
                    linkedin_login_status = {
                        "logged_in": True,
                        "timestamp": datetime.now().isoformat(),
                        "message": "Logged in (detected from URL check)"
                    }
                    logger.info(f"Login status updated to TRUE based on URL: {current_url}")
            else:
                # URL doesn't indicate login
                if linkedin_login_status["logged_in"]:
                    logger.info(f"Current URL doesn't indicate login: {current_url}")
        except Exception as e:
            # Session might be broken
            logger.error(f"Error checking driver status: {str(e)}")
    
    # Send last known status
    return jsonify({
        "logged_in": linkedin_login_status["logged_in"],
        "timestamp": linkedin_login_status["timestamp"],
        "message": linkedin_login_status["message"]
    })

@app.route('/api/linkedin/logout', methods=['POST'])
def linkedin_logout():
    """Close LinkedIn session"""
    global linkedin_driver, linkedin_login_status
    
    try:
        if linkedin_driver:
            linkedin_driver.quit()
            linkedin_driver = None
        
        linkedin_login_status = {
            "logged_in": False,
            "timestamp": datetime.now().isoformat(),
            "message": "Logged out"
        }
        
        return jsonify({"success": True, "message": "Logged out of LinkedIn"})
    except Exception as e:
        logger.error(f"Error during LinkedIn logout: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/linkedin/scrape-profile', methods=['POST'])
def scrape_linkedin():
    """Scrape a LinkedIn profile and save as lead"""
    global linkedin_login_status
    
    try:
        data = request.json
        profile_url = data.get('profile_url')
        login_method = data.get('login_method', 'manual')  # 'manual' or 'automatic'
        email = data.get('email')
        password = data.get('password')
        save_profile = data.get('save', True)  # Default to saving the profile
        use_existing_session = data.get('use_existing_session', True)  # Use existing session if available
        
        # Check if profile data is sent directly from test_scraper.py
        profile_data = data.get('profile_data')
        if profile_data and profile_url:
            logger.info(f"Menerima data profil langsung dari test_scraper.py: {profile_url}")
            
            # Create lead from sent profile data
            lead = {
                "name": profile_data.get("name", ""),
                "about": profile_data.get("about", ""),
                "title": "",  # Not in sent data
                "company": "",  # Not in sent data
                "location": "",  # Not in sent data
                "email": "",
                "emails": [],
                "source_url": profile_url,
                "experiences": profile_data.get("experiences", 0),
                "educations": profile_data.get("educations", 0)
            }
            
            # Save profile
            if save_profile:
                leads = load_leads()
                
                # Check if this profile already exists by URL
                existing_lead = next((ld for ld in leads if ld.get("source_url") == profile_url), None)
                
                if existing_lead:
                    # Update existing lead
                    for key, value in lead.items():
                        if value and key != "id":
                            existing_lead[key] = value
                    lead = existing_lead
                else:
                    # Add new lead
                    lead["id"] = generate_lead_id(leads)
                    leads.append(lead)
                
                save_leads(leads)
            
            return jsonify({
                "success": True, 
                "message": "Profile data received from test_scraper.py and saved",
                "lead": lead
            })
        
        if not profile_url:
            return jsonify({"success": False, "error": "LinkedIn profile URL is required"}), 400
        
        # Normalize LinkedIn URL
        # If URL is only username or format, convert to full URL format
        if not profile_url.startswith('http'):
            # Check if it's only username
            if "/" not in profile_url:
                profile_url = f"https://www.linkedin.com/in/{profile_url}"
            # If given format linkedin.com/in/username without https
            elif "linkedin.com/in/" in profile_url:
                profile_url = f"https://www.{profile_url}"
        
        # Ensure URL starts with correct format
        if not (profile_url.startswith('https://www.linkedin.com/') or profile_url.startswith('http://www.linkedin.com/')):
            logger.warning(f"URL not valid: {profile_url}, trying to correct format")
            # Try to extract username from possibly incorrect format
            if '/in/' in profile_url:
                username = profile_url.split('/in/')[1].split('/')[0].split('?')[0]
                profile_url = f"https://www.linkedin.com/in/{username}"
                logger.info(f"URL corrected to: {profile_url}")
            else:
                return jsonify({"success": False, "error": "LinkedIn URL format not valid. Use format https://www.linkedin.com/in/username"}), 400
            
        # Check if we need to ensure login first
        if not linkedin_login_status["logged_in"] and use_existing_session:
            logger.warning(f"Trying to scrape {profile_url} without login")
            return jsonify({
                "success": False, 
                "error": "Not logged in to LinkedIn. Please login first.",
                "requires_login": True
            }), 401
            
        # Scrape the LinkedIn profile
        logger.info(f"Starting to scrape profile: {profile_url}")
        result = scrape_linkedin_profile(
            profile_url, 
            login_method, 
            email, 
            password, 
            use_existing_session=use_existing_session
        )
        
        if not result["success"]:
            logger.error(f"Failed scraping: {result.get('error', 'Unknown error')}")
            return jsonify(result), 400
            
        lead = result["lead"]
        
        # Save the profile if requested
        if save_profile:
            leads = load_leads()
            
            # Check if this profile already exists by URL
            existing_lead = next((ld for ld in leads if ld.get("source_url") == profile_url), None)
            
            if existing_lead:
                # Update existing lead
                for key, value in lead.items():
                    if value and key != "id":
                        existing_lead[key] = value
                lead = existing_lead
            else:
                # Add new lead
                lead["id"] = generate_lead_id(leads)
                leads.append(lead)
            
            save_leads(leads)
        
        return jsonify({"success": True, "lead": lead})
    except Exception as e:
        logger.error(f"Error scraping LinkedIn profile: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/clean-data', methods=['POST'])
def clean_data():
    """Clean and normalize leads data"""
    try:
        leads = load_leads()
        cleaned_leads = clean_leads_data(leads)
        save_leads(cleaned_leads)
        
        return jsonify({"success": True, "count": len(cleaned_leads)})
    except Exception as e:
        logger.error(f"Error cleaning data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/clean-all', methods=['POST'])
def clean_all():
    """Complete reset and normalize leads data (remove duplicates)"""
    try:
        leads = load_leads()
        
        # Clean individual leads
        cleaned_leads = clean_leads_data(leads)
        
        # Remove duplicates by email
        email_dict = {}
        for lead in cleaned_leads:
            if lead.get("email"):
                email_dict[lead["email"]] = lead
        
        # Also check source_url for duplicates
        url_dict = {}
        for lead in [l for l in cleaned_leads if not l.get("email")]:
            if lead.get("source_url") and lead["source_url"] not in url_dict:
                url_dict[lead["source_url"]] = lead
        
        # Combine unique leads
        unique_leads = list(email_dict.values()) + list(url_dict.values())
        
        # Reassign IDs
        for i, lead in enumerate(unique_leads):
            lead["id"] = i + 1
        
        save_leads(unique_leads)
        
        return jsonify({"success": True, "count": len(unique_leads)})
    except Exception as e:
        logger.error(f"Error cleaning all data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/export/csv', methods=['POST'])
def export_csv():
    """Export leads to CSV"""
    try:
        leads = load_leads()
        
        if not leads:
            return jsonify({"error": "No leads to export"}), 400
        
        # Get export filename
        export_filename = os.getenv('DEFAULT_CSV_EXPORT_FILENAME', 'leads_export.csv')
        
        # Create a temporary file to store the CSV
        temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.csv', newline='')
        
        # Determine all possible fields from all leads
        all_fields = set()
        for lead in leads:
            all_fields.update(lead.keys())
        
        # Prioritize certain fields to appear first
        priority_fields = ['id', 'name', 'title', 'company', 'location', 'email', 'emails', 'source_url']
        fields = [f for f in priority_fields if f in all_fields] + [f for f in all_fields if f not in priority_fields]
        
        # Write leads to CSV
        writer = csv.DictWriter(temp_file, fieldnames=fields)
        writer.writeheader()
        
        for lead in leads:
            # Convert lists to strings for CSV
            lead_copy = lead.copy()
            for field, value in lead_copy.items():
                if isinstance(value, list):
                    lead_copy[field] = ", ".join(value)
            writer.writerow(lead_copy)
        
        temp_file.close()
        
        # Send the file
        return send_file(temp_file.name, as_attachment=True, download_name=export_filename, mimetype='text/csv')
    except Exception as e:
        logger.error(f"Error exporting to CSV: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status', methods=['GET'])
def api_status():
    """Check API status"""
    leads_count = len(load_leads())
    
    return jsonify({
        'status': 'online',
        'time': datetime.now().isoformat(),
        'leads_count': leads_count,
        'version': '1.0.0'
    })

@app.route('/api/run-test-scraper', methods=['POST'])
def run_test_scraper():
    """Run LinkedIn login process directly using WebDriver instead of test_scraper.py"""
    try:
        logger.info("Starting LinkedIn login process directly")
        
        # Get profile URL from request if available
        data = request.get_json()
        profile_url = data.get('profile_url', '') if data else ''
        
        # Setup Chrome WebDriver
        driver = setup_chrome_driver()
        
        # Inisiasi proses login dalam thread terpisah
        import threading
        
        def login_process():
            global linkedin_driver, linkedin_login_status
            
            try:
                # Buka halaman login LinkedIn
                logger.info("Opening LinkedIn login page...")
                driver.get("https://www.linkedin.com/login")
                
                # Wait for a moment to allow the login page to open
                time.sleep(2)
                
                # Tampilkan pesan instruksi
                logger.info("Waiting for user to login manually")
                
                # Cek status login setiap beberapa detik
                max_wait_time = 300  # 5 minutes
                start_time = time.time()
                login_successful = False
                last_url = ""  # Simpan URL terakhir untuk mengurangi spam log
                
                while time.time() - start_time < max_wait_time:
                    try:
                        current_url = driver.current_url
                        
                        # Hanya log jika URL berubah untuk mengurangi spam
                        if current_url != last_url:
                            logger.info(f"Current URL: {current_url}")
                            last_url = current_url
                        
                        # Cek apakah user sudah login dengan kondisi yang lebih ketat
                        if (
                            "feed" in current_url or 
                            "mynetwork" in current_url or
                            "messaging" in current_url or
                            "/in/" in current_url and "login" not in current_url or
                            "checkpoint" in current_url or
                            (not "login" in current_url and "linkedin.com" in current_url)
                        ):
                            # Extra wait to ensure the page is fully loaded
                            time.sleep(2)
                            
                            # Coba verifikasi status login dengan cara lain
                            try:
                                # Cek cookies LinkedIn
                                cookies = driver.get_cookies()
                                li_at_cookie = next((c for c in cookies if c['name'] == 'li_at'), None)
                                
                                if li_at_cookie:
                                    logger.info("LinkedIn auth cookie (li_at) found")
                                    login_successful = True
                                elif "login" not in current_url:
                                    # If there are no cookies but URL is not login, consider it successful
                                    login_successful = True
                            except Exception as cookie_e:
                                logger.warning(f"Error checking cookies: {str(cookie_e)}")
                                # Tetap gunakan URL sebagai indikator login jika error
                                login_successful = True
                            
                            if login_successful:
                                logger.info(f"LinkedIn login confirmed: {current_url}")
                                
                                # Update status login dengan pesan yang jelas
                                linkedin_login_status = {
                                    "logged_in": True,
                                    "timestamp": datetime.now().isoformat(),
                                    "message": f"Login successful via WebDriver (URL: {current_url})"
                                }
                                
                                # Simpan status ke file
                                try:
                                    cookie_count = len(driver.get_cookies())
                                    status_data = {
                                        "status": True,
                                        "timestamp": datetime.now().isoformat(),
                                        "url": driver.current_url,
                                        "source": "direct_webdriver_login",
                                        "cookies": cookie_count
                                    }
                                    
                                    with open("linkedin_login_status.json", "w") as f:
                                        json.dump(status_data, f)
                                    logger.info(f"Login status saved to file (cookies: {cookie_count})")
                                except Exception as e:
                                    logger.error(f"Failed to save status to file: {str(e)}")
                                
                                # Update global driver after successful login
                                if linkedin_driver:
                                    try:
                                        linkedin_driver.quit()
                                    except Exception as e:
                                        logger.error(f"Error closing existing driver: {str(e)}")
                                
                                # Set driver global
                                linkedin_driver = driver
                                
                                # Panggil API untuk update status
                                try:
                                    # Gunakan API manual-update yang lebih stabil
                                    requests.post(
                                        "http://localhost:5000/api/linkedin/manual-update",
                                        json={
                                            "status": True, 
                                            "message": f"Updated from WebDriver login process - URL: {current_url}"
                                        },
                                        timeout=5
                                    )
                                    logger.info("Status update API called successfully")
                                except Exception as api_e:
                                    logger.error(f"Error calling update API: {str(api_e)}")
                                
                                # Proses scraping profil jika URL tersedia
                                if profile_url:
                                    logger.info(f"Scraping profile: {profile_url}")
                                    try:
                                        # Wait for a moment
                                        time.sleep(2)
                                        
                                        # Buka profil LinkedIn
                                        driver.get(profile_url)
                                        time.sleep(5)  # Wait for profile page to open
                                        
                                        # Ambil data dari halaman
                                        name_element = driver.find_element(By.XPATH, "//h1")
                                        name = name_element.text if name_element else "Unknown"
                                        
                                        # Coba ambil data 'about'
                                        about = ""
                                        try:
                                            about_elements = driver.find_elements(By.XPATH, "//section[contains(@class,'summary')]//div[contains(@class,'display-flex')]")
                                            if about_elements:
                                                about = about_elements[0].text
                                        except:
                                            pass
                                        
                                        # Ekstrak job title/posisi dengan selector alternatif
                                        try:
                                            title_selectors = [
                                                "//div[contains(@class, 'text-body-medium')]",
                                                "//div[contains(@class, 'pv-text-details__left-panel')]/div",
                                                "//*[contains(@class, 'pv-text-details__left-panel')]//h2",
                                                "//div[contains(@class, 'ph5')]/div[contains(@class, 'mt2')]//div[contains(@class, 'text-body-medium')]"
                                            ]
                                            
                                            for selector in title_selectors:
                                                try:
                                                    elements = driver.find_elements(By.XPATH, selector)
                                                    for element in elements:
                                                        if element and element.text.strip():
                                                            text = element.text.strip()
                                                            # Jika teks terlalu panjang, mungkin bukan jabatan
                                                            if len(text) < 100:
                                                                profile_data["job_title"] = text
                                                                logger.info(f"Job title successfully extracted: {profile_data['job_title']}")
                                                                break
                                                    if profile_data.get("job_title"):
                                                        break
                                                except Exception as sel_err:
                                                    logger.debug(f"Error with selector {selector}: {str(sel_err)}")
                                        except Exception as sel_err:
                                            logger.debug(f"Error with selector {selector}: {str(sel_err)}")
                                            continue
                                        
                                        # Pastikan job_title selalu ada meskipun kosong
                                        if "job_title" not in profile_data:
                                            profile_data["job_title"] = ""
                                        
                                        # Hitung jumlah experience
                                        experiences = 0
                                        try:
                                            exp_elements = driver.find_elements(By.XPATH, "//section[contains(@class,'experience')]//li")
                                            experiences = len(exp_elements)
                                        except:
                                            pass
                                        
                                        # Hitung jumlah education
                                        educations = 0
                                        try:
                                            edu_elements = driver.find_elements(By.XPATH, "//section[contains(@class,'education')]//li")
                                            educations = len(edu_elements)
                                        except:
                                            pass
                                        
                                        # Kirim data ke endpoint scrape-profile
                                        profile_data = {
                                            "name": name,
                                            "about": about,
                                            "experiences": experiences,
                                            "educations": educations,
                                            "source_url": profile_url
                                        }
                                        
                                        try:
                                            api_url = "http://localhost:5000/api/linkedin/scrape-profile"
                                            response = requests.post(
                                                api_url,
                                                json={"profile_data": profile_data, "use_existing_session": True, "profile_url": profile_url},
                                                timeout=10
                                            )
                                            
                                            if response.status_code == 200:
                                                logger.info("Profile data successfully sent to backend")
                                            else:
                                                logger.error(f"Failed to send profile data: {response.status_code}")
                                        except Exception as e:
                                            logger.error(f"Error sending profile data: {str(e)}")
                                    except Exception as e:
                                        logger.error(f"Error scraping profile: {str(e)}")
                                
                                # Keluar dari loop setelah login berhasil
                                break
                        
                        # Wait before checking again
                        time.sleep(5)
                    
                    except Exception as url_e:
                        # Jika error mengakses URL, coba lagi
                        logger.warning(f"Error checking URL: {str(url_e)}")
                        time.sleep(5)
                
                if not login_successful:
                    logger.warning("Login timeout reached, no login detected")
                    # Update status login
                    linkedin_login_status = {
                        "logged_in": False,
                        "timestamp": datetime.now().isoformat(),
                        "message": "Login timeout reached, no login detected"
                    }
                    
                    # Tutup driver jika login gagal
                    try:
                        driver.quit()
                    except:
                        pass
            except Exception as e:
                logger.error(f"Error in login process: {str(e)}")
                # Tutup driver jika terjadi error
                try:
                    driver.quit()
                except:
                    pass
                
                # Update status login
                linkedin_login_status = {
                    "logged_in": False,
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Error dalam proses login: {str(e)}"
                }
        
        # Jalankan proses login di thread terpisah
        threading.Thread(target=login_process, daemon=True).start()
        
        # Return response
        return jsonify({
            "success": True,
            "message": "LinkedIn login process started. Please login in the opened browser window."
        })
        
    except Exception as e:
        logger.error(f"Error starting LinkedIn login process: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to start LinkedIn login process: {str(e)}"
        }), 500

@app.route('/api/linkedin/check-status-file', methods=['GET'])
def check_status_file():
    """Check LinkedIn login status from file"""
    global linkedin_driver, linkedin_login_status
    status_file = os.path.join(os.getcwd(), "linkedin_login_status.json")
    
    try:
        if os.path.exists(status_file):
            with open(status_file, "r") as f:
                status_data = json.load(f)
            
            # Perbarui status login global
            is_logged_in = status_data.get("status", False)
            
            # Jika ada URL di status data, coba buat driver baru
            browser_url = status_data.get("url", "")
            if is_logged_in and browser_url and "linkedin.com" in browser_url:
                logger.info(f"URL ditemukan di file status: {browser_url}")
                
                try:
                    # Buat driver baru
                    temp_driver = setup_chrome_driver()
                    temp_driver.get(browser_url)
                    time.sleep(3)  # Wait for browser to load
                    
                    # Jika berhasil dan tidak di halaman login
                    if "login" not in temp_driver.current_url:
                        # Update driver global
                        if linkedin_driver:
                            try:
                                linkedin_driver.quit()
                            except:
                                pass
                            
                        linkedin_driver = temp_driver
                        logger.info(f"Driver diperbarui berdasarkan URL dari file status: {temp_driver.current_url}")
                    else:
                        # Tutup driver jika tidak berhasil
                        temp_driver.quit()
                        logger.warning(f"URL di file status tidak valid: {browser_url}")
                except Exception as e:
                    logger.error(f"Error membuat driver dari URL di file status: {str(e)}")
                    try:
                        if 'temp_driver' in locals():
                            temp_driver.quit()
                    except:
                        pass
            
            linkedin_login_status = {
                "logged_in": is_logged_in,
                "timestamp": status_data.get("timestamp", datetime.now().isoformat()),
                "message": "Login status successfully updated from file"
            }
            
            # Hapus file status agar tidak digunakan lagi
            try:
                os.remove(status_file)
                logger.info("Status file successfully deleted after use")
            except Exception as e:
                logger.warning(f"Failed to delete status file: {str(e)}")
                
            return jsonify({
                "success": True,
                "logged_in": is_logged_in,
                "message": "Login status successfully updated from file"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Status file not found"
            })
    except Exception as e:
        logger.error(f"Error checking status file: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/api/linkedin/force-login', methods=['POST'])
def force_login_status():
    """Force update the LinkedIn login status without checking browser"""
    global linkedin_driver, linkedin_login_status
    
    try:
        data = request.json
        force_status = data.get('status', True)  # Default to logged in
        custom_message = data.get('message', "Status login diperbarui manual")
        
        # Update status login global tanpa membuka browser baru
        linkedin_login_status = {
            "logged_in": force_status,
            "timestamp": datetime.now().isoformat(),
            "message": custom_message
        }
        
        logger.info(f"LinkedIn login status forced to: {force_status}")
        
        return jsonify({
            "success": True,
            "logged_in": force_status,
            "message": f"LinkedIn login status successfully updated: {'Logged in' if force_status else 'Not logged in'}"
        })
    except Exception as e:
        logger.error(f"Error updating LinkedIn login status manually: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/api/linkedin/set-logged-in', methods=['GET'])
def set_logged_in():
    """Update LinkedIn login status to logged in (for browser access)"""
    global linkedin_login_status
    
    try:
        linkedin_login_status = {
            "logged_in": True,
            "timestamp": datetime.now().isoformat(),
            "message": "Login status successfully updated"
        }
        
        logger.info("LinkedIn login status set to TRUE via browser endpoint")
        
        # Return HTML untuk browser
        return """
        <html>
            <head>
                <title>LinkedIn Status Updated</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
                    .success { color: green; font-size: 24px; }
                    button { padding: 10px 20px; margin-top: 20px; cursor: pointer; }
                </style>
            </head>
            <body>
                <h1 class="success">LinkedIn login status successfully updated: Logged In</h1>
                <p>The status in the web application should now be changed to "Logged In".</p>
                <p>You can close this window and return to the application.</p>
                <button onclick="window.close()">Close Window</button>
            </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error updating LinkedIn login status via browser endpoint: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/api/linkedin/manual-update', methods=['POST'])
def manual_update_login():
    """Update LinkedIn login status manually from frontend"""
    global linkedin_login_status
    
    try:
        data = request.json
        status = data.get('status', True)
        message = data.get('message', 'Status login diperbarui secara manual dari frontend')
        
        linkedin_login_status = {
            "logged_in": status,
            "timestamp": datetime.now().isoformat(),
            "message": message
        }
        
        logger.info(f"LinkedIn login status manually updated to {status} from frontend")
        
        return jsonify({
            "success": True,
            "logged_in": status,
            "message": "Status login berhasil diperbarui"
        })
    except Exception as e:
        logger.error(f"Error updating LinkedIn login status manually from frontend: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/linkedin/browser-check', methods=['GET'])
def check_browser_session():
    """Check if there's an active LinkedIn session in a browser"""
    global linkedin_driver, linkedin_login_status
    
    try:
        # Coba buat driver baru untuk periksa status login
        logger.info("Creating new driver to check for active LinkedIn session")
        
        try:
            temp_driver = setup_chrome_driver()
            # Langsung akses feed LinkedIn
            temp_driver.get("https://www.linkedin.com/feed/")
            time.sleep(3)  # Berikan waktu untuk browser load
            
            # Cek apakah diarahkan ke halaman login
            current_url = temp_driver.current_url
            is_logged_in = "login" not in current_url
            
            logger.info(f"Browser check URL: {current_url}, logged in: {is_logged_in}")
            
            # Jika terdeteksi login (tidak di halaman login), perbarui
            if is_logged_in:
                # Jika browser sebelumnya masih ada, matikan
                if linkedin_driver:
                    try:
                        linkedin_driver.quit()
                    except:
                        pass
                
                # Gunakan driver baru sebagai driver global
                linkedin_driver = temp_driver
                linkedin_login_status = {
                    "logged_in": True,
                    "timestamp": datetime.now().isoformat(),
                    "message": "Login detected via browser check"
                }
                
                logger.info("Active LinkedIn session found and driver updated")
                
                return jsonify({
                    "success": True,
                    "logged_in": True,
                    "message": "Active LinkedIn session detected and driver updated"
                })
            else:
                # Tutup driver jika tidak terdeteksi login
                temp_driver.quit()
                logger.info("No active LinkedIn session found in browser")
                
                return jsonify({
                    "success": True,
                    "logged_in": False,
                    "message": "No active LinkedIn session detected in browser"
                })
                
        except Exception as e:
            logger.error(f"Error checking browser session: {str(e)}")
            # Pastikan driver sementara dimatikan jika terjadi error
            try:
                if 'temp_driver' in locals():
                    temp_driver.quit()
            except:
                pass
                
            return jsonify({
                "success": False,
                "error": f"Failed to check browser session: {str(e)}"
            })
            
    except Exception as e:
        logger.error(f"Error in browser session check: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/api/linkedin/verify-login', methods=['GET'])
def verify_linkedin_login():
    """Verify LinkedIn login by checking if the driver is still active and logged in"""
    global linkedin_driver, linkedin_login_status
    
    try:
        # Cek apakah driver masih aktif
        is_active = False
        is_logged_in = False
        message = ""
        
        if linkedin_driver:
            try:
                # Coba akses current_url untuk melihat apakah driver masih hidup
                current_url = linkedin_driver.current_url
                is_active = True
                
                # Jika URL mengandung indikasi halaman LinkedIn yang memerlukan login
                if any(domain in current_url for domain in ["linkedin.com/feed", "linkedin.com/checkpoint", "linkedin.com/in", "linkedin.com/mynetwork"]):
                    is_logged_in = True
                    message = f"Verified active session at {current_url}"
                    logger.info(f"LinkedIn driver active and logged in at URL: {current_url}")
                else:
                    message = f"Driver active but not on LinkedIn page: {current_url}"
                    logger.warning(message)
            except Exception as e:
                message = f"Error checking driver: {str(e)}"
                logger.error(message)
                is_active = False
        else:
            message = "No active Chrome driver instance found"
            logger.warning(message)
            
            # Jika tidak ada driver aktif, periksa file status saja
            status_file = os.path.join(os.getcwd(), "linkedin_login_status.json")
            if os.path.exists(status_file):
                try:
                    with open(status_file, "r") as f:
                        status_data = json.load(f)
                    is_logged_in = status_data.get("status", False)
                    if is_logged_in:
                        message = "Status login diambil dari file status"
                        logger.info(message)
                except Exception as file_e:
                    logger.error(f"Error reading status file: {str(file_e)}")
        
        # Update status login global berdasarkan pemeriksaan
        if is_active and is_logged_in:
            linkedin_login_status = {
                "logged_in": True,
                "timestamp": datetime.now().isoformat(),
                "message": "Login verified by active session check"
            }
        elif not is_active and not is_logged_in:
            # Driver tidak aktif dan tidak ada bukti login
            linkedin_login_status = {
                "logged_in": False,
                "timestamp": datetime.now().isoformat(),
                "message": "No active login detected"
            }
        
        return jsonify({
            "success": True,
            "driver_active": is_active,
            "logged_in": is_logged_in or linkedin_login_status.get("logged_in", False),
            "status": linkedin_login_status,
            "message": message
        })
    except Exception as e:
        error_msg = f"Error verifying LinkedIn login: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        })

@app.route('/api/linkedin/profile-details/<int:lead_id>', methods=['GET'])
def get_profile_details(lead_id):
    """Get detailed LinkedIn profile data for a specific lead"""
    try:
        leads = load_leads()
        lead = next((lead for lead in leads if lead.get("id") == lead_id), None)
        
        if not lead:
            return jsonify({"success": False, "error": "Lead not found"}), 404
        
        if not lead.get("source_url") or "linkedin.com" not in lead.get("source_url", ""):
            return jsonify({"success": False, "error": "Not a LinkedIn profile or missing URL"}), 400
        
        # Return existing detailed data
        return jsonify({
            "success": True,
            "profile": {
                "id": lead.get("id"),
                "name": lead.get("name", ""),
                "title": lead.get("title", ""),
                "company": lead.get("company", ""),
                "location": lead.get("location", ""),
                "about": lead.get("about", ""),
                "experiences": lead.get("experiences", []),
                "educations": lead.get("educations", []),
                "source_url": lead.get("source_url", ""),
                "email": lead.get("email", ""),
                "emails": lead.get("emails", [])
            }
        })
    except Exception as e:
        logger.error(f"Error getting profile details: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='LinkedIn Lead Generator API')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the API server on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to run the API server on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    # Run the app
    app.run(host=args.host, port=args.port, debug=args.debug) 