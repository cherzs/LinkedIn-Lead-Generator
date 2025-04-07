from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
import time
from dotenv import load_dotenv
import json

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

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Contoh data lead untuk frontend
sample_leads = []

# Path untuk menyimpan data
LEADS_FILE = 'leads_data.json'

def load_leads():
    """Load leads data from file or return empty list"""
    if os.path.exists(LEADS_FILE):
        try:
            with open(LEADS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading leads data: {e}")
            return []
    return []  # Return empty list if file doesn't exist

def save_leads(leads):
    """Save leads data to file"""
    try:
        with open(LEADS_FILE, 'w') as f:
            json.dump(leads, f)
        return True
    except Exception as e:
        logger.error(f"Error saving leads data: {e}")
        return False

@app.route('/')
def index():
    """Root endpoint untuk mengecek apakah API berjalan"""
    return jsonify({
        "status": "online",
        "message": "LinkedIn Lead Generator API",
        "endpoints": [
            "/api/leads",
            "/api/leads/<id>",
            "/api/leads/search",
            "/api/auth/login",
            "/api/auth/register"
        ]
    })

@app.route('/api/leads', methods=['GET'])
def get_leads():
    """Get all leads"""
    leads = load_leads()
    return jsonify(leads)

@app.route('/api/leads/<int:lead_id>', methods=['GET'])
def get_lead(lead_id):
    """Get a specific lead by ID (index)"""
    leads = load_leads()
    if lead_id >= 0 and lead_id < len(leads):
        return jsonify(leads[lead_id])
    return jsonify({"error": "Lead not found"}), 404

@app.route('/api/leads', methods=['POST'])
def add_lead():
    """Add a new lead"""
    lead = request.json
    leads = load_leads()
    leads.append(lead)
    save_leads(leads)
    return jsonify(lead), 201

@app.route('/api/leads/<int:lead_id>', methods=['PUT'])
def update_lead(lead_id):
    """Update an existing lead"""
    lead = request.json
    leads = load_leads()
    if lead_id >= 0 and lead_id < len(leads):
        leads[lead_id] = lead
        save_leads(leads)
        return jsonify(lead)
    return jsonify({"error": "Lead not found"}), 404

@app.route('/api/leads/<int:lead_id>', methods=['DELETE'])
def delete_lead(lead_id):
    """Delete a lead"""
    leads = load_leads()
    if lead_id >= 0 and lead_id < len(leads):
        deleted_lead = leads.pop(lead_id)
        save_leads(leads)
        return jsonify(deleted_lead)
    return jsonify({"error": "Lead not found"}), 404

@app.route('/api/leads/search', methods=['POST'])
def search_leads():
    """Search for new leads using LinkedIn scraper"""
    data = request.json
    search_query = data.get('query', '')
    location = data.get('location', '')
    count = data.get('count', 10)
    validate = data.get('validate', False)
    
    if not search_query:
        return jsonify({"error": "Search query is required"}), 400
    
    # Gabungkan query dengan lokasi jika ada
    if location:
        full_query = f"{search_query} {location}"
    else:
        full_query = search_query
    
    try:
        # Inisialisasi LinkedIn scraper
        linkedin_scraper = LinkedInScraper()
        
        # Jalankan scraper
        logger.info(f"Starting scraping with query: {full_query}")
        profile_results = linkedin_scraper.run_scraper(full_query, count)
        
        # Jika scraper tidak menemukan hasil, berikan pesan
        if not profile_results:
            logger.warning(f"No profiles found for query: {full_query}")
            return jsonify({"error": f"No profiles found for '{full_query}'. Try different keywords."}), 404
            
        logger.info(f"Successfully got {len(profile_results)} profiles")
        
        # Validasi dan perkaya data email jika diminta
        if validate:
            logger.info("Validating emails...")
            email_validator = EmailValidator()
            
            for profile in profile_results:
                enriched_profile = email_validator.enrich_profile_with_email(profile)
                
                # Ubah nama field email_valid menjadi emailValid untuk konsistensi dengan frontend
                if 'email_valid' in enriched_profile:
                    enriched_profile['emailValid'] = enriched_profile['email_valid']
                if 'email_score' in enriched_profile:
                    enriched_profile['emailScore'] = enriched_profile['email_score']
                
                profile.update(enriched_profile)
                
            logger.info("Email validation complete")
        
        # Tambahkan hasil ke data yang ada
        existing_leads = load_leads()
        existing_leads.extend(profile_results)
        save_leads(existing_leads)
        
        return jsonify(profile_results)
        
    except Exception as e:
        logger.error(f"Error searching for leads: {str(e)}")
        return jsonify({"error": f"Failed to search for leads: {str(e)}"}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Simulate login (for demo purposes)"""
    data = request.json
    email = data.get('email', '')
    password = data.get('password', '')
    
    # Untuk demo, terima login dengan kredensial apapun
    if email and password:
        return jsonify({
            "token": "sample_jwt_token_1234567890",
            "user": {
                "email": email,
                "name": "Demo User"
            }
        })
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Simulate registration (for demo purposes)"""
    data = request.json
    email = data.get('email', '')
    password = data.get('password', '')
    name = data.get('name', '')
    
    if email and password and name:
        return jsonify({
            "message": "User registered successfully",
            "user": {
                "email": email,
                "name": name
            }
        }), 201
    return jsonify({"error": "Invalid registration data"}), 400

@app.route('/api/search', methods=['POST'])
def search_profiles():
    """
    API endpoint untuk mencari profil LinkedIn
    """
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Query parameter is required'}), 400
    
    search_query = data.get('query')
    location = data.get('location', '')
    count = data.get('count', 10)
    validate_emails = data.get('validate', False)
    
    # Gabungkan query dengan lokasi jika ada
    if location:
        full_query = f"{search_query} {location}"
    else:
        full_query = search_query
    
    try:
        # Inisialisasi LinkedIn scraper
        linkedin_scraper = LinkedInScraper()
        
        # Jalankan scraper
        logger.info(f"Memulai scraping melalui API dengan query: {full_query}")
        profile_results = linkedin_scraper.run_scraper(full_query, count)
        
        if not profile_results:
            return jsonify({'message': 'No profiles found', 'results': []}), 200
            
        logger.info(f"Berhasil mendapatkan {len(profile_results)} profil")
        
        # Validasi dan perkaya data email jika diminta
        if validate_emails:
            logger.info("Memvalidasi email...")
            email_validator = EmailValidator()
            
            for profile in profile_results:
                enriched_profile = email_validator.enrich_profile_with_email(profile)
                profile.update(enriched_profile)
                
            logger.info("Validasi email selesai")
        
        return jsonify({
            'message': f'Successfully found {len(profile_results)} profiles',
            'results': profile_results
        }), 200
    
    except Exception as e:
        logger.error(f"Error saat menjalankan pencarian: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/csv', methods=['POST'])
def export_to_csv():
    """
    API endpoint untuk mengekspor profil ke CSV
    """
    data = request.json
    
    if not data or 'profiles' not in data:
        return jsonify({'error': 'Profiles data is required'}), 400
    
    profiles = data.get('profiles')
    filename = data.get('filename', 'leads_export.csv')
    
    try:
        exporter = SheetsExporter()
        success = exporter.export_to_csv(profiles, filename)
        
        if success:
            return jsonify({
                'message': f'Successfully exported {len(profiles)} profiles to {filename}',
                'filename': filename
            }), 200
        else:
            return jsonify({'error': 'Failed to export to CSV'}), 500
    
    except Exception as e:
        logger.error(f"Error saat mengekspor ke CSV: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/sheets', methods=['POST'])
def export_to_sheets():
    """
    API endpoint untuk mengekspor profil ke Google Sheets
    """
    data = request.json
    
    if not data or 'profiles' not in data:
        return jsonify({'error': 'Profiles data is required'}), 400
    
    profiles = data.get('profiles')
    worksheet_name = data.get('worksheet', 'Leads')
    
    try:
        exporter = SheetsExporter()
        success = exporter.export_profiles(profiles, worksheet_name)
        
        if success:
            sheet_url = exporter.get_spreadsheet_url()
            return jsonify({
                'message': f'Successfully exported {len(profiles)} profiles to Google Sheets',
                'url': sheet_url
            }), 200
        else:
            return jsonify({'error': 'Failed to export to Google Sheets'}), 500
    
    except Exception as e:
        logger.error(f"Error saat mengekspor ke Google Sheets: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def status():
    """
    API endpoint untuk cek status
    """
    return jsonify({
        'status': 'ok',
        'message': 'LinkedIn Lead Generator API is running'
    }), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 