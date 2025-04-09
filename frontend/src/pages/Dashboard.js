import React, { useState, useEffect } from 'react';
import '../styles/Dashboard.css';

const Dashboard = () => {
  const [leads, setLeads] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });
  const [editingLead, setEditingLead] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [linkedinId, setLinkedinId] = useState('');
  const [isScrapingLinkedin, setIsScrapingLinkedin] = useState(false);
  const [showLinkedinForm, setShowLinkedinForm] = useState(false);
  // eslint-disable-next-line no-unused-vars
  const [useAdvancedScraping, _setUseAdvancedScraping] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [importData, setImportData] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [isLinkedinLoggedIn, setIsLinkedinLoggedIn] = useState(false);
  const [isRunningTestScraper, setIsRunningTestScraper] = useState(false);

  useEffect(() => {
    fetchLeads();
    checkLinkedinLoginStatus();
    
    // Poll for LinkedIn login status
    const interval = setInterval(checkLinkedinLoginStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const checkLinkedinLoginStatus = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/linkedin/login-status');
      const data = await response.json();
      setIsLinkedinLoggedIn(data.logged_in);
    } catch (error) {
      console.error('Error checking LinkedIn login status:', error);
    }
  };

  // eslint-disable-next-line no-unused-vars
  const handleLinkedInLoginStatusChange = (status) => {
    setIsLinkedinLoggedIn(status);
  };

  const fetchLeads = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/leads');
      const data = await response.json();
      
      // Process data for display
      const processedData = data.map(lead => {
        // Ensure company name is properly formatted
        if (lead.company) {
          // Capitalize each word in company name
          lead.company = lead.company
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(' ');
        }
        
        // Process emails array for backward compatibility
        if (!lead.emails && lead.email) {
          lead.emails = lead.email.split(',').map(e => e.trim()).filter(Boolean);
        }
        
        // If name is same as company or contains domain, use company as name
        if (lead.name) {
          if (lead.name.toLowerCase() === lead.company?.toLowerCase() || lead.name.includes('.')) {
            lead.name = lead.company;
          } else {
            // Capitalize each word in name
            lead.name = lead.name
              .split(' ')
              .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
              .join(' ');
          }
        } else if (lead.company) {
          lead.name = lead.company;
        }
        
        // Clean up title field
        if (lead.title) {
          // Remove extra spaces and newlines
          let cleanTitle = lead.title.replace(/\s+/g, ' ').trim();
          
          // Capitalize first letter
          if (cleanTitle.length > 0) {
            lead.title = cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1);
          }
        }
        
        return lead;
      });
      
      setLeads(processedData);
      setIsLoading(false);
    } catch (error) {
      console.error('Error fetching leads:', error);
      setIsLoading(false);
      setMessage({ 
        text: 'Failed to fetch profiles. Please try again.', 
        type: 'error' 
      });
    }
  };

  const handleExportData = async () => {
    if (leads.length === 0) {
      setMessage({ text: 'No data to export', type: 'error' });
      return;
    }

    try {
      const headers = ['Name', 'Position', 'Company', 'Location', 'Email', 'Source URL'];
      const csvRows = [
        headers.join(','),
        ...leads.map(lead => [
          `"${lead.name || ''}"`, 
          `"${lead.title || ''}"`,
          `"${lead.company || ''}"`,
          `"${lead.location || ''}"`,
          `"${lead.email || ''}"`,
          `"${lead.source_url || ''}"`
        ].join(','))
      ];

      const csvContent = csvRows.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', `profiles_export_${new Date().toISOString().slice(0,10)}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      setMessage({ text: 'Data exported successfully', type: 'success' });
    } catch (error) {
      console.error('Error exporting data:', error);
      setMessage({ text: 'Failed to export data', type: 'error' });
    }
  };

  const handleEdit = (lead, index) => {
    setEditingLead({...lead, index});
    setShowEditModal(true);
  };

  const handleDelete = async (index) => {
    if (!window.confirm('Delete this profile?')) {
      return;
    }

    try {
      const response = await fetch(`http://localhost:5000/api/leads/${index}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete profile');
      }

      setLeads(prevLeads => prevLeads.filter((_, i) => i !== index));
      setMessage({ text: 'Profile deleted', type: 'success' });
    } catch (error) {
      console.error('Error deleting lead:', error);
      setMessage({ text: 'Failed to delete profile', type: 'error' });
    }
  };

  const handleEditInputChange = (e) => {
    const { name, value } = e.target;
    
    if (name === 'email') {
      // When editing email field, update both email and emails array
      const emailArray = value.split(',').map(e => e.trim()).filter(Boolean);
      setEditingLead(prev => ({
        ...prev,
        [name]: value,
        emails: emailArray
      }));
    } else {
      setEditingLead(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };

  const handleSaveEdit = async () => {
    try {
      // Make sure emails array is up to date with the email field
      const updatedLead = {
        ...editingLead
      };
      
      // Make sure we have both email string and emails array consistent
      if (updatedLead.email && !updatedLead.emails) {
        updatedLead.emails = updatedLead.email.split(',').map(e => e.trim()).filter(Boolean);
      } else if (updatedLead.emails && updatedLead.emails.length > 0) {
        updatedLead.email = updatedLead.emails.join(', ');
      }
      
      const response = await fetch(`http://localhost:5000/api/leads/${editingLead.index}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: updatedLead.name,
          title: updatedLead.title,
          company: updatedLead.company,
          location: updatedLead.location,
          email: updatedLead.email,
          emails: updatedLead.emails,
          source_url: updatedLead.source_url
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update profile');
      }

      // We don't need to use the response data since we're using our local updatedLead object
      await response.json(); // Still parse the response but don't assign to variable

      setLeads(prevLeads => 
        prevLeads.map((lead, i) => 
          i === editingLead.index ? updatedLead : lead
        )
      );

      setShowEditModal(false);
      setEditingLead(null);
      setMessage({ text: 'Profile updated', type: 'success' });
    } catch (error) {
      console.error('Error updating lead:', error);
      setMessage({ text: 'Failed to update profile', type: 'error' });
    }
  };

  const handleScrapeWebsite = async () => {
    if (!websiteUrl.trim()) {
      setMessage({ text: 'Please enter a website URL', type: 'error' });
      return;
    }

    setIsSearching(true);
    setMessage({ text: 'Scraping website...', type: 'info' });

    try {
      const response = await fetch('http://localhost:5000/api/scrape-website', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: websiteUrl.trim() }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || errorData.message || 'Failed to scrape website');
      }

      const scrapeResult = await response.json();
      
      if (!scrapeResult.results || scrapeResult.results.length === 0) {
        setMessage({ 
          text: `No profiles found on "${websiteUrl}"`, 
          type: 'error' 
        });
      } else {
        setMessage({ 
          text: `Found ${scrapeResult.results.length} profiles`, 
          type: 'success' 
        });
      }
      
      fetchLeads();
    } catch (error) {
      console.error('Error scraping website:', error);
      setMessage({ 
        text: error.message || 'Failed to scrape website', 
        type: 'error' 
      });
    } finally {
      setIsSearching(false);
    }
  };

  const handleScrapeLinkedin = async () => {
    if (!linkedinId.trim()) {
      setMessage({ text: 'Please enter a LinkedIn profile URL', type: 'error' });
      return;
    }

    if (!isLinkedinLoggedIn) {
      setMessage({ text: 'Please login to LinkedIn first', type: 'error' });
      return;
    }
    
    setIsScrapingLinkedin(true);
    setMessage({ text: 'Scraping LinkedIn profile...', type: 'info' });

    try {
      const profileUrl = `https://www.linkedin.com/in/${linkedinId.trim()}`;
      const response = await fetch('http://localhost:5000/api/linkedin/scrape-profile', {
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

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || errorData.message || 'Failed to scrape LinkedIn profile');
      }

      const scrapeResult = await response.json();
      
      if (!scrapeResult.success) {
        setMessage({ 
          text: `No profile found for LinkedIn URL "${linkedinId}"`, 
          type: 'error' 
        });
      } else {
        setMessage({ 
          text: scrapeResult.message || `Successfully scraped LinkedIn profile`, 
          type: 'success' 
        });
        // Clear the input field after successful scraping
        setLinkedinId('');
        // Hide the LinkedIn form
        setShowLinkedinForm(false);
      }
      
      fetchLeads();
    } catch (error) {
      console.error('Error scraping LinkedIn profile:', error);
      setMessage({ 
        text: error.message || 'Failed to scrape LinkedIn profile', 
        type: 'error' 
      });
    } finally {
      setIsScrapingLinkedin(false);
    }
  };

  const handleCleanData = async () => {
    if (!window.confirm('This will group profiles by company and clean the data. Continue?')) {
      return;
    }
    
    try {
      setIsLoading(true);
      setMessage({ text: 'Cleaning data...', type: 'info' });
      
      const response = await fetch('http://localhost:5000/api/clean-data', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to clean data');
      }
      
      const result = await response.json();
      
      if (result.success) {
        setMessage({ text: 'Data cleaned successfully', type: 'success' });
        // Fetch the cleaned data
        fetchLeads();
      } else {
        setMessage({ text: result.message || 'No changes made', type: 'info' });
        setIsLoading(false);
      }
    } catch (error) {
      console.error('Error cleaning data:', error);
      setMessage({ text: 'Failed to clean data', type: 'error' });
      setIsLoading(false);
    }
  };

  const handleCleanAllData = async () => {
    if (!window.confirm('This will completely reorganize all data, removing duplicates and fixing formatting. Continue?')) {
      return;
    }
    
    try {
      setIsLoading(true);
      setMessage({ text: 'Cleaning all data...', type: 'info' });
      
      const response = await fetch('http://localhost:5000/api/clean-all', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to clean data');
      }
      
      const result = await response.json();
      
      if (result.success) {
        setMessage({ text: result.message || 'Data cleaned successfully', type: 'success' });
        // Fetch the cleaned data
        fetchLeads();
      } else {
        setMessage({ text: result.message || 'No changes made', type: 'info' });
        setIsLoading(false);
      }
    } catch (error) {
      console.error('Error cleaning all data:', error);
      setMessage({ text: 'Failed to clean data', type: 'error' });
      setIsLoading(false);
    }
  };

  const handleAdvancedScrape = async () => {
    if (!websiteUrl.trim()) {
      setMessage({ text: 'Please enter a website URL', type: 'error' });
      return;
    }

    setIsSearching(true);
    setMessage({ text: 'Advanced scraping in progress...', type: 'info' });

    try {
      const response = await fetch('http://localhost:5000/api/scrape-website', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          url: websiteUrl.trim()
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || errorData.message || 'Failed to scrape website');
      }

      const scrapeResult = await response.json();
      
      if (!scrapeResult.results || scrapeResult.results.length === 0) {
        setMessage({ 
          text: `No profiles found on "${websiteUrl}" using advanced scraping`, 
          type: 'error' 
        });
      } else {
        setMessage({ 
          text: `Found ${scrapeResult.results.length} profiles using advanced scraping`, 
          type: 'success' 
        });
      }
      
      fetchLeads();
    } catch (error) {
      console.error('Error with advanced scraping:', error);
      setMessage({ 
        text: error.message || 'Failed to scrape website', 
        type: 'error' 
      });
    } finally {
      setIsSearching(false);
    }
  };

  const handleImportData = async () => {
    if (!importData.trim()) {
      setMessage({ text: 'Please enter data to import', type: 'error' });
      return;
    }

    setIsImporting(true);
    setMessage({ text: 'Importing data...', type: 'info' });

    try {
      // Try to parse the imported data as JSON
      let profileData;
      try {
        profileData = JSON.parse(importData.trim());
      } catch (e) {
        // If not valid JSON, assume it's a plain text description
        profileData = {
          name: importData.trim().split('\n')[0], // First line is name
          description: importData.trim() // Full text as description
        };
      }

      const response = await fetch('http://localhost:5000/api/import-data', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ profile_data: profileData }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || errorData.message || 'Failed to import data');
      }

      const result = await response.json();
      
      setMessage({ 
        text: result.message || 'Successfully imported profile data', 
        type: 'success' 
      });
      
      // Clear the import data field
      setImportData('');
      
      // Close the import modal
      setShowImportModal(false);
      
      // Refresh the leads list
      fetchLeads();
    } catch (error) {
      console.error('Error importing data:', error);
      setMessage({ 
        text: error.message || 'Failed to import data', 
        type: 'error' 
      });
    } finally {
      setIsImporting(false);
    }
  };

  const handleRunTestScraper = async () => {
    setIsRunningTestScraper(true);
    setMessage({ text: 'Starting LinkedIn login script...', type: 'info' });

    try {
      // Persiapkan data untuk dikirim ke API
      const requestData = {};
      if (linkedinId) {
        // Jika ada URL profil, tambahkan ke request
        requestData.profile_url = linkedinId;
      }

      const response = await fetch('http://localhost:5000/api/run-test-scraper', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || errorData.message || 'Failed to run LinkedIn login script');
      }

      const result = await response.json();
      
      if (result.success) {
        setMessage({ 
          text: linkedinId 
            ? 'LinkedIn login script started. Please follow the instructions in the opened browser window. Profile will be scraped automatically.'
            : 'LinkedIn login script started. Please follow the instructions in the opened browser window.',
          type: 'success' 
        });
        
        // Reset URL jika berhasil dikirim untuk scraping
        if (linkedinId) {
          setLinkedinId('');
        }
        
        // Set timeout untuk check status login setelah beberapa saat
        setTimeout(checkLinkedinLoginStatus, 5000);
      } else {
        setMessage({ 
          text: result.error || 'Failed to start LinkedIn login script',
          type: 'error' 
        });
      }
    } catch (error) {
      console.error('Error running test_scraper.py:', error);
      setMessage({ 
        text: error.message || 'Failed to run LinkedIn login script',
        type: 'error' 
      });
    } finally {
      setIsRunningTestScraper(false);
    }
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>Profile Scraper</h1>
        <nav className="dashboard-nav">
          <button 
            className="nav-button"
            onClick={handleExportData}
            disabled={leads.length === 0 || isSearching || isLoading}
          >
            Export
          </button>
          <button className="nav-button logout">Logout</button>
        </nav>
      </header>

      <main className="dashboard-content">
        {message.text && (
          <div className={`${message.type}-message`}>
            {message.text}
          </div>
        )}

        <section className="search-section">
          <h2>Extract Profiles</h2>
          
          <div className="search-tabs">
            
          </div>
          
          <div className="search-controls">
            <div className="linkedin-status">
              <strong>LinkedIn Status:</strong>{' '}
              {isLinkedinLoggedIn ? (
                <span className="text-success">Logged In</span>
              ) : (
                <span className="text-danger">Not Logged In</span>
              )}
              {!isLinkedinLoggedIn && (
                <div className="login-actions">
                  <p className="login-message">
                    You need to login to LinkedIn before scraping profiles.
                    {linkedinId && (
                      <span className="emphasized-text"> Your entered URL will be scraped automatically after login.</span>
                    )}
                  </p>
                  <button 
                    className="login-button"
                    onClick={handleRunTestScraper}
                    disabled={isRunningTestScraper}
                  >
                    {isRunningTestScraper ? (
                      <span className="button-with-loader">
                        <span className="button-loader"></span>
                        Starting Login...
                      </span>
                    ) : 'Run LinkedIn Login'}
                  </button>
                </div>
              )}
            </div>
            <div className="form-group">
              <input
                type="text"
                value={linkedinId || ''}
                onChange={(e) => setLinkedinId(e.target.value)}
                placeholder="Enter LinkedIn profile URL here"
                disabled={isScrapingLinkedin}
                style={{width: '300px'}}
              />
            </div>
            <button 
              className={`search-button ${isScrapingLinkedin ? 'disabled' : ''}`}
              onClick={handleScrapeLinkedin}
              disabled={isScrapingLinkedin || !linkedinId || !isLinkedinLoggedIn}
              style={{
                padding: '6px 12px', 
                fontSize: '13px',
                width: '110px',
                height: '34px',
                minWidth: 'unset',
                borderRadius: '4px',
                margin: '0 0 0 10px'
              }}
            >
              {isScrapingLinkedin ? (
                <span className="button-with-loader">
                  <span className="button-loader"></span>
                  Scraping
                </span>
              ) : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{marginRight: '5px'}}>
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  </svg>
                  Scrape
                </>
              )}
            </button>            
          </div>
        </section>

        <div className="stats-and-table">
          <section className="lead-stats">
            <div className="stat-card">
              <h3>Profiles</h3>
              <p>{leads.length}</p>
            </div>
            <div className="stat-card">
              <h3>Companies</h3>
              <p>{new Set(leads.map(lead => lead.company?.toLowerCase()).filter(Boolean)).size}</p>
            </div>
            <div className="stat-card">
              <h3>Locations</h3>
              <p>{new Set(leads.map(lead => lead.location?.toLowerCase()).filter(Boolean)).size}</p>
            </div>
          </section>

          <section className="lead-table-section">
            <h2>Extracted Profiles</h2>
            {isLoading ? (
              <div className="loading-spinner">
                <div className="spinner"></div>
                <div className="loading-text">Loading profiles...</div>
              </div>
            ) : (
              <div className="table-container">
                <table className="lead-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>About</th>
                      <th>Experiences</th>
                      <th>Educations</th>
                      <th>Source</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.length > 0 ? (
                      leads.map((lead, index) => (
                        <tr key={index}>
                          <td>{lead.name || '—'}</td>
                          <td>
                            {lead.about ? (
                              <div 
                                className="about-content"
                                data-content={lead.about}
                              >
                                {lead.about.length > 100 ? lead.about.substring(0, 100) + '...' : lead.about}
                                {lead.about.length > 100 && (
                                  <span className="view-more-tooltip">Hover to see more</span>
                                )}
                              </div>
                            ) : '—'}
                          </td>
                          <td>
                            {lead.experiences ? (
                              <div className="badge">{lead.experiences.length}</div>
                            ) : '—'}
                          </td>
                          <td>
                            {lead.educations ? (
                              <div className="badge">{lead.educations.length}</div>
                            ) : '—'}
                          </td>
                          <td>
                            {lead.source_url ? (
                              <a href={lead.source_url} target="_blank" rel="noopener noreferrer" className="source-link">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                                  <polyline points="15 3 21 3 21 9"></polyline>
                                  <line x1="10" y1="14" x2="21" y2="3"></line>
                                </svg>
                              </a>
                            ) : '—'}
                          </td>
                          <td>
                            <div className="action-buttons">
                              <button 
                                className="action-btn" 
                                onClick={() => handleEdit(lead, index)}
                              >
                                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{marginRight: '3px'}}>
                                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                                </svg>
                                Edit
                              </button>
                              <button 
                                className="action-btn delete" 
                                onClick={() => handleDelete(index)}
                              >
                                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{marginRight: '3px'}}>
                                  <polyline points="3 6 5 6 21 6"></polyline>
                                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                  <line x1="10" y1="11" x2="10" y2="17"></line>
                                  <line x1="14" y1="11" x2="14" y2="17"></line>
                                </svg>
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="6" className="empty-state">
                          <div className="empty-state-message">
                            <p>No profiles found</p>
                            <small>Scrape a LinkedIn profile to get started</small>
                          </div>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>

        {showEditModal && editingLead && (
          <div className="modal-overlay">
            <div className="modal">
              <h2>Edit Profile</h2>
              <div className="form-group">
                <label htmlFor="name">Name</label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={editingLead.name || ''}
                  onChange={handleEditInputChange}
                  placeholder="Full name"
                />
              </div>
              <div className="form-group">
                <label htmlFor="about">About</label>
                <textarea
                  id="about"
                  name="about"
                  value={editingLead.about || ''}
                  onChange={handleEditInputChange}
                  placeholder="About information"
                  rows={4}
                />
              </div>
              <div className="form-group">
                <label htmlFor="company">Company</label>
                <input
                  type="text"
                  id="company"
                  name="company"
                  value={editingLead.company || ''}
                  onChange={handleEditInputChange}
                  placeholder="Company name"
                />
              </div>
              <div className="form-group">
                <label htmlFor="location">Location</label>
                <input
                  type="text"
                  id="location"
                  name="location"
                  value={editingLead.location || ''}
                  onChange={handleEditInputChange}
                  placeholder="City, Country"
                />
              </div>
              <div className="form-group">
                <label htmlFor="source_url">Source URL</label>
                <input
                  type="text"
                  id="source_url"
                  name="source_url"
                  value={editingLead.source_url || ''}
                  onChange={handleEditInputChange}
                  placeholder="https://"
                />
              </div>
              <div className="modal-actions">
                <button 
                  className="action-btn" 
                  onClick={handleSaveEdit}
                >
                  Save
                </button>
                <button 
                  className="action-btn delete" 
                  onClick={() => {
                    setShowEditModal(false);
                    setEditingLead(null);
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
      
      {/* Import Data Modal */}
      {showImportModal && (
        <div className="modal-overlay">
          <div className="modal">
            <h2>Import Profile Data</h2>
            <div className="form-group">
              <label htmlFor="importData">Enter JSON or Profile Information</label>
              <textarea
                id="importData"
                name="importData"
                value={importData}
                onChange={(e) => setImportData(e.target.value)}
                placeholder={`Enter JSON data or profile information. Example:\n{\n  "name": "John Doe",\n  "about": "Professional summary...",\n  "experiences": [],\n  "educations": []\n}`}
                rows={10}
                disabled={isImporting}
              />
            </div>
            <div className="modal-actions">
              <button 
                className="action-btn" 
                onClick={handleImportData}
                disabled={isImporting || !importData.trim()}
              >
                {isImporting ? (
                  <span className="button-with-loader">
                    <span className="button-loader"></span>
                    Importing
                  </span>
                ) : 'Import'}
              </button>
              <button 
                className="action-btn delete" 
                onClick={() => {
                  setShowImportModal(false);
                  setImportData('');
                }}
                disabled={isImporting}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard; 
