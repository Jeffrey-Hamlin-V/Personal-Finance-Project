import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';

function VisualDashboard({ setCurrentPage }) {
  const [dashboardData, setDashboardData] = useState(null);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const userId = localStorage.getItem('user_id');
  const userEmail = localStorage.getItem('email');

  useEffect(() => {
    fetchAllData();
  }, [userId]);

  // Refresh data when component becomes visible (e.g., after upload)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        fetchAllData();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  const fetchAllData = async () => {
    if (!userId) {
      setError('no_user');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      // Fetch all data in parallel
      const [dashboardRes, analyticsRes, transactionsRes] = await Promise.all([
        fetch(`http://localhost:8000/api/dashboard?user_id=${userId}`).catch(err => ({ error: err, status: 0 })),
        fetch(`http://localhost:8000/api/analytics?user_id=${userId}`).catch(err => ({ error: err, status: 0 })),
        fetch(`http://localhost:8000/api/transactions?user_id=${userId}&page_size=500`).catch(err => ({ error: err, status: 0 }))
      ]);

      // Check for network errors
      if (dashboardRes.error || analyticsRes.error || transactionsRes.error) {
        console.error('Network error:', { dashboardRes, analyticsRes, transactionsRes });
        setError('network_error');
        setLoading(false);
        return;
      }

      let dashboardData, analyticsData, transactionsData;
      
      try {
        dashboardData = await dashboardRes.json();
      } catch (e) {
        console.error('Failed to parse dashboard response:', e);
        dashboardData = { detail: 'Invalid response from server' };
      }

      try {
        analyticsData = await analyticsRes.json();
      } catch (e) {
        console.error('Failed to parse analytics response:', e);
        analyticsData = { detail: 'Invalid response from server' };
      }

      try {
        transactionsData = await transactionsRes.json();
      } catch (e) {
        console.error('Failed to parse transactions response:', e);
        transactionsData = { transactions: [] };
      }

      // Handle 404 - no data available
      if (dashboardRes.status === 404 || analyticsRes.status === 404) {
        setError('no_data');
        setLoading(false);
        return;
      }

      if (dashboardRes.ok && analyticsRes.ok && transactionsRes.ok) {
        setDashboardData(dashboardData);
        setAnalyticsData(analyticsData);
        setTransactions(transactionsData.transactions || []);
      } else {
        setError('fetch_error');
        console.error('Failed to fetch data:', {
          dashboard: { status: dashboardRes.status, detail: dashboardData.detail || dashboardData.error },
          analytics: { status: analyticsRes.status, detail: analyticsData.detail || analyticsData.error },
          transactions: { status: transactionsRes.status, detail: transactionsData.detail || transactionsData.error }
        });
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      setError('network_error');
    } finally {
      setLoading(false);
    }
  };

  const fetchDashboardData = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/dashboard?user_id=${userId}`);
      const data = await response.json();
      
      if (response.ok) {
        setDashboardData(data);
      } else {
        console.error('Failed to fetch dashboard:', data.detail);
      }
    } catch (error) {
      console.error('Error fetching dashboard:', error);
    }
  };

  const fetchAnalyticsData = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/analytics?user_id=${userId}`);
      const data = await response.json();
      
      if (response.ok) {
        setAnalyticsData(data);
        setLoading(false);
      }
    } catch (error) {
      console.error('Error fetching analytics:', error);
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('user_id');
    localStorage.removeItem('email');
    setCurrentPage('login');
  };

  const handleRefresh = () => {
    fetchAllData();
  };

  const handleBackToDashboard = () => {
    setCurrentPage('dashboard');
  };

  if (loading) {
    return (
      <div className="dashboard-container">
        <header className="dashboard-header">
          <div className="header-content">
            <h1 className="dashboard-logo">💰 Finance Intelligence</h1>
            <button className="logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </header>
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading your financial data...</p>
        </div>
      </div>
    );
  }

  if (error === 'no_data' || !dashboardData || !analyticsData) {
    return (
      <div className="dashboard-container">
        <header className="dashboard-header">
          <div className="header-content">
            <h1 className="dashboard-logo">💰 Finance Intelligence</h1>
            <button className="logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </header>
        <div className="empty-state">
          <h2>No Data Available</h2>
          <p>Upload a CSV file to get started with your financial analysis</p>
          <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
            <button onClick={handleBackToDashboard}>Go Back</button>
            <button onClick={handleRefresh}>Refresh</button>
          </div>
        </div>
      </div>
    );
  }

  if (error === 'no_user') {
    return (
      <div className="dashboard-container">
        <header className="dashboard-header">
          <div className="header-content">
            <h1 className="dashboard-logo">💰 Finance Intelligence</h1>
            <button className="logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </header>
        <div className="empty-state">
          <h2>Session Expired</h2>
          <p>Please login again to access your dashboard.</p>
          <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
            <button onClick={() => setCurrentPage('login')}>Go to Login</button>
          </div>
        </div>
      </div>
    );
  }

  if (error === 'network_error' || error === 'fetch_error') {
    return (
      <div className="dashboard-container">
        <header className="dashboard-header">
          <div className="header-content">
            <h1 className="dashboard-logo">💰 Finance Intelligence</h1>
            <button className="logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </header>
        <div className="empty-state">
          <h2>Error Loading Data</h2>
          <p>
            {error === 'network_error' 
              ? 'Cannot connect to the server. Please make sure the backend is running at http://localhost:8000'
              : 'There was an error fetching your financial data. Please check the browser console for details.'}
          </p>
          <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
            <button onClick={handleRefresh}>Retry</button>
            <button onClick={handleBackToDashboard}>Go Back</button>
          </div>
        </div>
      </div>
    );
  }

  // Prepare chart data
  const categoryData = (analyticsData.by_category || []).map(cat => ({
    name: cat.category,
    value: cat.total,
    count: cat.count
  }));

  const COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#F06292', '#4DD0E1', '#AED581'];

  // Top merchant
  const topMerchant = analyticsData.by_merchant && analyticsData.by_merchant.length > 0 
    ? analyticsData.by_merchant[0] 
    : null;

  // Recent transactions (limit to 10)
  const recentTransactions = (dashboardData.recent_transactions || []).slice(0, 10);

  // Prepare monthly spending trend data
  const monthlyData = React.useMemo(() => {
    if (!transactions || transactions.length === 0) return [];

    // Group transactions by month
    const monthlySpending = {};
    
    transactions.forEach(txn => {
      if (!txn.is_credit) { // Only count expenses, not income
        try {
          const date = new Date(txn.transaction_date);
          if (isNaN(date.getTime())) {
            console.warn('Invalid date:', txn.transaction_date);
            return;
          }
          
          const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
          const monthLabel = date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
          
          if (!monthlySpending[monthKey]) {
            monthlySpending[monthKey] = {
              month: monthLabel,
              monthKey: monthKey, // For sorting
              spending: 0,
              count: 0
            };
          }
          
          monthlySpending[monthKey].spending += Math.abs(txn.amount);
          monthlySpending[monthKey].count += 1;
        } catch (error) {
          console.warn('Error processing transaction date:', error, txn);
        }
      }
    });

    // Convert to array and sort by month key
    return Object.values(monthlySpending)
      .sort((a, b) => a.monthKey.localeCompare(b.monthKey))
      .map(item => ({
        month: item.month,
        spending: parseFloat(item.spending.toFixed(2)),
        transactions: item.count
      }));
  }, [transactions]);

  // Get primary insight
  const primaryInsight = dashboardData.insights && dashboardData.insights.length > 0
    ? dashboardData.insights[0]
    : null;

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="dashboard-logo">💰 Personal Finance Intelligence Platform</h1>
          <div className="header-actions">
            <button className="icon-btn" onClick={handleRefresh} title="Refresh Data">🔄</button>
            <button className="logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </header>

      {/* Main Dashboard */}
      <div className="visual-dashboard">
        {/* Top Stats Row */}
        <div className="stats-grid">
          <div className="stat-card">
            <h3>Total Spending</h3>
            <div className="stat-value">${(analyticsData.total_spent || 0).toFixed(2)}</div>
            <div className="stat-subtitle">
              {transactions.filter(t => !t.is_credit).length} transactions
            </div>
          </div>

          <div className="stat-card alert-card">
            <h3>Anomalies Detected</h3>
            <div className="stat-value red">{dashboardData.anomaly_count || 0} Alerts</div>
            <div className="stat-subtitle">
              {transactions.filter(t => t.is_amount_anomaly).length} Amount, {' '}
              {transactions.filter(t => t.is_frequency_anomaly).length} Frequency
            </div>
          </div>

          <div className="stat-card">
            <h3>Top Merchant</h3>
            <div className="merchant-info">
              <div className="merchant-icon">🏪</div>
              <div>
                <div className="merchant-name">{topMerchant?.merchant || 'N/A'}</div>
                <div className="merchant-amount">${(topMerchant?.total || 0).toFixed(2)} Spent</div>
              </div>
            </div>
          </div>

          <div className="stat-card insight-card">
            <h3>Key Insight</h3>
            <div className="insight-text">
              {primaryInsight?.description || primaryInsight?.title || 'No insights available yet'}
            </div>
          </div>
        </div>

        {/* Charts Row */}
        <div className="charts-grid">
          {/* Pie Chart */}
          <div className="chart-card">
            <h3>Spending Breakdown by Category</h3>
            {categoryData.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={categoryData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {categoryData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#161a22', 
                        border: '1px solid #2a2f3a',
                        borderRadius: '8px',
                        color: '#e5e7eb'
                      }}
                      formatter={(value) => `$${value.toFixed(2)}`}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="legend-list">
                  {categoryData.map((cat, idx) => (
                    <div key={idx} className="legend-item">
                      <span className="legend-color" style={{backgroundColor: COLORS[idx % COLORS.length]}}></span>
                      <span>{cat.name}</span>
                      <span className="legend-value">
                        {analyticsData.total_spent > 0 
                          ? `${((cat.value / analyticsData.total_spent) * 100).toFixed(0)}%`
                          : '0%'
                        }
                      </span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="chart-placeholder">
                <p>📊</p>
                <p className="placeholder-text">No spending data available</p>
              </div>
            )}
          </div>

          {/* Monthly Spending Trend Line Chart */}
          <div className="chart-card">
            <h3>Monthly Spending Trend</h3>
            {monthlyData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={monthlyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2f3a" />
                  <XAxis 
                    dataKey="month" 
                    stroke="#9ca3af"
                    style={{ fontSize: '12px' }}
                  />
                  <YAxis 
                    stroke="#9ca3af"
                    style={{ fontSize: '12px' }}
                    tickFormatter={(value) => `$${value.toFixed(0)}`}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#161a22', 
                      border: '1px solid #2a2f3a',
                      borderRadius: '8px',
                      color: '#e5e7eb'
                    }}
                    formatter={(value) => [`$${value.toFixed(2)}`, 'Spending']}
                  />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="spending" 
                    stroke="#f5c16c" 
                    strokeWidth={3}
                    dot={{ fill: '#f5c16c', r: 5 }}
                    activeDot={{ r: 7 }}
                    name="Spending"
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="chart-placeholder">
                <p>📈</p>
                <p className="placeholder-text">Upload multiple months of data to see trends</p>
              </div>
            )}
          </div>
        </div>

        {/* Bottom Row */}
        <div className="bottom-grid">
          {/* Recent Transactions */}
          <div className="table-card">
            <h3>Recent Transactions</h3>
            <table className="transactions-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Description</th>
                  <th>Amount</th>
                  <th>Category</th>
                </tr>
              </thead>
              <tbody>
                {recentTransactions.map((txn, idx) => (
                  <tr key={idx}>
                    <td>{new Date(txn.transaction_date).toLocaleDateString()}</td>
                    <td>
                      {txn.merchant}
                      {txn.is_amount_anomaly && <span className="badge duplicate">Duplicate</span>}
                    </td>
                    <td>${txn.amount.toFixed(2)}</td>
                    <td>
                      <span className={`category-badge ${txn.category.toLowerCase()}`}>
                        {txn.category}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Anomaly Alerts */}
          <div className="alerts-card">
            <h3>Anomaly Alerts</h3>
            {dashboardData.insights && dashboardData.insights.filter(i => i.type === 'anomaly_alert' || i.severity).length > 0 ? (
              dashboardData.insights
                .filter(i => i.type === 'anomaly_alert' || i.severity)
                .slice(0, 5)
                .map((alert, idx) => (
                  <div key={idx} className="alert-item">
                    <div className="alert-title">{alert.title || 'Anomaly Detected'}</div>
                    <div className="alert-date">{alert.description || 'Unusual transaction pattern'}</div>
                    {alert.amount && (
                      <div className="alert-amount">${alert.amount.toFixed(2)}</div>
                    )}
                  </div>
                ))
            ) : (
              <p className="no-alerts">No anomalies detected 🎉</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default VisualDashboard;