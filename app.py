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

# Import LinkedIn scraper
from linkedin_scraper import Person, actions
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
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

def get_domain_from_url(url):
    """Extract domain from URL"""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

def setup_chrome_driver():
    """Setup and return a Chrome WebDriver instance"""
    chromedriver_path = os.getenv("CHROMEDRIVER", os.path.join(os.getcwd(), "drivers/chromedriver-linux64/chromedriver"))
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
        if use_existing_session and linkedin_driver and linkedin_login_status["logged_in"]:
            driver = linkedin_driver
            logger.info("Using existing LinkedIn session")
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
                # Give user 60 seconds to login manually
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
                    "message": "Logged in successfully"
                }
            else:
                logger.error("Login unsuccessful")
                driver.quit()
                return {"success": False, "error": "Login to LinkedIn failed. Please check credentials or try manual login."}
        
        # Scrape the profile
        logger.info(f"Starting profile scraping: {profile_url}")
        person = Person(profile_url, driver=driver, close_on_complete=False)
        
        # Create lead from scraped profile
        lead = {
            "name": person.name,
            "title": person.job_title if person.job_title else "",
            "company": person.company if person.company else "",
            "location": person.location if hasattr(person, 'location') else "",
            "email": "",  # LinkedIn doesn't expose email
            "emails": [],
            "source_url": profile_url,
            "about": person.about if person.about else "",
            "experiences": [
                {
                    "title": exp.position_title, 
                    "company": exp.institution_name,
                    "duration": exp.duration
                } for exp in person.experiences
            ] if hasattr(person, 'experiences') else [],
            "educations": [
                {
                    "school": edu.institution_name,
                    "degree": edu.degree
                } for edu in person.educations
            ] if hasattr(person, 'educations') else []
        }
        
        return {"success": True, "lead": lead}
            
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
            '/api/scrape-website',
            '/api/linkedin/scrape-profile',
            '/api/clean-data',
            '/api/export/csv',
            '/api/export/sheets',
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
        
        # If there's already an active session, close it
        if linkedin_driver:
            try:
                linkedin_driver.quit()
            except:
                pass
            linkedin_driver = None
        
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
    """Check if user is logged in to LinkedIn"""
    global linkedin_driver, linkedin_login_status
    
    if linkedin_driver and linkedin_login_status["logged_in"] == False:
        # Check if user has completed manual login
        try:
            if "feed" in linkedin_driver.current_url or "checkpoint" in linkedin_driver.current_url:
                linkedin_login_status = {
                    "logged_in": True,
                    "timestamp": datetime.now().isoformat(),
                    "message": "Logged in manually"
                }
        except:
            # Session might be broken
            linkedin_login_status = {
                "logged_in": False,
                "timestamp": datetime.now().isoformat(),
                "message": "Session error, please login again"
            }
    
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
        
        if not profile_url:
            return jsonify({"error": "LinkedIn profile URL is required"}), 400
            
        if not profile_url.startswith('https://www.linkedin.com/'):
            return jsonify({"error": "Invalid LinkedIn profile URL"}), 400
        
        # Check if we need to ensure login first
        if not linkedin_login_status["logged_in"] and use_existing_session:
            return jsonify({
                "success": False, 
                "error": "Not logged in to LinkedIn. Please login first.",
                "requires_login": True
            }), 401
            
        # Scrape the LinkedIn profile
        result = scrape_linkedin_profile(
            profile_url, 
            login_method, 
            email, 
            password, 
            use_existing_session=use_existing_session
        )
        
        if not result["success"]:
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
        return jsonify({"error": str(e)}), 500

@app.route('/api/scrape-website', methods=['POST'])
def scrape_website():
    """Scrape a website for leads"""
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        # Fetch the webpage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract profile data
        profile = extract_profile_data(soup, url)
        
        # If company not found, use domain name as fallback
        if not profile.get("company"):
            profile["company"] = get_domain_from_url(url)
        
        # Clean the profile data
        profile = clean_leads_data([profile])[0]
        
        # Check if we should save
        save_profile = data.get('save', False)
        if save_profile:
            leads = load_leads()
            
            # Check if this profile already exists by URL
            existing_lead = next((lead for lead in leads if lead.get("source_url") == url), None)
            
            if existing_lead:
                # Update existing lead
                for key, value in profile.items():
                    if value and not existing_lead.get(key):
                        existing_lead[key] = value
                profile = existing_lead
            else:
                # Add new lead
                profile["id"] = generate_lead_id(leads)
                leads.append(profile)
            
            save_leads(leads)
        
        return jsonify({"success": True, "profile": profile})
    except Exception as e:
        logger.error(f"Error scraping website: {str(e)}")
        return jsonify({"error": str(e)}), 500

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

@app.route('/api/export/sheets', methods=['POST'])
def export_sheets():
    """Export leads to Google Sheets"""
    # This function would require Google Sheets API setup
    # For now, just return a message
    return jsonify({
        "message": "Google Sheets export not implemented yet. Please set up Google Sheets API credentials.",
        "instructions": "See SETUP.md for instructions on setting up Google Sheets API."
    })

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
    """Run the test_scraper.py script in a separate process"""
    try:
        logger.info("Starting test_scraper.py script")
        
        # Get the absolute path to test_scraper.py
        script_path = os.path.join(os.getcwd(), "test_scraper.py")
        
        # Start the script as a separate process
        process = subprocess.Popen(
            ["python3", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Return success response (script runs in background)
        return jsonify({
            "success": True,
            "message": "LinkedIn login script started successfully. Please follow the instructions in the browser window."
        })
        
    except Exception as e:
        logger.error(f"Error running test_scraper.py: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to run LinkedIn login script: {str(e)}"
        }), 500

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='LinkedIn Lead Generator API')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the API server on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to run the API server on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    # Run the app
    app.run(host=args.host, port=args.port, debug=args.debug) 