import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const Dashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (!userData) {
      navigate('/auth');
    } else {
      setUser(JSON.parse(userData));
    }
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/auth');
  };

  if (!user) return null;

  return (
    <div className="bg-background-light dark:bg-background-dark min-h-screen flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 flex items-center justify-between border-b border-solid border-blue-100 dark:border-border-dark bg-surface-light/80 dark:bg-surface-dark/95 backdrop-blur-md px-6 py-4 md:px-10 transition-colors duration-200 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-primary dark:bg-blue-900/30 dark:text-blue-400">
            <span className="material-symbols-outlined text-[28px]">psychology_alt</span>
          </div>
          <h1 className="text-xl font-display font-bold tracking-tight text-text-primary-light dark:text-text-primary-dark">MindTrackAi</h1>
        </div>
        <button 
          onClick={handleLogout}
          className="group flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold text-text-secondary-light dark:text-text-secondary-dark hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-600 dark:hover:text-red-400 transition-all"
        >
          <span className="material-symbols-outlined text-[20px]">logout</span>
          <span className="hidden sm:inline">Logout</span>
        </button>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center px-4 py-8">
        <div className="max-w-2xl w-full text-center">
          <div className="bg-surface-light dark:bg-surface-dark rounded-2xl border border-white/50 dark:border-border-dark shadow-xl p-8 md:p-12">
            <div className="flex h-20 w-20 mx-auto mb-6 items-center justify-center rounded-full bg-gradient-to-br from-blue-400 to-primary text-white shadow-lg">
              <span className="material-symbols-outlined text-[48px]">auto_awesome</span>
            </div>
            
            <h2 className="text-3xl font-display font-bold text-text-primary-light dark:text-text-primary-dark mb-3">
              Welcome, {user.firstName}! 👋
            </h2>
            
            <p className="text-lg text-text-secondary-light dark:text-text-secondary-dark mb-6">
              Your mental health dashboard is coming soon. We're building personalized AI insights based on your baseline assessment.
            </p>

            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-6 text-left">
              <div className="flex items-start gap-3">
                <span className="material-symbols-outlined text-primary text-[28px] shrink-0">check_circle</span>
                <div>
                  <h3 className="font-bold text-text-primary-light dark:text-text-primary-dark mb-2">Baseline Assessment Complete</h3>
                  <p className="text-sm text-text-secondary-light dark:text-text-secondary-dark">
                    Thank you for completing your baseline assessment. Our AI will use this data to provide personalized mental wellness insights and track your progress over time.
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-8 text-sm text-text-secondary-light dark:text-text-secondary-dark">
              <p>Dashboard features coming soon:</p>
              <ul className="mt-2 space-y-1">
                <li>📊 Mood tracking & analytics</li>
                <li>🤖 AI-powered wellness insights</li>
                <li>📈 Progress visualization</li>
                <li>💡 Personalized recommendations</li>
              </ul>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
