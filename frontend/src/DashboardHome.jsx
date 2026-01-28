import React, { useState } from 'react';

function DashboardHome({ setCurrentPage }) {
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  const userId = localStorage.getItem('user_id');

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file && file.name.endsWith('.csv')) {
      setSelectedFile(file);
    } else {
      alert('Please select a CSV file');
    }
  };

  const handleUploadCSV = async () => {
    if (!selectedFile) {
      alert('Please select a file first');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(`http://localhost:8000/api/upload?user_id=${userId}`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        alert('CSV uploaded successfully! Processing your data...');
        setShowUploadModal(false);
        // Wait a bit for processing, then redirect to D3 dashboard
        setTimeout(() => {
          setCurrentPage('d3-dashboard');
        }, 2000);
      } else {
        alert(`Upload failed: ${data.detail}`);
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('Failed to upload file. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleUseExistingData = () => {
    // Navigate to D3 dashboard with existing data
    setCurrentPage('d3-dashboard');
  };

  const handleLogout = () => {
    localStorage.removeItem('user_id');
    localStorage.removeItem('email');
    setCurrentPage('login');
  };

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="dashboard-logo">💰 Finance Intelligence</h1>
          <button className="logout-btn" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      {/* Main Content */}
      <div className="dashboard-main">
        <div className="welcome-section">
          <h2>Welcome Back!</h2>
          <p>Choose how you'd like to proceed with your financial data</p>
        </div>

        <div className="options-grid">
          <div className="option-card" onClick={() => setShowUploadModal(true)}>
            <div className="option-icon">📊</div>
            <h3>Upload New CSV</h3>
            <p>Upload a new transaction file to create a fresh dashboard</p>
          </div>

          <div className="option-card" onClick={handleUseExistingData}>
            <div className="option-icon">📈</div>
            <h3>Use Existing Data</h3>
            <p>Continue with your previously uploaded financial data</p>
          </div>
        </div>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="modal-overlay" onClick={() => !uploading && setShowUploadModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Upload CSV File</h3>
            <div className="upload-area">
              <input 
                type="file" 
                accept=".csv" 
                id="csv-upload" 
                onChange={handleFileSelect}
                disabled={uploading}
              />
              <label htmlFor="csv-upload" className="upload-label">
                <div className="upload-icon">📁</div>
                {selectedFile ? (
                  <p>Selected: {selectedFile.name}</p>
                ) : (
                  <p>Click to browse or drag & drop your CSV file here</p>
                )}
              </label>
            </div>
            <div className="modal-actions">
              <button onClick={() => setShowUploadModal(false)} disabled={uploading}>
                Cancel
              </button>
              <button 
                className="primary-btn" 
                onClick={handleUploadCSV}
                disabled={!selectedFile || uploading}
              >
                {uploading ? 'Uploading...' : 'Upload & Process'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default DashboardHome;