// ==============================================================================
// File: client/src/components/dashboard/MyPlansDashboard.tsx
// Purpose: Dashboard listing all saved AI learning plans from PostgreSQL (Neon).
// ==============================================================================

import React, { useEffect, useState } from 'react';
import type { SavedPlanSummary } from '../../types/form';
import { fetchSavedPlans } from '../../services/api';
import {
  LuBookOpen,
  LuCalendar,
  LuClock,
  LuSparkles,
  LuFileText,
  LuArrowRight,
  LuRefreshCw,
  LuCircleAlert,
} from 'react-icons/lu';

interface MyPlansDashboardProps {
  onSelectPlan: (planId: number) => void;
  onCreateNewPlan: () => void;
}

export const MyPlansDashboard: React.FC<MyPlansDashboardProps> = ({
  onSelectPlan,
  onCreateNewPlan,
}) => {
  const [plans, setPlans] = useState<SavedPlanSummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadPlans = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchSavedPlans();
      setPlans(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to load saved learning plans from server.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPlans();
  }, []);

  const formatDate = (isoString?: string | null): string => {
    if (!isoString) return 'Recently created';
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-6 text-left">
      {/* Header bar */}
      <div className="flex items-center justify-between pb-4 border-b border-[#222222]">
        <div>
          <h2 className="text-xl font-semibold text-white tracking-[-0.02em]">
            My Learning Plans
          </h2>
          <p className="text-xs text-[#888888] mt-0.5">
            {plans.length === 1
              ? '1 plan saved in PostgreSQL'
              : `${plans.length} plans saved in PostgreSQL`}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadPlans}
            disabled={isLoading}
            title="Refresh plans"
            className="p-2 text-[#A1A1A1] hover:text-white bg-[#111111] hover:bg-[#1A1A1A] border border-[#262626] rounded-lg transition-colors cursor-pointer disabled:opacity-50"
          >
            <LuRefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            type="button"
            onClick={onCreateNewPlan}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-black bg-white hover:bg-[#E5E5E5] active:bg-[#CCCCCC] rounded-lg transition-colors cursor-pointer"
          >
            <LuSparkles className="w-3.5 h-3.5 text-black" />
            <span>New Plan</span>
          </button>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="p-5 rounded-xl bg-[#111111] border border-[#262626] animate-pulse space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="h-4 bg-[#262626] rounded w-1/3" />
                <div className="h-4 bg-[#262626] rounded w-16" />
              </div>
              <div className="h-3 bg-[#1A1A1A] rounded w-2/3" />
            </div>
          ))}
        </div>
      )}

      {/* Error State */}
      {!isLoading && error && (
        <div className="p-4 rounded-xl bg-[#1A0A0A] border border-red-900/50 flex items-start gap-3 text-red-300 text-xs">
          <LuCircleAlert className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <p className="font-medium text-red-200">Unable to load plans</p>
            <p className="text-red-400/90">{error}</p>
            <button
              type="button"
              onClick={loadPlans}
              className="px-3 py-1 bg-red-950/80 hover:bg-red-900/80 border border-red-800 text-red-200 rounded text-xs transition-colors cursor-pointer font-medium"
            >
              Try Again
            </button>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && plans.length === 0 && (
        <div className="p-10 sm:p-14 text-center rounded-2xl bg-[#111111] border border-[#262626] space-y-4">
          <div className="w-12 h-12 rounded-xl bg-[#1A1A1A] border border-[#333333] text-[#A1A1A1] flex items-center justify-center mx-auto">
            <LuBookOpen className="w-6 h-6 text-[#EDEDED]" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-[#EDEDED]">No learning plans saved yet</h3>
            <p className="text-xs text-[#888888] max-w-sm mx-auto leading-relaxed">
              Generate your first personalized AI curriculum and it will be automatically saved here.
            </p>
          </div>
          <button
            type="button"
            onClick={onCreateNewPlan}
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-medium text-black bg-white hover:bg-[#E5E5E5] rounded-lg transition-colors cursor-pointer"
          >
            <LuSparkles className="w-3.5 h-3.5" />
            <span>Create a Learning Plan</span>
          </button>
        </div>
      )}

      {/* Plans List */}
      {!isLoading && !error && plans.length > 0 && (
        <div className="space-y-3">
          {plans.map((plan) => (
            <div
              key={plan.id}
              onClick={() => onSelectPlan(plan.id)}
              className="group p-5 rounded-xl bg-[#111111] hover:bg-[#141414] border border-[#262626] hover:border-[#404040] transition-all cursor-pointer space-y-3 text-left"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-base font-semibold text-white group-hover:text-white tracking-[-0.01em]">
                      {plan.title}
                    </h3>
                    {plan.durationDays && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-semibold bg-[#1C1C1C] text-[#EDEDED] border border-[#333333] rounded-md">
                        <LuClock className="w-3 h-3 text-[#A1A1A1]" />
                        <span>{plan.durationDays} Days</span>
                      </span>
                    )}
                    {plan.google_doc_url && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-md">
                        <LuFileText className="w-3 h-3" />
                        <span>Google Doc</span>
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[#888888] line-clamp-2 leading-relaxed">
                    <span className="font-medium text-[#A1A1A1]">Goal:</span> {plan.goal}
                  </p>
                </div>

                <div className="text-[#555555] group-hover:text-white transition-colors pt-1">
                  <LuArrowRight className="w-4 h-4" />
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-[#1C1C1C] text-[11px] text-[#666666]">
                <div className="flex items-center gap-1.5">
                  <LuCalendar className="w-3 h-3 text-[#666666]" />
                  <span>Created {formatDate(plan.created_at)}</span>
                </div>
                <span className="text-xs font-medium text-[#EDEDED] group-hover:underline">
                  View Curriculum →
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MyPlansDashboard;
