import React, { useState, useEffect } from 'react';
import { Card, Button, Form, Alert, Spinner, Tabs, Tab } from 'react-bootstrap';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5000';

const LinkedIn = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginMethod, setLoginMethod] = useState('manual');
  const [profileUrl, setProfileUrl] = useState('');
  const [waitingForManualLogin, setWaitingForManualLogin] = useState(false);
  const [statusPolling, setStatusPolling] = useState(null);
  const [scrapedProfile, setScrapedProfile] = useState(null);

  // Check login status on component mount
  useEffect(() => {
    checkLoginStatus();
  }, []);

  // Poll for login status when waiting for manual login
  useEffect(() => {
    if (waitingForManualLogin) {
      const interval = setInterval(() => {
        checkLoginStatus();
      }, 3000);
      setStatusPolling(interval);
    } else if (statusPolling) {
      clearInterval(statusPolling);
      setStatusPolling(null);
    }
    return () => {
      if (statusPolling) clearInterval(statusPolling);
    };
  }, [waitingForManualLogin]);

  const checkLoginStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/linkedin/login-status`);
      const data = await response.json();
      setIsLoggedIn(data.logged_in);
      
      if (data.logged_in && waitingForManualLogin) {
        setWaitingForManualLogin(false);
        setMessage('Login successful! You can now scrape LinkedIn profiles.');
      }
    } catch (error) {
      console.error('Error checking login status:', error);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage(null);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/linkedin/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          login_method: loginMethod,
          email: loginMethod === 'automatic' ? email : undefined,
          password: loginMethod === 'automatic' ? password : undefined,
        }),
      });

      const data = await response.json();
      
      if (data.success) {
        if (data.status === 'waiting_for_login') {
          setWaitingForManualLogin(true);
          setMessage('Browser opened for manual login. Please login to LinkedIn in the browser window.');
        } else {
          setIsLoggedIn(true);
          setMessage(data.message || 'Login successful!');
        }
      } else {
        setError(data.error || 'Login failed');
      }
    } catch (error) {
      setError(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = async () => {
    setIsLoading(true);
    setMessage(null);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/linkedin/logout`, {
        method: 'POST',
      });

      const data = await response.json();
      
      if (data.success) {
        setIsLoggedIn(false);
        setMessage('Logged out successfully');
        setScrapedProfile(null);
      } else {
        setError(data.error || 'Logout failed');
      }
    } catch (error) {
      setError(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleScrapeProfile = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage(null);
    setError(null);
    setScrapedProfile(null);

    try {
      const response = await fetch(`${API_BASE}/api/linkedin/scrape-profile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          profile_url: profileUrl,
          use_existing_session: true,
          save: true
        }),
      });

      const data = await response.json();
      
      if (data.success) {
        setMessage('Profile scraped successfully!');
        setScrapedProfile(data.lead);
      } else {
        if (data.requires_login) {
          setError('You need to login to LinkedIn first');
        } else {
          setError(data.error || 'Failed to scrape profile');
        }
      }
    } catch (error) {
      setError(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="mb-4">
      <Card.Header>LinkedIn Tools</Card.Header>
      <Card.Body>
        {message && <Alert variant="success">{message}</Alert>}
        {error && <Alert variant="danger">{error}</Alert>}
        
        <Tabs defaultActiveKey="login" className="mb-3">
          <Tab eventKey="login" title="Login">
            {!isLoggedIn ? (
              <Form onSubmit={handleLogin}>
                <Form.Group className="mb-3">
                  <Form.Label>Login Method</Form.Label>
                  <Form.Select 
                    value={loginMethod}
                    onChange={(e) => setLoginMethod(e.target.value)}
                  >
                    <option value="manual">Manual Login (Browser Window)</option>
                    <option value="automatic">Automatic Login (Credentials)</option>
                  </Form.Select>
                </Form.Group>
                
                {loginMethod === 'automatic' && (
                  <>
                    <Form.Group className="mb-3">
                      <Form.Label>LinkedIn Email</Form.Label>
                      <Form.Control
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required={loginMethod === 'automatic'}
                      />
                    </Form.Group>
                    
                    <Form.Group className="mb-3">
                      <Form.Label>LinkedIn Password</Form.Label>
                      <Form.Control
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required={loginMethod === 'automatic'}
                      />
                    </Form.Group>
                  </>
                )}
                
                <Button 
                  variant="primary" 
                  type="submit" 
                  disabled={isLoading || waitingForManualLogin}
                >
                  {isLoading ? <Spinner animation="border" size="sm" /> : 'Login to LinkedIn'}
                </Button>
                
                {waitingForManualLogin && (
                  <Alert variant="info" className="mt-3">
                    <Spinner animation="border" size="sm" /> Waiting for you to complete login in the browser window...
                  </Alert>
                )}
              </Form>
            ) : (
              <div>
                <Alert variant="success">
                  You are logged in to LinkedIn
                </Alert>
                <Button 
                  variant="secondary" 
                  onClick={handleLogout}
                  disabled={isLoading}
                >
                  {isLoading ? <Spinner animation="border" size="sm" /> : 'Logout from LinkedIn'}
                </Button>
              </div>
            )}
          </Tab>
          
          <Tab eventKey="scrape" title="Scrape Profile">
            <Form onSubmit={handleScrapeProfile}>
              <Form.Group className="mb-3">
                <Form.Label>LinkedIn Profile URL</Form.Label>
                <Form.Control
                  type="url"
                  placeholder="https://www.linkedin.com/in/username"
                  value={profileUrl}
                  onChange={(e) => setProfileUrl(e.target.value)}
                  required
                />
                <Form.Text className="text-muted">
                  Enter the full URL of the LinkedIn profile you want to scrape
                </Form.Text>
              </Form.Group>
              
              <Button 
                variant="primary" 
                type="submit" 
                disabled={isLoading || !isLoggedIn}
              >
                {isLoading ? <Spinner animation="border" size="sm" /> : 'Scrape Profile'}
              </Button>
              
              {!isLoggedIn && (
                <Alert variant="warning" className="mt-3">
                  You need to login to LinkedIn first before scraping profiles
                </Alert>
              )}
            </Form>
            
            {scrapedProfile && (
              <div className="mt-4">
                <h5>Scraped Profile</h5>
                <div className="border rounded p-3">
                  <p><strong>Name:</strong> {scrapedProfile.name}</p>
                  {scrapedProfile.title && <p><strong>Title:</strong> {scrapedProfile.title}</p>}
                  {scrapedProfile.company && <p><strong>Company:</strong> {scrapedProfile.company}</p>}
                  {scrapedProfile.location && <p><strong>Location:</strong> {scrapedProfile.location}</p>}
                  
                  {scrapedProfile.about && (
                    <div className="mb-2">
                      <strong>About:</strong>
                      <p>{scrapedProfile.about}</p>
                    </div>
                  )}
                  
                  {scrapedProfile.experiences && scrapedProfile.experiences.length > 0 && (
                    <div className="mb-2">
                      <strong>Experience:</strong>
                      <ul>
                        {scrapedProfile.experiences.map((exp, i) => (
                          <li key={i}>
                            {exp.title} at {exp.company} {exp.duration && `(${exp.duration})`}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {scrapedProfile.educations && scrapedProfile.educations.length > 0 && (
                    <div className="mb-2">
                      <strong>Education:</strong>
                      <ul>
                        {scrapedProfile.educations.map((edu, i) => (
                          <li key={i}>
                            {edu.degree} at {edu.school}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
          </Tab>
        </Tabs>
      </Card.Body>
    </Card>
  );
};

export default LinkedIn; 