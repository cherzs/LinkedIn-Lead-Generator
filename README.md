# LinkedIn Lead Generator

A powerful tool to scrape and collect LinkedIn profile data for lead generation and sales outreach. This application allows you to automate LinkedIn profile scraping while collecting essential contact information.

## Features

- LinkedIn profile scraping with detailed information extraction
- Clean, modern UI for managing leads
- Interactive dashboard to monitor and control the scraping process
- Export functionality to CSV
- Contact information validation
- Profile data organization and search

## Installation

### Prerequisites

- Python 3.8 or higher
- Node.js and npm
- Chrome browser installed
- ChromeDriver matching your Chrome version

### Setup

1. Clone the repository:
```bash
git clone https://github.com/cherzs/LinkedIn-Lead-Generator.git
cd LinkedIn-Lead-Generator
```

2. Install backend dependencies:
```bash
pip install -r requirements.txt
```

3. Install frontend dependencies:
```bash
cd frontend
npm install
cd ..
```

4. Configure ChromeDriver:
   - Download ChromeDriver matching your Chrome version from [ChromeDriver official site](https://chromedriver.chromium.org/downloads)
   - Place it in the `drivers/chromedriver-win64/` directory (for Windows)
   - Or set the path in your environment variables

## Usage

1. Start the backend server:
```bash
python app.py
```

2. Start the frontend development server:
```bash
cd frontend
npm start
```

3. Access the application at `http://localhost:3000`

4. Login to LinkedIn:
   - Click on "Run LinkedIn Login" in the dashboard
   - When Chrome opens, manually log in to your LinkedIn account
   - The session will be captured for scraping

5. Start scraping profiles:
   - Enter a LinkedIn profile URL or username in the search box
   - Click "Scrape" to extract profile data
   - View results in the dashboard

## Technical Details

- Backend: Flask (Python)
- Frontend: React with custom styling
- Browser Automation: Selenium
- Data Storage: Local JSON files with optional API endpoints

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

Copyright (c) 2024 Muhammad Zhafran Ghaly (Cherzs)

## Disclaimer

This tool is for educational purposes only. Use responsibly and in accordance with LinkedIn's Terms of Service. The developer is not responsible for any misuse of this application or violation of LinkedIn's terms.

## Contact

Muhammad Zhafran Ghaly (Cherzs) - [GitHub Profile](https://github.com/cherzs) 