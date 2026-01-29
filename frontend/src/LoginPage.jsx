import React, { useState } from 'react';

function LoginPage({ setCurrentPage }) {
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [errors, setErrors] = useState({});

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    // Clear error when typing
    if (errors[e.target.name]) {
      setErrors({
        ...errors,
        [e.target.name]: ''
      });
    }
  };

  const handleLogin = async () => {
    const newErrors = {};

    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    // Call backend API
    try {
      console.log('🔐 Attempting login with:', formData.email);
      
      const response = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password
        })
      });

      const data = await response.json();
      console.log('📥 Login response:', data);

      if (!response.ok) {
        // Login failed
        console.error('❌ Login failed:', data.detail);
        newErrors.password = data.detail || 'Invalid email or password';
        setErrors(newErrors);
        return;
      }

      // Success! Store user data and navigate to dashboard
      console.log('✅ Login successful:', data);
      localStorage.setItem('user_id', data.user_id);
      localStorage.setItem('email', data.email);
      setCurrentPage('dashboard');

    } catch (error) {
      console.error('❌ Login error:', error);
      alert('Failed to connect to server. Please make sure the backend is running at http://localhost:8000');
    }
  };

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
            name="email"
            placeholder="Email or User ID"
            value={formData.email}
            onChange={handleChange}
            className={errors.email ? 'error' : ''}
          />
          {errors.email && <span className="error-message">{errors.email}</span>}
        </div>

        <div className="input-group">
          <input
            type="password"
            name="password"
            placeholder="Password"
            value={formData.password}
            onChange={handleChange}
            className={errors.password ? 'error' : ''}
          />
          {errors.password && <span className="error-message">{errors.password}</span>}
        </div>

        <button onClick={handleLogin}>Login</button>

        <p className="toggle-text">
          New user? <span onClick={() => setCurrentPage('signup')}>Create an account</span>
        </p>
      </div>
    </div>
  );
}

export default LoginPage;