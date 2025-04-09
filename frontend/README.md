# LinkedIn Login Integration

This guide explains how to integrate the new LinkedIn login functionality into your Dashboard.

## 1. Start the Backend Server

First, make sure your backend API server is running on the correct port:

```bash
python app.py --port 5000 --debug
```

## 2. Add the LinkedIn Component to Dashboard

Import and add the LinkedIn component to your Dashboard component:

```jsx
// In Dashboard.js
import LinkedIn from './LinkedIn';

// Add this to your Dashboard render method, where appropriate:
<div className="row">
  <div className="col-12">
    <LinkedIn />
  </div>
</div>
```

## 3. Update Environment Variables

Make sure your frontend is configured to use the correct API endpoint:

```
// In .env file or environment variables
REACT_APP_API_BASE=http://localhost:5000
```

## 4. New LinkedIn Workflow

The new LinkedIn integration provides the following workflow:

1. **Login to LinkedIn**: Users first need to login to LinkedIn using either:
   - **Manual login**: Opens a browser window where they can manually enter credentials
   - **Automatic login**: Uses provided credentials (email/password)

2. **Session Management**: The backend maintains the LinkedIn session for subsequent scraping operations

3. **Profile Scraping**: After login, users can enter a LinkedIn profile URL to scrape

4. **Logout**: Users can logout when finished, which closes the browser session

## 5. API Endpoints

The following new API endpoints are available:

- `POST /api/linkedin/login`: Login to LinkedIn
- `GET /api/linkedin/login-status`: Check current login status
- `POST /api/linkedin/logout`: Logout from LinkedIn
- `POST /api/linkedin/scrape-profile`: Scrape a LinkedIn profile (now uses persistent sessions)

## 6. Troubleshooting

- If you encounter connection errors, make sure both frontend and backend are running and using the correct ports
- For login issues, try the manual login method, which shows the browser window and allows you to see any LinkedIn security challenges
- Check the Chrome browser window to see if LinkedIn is showing any security verification steps
- Review the logs in the terminal where the backend is running for detailed error information 