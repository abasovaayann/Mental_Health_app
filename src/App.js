import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import AuthPage from './pages/AuthPage';
import BaselineSurvey from './pages/BaselineSurvey';
import Dashboard from './pages/Dashboard';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<Navigate to="/auth" replace />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/baseline-survey" element={<BaselineSurvey />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
