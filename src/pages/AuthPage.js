import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import Login from '../components/Login';
import Register from '../components/Register';

const AuthPage = () => {
  const [activeTab, setActiveTab] = useState('login');
  const navigate = useNavigate();

  const handleAuthSuccess = () => {
    // Redirect to dashboard or home page after successful authentication
    console.log('Authentication successful!');
    // navigate('/dashboard'); // Uncomment when dashboard is ready
  };

  return (
    <div className="relative flex min-h-screen w-full flex-col">
      <Header />
      
      <main className="flex flex-1 flex-col lg:flex-row">
        {/* Left Section - Hero */}
        <section
          className="hidden lg:flex lg:w-1/2 xl:w-5/12 relative flex-col justify-end p-12 overflow-hidden bg-cover bg-center"
          style={{
            backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuCap2LnAhEYQ3ZGoeHT99C-SPaC6BkQZu51UxD9wAy7q-uDKLxT_-NTPVa95V7g2kiF14IsHGiRq_JbKm4FCJos8C_AlWbE_pg6-0ZCI7wm6agbW4Zx2tS3d5rs2GHdIlQhM_i_6bsnkYkxg2cdVxep0NorPHQFFlJn_fD7xS8BroYl4Byf9HHwqx0Kll4vPUlkEMKYISwvIuEu1mdmQ3IDey928sd54wmzK2fGtOXmXT2u6cVc2_9jqE8t0jdZh80wfVO3Lhw5og')",
          }}
        >
          <div className="absolute inset-0 bg-gradient-to-t from-blue-950/90 via-blue-900/40 to-transparent z-0"></div>
          <div className="absolute inset-0 bg-primary/30 mix-blend-overlay z-0"></div>
          
          <div className="relative z-10 flex flex-col gap-6 max-w-lg pb-8">
            <div className="size-12 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center text-white mb-2 shadow-inner shadow-white/10">
              <span className="material-symbols-outlined">format_quote</span>
            </div>
            <h1 className="text-white text-4xl xl:text-5xl font-black leading-tight tracking-[-0.033em]">
              Your mental health is a priority. Your happiness is an essential.
            </h1>
          </div>
        </section>

        {/* Right Section - Auth Forms */}
        <section className="flex flex-1 flex-col items-center justify-center p-6 lg:p-12 bg-background-light dark:bg-background-dark">
          <div className="w-full max-w-[480px] flex flex-col gap-6">
            {/* Tabs */}
            <div className="w-full">
              <div className="flex border-b border-border-medium dark:border-gray-700 justify-between">
                <button
                  className={`group flex flex-col items-center justify-center border-b-[3px] pb-[13px] pt-4 flex-1 focus:outline-none transition-all ${
                    activeTab === 'login'
                      ? 'border-b-primary text-text-heading dark:text-white'
                      : 'border-b-transparent hover:border-b-primary/30 text-text-muted dark:text-gray-400'
                  }`}
                  onClick={() => setActiveTab('login')}
                >
                  <p className="text-sm font-bold leading-normal tracking-[0.015em]">Login</p>
                </button>
                <button
                  className={`group flex flex-col items-center justify-center border-b-[3px] pb-[13px] pt-4 flex-1 focus:outline-none transition-all ${
                    activeTab === 'signup'
                      ? 'border-b-primary text-text-heading dark:text-white'
                      : 'border-b-transparent hover:border-b-primary/30 text-text-muted dark:text-gray-400'
                  }`}
                  onClick={() => setActiveTab('signup')}
                >
                  <p className="text-sm font-bold leading-normal tracking-[0.015em]">Sign Up</p>
                </button>
              </div>
            </div>

            {/* Form Content */}
            {activeTab === 'login' ? (
              <Login onSuccess={handleAuthSuccess} />
            ) : (
              <Register onSuccess={handleAuthSuccess} />
            )}
          </div>
        </section>
      </main>
    </div>
  );
};

export default AuthPage;
