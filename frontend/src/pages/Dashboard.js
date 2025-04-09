import React, { useState, useEffect } from 'react';
import '../styles/Dashboard.css';
import { Link } from 'react-router-dom';

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
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);

  useEffect(() => {
    fetchLeads();
    checkLinkedinLoginStatus();
    
    // Poll for LinkedIn login status more frequently
    const interval = setInterval(checkLinkedinLoginStatus, 5000);  // Poll every 5 seconds instead of 10
    
    // Check if LinkedIn is already opened in another tab
    tryDetectLinkedInBrowser();
    
    return () => clearInterval(interval);
  }, []);

  const checkLinkedinLoginStatus = async () => {
    try {
      console.log('Checking LinkedIn login status...');
      
      // Tambah random query parameter untuk menghindari caching
      const timestamp = new Date().getTime();
      
      // Gunakan endpoint verifikasi terlebih dahulu
      try {
        console.log('Calling verify-login endpoint...');
        const verifyResponse = await fetch(`http://localhost:5000/api/linkedin/verify-login?_t=${timestamp}`);
        const verifyData = await verifyResponse.json();
        
        console.log('Verify login response:', verifyData);
        
        if (verifyData.success) {
          // Update status berdasarkan verifikasi aktif
          if (verifyData.logged_in) {
            setIsLinkedinLoggedIn(true);
            setMessage({
              text: 'LinkedIn session detected may not be accurate. Browser session may be closed.',
              type: 'warning'
            });
            return;
          }
          
          // If driver is not active but login status is still true, show message
          if (!verifyData.driver_active && verifyData.status.logged_in) {
            setMessage({
              text: 'LinkedIn session detected may not be accurate. Browser session may be closed.',
              type: 'warning'
            });
          }
        }
      } catch (verifyError) {
        console.error('Error verifying LinkedIn status:', verifyError);
      }
      
      // Fallback to endpoint status login standard
      const response = await fetch(`http://localhost:5000/api/linkedin/login-status?_t=${timestamp}`);
      const data = await response.json();
      
      console.log('Login status response:', data);
      
      if (data.logged_in) {
        setIsLinkedinLoggedIn(true);
        setMessage({
          text: 'Login status successfully updated: Logged In',
          type: 'success'
        });
        return; // If already logged in, no need to check again
      } else {
        setIsLinkedinLoggedIn(false);
      }
      
      // If not logged in, try to check status file as fallback
      try {
        const fileStatusResponse = await fetch(`http://localhost:5000/api/linkedin/check-status-file?_t=${timestamp}`);
        const fileStatusData = await fileStatusResponse.json();
        
        console.log('File status response:', fileStatusData);
        
        if (fileStatusData.success && fileStatusData.logged_in) {
          console.log('Login status successfully retrieved from file');
          setIsLinkedinLoggedIn(true);
          setMessage({
            text: 'Login status updated from status file',
            type: 'success'
          });
        }
      } catch (fileError) {
        console.error('Error checking status file:', fileError);
      }
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

  const handleDelete = async (leadId) => {
    if (window.confirm('Are you sure you want to delete this lead?')) {
      try {
        setIsLoading(true);
        const response = await fetch(`http://localhost:5000/api/leads/${leadId}`, {
          method: 'DELETE'
        });
        
        if (response.ok) {
          // Hapus lead dari state
          setLeads(leads.filter(lead => lead.id !== leadId));
          setMessage({
            text: 'Lead successfully deleted',
            type: 'success'
          });
        } else {
          const data = await response.json();
          setMessage({
            text: data.error || 'Failed to delete lead',
            type: 'error'
          });
        }
      } catch (error) {
        console.error("Error deleting lead:", error);
        setMessage({
          text: 'Error saat menghapus lead',
          type: 'error'
        });
      } finally {
        setIsLoading(false);
      }
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
      // Normalisasi URL LinkedIn
      let profileUrl = linkedinId.trim();
      
      // Jika hanya username, tambahkan URL lengkap
      if (!profileUrl.includes('linkedin.com') && !profileUrl.startsWith('http')) {
        // Hapus @ jika ada
        if (profileUrl.startsWith('@')) {
          profileUrl = profileUrl.substring(1);
        }
        
        // Hapus karakter non-alfanumerik dan strip
        profileUrl = profileUrl.replace(/[^a-zA-Z0-9-]/g, '');
        
        // Tambahkan URL lengkap
        profileUrl = `https://www.linkedin.com/in/${profileUrl}`;
        console.log('Normalized LinkedIn URL:', profileUrl);
      }
      
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

      const scrapeResult = await response.json();
      
      // Cek error secara spesifik
      if (!response.ok) {
        if (response.status === 401) {
          // Error login
          setMessage({ 
            text: `You need to login to LinkedIn first. Click the "Force Login" or "Run LinkedIn Login" button`, 
            type: 'error' 
          });
        } else {
          // Error lainnya
          throw new Error(scrapeResult.error || `Failed to scrape LinkedIn profile (Error ${response.status})`);
        }
      } else if (!scrapeResult.success) {
        setMessage({ 
          text: scrapeResult.error || `Could not find profile for "${linkedinId}"`, 
          type: 'error' 
        });
      } else {
        setMessage({ 
          text: scrapeResult.message || `Successfully scraped LinkedIn profile`, 
          type: 'success' 
        });
        // Bersihkan input setelah berhasil
        setLinkedinId('');
        // Sembunyikan form LinkedIn
        setShowLinkedinForm(false);
        
        // Refresh data profil
        fetchLeads();
      }
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
        // If profile URL exists, add to request
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
        
        // Reset URL if successfully sent for scraping
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

  // Fungsi untuk deteksi keberadaan LinkedIn di tab lain dan set login otomatis
  const tryDetectLinkedInBrowser = () => {
    console.log("Trying to detect LinkedIn browser already logged in...");
    
    // Panggil force-login endpoint dengan lebih agresif
    fetch('http://localhost:5000/api/linkedin/force-login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        status: true,
        message: "Auto-detection check pada load halaman"
      })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success && data.logged_in) {
        console.log("Login status successfully forced:", data);
        // Segera update status
        setIsLinkedinLoggedIn(true);
        setMessage({
          text: 'Login status updated to Logged In manually',
          type: 'success'
        });
      } else {
        console.log("Could not auto-detect LinkedIn login");
        // Coba cek status file sebagai fallback
        setTimeout(() => {
          fetch('http://localhost:5000/api/linkedin/check-status-file', {
            method: 'GET'
          })
          .then(response => response.json())
          .then(fileData => {
            if (fileData.success && fileData.logged_in) {
              console.log("Session LinkedIn terdeteksi via file status");
              setIsLinkedinLoggedIn(true);
              setMessage({
                text: 'Login status updated from status file',
                type: 'success'
              });
            }
          })
          .catch(err => {
            console.error("Error pada file status check:", err);
          });
        }, 5000);
      }
    })
    .catch(err => {
      console.error("Error force login:", err);
    });
  };

  // Fungsi untuk menampilkan detail profil
  const viewProfileDetails = async (leadId) => {
    try {
      setIsLoading(true);
      const response = await fetch(`http://localhost:5000/api/linkedin/profile-details/${leadId}`);
      const data = await response.json();
      
      if (data.success) {
        setSelectedProfile(data.profile);
        setIsProfileModalOpen(true);
      } else {
        setMessage({
          text: data.error || 'Failed to retrieve profile details',
          type: 'error'
        });
      }
    } catch (error) {
      console.error("Error fetching profile details:", error);
      setMessage({
        text: 'Error while fetching profile details',
        type: 'error'
      });
    } finally {
      setIsLoading(false);
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
                <>
                  <span className="text-success">Logged In</span>
                  <button 
                    onClick={() => {
                      // Panggil API untuk reset status login
                      fetch('http://localhost:5000/api/linkedin/force-login', {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ status: false })
                      })
                      .then(response => response.json())
                      .then(data => {
                        if (data.success) {
                          setIsLinkedinLoggedIn(false);
                          setMessage({ 
                            text: 'Login status updated to Not Logged In', 
                            type: 'warning' 
                          });
                        }
                      })
                      .catch(err => {
                        console.error("Error resetting login status:", err);
                      });
                    }}
                    style={{
                      marginLeft: '10px',
                      padding: '3px 8px',
                      fontSize: '12px',
                      color: '#d32f2f',
                      background: 'none',
                      border: '1px solid #d32f2f',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    Reset Status
                  </button>
                </>
              ) : (
                <>
                  <span className="text-danger">Not Logged In</span>
                  
                  {/* Tombol Force Update Status Baru */}
                  <button 
                    onClick={() => {
                      // Panggil API force login
                      fetch('http://localhost:5000/api/linkedin/force-login', {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ 
                          status: true,
                          message: "Status updated manually from UI"
                        })
                      })
                      .then(response => response.json())
                      .then(data => {
                        if (data.success) {
                          setIsLinkedinLoggedIn(true);
                          setMessage({ 
                            text: 'Login status updated to Logged In manually', 
                            type: 'success' 
                          });
                        }
                      })
                      .catch(err => {
                        console.error("Error updating login status:", err);
                      });
                    }}
                    style={{
                      marginLeft: '10px',
                      padding: '5px 12px',
                      fontSize: '14px',
                      color: 'white',
                      background: '#4caf50',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontWeight: 'bold',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                      display: 'inline-flex',
                      alignItems: 'center'
                    }}
                  >
                    <span role="img" aria-label="force" style={{ marginRight: '5px' }}>⚡</span>
                    Force Login
                  </button>
                </>
              )}
              {!isLinkedinLoggedIn && (
                <div className="login-actions">
                  <div className="login-help-box" style={{
                    border: '2px dashed #2196f3',
                    borderRadius: '5px',
                    padding: '15px',
                    marginBottom: '15px',
                    backgroundColor: '#e3f2fd'
                  }}>
                    <h3 style={{ color: '#1976d2', margin: '0 0 10px', fontSize: '16px' }}>
                      <span role="img" aria-label="tip">💡</span> Login LinkedIn
                    </h3>
                  </div>
                  
                  <div className="button-group" style={{ display: 'flex', gap: '10px' }}>
                    <button 
                      className="login-button"
                      onClick={handleRunTestScraper}
                      disabled={isRunningTestScraper}
                      style={{ flex: '1' }}
                    >
                      {isRunningTestScraper ? (
                        <span className="button-with-loader">
                          <span className="button-loader"></span>
                          Starting Login...
                        </span>
                      ) : 'Run LinkedIn Login'}
                    </button>
                    <button 
                      className="refresh-button"
                      onClick={() => {
                        // Cek status secara manual
                        checkLinkedinLoginStatus();
                        // Tampilkan pesan sedang refresh
                        setMessage({ 
                          text: 'Memeriksa status login LinkedIn...', 
                          type: 'info' 
                        });
                        // Set ulang pesan setelah beberapa detik
                        setTimeout(() => {
                          setMessage({
                            text: isLinkedinLoggedIn 
                              ? 'Login status successfully updated: Logged In' 
                              : 'Login status updated: Still Not Logged In',
                            type: isLinkedinLoggedIn ? 'success' : 'warning'
                          });
                        }, 1000);
                      }}
                      style={{ flex: '1' }}
                    >
                      Refresh Status
                    </button>
                  </div>
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
                      <th>Company</th>
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
                            {lead.company ? (
                              <div className="dropdown-container">
                                <div 
                                  className="company-name"
                                  onClick={() => {
                                    setSelectedProfile(lead);
                                    setIsProfileModalOpen(true);
                                  }}
                                >
                                  {lead.company}
                                </div>
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
                          <td className="action-cell">
                            <button
                              className="view-button"
                              onClick={() => viewProfileDetails(lead.id)}
                            >
                              <i className="fas fa-eye"></i> Detail
                            </button>
                            <Link to={`/edit/${lead.id}`} className="edit-button">
                              <i className="fas fa-edit"></i> Edit
                            </Link>
                            <button
                              className="delete-button"
                              onClick={() => handleDelete(lead.id)}
                            >
                              <i className="fas fa-trash"></i> Delete
                            </button>
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

      {/* Modal Detail Profil */}
      {isProfileModalOpen && selectedProfile && (
        <div className="profile-modal">
          <div className="profile-modal-content">
            <div className="profile-modal-header">
              <h2>{selectedProfile.name || "Profile Details"}</h2>
              <button 
                className="close-button" 
                onClick={() => setIsProfileModalOpen(false)}
              >
                &times;
              </button>
            </div>
            <div className="profile-modal-body">
              <div className="profile-section">
                <h3>Basic Information</h3>
                <p><strong>Name:</strong> {selectedProfile.name || "Not available"}</p>
                <p><strong>Position:</strong> {selectedProfile.title || "Not available"}</p>
                <p><strong>Company:</strong> {selectedProfile.company || "Not available"}</p>
                <p><strong>Location:</strong> {selectedProfile.location || "Not available"}</p>
                <p><strong>Email:</strong> {selectedProfile.email || "Not available"}</p>
              </div>
              
              {selectedProfile.about && (
                <div className="profile-section">
                  <h3>About</h3>
                  <div className="profile-about">
                    {selectedProfile.about}
                  </div>
                </div>
              )}
              
              {selectedProfile.experiences && selectedProfile.experiences.length > 0 && (
                <div className="profile-section">
                  <h3>Experience ({selectedProfile.experiences.length})</h3>
                  <ul className="experience-list no-dots">
                    {selectedProfile.experiences.map((exp, index) => (
                      <li key={`exp-${index}`} className="experience-item">
                        <div className="experience-title">{exp.title || "Position not specified"}</div>
                        {exp.company && <div className="experience-company">{exp.company}</div>}
                        {exp.duration && <div className="experience-duration">{exp.duration}</div>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {selectedProfile.educations && selectedProfile.educations.length > 0 && (
                <div className="profile-section">
                  <h3>Education ({selectedProfile.educations.length})</h3>
                  <ul className="education-list no-dots">
                    {selectedProfile.educations.map((edu, index) => (
                      <li key={`edu-${index}`} className="education-item">
                        <div className="education-school">{edu.school || "Institution not specified"}</div>
                        {edu.degree && <div className="education-degree">{edu.degree}</div>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              <div className="profile-section">
                <h3>Source</h3>
                <a 
                  href={selectedProfile.source_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="profile-source-link"
                >
                  View Original LinkedIn Profile
                </a>
              </div>
            </div>
            <div className="profile-modal-footer">
              <button 
                className="close-modal-button" 
                onClick={() => setIsProfileModalOpen(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard; 
