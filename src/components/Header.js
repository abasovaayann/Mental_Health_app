import React from 'react';

const Header = () => {
  return (
    <header className="flex items-center justify-between whitespace-nowrap border-b border-solid border-border-light dark:border-b-gray-800 px-6 lg:px-10 py-3 bg-white dark:bg-background-dark z-20">
      <div className="flex items-center gap-4 text-text-heading dark:text-white">
        <div className="size-8 text-primary">
          <span className="material-symbols-outlined text-3xl">self_improvement</span>
        </div>
        <h2 className="text-text-heading dark:text-white text-lg font-bold leading-tight tracking-[-0.015em]">
          MindTrackAi
        </h2>
      </div>
      <button className="flex min-w-[84px] cursor-pointer items-center justify-center overflow-hidden rounded-xl h-10 px-4 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/30 dark:hover:bg-blue-900/50 text-primary dark:text-blue-300 text-sm font-bold leading-normal tracking-[0.015em] transition-colors">
        <span className="truncate">Get Help</span>
      </button>
    </header>
  );
};

export default Header;
