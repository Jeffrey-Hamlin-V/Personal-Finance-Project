import React, { useState } from 'react';

function DashboardHome({ setCurrentPage }) {
  const [showUploadModal, setShowUploadModal] = useState(false);

  const handleUploadCSV = () => {
    setShowUploadModal(true);
  };

  const handleUseExistingData = () => {
    alert('Loading dashboard with existing data...');
    // This will be connected to backend later
  };

  const handleLogout = () => {
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
          <div className="option-card" onClick={handleUploadCSV}>
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
        <div className="modal-overlay" onClick={() => setShowUploadModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Upload CSV File</h3>
            <div className="upload-area">
              <input type="file" accept=".csv" id="csv-upload" />
              <label htmlFor="csv-upload" className="upload-label">
                <div className="upload-icon">📁</div>
                <p>Click to browse or drag & drop your CSV file here</p>
              </label>
            </div>
            <div className="modal-actions">
              <button onClick={() => setShowUploadModal(false)}>Cancel</button>
              <button className="primary-btn" onClick={() => alert('CSV processing will be implemented with backend')}>
                Upload & Process
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default DashboardHome;