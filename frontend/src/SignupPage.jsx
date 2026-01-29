import React, { useState } from 'react';

function SignupPage({ setCurrentPage }) {
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: ''
  });

  const [errors, setErrors] = useState({});

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    // Clear error for this field when user starts typing
    if (errors[e.target.name]) {
      setErrors({
        ...errors,
        [e.target.name]: ''
      });
    }
  };

  const handleSubmit = async () => {
    const newErrors = {};

    // Validate all fields
    if (!formData.fullName.trim()) {
      newErrors.fullName = 'Full name is required';
    }

    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(formData.email)) {
        newErrors.email = 'Please enter a valid email address';
      }
    }

    if (!formData.phone.trim()) {
      newErrors.phone = 'Phone number is required';
    } else {
      const phoneRegex = /^[0-9]{10,}$/;
      if (!phoneRegex.test(formData.phone.replace(/[\s-]/g, ''))) {
        newErrors.phone = 'Please enter at least 10 digits';
      }
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    // If there are errors, set them and return
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    // Send data to backend
    try {
      const response = await fetch('http://localhost:8000/api/auth/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          fullName: formData.fullName,
          email: formData.email,
          phone: formData.phone,
          password: formData.password,
          confirmPassword: formData.confirmPassword
        })
      });

      const data = await response.json();

      if (!response.ok) {
        // Backend returned an error
        if (data.detail) {
          newErrors.email = data.detail;
          setErrors(newErrors);
        } else {
          alert('Signup failed. Please try again.');
        }
        return;
      }

      // Success!
      console.log('✅ Account created:', data);
      alert('Account created successfully! Redirecting to login...');
      
      // Clear form
      setFormData({
        fullName: '',
        email: '',
        phone: '',
        password: '',
        confirmPassword: ''
      });
      
      setCurrentPage('login');  // Go to login, not dashboard
      
    } catch (error) {
      console.error('❌ Signup error:', error);
      alert('Failed to connect to server. Please make sure the backend is running.');
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        <div className="app-title">
          💰 Create Your <span>Account</span>
        </div>

        <p className="tagline">
          Start tracking your finances intelligently.
        </p>

        <div className="input-group">
          <input
            type="text"
            name="fullName"
            placeholder="Full Name"
            value={formData.fullName}
            onChange={handleChange}
            className={errors.fullName ? 'error' : ''}
          />
          {errors.fullName && <span className="error-message">{errors.fullName}</span>}
        </div>

        <div className="input-group">
          <input
            type="email"
            name="email"
            placeholder="Email Address"
            value={formData.email}
            onChange={handleChange}
            className={errors.email ? 'error' : ''}
          />
          {errors.email && <span className="error-message">{errors.email}</span>}
        </div>

        <div className="input-group">
          <input
            type="tel"
            name="phone"
            placeholder="Phone Number"
            value={formData.phone}
            onChange={handleChange}
            className={errors.phone ? 'error' : ''}
          />
          {errors.phone && <span className="error-message">{errors.phone}</span>}
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

        <div className="input-group">
          <input
            type="password"
            name="confirmPassword"
            placeholder="Confirm Password"
            value={formData.confirmPassword}
            onChange={handleChange}
            className={errors.confirmPassword ? 'error' : ''}
          />
          {errors.confirmPassword && <span className="error-message">{errors.confirmPassword}</span>}
        </div>

        <button onClick={handleSubmit}>Create Account</button>

        <p className="toggle-text">
          Already have an account? <span onClick={() => setCurrentPage('login')}>Sign in</span>
        </p>
      </div>
    </div>
  );
}

export default SignupPage;