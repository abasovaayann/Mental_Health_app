import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';

const BaselineSurvey = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [validationError, setValidationError] = useState('');
  const [formData, setFormData] = useState({
    sleepDuration: '4',
    energyLevel: '',
    academicPressure: '',
    studyMotivation: '',
    concentrationDifficulty: '',
    morningMood: '',
    emotionalLow: '',
    anxietyLevel: '',
    socialSupport: '',
    financialStress: ''
  });

  const totalSteps = 4;
  const progress = (currentStep / totalSteps) * 100;

  const handleChange = (name, value) => {
    setFormData({
      ...formData,
      [name]: value
    });
    // Clear validation error when user makes a change
    if (validationError) {
      setValidationError('');
    }
  };

  const handleNext = () => {
    // Validate current section before proceeding
    let isValid = true;

    if (currentStep === 1) {
      if (!formData.energyLevel) {
        isValid = false;
      }
    } else if (currentStep === 2) {
      if (!formData.academicPressure || !formData.studyMotivation || !formData.concentrationDifficulty) {
        isValid = false;
      }
    } else if (currentStep === 3) {
      if (!formData.morningMood || !formData.emotionalLow || !formData.anxietyLevel) {
        isValid = false;
      }
    }

    if (!isValid) {
      setValidationError('⚠️ You must answer all questions before proceeding to the next section.');
      window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
      return;
    }

    setValidationError('');
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const surveyPayload = {
        sleep_duration: formData.sleepDuration,
        energy_level: formData.energyLevel,
        academic_pressure: formData.academicPressure,
        study_motivation: formData.studyMotivation,
        concentration_difficulty: formData.concentrationDifficulty,
        morning_mood: formData.morningMood,
        emotional_low: formData.emotionalLow,
        anxiety_level: formData.anxietyLevel,
        social_support: formData.socialSupport,
        financial_stress: formData.financialStress
      };

      await api.post('/survey/baseline', surveyPayload);
      
      await api.post('/survey/complete-baseline');
      
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      user.baselineCompleted = true;
      localStorage.setItem('user', JSON.stringify(user));
      
      navigate('/dashboard');
    } catch (error) {
      console.error('Survey submission error:', error);
      alert(error.response?.data?.detail || 'Failed to submit survey. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveExit = () => {
    localStorage.setItem('surveyProgress', JSON.stringify({ step: currentStep, data: formData }));
    navigate('/dashboard');
  };

  return (
    <div className="bg-background-light dark:bg-background-dark font-body text-text-primary-light dark:text-text-primary-dark min-h-screen flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 flex items-center justify-between border-b border-solid border-blue-100 dark:border-border-dark bg-surface-light/80 dark:bg-surface-dark/95 backdrop-blur-md px-6 py-4 md:px-10 transition-colors duration-200 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-primary dark:bg-blue-900/30 dark:text-blue-400">
            <span className="material-symbols-outlined text-[28px]">psychology_alt</span>
          </div>
          <h1 className="text-xl font-display font-bold tracking-tight text-text-primary-light dark:text-text-primary-dark">MindTrackAi</h1>
        </div>
        <button 
          onClick={handleSaveExit}
          className="group flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold text-text-secondary-light dark:text-text-secondary-dark hover:bg-blue-50 dark:hover:bg-slate-800 hover:text-primary transition-all"
        >
          <span className="material-symbols-outlined text-[20px] transition-transform group-hover:-translate-x-0.5">arrow_back</span>
          <span className="hidden sm:inline">Save & Exit</span>
        </button>
      </header>

      <main className="flex-1 flex flex-col items-center justify-start py-10 px-4 sm:px-6">
        <div className="w-full max-w-[800px] mb-8 animate-fade-in-down">
          <div className="flex flex-col gap-4 mb-6">
            <div>
              <h2 className="text-2xl font-display font-bold text-text-primary-light dark:text-text-primary-dark">Baseline Assessment</h2>
              <p className="text-text-secondary-light dark:text-text-secondary-dark mt-1">Please answer honestly. This establishes your baseline for the AI.</p>
            </div>
            
            {/* Progress Bar */}
            <div className="w-full">
              <div className="flex justify-between items-end mb-2">
                <span className="text-xs font-semibold text-primary uppercase tracking-widest">Progress</span>
                <span className="text-sm font-bold text-primary">{Math.round(progress)}%</span>
              </div>
              <div className="h-2.5 w-full rounded-full bg-blue-100 dark:bg-slate-700 overflow-hidden shadow-inner">
                <div 
                  className="h-full rounded-full bg-gradient-to-r from-blue-400 to-primary transition-all duration-500 ease-out shadow-[0_0_10px_rgba(59,130,246,0.5)]" 
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
          </div>
          
          <div className="flex items-start gap-3 rounded-lg border border-sky-200 bg-sky-50 dark:bg-sky-900/20 dark:border-sky-800 p-4 text-sm text-sky-900 dark:text-sky-200 shadow-sm">
            <span className="material-symbols-outlined text-sky-600 dark:text-sky-400 shrink-0">volunteer_activism</span>
            <p>
              <span className="font-semibold">Confidentiality Notice:</span> 
              Your wellness data is encrypted and used solely to personalize your AI insights.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="w-full max-w-[800px] flex flex-col gap-8">
          
          {/* SECTION 1: Sleep & Physical State */}
          {currentStep === 1 && (
            <section className="flex flex-col gap-4 animate-fade-in-down">
              <div className="flex items-center gap-2 px-1">
                <span className="h-px w-8 bg-blue-300 dark:bg-slate-600"></span>
                <span className="text-xs font-bold text-primary uppercase tracking-widest">Section 1: Sleep & Physical State</span>
                <span className="h-px flex-1 bg-blue-200 dark:bg-slate-700"></span>
              </div>
              
              <div className="relative overflow-hidden rounded-2xl bg-surface-light dark:bg-surface-dark border border-white/50 dark:border-border-dark shadow-xl shadow-blue-900/5 dark:shadow-none p-6 md:p-10 transition-colors duration-200">
                <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-blue-50 dark:bg-blue-900/10 blur-3xl opacity-60 pointer-events-none"></div>
                
                <div className="relative z-10">
                  {/* Question 1 - Sleep Duration */}
                  <div className="mb-10">
                    <label className="block text-lg font-semibold text-text-primary-light dark:text-text-primary-dark mb-4">
                      1. On average, how many hours do you sleep per night?
                    </label>
                    <div className="bg-blue-50/50 dark:bg-slate-800/50 p-6 rounded-xl border border-blue-100 dark:border-slate-700">
                      <div className="flex justify-between text-xs font-medium text-text-secondary-light dark:text-text-secondary-dark mb-3 px-1">
                        <span>Less than 4h</span>
                        <span>4-5h</span>
                        <span>6h</span>
                        <span>7-8h</span>
                        <span>More than 8h</span>
                      </div>
                      <input 
                        className="w-full h-3 bg-blue-200 rounded-lg appearance-none cursor-pointer dark:bg-slate-600 accent-primary focus:outline-none focus:ring-2 focus:ring-primary/50" 
                        type="range"
                        min="1"
                        max="5"
                        step="1"
                        value={formData.sleepDuration}
                        onChange={(e) => handleChange('sleepDuration', e.target.value)}
                      />
                      <div className="mt-4 text-center">
                        <span className="inline-block px-3 py-1 bg-white dark:bg-slate-700 rounded-md shadow-sm border border-blue-100 dark:border-slate-600 text-primary font-bold">
                          {formData.sleepDuration === '1' ? 'Less than 4 hours' : 
                           formData.sleepDuration === '2' ? '4-5 hours' :
                           formData.sleepDuration === '3' ? '6 hours' :
                           formData.sleepDuration === '4' ? '7-8 hours' :
                           'More than 8 hours'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Question 2 - Daytime Energy Level */}
                  <div>
                    <label className="block text-lg font-semibold text-text-primary-light dark:text-text-primary-dark mb-4">
                      2. How would you rate your overall energy level during the day?
                    </label>
                    <div className="flex flex-col sm:flex-row gap-3">
                      {['Very low', 'Low', 'Moderate', 'High', 'Very high'].map((option, index) => (
                        <label key={index} className="flex-1 relative">
                          <input 
                            className="peer sr-only" 
                            name="energyLevel" 
                            type="radio" 
                            value={option}
                            checked={formData.energyLevel === option}
                            onChange={(e) => handleChange('energyLevel', e.target.value)}
                            required
                          />
                          <div className="w-full text-center py-3 px-2 rounded-lg border-2 border-blue-100 bg-blue-50/30 dark:border-slate-700 dark:bg-slate-800 cursor-pointer hover:border-blue-300 peer-checked:border-primary peer-checked:bg-primary peer-checked:text-white transition-all text-sm font-medium">
                            {option}
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* SECTION 2: Academic & Daily Life */}
          {currentStep === 2 && (
            <section className="flex flex-col gap-4 animate-fade-in-down">
              <div className="flex items-center gap-2 px-1">
                <span className="h-px w-8 bg-blue-300 dark:bg-slate-600"></span>
                <span className="text-xs font-bold text-primary uppercase tracking-widest">Section 2: Academic & Daily Life</span>
                <span className="h-px flex-1 bg-blue-200 dark:bg-slate-700"></span>
              </div>
              
              <div className="relative overflow-hidden rounded-2xl bg-surface-light dark:bg-surface-dark border border-white/50 dark:border-border-dark shadow-xl shadow-blue-900/5 dark:shadow-none p-6 md:p-10 transition-colors duration-200">
                <div className="absolute -left-10 bottom-0 h-48 w-48 rounded-full bg-sky-50 dark:bg-sky-900/10 blur-3xl opacity-60 pointer-events-none"></div>
                
                <div className="relative z-10 space-y-10">
                  {/* Question 3 - Academic Pressure */}
                  <div>
                    <label className="block text-lg font-semibold text-text-primary-light dark:text-text-primary-dark mb-4">
                      3. How often do you feel under academic pressure?
                    </label>
                    <div className="flex flex-col sm:flex-row gap-3">
                      {['Never', 'Rarely', 'Sometimes', 'Often', 'Constantly'].map((option, index) => (
                        <label key={index} className="flex-1 relative">
                          <input 
                            className="peer sr-only" 
                            name="academicPressure" 
                            type="radio" 
                            value={option}
                            checked={formData.academicPressure === option}
                            onChange={(e) => handleChange('academicPressure', e.target.value)}
                            required
                          />
                          <div className="w-full text-center py-3 px-2 rounded-lg border-2 border-blue-100 bg-blue-50/30 dark:border-slate-700 dark:bg-slate-800 cursor-pointer hover:border-blue-300 peer-checked:border-primary peer-checked:bg-primary peer-checked:text-white transition-all text-sm font-medium">
                            {option}
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Question 4 - Study Motivation (with emojis) */}
                  <div>
                    <label className="block text-lg font-semibold text-text-primary-light dark:text-text-primary-dark mb-4">
                      4. How motivated do you feel to study or complete your responsibilities?
                    </label>
                    <div className="flex flex-col gap-3">
                      {[
                        { emoji: '😞', text: 'Not motivated' },
                        { emoji: '😕', text: 'Slightly motivated' },
                        { emoji: '😐', text: 'Neutral' },
                        { emoji: '🙂', text: 'Motivated' },
                        { emoji: '🔥', text: 'Highly motivated' }
                      ].map((option, index) => (
                        <label key={index} className="relative">
                          <input 
                            className="peer sr-only" 
                            name="studyMotivation" 
                            type="radio" 
                            value={option.text}
                            checked={formData.studyMotivation === option.text}
                            onChange={(e) => handleChange('studyMotivation', e.target.value)}
                            required
                          />
                          <div className="flex items-center gap-3 py-3 px-4 rounded-lg border-2 border-blue-100 bg-blue-50/30 dark:border-slate-700 dark:bg-slate-800 cursor-pointer hover:border-blue-300 peer-checked:border-primary peer-checked:bg-primary peer-checked:text-white transition-all font-medium">
                            <span className="text-2xl">{option.emoji}</span>
                            <span>{option.text}</span>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Question 5 - Concentration Difficulty */}
                  <div>
                    <label className="block text-lg font-semibold text-text-primary-light dark:text-text-primary-dark mb-4">
                      5. How difficult is it for you to concentrate on tasks?
                    </label>
                    <div className="flex flex-col sm:flex-row gap-3">
                      {['Not difficult', 'Slightly difficult', 'Moderately difficult', 'Very difficult', 'Extremely difficult'].map((option, index) => (
                        <label key={index} className="flex-1 relative">
                          <input 
                            className="peer sr-only" 
                            name="concentrationDifficulty" 
                            type="radio" 
                            value={option}
                            checked={formData.concentrationDifficulty === option}
                            onChange={(e) => handleChange('concentrationDifficulty', e.target.value)}
                            required
                          />
                          <div className="w-full text-center py-3 px-2 rounded-lg border-2 border-blue-100 bg-blue-50/30 dark:border-slate-700 dark:bg-slate-800 cursor-pointer hover:border-blue-300 peer-checked:border-primary peer-checked:bg-primary peer-checked:text-white transition-all text-sm font-medium">
                            {option}
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* SECTION 3: Emotional Well-Being */}
          {currentStep === 3 && (
            <section className="flex flex-col gap-4 animate-fade-in-down">
              <div className="flex items-center gap-2 px-1">
                <span className="h-px w-8 bg-blue-300 dark:bg-slate-600"></span>
                <span className="text-xs font-bold text-primary uppercase tracking-widest">Section 3: Emotional Well-Being</span>
                <span className="h-px flex-1 bg-blue-200 dark:bg-slate-700"></span>
              </div>
              
              <div className="relative overflow-hidden rounded-2xl bg-surface-light dark:bg-surface-dark border border-white/50 dark:border-border-dark shadow-xl shadow-blue-900/5 dark:shadow-none p-6 md:p-10 transition-colors duration-200">
                <div className="absolute -right-20 top-1/2 h-64 w-64 rounded-full bg-purple-50 dark:bg-purple-900/10 blur-3xl opacity-60 pointer-events-none"></div>
                
                <div className="relative z-10 space-y-10">
                  {/* Question 6 - Morning Mood (with emojis) */}
                  <div>
                    <label className="block text-lg font-semibold text-text-primary-light dark:text-text-primary-dark mb-4">
                      6. How do you usually feel when you wake up?
                    </label>
                    <div className="flex flex-col gap-3">
                      {[
                        { emoji: '😔', text: 'Very sad / hopeless' },
                        { emoji: '😕', text: 'Sad' },
                        { emoji: '😐', text: 'Neutral' },
                        { emoji: '🙂', text: 'Positive' },
                        { emoji: '😊', text: 'Very happy / energized' }
                      ].map((option, index) => (
                        <label key={index} className="relative">
                          <input 
                            className="peer sr-only" 
                            name="morningMood" 
                            type="radio" 
                            value={option.text}
                            checked={formData.morningMood === option.text}
                            onChange={(e) => handleChange('morningMood', e.target.value)}
                            required
                          />
                          <div className="flex items-center gap-3 py-3 px-4 rounded-lg border-2 border-blue-100 bg-blue-50/30 dark:border-slate-700 dark:bg-slate-800 cursor-pointer hover:border-blue-300 peer-checked:border-primary peer-checked:bg-primary peer-checked:text-white transition-all font-medium">
                            <span className="text-2xl">{option.emoji}</span>
                            <span>{option.text}</span>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Question 7 - Emotional Low Feelings */}
                  <div>
                    <label className="block text-lg font-semibold text-text-primary-light dark:text-text-primary-dark mb-4">
                      7. How often have you felt emotionally low recently?
                    </label>
                    <div className="flex flex-col sm:flex-row gap-3">
                      {['Never', 'Rarely', 'Sometimes', 'Often', 'Almost always'].map((option, index) => (
                        <label key={index} className="flex-1 relative">
                          <input 
                            className="peer sr-only" 
                            name="emotionalLow" 
                            type="radio" 
                            value={option}
                            checked={formData.emotionalLow === option}
                            onChange={(e) => handleChange('emotionalLow', e.target.value)}
                            required
                          />
                          <div className="w-full text-center py-3 px-2 rounded-lg border-2 border-blue-100 bg-blue-50/30 dark:border-slate-700 dark:bg-slate-800 cursor-pointer hover:border-blue-300 peer-checked:border-primary peer-checked:bg-primary peer-checked:text-white transition-all text-sm font-medium">
                            {option}
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Question 8 - Anxiety Level */}
                  <div>
                    <label className="block text-lg font-semibold text-text-primary-light dark:text-text-primary-dark mb-4">
                      8. How frequently do you feel anxious or worried?
                    </label>
                    <div className="flex flex-col sm:flex-row gap-3">
                      {['Never', 'Rarely', 'Sometimes', 'Often', 'Almost always'].map((option, index) => (
                        <label key={index} className="flex-1 relative">
                          <input 
                            className="peer sr-only" 
                            name="anxietyLevel" 
                            type="radio" 
                            value={option}
                            checked={formData.anxietyLevel === option}
                            onChange={(e) => handleChange('anxietyLevel', e.target.value)}
                            required
                          />
                          <div className="w-full text-center py-3 px-2 rounded-lg border-2 border-blue-100 bg-blue-50/30 dark:border-slate-700 dark:bg-slate-800 cursor-pointer hover:border-blue-300 peer-checked:border-primary peer-checked:bg-primary peer-checked:text-white transition-all text-sm font-medium">
                            {option}
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* SECTION 4: Social & External Factors */}
          {currentStep === 4 && (
            <section className="flex flex-col gap-4 animate-fade-in-down">
              <div className="flex items-center gap-2 px-1">
                <span className="h-px w-8 bg-blue-300 dark:bg-slate-600"></span>
                <span className="text-xs font-bold text-primary uppercase tracking-widest">Section 4: Social & External Factors</span>
                <span className="h-px flex-1 bg-blue-200 dark:bg-slate-700"></span>
              </div>
              
              <div className="relative overflow-hidden rounded-2xl bg-surface-light dark:bg-surface-dark border border-white/50 dark:border-border-dark shadow-xl shadow-blue-900/5 dark:shadow-none p-6 md:p-10 transition-colors duration-200">
                <div className="absolute -left-10 top-0 h-64 w-64 rounded-full bg-green-50 dark:bg-green-900/10 blur-3xl opacity-60 pointer-events-none"></div>
                
                <div className="relative z-10 space-y-10">
                  {/* Question 9 - Social Support */}
                  <div>
                    <label className="block text-lg font-semibold text-text-primary-light dark:text-text-primary-dark mb-4">
                      9. Do you feel supported by friends or family?
                    </label>
                    <div className="flex flex-col sm:flex-row gap-3">
                      {['Not at all', 'Slightly', 'Moderately', 'Mostly', 'Very supported'].map((option, index) => (
                        <label key={index} className="flex-1 relative">
                          <input 
                            className="peer sr-only" 
                            name="socialSupport" 
                            type="radio" 
                            value={option}
                            checked={formData.socialSupport === option}
                            onChange={(e) => handleChange('socialSupport', e.target.value)}
                            required
                          />
                          <div className="w-full text-center py-3 px-2 rounded-lg border-2 border-blue-100 bg-blue-50/30 dark:border-slate-700 dark:bg-slate-800 cursor-pointer hover:border-blue-300 peer-checked:border-primary peer-checked:bg-primary peer-checked:text-white transition-all text-sm font-medium">
                            {option}
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Question 10 - Financial Stress */}
                  <div>
                    <label className="block text-lg font-semibold text-text-primary-light dark:text-text-primary-dark mb-4">
                      10. How much financial stress are you currently experiencing?
                    </label>
                    <div className="flex flex-col sm:flex-row gap-3">
                      {['None', 'Low', 'Moderate', 'High', 'Extremely high'].map((option, index) => (
                        <label key={index} className="flex-1 relative">
                          <input 
                            className="peer sr-only" 
                            name="financialStress" 
                            type="radio" 
                            value={option}
                            checked={formData.financialStress === option}
                            onChange={(e) => handleChange('financialStress', e.target.value)}
                            required
                          />
                          <div className="w-full text-center py-3 px-2 rounded-lg border-2 border-blue-100 bg-blue-50/30 dark:border-slate-700 dark:bg-slate-800 cursor-pointer hover:border-blue-300 peer-checked:border-primary peer-checked:bg-primary peer-checked:text-white transition-all text-sm font-medium">
                            {option}
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Validation Error Message */}
          {validationError && (
            <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-300 dark:border-red-800 text-red-700 dark:text-red-300 px-6 py-4 rounded-xl text-center font-semibold animate-fade-in-down">
              {validationError}
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex gap-4 mt-4">
            {currentStep > 1 && (
              <button
                type="button"
                onClick={handleBack}
                className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 px-8 py-4 text-lg font-bold text-text-heading dark:text-white transition-all"
              >
                <span className="material-symbols-outlined text-[20px]">arrow_back</span>
                Back
              </button>
            )}
            
            {currentStep < totalSteps ? (
              <button
                type="button"
                onClick={handleNext}
                className="flex-1 group relative flex items-center justify-center gap-3 rounded-xl bg-primary px-8 py-4 text-lg font-bold text-white shadow-xl shadow-blue-500/25 hover:bg-primary-hover hover:shadow-blue-500/40 hover:-translate-y-1 transition-all transform active:scale-[0.98] overflow-hidden"
              >
                <span className="relative z-10">Next Section</span>
                <span className="material-symbols-outlined relative z-10 text-[24px] group-hover:translate-x-1 transition-transform">arrow_forward</span>
                <div className="absolute inset-0 bg-gradient-to-r from-blue-400/0 via-white/20 to-blue-400/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 ease-in-out"></div>
              </button>
            ) : (
              <button
                type="submit"
                disabled={loading}
                className="flex-1 group relative flex items-center justify-center gap-3 rounded-xl bg-primary px-8 py-4 text-lg font-bold text-white shadow-xl shadow-blue-500/25 hover:bg-primary-hover hover:shadow-blue-500/40 hover:-translate-y-1 transition-all transform active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden"
              >
                <span className="relative z-10">{loading ? 'Submitting...' : 'Complete Assessment'}</span>
                <span className="material-symbols-outlined relative z-10 text-[24px] group-hover:scale-110 transition-transform">auto_awesome</span>
                <div className="absolute inset-0 bg-gradient-to-r from-blue-400/0 via-white/20 to-blue-400/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 ease-in-out"></div>
              </button>
            )}
          </div>

          <div className="mt-4 flex justify-center">
            <p className="flex items-center text-xs text-blue-400 dark:text-slate-500 px-4 bg-white/50 dark:bg-slate-800/50 py-2 rounded-full backdrop-blur-sm">
              <span className="material-symbols-outlined text-sm mr-1.5">lock</span>
              Your responses are confidential and analyzed by AI for personalized wellness.
            </p>
          </div>
        </form>
      </main>
    </div>
  );
};

export default BaselineSurvey;
