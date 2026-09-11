// ==============================================================================
// File: client/src/components/layout/Header.tsx
// Purpose: Minimalist header component inspired by the Vercel Geist Design System.
//
// What this component does:
// 1. Renders the PathAI brand with high-contrast typography.
// 2. Features an iconic geometric mark.
// 3. Displays the tagline with balanced sizing and letter-spacing.
// ==============================================================================

import React from 'react';
import { LuSparkles } from 'react-icons/lu';

export const Header: React.FC = () => {
  return (
    <header className="text-center space-y-4 pb-8 border-b border-[#222222]">
      {/* Vercel-style pill badge */}
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-normal bg-[#111111] text-[#A1A1A1] border border-[#222222]">
        <LuSparkles className="w-3.5 h-3.5 text-[#EDEDED]" />
        <span>AI-powered personalized learning paths</span>
      </div>

      {/* Main Brand Title & Geometric Mark */}
      <div className="flex items-center justify-center gap-3">
        

        <h1 className="text-3xl font-semibold tracking-[-0.03em] text-[#FFFFFF]">
          Path<span className="text-[#A1A1A1]">AI</span>
        </h1>
      </div>

      {/* Subtitle */}
      <p className="text-sm text-[#737373] max-w-md mx-auto leading-relaxed">
        Researching, synthesizing, and scheduling your personalized curriculum with verifiable agent workflows.
      </p>
    </header>
  );
};

export default Header;
