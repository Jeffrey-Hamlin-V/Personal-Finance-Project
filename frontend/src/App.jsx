import { useState } from 'react';
import './App.css';
import LoginPage from './LoginPage';
import SignupPage from './SignupPage';
import DashboardHome from './DashboardHome';

function App() {
  const [currentPage, setCurrentPage] = useState('login');

  return (
    <div>
      {currentPage === 'login' && <LoginPage setCurrentPage={setCurrentPage} />}
      {currentPage === 'signup' && <SignupPage setCurrentPage={setCurrentPage} />}
      {currentPage === 'dashboard' && <DashboardHome setCurrentPage={setCurrentPage} />}
    </div>
  );
}

export default App;