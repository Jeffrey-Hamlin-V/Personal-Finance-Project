import React from 'react';

function LoginPage({ setCurrentPage }) {
  return (
    <div className="auth-container">
      <div className="auth-box">
        <div className="app-title">
          💰 Personal Finance <span>Intelligence</span>
        </div>

        <p className="tagline">
          Track spending. Detect anomalies. Gain insights.
        </p>

        <div className="input-group">
          <input
            type="text"
            placeholder="Email or User ID"
          />
        </div>

        <div className="input-group">
          <input
            type="password"
            placeholder="Password"
          />
        </div>

        <button onClick={() => setCurrentPage('dashboard')}>Login</button>

        <p className="toggle-text">
          New user? <span onClick={() => setCurrentPage('signup')}>Create an account</span>
        </p>
      </div>
    </div>
  );
}

export default LoginPage;