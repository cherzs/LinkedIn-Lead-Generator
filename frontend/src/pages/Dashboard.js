import React, { useState, useEffect } from 'react';
import '../styles/Dashboard.css';

const Dashboard = () => {
  const [leads, setLeads] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchLocation, setSearchLocation] = useState('');
  const [searchCount, setSearchCount] = useState(10);
  const [isSearching, setIsSearching] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [editingLead, setEditingLead] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);

  useEffect(() => {
    // Function to fetch lead data from backend
    const fetchLeads = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/leads');
        const data = await response.json();
        setLeads(data);
        setIsLoading(false);
      } catch (error) {
        console.error('Error fetching leads:', error);
        setIsLoading(false);
        setErrorMessage('Failed to fetch leads. Please try again.');
      }
    };

    fetchLeads();
  }, []);

  const handleGenerateLeads = async () => {
    if (!searchQuery.trim()) {
      setErrorMessage('Please enter a search query first');
      return;
    }

    setIsSearching(true);
    setErrorMessage('');

    try {
      // Combine search query with location if provided
      const fullQuery = searchLocation.trim() 
        ? `${searchQuery} ${searchLocation}` 
        : searchQuery;

      const response = await fetch('http://localhost:5000/api/leads/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: fullQuery,
          count: parseInt(searchCount),
          validate: true
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate leads');
      }

      const newLeads = await response.json();
      
      // Refresh data
      const updatedLeadsResponse = await fetch('http://localhost:5000/api/leads');
      const updatedLeads = await updatedLeadsResponse.json();
      setLeads(updatedLeads);
      
      setErrorMessage('');
    } catch (error) {
      console.error('Error generating leads:', error);
      setErrorMessage(error.message || 'Failed to generate leads. Please try again.');
    } finally {
      setIsSearching(false);
    }
  };

  const handleExportData = async () => {
    if (leads.length === 0) {
      setErrorMessage('No data to export');
      return;
    }

    try {
      // Create CSV file from leads data
      const headers = [
        'Name',
        'Position',
        'Company',
        'Location',
        'Email',
        'Email Status',
        'Profile URL'
      ];

      const csvRows = [
        headers.join(','),
        ...leads.map(lead => [
          `"${lead.name || ''}"`, 
          `"${lead.title || ''}"`,
          `"${lead.company || ''}"`,
          `"${lead.location || ''}"`,
          `"${lead.email || ''}"`,
          `"${lead.emailValid ? 'Valid' : lead.emailValid === false ? 'Invalid' : 'Not validated'}"`,
          `"${lead.profile_url || ''}"`
        ].join(','))
      ];

      const csvContent = csvRows.join('\n');
      
      // Create file and download
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', `linkedin_leads_${new Date().toISOString().slice(0,10)}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      setErrorMessage('');
    } catch (error) {
      console.error('Error exporting data:', error);
      setErrorMessage('Failed to export data. Please try again.');
    }
  };

  const handleEdit = (lead, index) => {
    setEditingLead({...lead, index});
    setShowEditModal(true);
  };

  const handleDelete = async (index) => {
    if (!window.confirm('Are you sure you want to delete this lead?')) {
      return;
    }

    try {
      const response = await fetch(`http://localhost:5000/api/leads/${index}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete lead');
      }

      // Update leads state by removing the deleted lead
      setLeads(prevLeads => prevLeads.filter((_, i) => i !== index));
    } catch (error) {
      console.error('Error deleting lead:', error);
      setErrorMessage('Failed to delete lead. Please try again.');
    }
  };

  const handleSaveEdit = async () => {
    try {
      const response = await fetch(`http://localhost:5000/api/leads/${editingLead.index}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: editingLead.name,
          title: editingLead.title,
          company: editingLead.company,
          location: editingLead.location,
          email: editingLead.email,
          emailValid: editingLead.emailValid || editingLead.email_valid,
          emailScore: editingLead.emailScore || editingLead.email_score,
          profile_url: editingLead.profile_url
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update lead');
      }

      const updatedLead = await response.json();

      // Update leads state with the edited lead
      setLeads(prevLeads => 
        prevLeads.map((lead, i) => 
          i === editingLead.index ? updatedLead : lead
        )
      );

      setShowEditModal(false);
      setEditingLead(null);
    } catch (error) {
      console.error('Error updating lead:', error);
      setErrorMessage('Failed to update lead. Please try again.');
    }
  };

  const handleEditInputChange = (e) => {
    const { name, value } = e.target;
    setEditingLead(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>LinkedIn Lead Generator</h1>
        <nav className="dashboard-nav">
          <button 
            className={`nav-button ${isSearching ? 'disabled' : ''}`}
            onClick={handleGenerateLeads}
            disabled={isSearching}
          >
            {isSearching ? 'Searching...' : 'Generate Leads'}
          </button>
          <button 
            className="nav-button"
            onClick={handleExportData}
            disabled={leads.length === 0 || isSearching}
          >
            Export Data
          </button>
          <button className="nav-button logout">Logout</button>
        </nav>
      </header>

      <main className="dashboard-content">
        {errorMessage && (
          <div className="error-message">
            {errorMessage}
          </div>
        )}

        <section className="search-section">
          <h2>Find New Leads</h2>
          <div className="search-controls">
            <div className="form-group">
              <label htmlFor="searchQuery">Job Title or Keywords</label>
              <input
                type="text"
                id="searchQuery"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="e.g. Software Engineer, Data Scientist"
                disabled={isSearching}
              />
            </div>
            <div className="form-group">
              <label htmlFor="searchLocation">Location</label>
              <input
                type="text"
                id="searchLocation"
                value={searchLocation}
                onChange={(e) => setSearchLocation(e.target.value)}
                placeholder="e.g. Jakarta, Indonesia"
                disabled={isSearching}
              />
            </div>
            <div className="form-group">
              <label htmlFor="searchCount">Number of Results</label>
              <input
                type="number"
                id="searchCount"
                value={searchCount}
                onChange={(e) => setSearchCount(e.target.value)}
                min="1"
                max="50"
                disabled={isSearching}
              />
            </div>
          </div>
        </section>

        <section className="lead-stats">
          <div className="stat-card">
            <h3>Total Leads</h3>
            <p>{leads.length}</p>
          </div>
          <div className="stat-card">
            <h3>Valid Emails</h3>
            <p>{leads.filter(lead => lead.emailValid || lead.email_valid).length}</p>
          </div>
          <div className="stat-card">
            <h3>Pending Validation</h3>
            <p>{leads.filter(lead => lead.emailValid === null || lead.email_valid === null).length}</p>
          </div>
        </section>

        <section className="lead-table-section">
          <h2>Recent Leads</h2>
          {isLoading ? (
            <p>Loading leads...</p>
          ) : (
            <table className="lead-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Position</th>
                  <th>Company</th>
                  <th>Location</th>
                  <th>Email</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {leads.length > 0 ? (
                  leads.map((lead, index) => (
                    <tr key={index}>
                      <td>{lead.name}</td>
                      <td>{lead.title}</td>
                      <td>{lead.company}</td>
                      <td>{lead.location}</td>
                      <td>{lead.email}</td>
                      <td>{lead.emailValid || lead.email_valid ? 'Valid' : (lead.emailValid === false || lead.email_valid === false) ? 'Invalid' : 'Pending'}</td>
                      <td>
                        <button 
                          className="action-btn" 
                          onClick={() => handleEdit(lead, index)}
                        >
                          Edit
                        </button>
                        <button 
                          className="action-btn delete" 
                          onClick={() => handleDelete(index)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="7">No leads found. Generate some leads to get started!</td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </section>

        {/* Edit Modal */}
        {showEditModal && editingLead && (
          <div className="modal-overlay">
            <div className="modal">
              <h2>Edit Lead</h2>
              <div className="form-group">
                <label htmlFor="name">Name</label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={editingLead.name}
                  onChange={handleEditInputChange}
                />
              </div>
              <div className="form-group">
                <label htmlFor="title">Position</label>
                <input
                  type="text"
                  id="title"
                  name="title"
                  value={editingLead.title}
                  onChange={handleEditInputChange}
                />
              </div>
              <div className="form-group">
                <label htmlFor="company">Company</label>
                <input
                  type="text"
                  id="company"
                  name="company"
                  value={editingLead.company}
                  onChange={handleEditInputChange}
                />
              </div>
              <div className="form-group">
                <label htmlFor="location">Location</label>
                <input
                  type="text"
                  id="location"
                  name="location"
                  value={editingLead.location}
                  onChange={handleEditInputChange}
                />
              </div>
              <div className="form-group">
                <label htmlFor="email">Email</label>
                <input
                  type="text"
                  id="email"
                  name="email"
                  value={editingLead.email}
                  onChange={handleEditInputChange}
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
    </div>
  );
};

export default Dashboard; 