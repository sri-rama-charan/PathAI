// ==============================================================================
// File: client/src/App.tsx
// Purpose: Main React component representing the root placeholder page for PathAI.
//
// What this component does:
// Renders the clean starting page for PathAI:
// 1. Shows the project title ("PathAI") and a subtitle.
// 2. Displays a short, clear description explaining that the application will
//    generate personalized learning paths.
// 3. Serves as a clean canvas to be expanded in upcoming milestones.
// ==============================================================================

import React from 'react';

/**
 * App: The root component for the PathAI frontend.
 * 
 * Simple explanation:
 * Think of this as the main TV screen of our frontend. Whatever JSX we write
 * here will be displayed to the user in their web browser.
 */
export const App: React.FC = () => {
  return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-slate-900 text-slate-100">
      <div className="max-w-xl w-full text-center space-y-6 p-8 rounded-2xl bg-slate-800/60 border border-slate-700/60 shadow-xl backdrop-blur-sm">
        
        {/* Project Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          Foundation Initialized • Milestone 1
        </div>

        {/* Project Title */}
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
          PathAI
        </h1>

        {/* Short Description */}
        <p className="text-lg text-slate-300 leading-relaxed">
          An AI-powered learning path generator that creates structured, personalized
          curricula tailored to your goals, prior experience, and schedule constraints.
        </p>

        {/* Development Status Callout */}
        <div className="pt-4 border-t border-slate-700/50 text-xs text-slate-400 flex justify-center items-center gap-4">
          <span>⚡ Vite + React + TypeScript</span>
          <span>•</span>
          <span>🐍 Python + FastAPI</span>
        </div>

      </div>
    </main>
  );
};

export default App;
