import React, { useState } from 'react';

function DashboardHome({ setCurrentPage }) {
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('');

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

    if (!userId) {
      alert('User ID not found. Please login again.');
      setCurrentPage('login');
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

      let data;
      try {
        data = await response.json();
      } catch (jsonError) {
        const text = await response.text();
        console.error('Failed to parse JSON response:', text);
        throw new Error(`Server error: ${response.status} ${response.statusText}. Response: ${text.substring(0, 200)}`);
      }

      if (response.ok) {
        setShowUploadModal(false);
        setSelectedFile(null);
        
        // Poll for upload completion
        const uploadId = data.upload_id;
        if (!uploadId) {
          console.error('No upload_id in response:', data);
          alert('Upload received but no upload ID. Redirecting to dashboard...');
          setTimeout(() => {
            setCurrentPage('visual-dashboard');
            setUploading(false);
          }, 2000);
          return;
        }

        let attempts = 0;
        const maxAttempts = 60; // 60 seconds max wait (processing can take time)
        
        const checkStatus = async () => {
          try {
            setUploadStatus(`Checking processing status... (${attempts + 1}/${maxAttempts})`);
            const statusResponse = await fetch(`http://localhost:8000/api/uploads/${uploadId}/status`);
            
            if (!statusResponse.ok) {
              // If status endpoint fails, redirect anyway after a delay
              console.warn('Status check failed, redirecting anyway');
              setUploadStatus('Status check unavailable. Redirecting...');
              setTimeout(() => {
                setCurrentPage('visual-dashboard');
                setUploading(false);
                setUploadStatus('');
              }, 3000);
              return;
            }

            const statusData = await statusResponse.json();
            console.log('Upload status:', statusData);
            
            if (statusData.status === 'completed') {
              setUploadStatus('Processing complete!');
              setTimeout(() => {
                alert('CSV processed successfully! Loading your dashboard...');
                setCurrentPage('visual-dashboard');
                setUploading(false);
                setUploadStatus('');
              }, 500);
            } else if (statusData.status === 'failed') {
              const errorMsg = statusData.error_message || 'Unknown error during processing';
              console.error('Upload processing failed:', errorMsg);
              
              // Show detailed error in alert
              const errorDisplay = errorMsg.length > 500 
                ? `${errorMsg.substring(0, 500)}...\n\n(Full error in console)` 
                : errorMsg;
              
              alert(`Processing failed:\n\n${errorDisplay}\n\nCheck the browser console and backend logs for full details.`);
              setUploading(false);
              setUploadStatus('');
            } else if (attempts < maxAttempts) {
              // Still processing, check again in 2 seconds
              attempts++;
              setUploadStatus(`Processing... (${Math.round(statusData.progress_pct || 0)}%)`);
              setTimeout(checkStatus, 2000);
            } else {
              // Timeout - redirect anyway, data might still be processing
              console.warn('Status check timeout, redirecting to dashboard');
              setUploadStatus('Processing taking longer than expected. Redirecting...');
              setTimeout(() => {
                alert('Upload received! Processing may still be in progress. Redirecting to dashboard...');
                setCurrentPage('visual-dashboard');
                setUploading(false);
                setUploadStatus('');
              }, 1000);
            }
          } catch (error) {
            console.error('Status check error:', error);
            // If status check fails repeatedly, redirect anyway after a delay
            if (attempts >= 5) {
              setUploadStatus('Redirecting to dashboard...');
              setTimeout(() => {
                alert('Upload received! Redirecting to dashboard...');
                setCurrentPage('visual-dashboard');
                setUploading(false);
                setUploadStatus('');
              }, 1000);
            } else {
              attempts++;
              setTimeout(checkStatus, 2000);
            }
          }
        };
        
        // Start checking status after a short delay
        setTimeout(checkStatus, 2000);
      } else {
        // Handle different error status codes
        const errorMsg = data.detail || data.error || `HTTP ${response.status}: ${response.statusText}`;
        console.error('Upload failed:', errorMsg, data);
        alert(`Upload failed: ${errorMsg}`);
        setUploading(false);
      }
    } catch (error) {
      console.error('Upload error:', error);
      const errorMsg = error.message || 'Network error. Please check if the backend server is running at http://localhost:8000';
      alert(`Failed to upload file: ${errorMsg}`);
      setUploading(false);
    }
  };

  const handleUseExistingData = () => {
    // Navigate to visual dashboard with existing data
    setCurrentPage('visual-dashboard');
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
            {uploadStatus && (
              <div style={{ 
                padding: '12px', 
                marginBottom: '16px', 
                backgroundColor: '#2a2f3a', 
                borderRadius: '6px',
                fontSize: '14px',
                color: '#e5e7eb',
                textAlign: 'center'
              }}>
                {uploadStatus}
              </div>
            )}
            <div className="modal-actions">
              <button onClick={() => {
                setShowUploadModal(false);
                setUploadStatus('');
                setSelectedFile(null);
              }} disabled={uploading}>
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