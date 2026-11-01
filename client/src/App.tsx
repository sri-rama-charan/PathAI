// ==============================================================================
// File: client/src/App.tsx
// Purpose: Main view implementing the Vercel Geist aesthetic for PathAI.
//
// What this component does:
// 1. Sets a true black background (#000000) with a subtle radial gradient.
// 2. Centers the content in a max-width container with responsive spacing.
// 3. Renders the Header and LearningPathForm components.
// ==============================================================================

import React, { useState } from 'react';
import Header from './components/layout/Header';
import LearningPathForm from './components/forms/LearningPathForm';
import MyPlansDashboard from './components/dashboard/MyPlansDashboard';
import PlanDetailView from './components/dashboard/PlanDetailView';
import { LuCirclePlus, LuLayers } from 'react-icons/lu';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'create' | 'dashboard'>('create');
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);

  const handleSelectPlan = (planId: number) => {
    setSelectedPlanId(planId);
  };

  const handleBackToDashboard = () => {
    setSelectedPlanId(null);
    setActiveTab('dashboard');
  };

  const handleCreateNew = () => {
    setSelectedPlanId(null);
    setActiveTab('create');
  };

  return (
    <div className="min-h-screen bg-[#000000] text-[#EDEDED] flex flex-col justify-between p-4 sm:p-8 selection:bg-[#0070F3] selection:text-white">
      {/* Centered Main Area */}
      <main className="max-w-2xl w-full mx-auto space-y-6 my-auto py-8">
        {/* Minimalist Vercel Geist Header */}
        <Header />

        {/* Tab Navigation */}
        <div className="flex items-center justify-center p-1 bg-[#111111] border border-[#222222] rounded-xl max-w-xs mx-auto">
          <button
            type="button"
            onClick={handleCreateNew}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-medium transition-all cursor-pointer ${
              activeTab === 'create' && !selectedPlanId
                ? 'bg-white text-black font-semibold shadow-sm'
                : 'text-[#888888] hover:text-white'
            }`}
          >
            <LuCirclePlus className="w-3.5 h-3.5" />
            <span>Create Plan</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setSelectedPlanId(null);
              setActiveTab('dashboard');
            }}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-medium transition-all cursor-pointer ${
              activeTab === 'dashboard' || selectedPlanId
                ? 'bg-white text-black font-semibold shadow-sm'
                : 'text-[#888888] hover:text-white'
            }`}
          >
            <LuLayers className="w-3.5 h-3.5" />
            <span>My Plans</span>
          </button>
        </div>

        {/* Dynamic View Display */}
        {selectedPlanId !== null ? (
          <PlanDetailView
            planId={selectedPlanId}
            onBack={handleBackToDashboard}
            onNewPlan={handleCreateNew}
          />
        ) : activeTab === 'dashboard' ? (
          <MyPlansDashboard
            onSelectPlan={handleSelectPlan}
            onCreateNewPlan={handleCreateNew}
          />
        ) : (
          <LearningPathForm />
        )}
      </main>

      {/* Minimalist Footer */}
      <footer className="text-center text-xs text-[#525252] py-4 border-t border-[#171717]">
        <p>PathAI • Built with Vercel Geist Design System & Neon PostgreSQL</p>
      </footer>
    </div>
  );
};

export default App;

