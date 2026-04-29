import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import AuthPage from './pages/AuthPage';
import BaselineSurvey from './pages/BaselineSurvey';
import Dashboard from './pages/Dashboard';
import Diary from './pages/Diary';
import Insights from './pages/Insights';
import Settings from './pages/Settings';
import { applyTheme, getStoredTheme } from './theme';

function App() {
  useEffect(() => {
    applyTheme(getStoredTheme());
  }, []);

  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<Navigate to="/auth" replace />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/baseline-survey" element={<BaselineSurvey />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/diary" element={<Diary />} />
          <Route path="/diary/entry/:date" element={<Diary />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
