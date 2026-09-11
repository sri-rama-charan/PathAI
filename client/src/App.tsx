// ==============================================================================
// File: client/src/App.tsx
// Purpose: Main view implementing the Vercel Geist aesthetic for PathAI.
//
// What this component does:
// 1. Sets a true black background (#000000) with a subtle radial gradient.
// 2. Centers the content in a max-width container with responsive spacing.
// 3. Renders the Header and LearningPathForm components.
// ==============================================================================

import React from 'react';
import Header from './components/layout/Header';
import LearningPathForm from './components/forms/LearningPathForm';

export const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#000000] text-[#EDEDED] flex flex-col justify-between p-4 sm:p-8 selection:bg-[#0070F3] selection:text-white">
      {/* Centered Main Area */}
      <main className="max-w-2xl w-full mx-auto space-y-8 my-auto py-8">
        {/* Minimalist Vercel Geist Header */}
        <Header />

        {/* Input Form with Geist color tokens & icons */}
        <LearningPathForm />
      </main>

      {/* Minimalist Footer */}
      <footer className="text-center text-xs text-[#525252] py-4 border-t border-[#171717]">
        <p>PathAI • Built with Vercel Geist Design System</p>
      </footer>
    </div>
  );
};

export default App;
