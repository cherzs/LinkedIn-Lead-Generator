# LinkedIn Lead Generator

A tool to scrape website information and generate leads for LinkedIn outreach.

## Features

- 🌐 **Website Scraping**: Extract profile data from company websites
- 📊 **Lead Management**: Store, update, and manage leads
- 📝 **Data Cleaning**: Automatically normalize and deduplicate lead data
- 📤 **Export Options**: Export leads to CSV or Google Sheets

## Setup

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Installation

1. Clone this repository:
```
git clone https://github.com/yourusername/LinkedIn-Lead-Generator.git
cd LinkedIn-Lead-Generator
```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root directory and add your API keys:
```
# LinkedIn Scraping API Key (if you plan to use ScrapingDog)
SCRAPINGDOG_API_KEY="your_api_key_here"

# Other environment variables
# Add any other API keys or configuration here
```

## Running the Application

### Starting the API Server

Run the API server with:

```
python app.py
```

This will start the API server on http://localhost:5000 by default.

### API Endpoints

The API has the following endpoints:

- **GET `/api/leads`**: Get all leads
- **GET `/api/leads/<id>`**: Get a specific lead
- **POST `/api/leads`**: Add a new lead
- **PUT `/api/leads/<id>`**: Update a lead
- **DELETE `/api/leads/<id>`**: Delete a lead
- **POST `/api/scrape-website`**: Scrape a website for leads
- **POST `/api/clean-data`**: Clean and normalize leads data
- **POST `/api/clean-all`**: Complete reset and normalize leads data
- **POST `/api/export/csv`**: Export leads to CSV
- **POST `/api/export/sheets`**: Export leads to Google Sheets
- **GET `/api/status`**: Check API status

### Command Line Options

The API server can be configured with the following command line options:

- `--port <port>`: Port to run the API server on (default: 5000)
- `--host <host>`: Host to run the API server on (default: 0.0.0.0)
- `--debug`: Run in debug mode

## Frontend

The application includes a React frontend for a user-friendly experience. To start the frontend:

1. Navigate to the frontend directory:
```
cd frontend
```

2. Install dependencies:
```
npm install
```

3. Start the development server:
```
npm start
```

4. Open your browser and go to http://localhost:3000

## Data Storage

All lead data is stored in a local JSON file (`leads_data.json`) in the following format:

```json
[
  {
    "name": "Example Person",
    "title": "CEO",
    "company": "Example Company",
    "location": "New York, USA",
    "email": "example@example.com",
    "emails": ["example@example.com"],
    "source_url": "https://example.com"
  }
]
```

## Technical Architecture

The application consists of:

- **API Server** (`api.py`): Flask-based REST API for the application
- **Web Scraper** (`websitescraper.py`): Extracts profiles from websites
- **Sheets Exporter** (`sheets_exporter.py`): Handles exporting to CSV and Google Sheets
- **Frontend** (`/frontend`): React-based user interface

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 