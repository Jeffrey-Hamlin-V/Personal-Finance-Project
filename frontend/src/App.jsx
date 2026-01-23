import { useState } from 'react';
import './App.css';
import LoginPage from './LoginPage';
import SignupPage from './SignupPage';
import DashboardHome from './DashboardHome';
import VisualDashboard from './VisualDashboard';

function App() {
  const [currentPage, setCurrentPage] = useState('login');

  return (
    <div>
      {currentPage === 'login' && <LoginPage setCurrentPage={setCurrentPage} />}
      {currentPage === 'signup' && <SignupPage setCurrentPage={setCurrentPage} />}
      {currentPage === 'dashboard' && <DashboardHome setCurrentPage={setCurrentPage} />}
      {currentPage === 'visual-dashboard' && <VisualDashboard setCurrentPage={setCurrentPage} />}
    </div>
  );
}

export default App;