// ==============================================================================
// File: client/src/components/dashboard/PlanDetailView.tsx
// Purpose: Displays complete plan details for a single saved learning plan.
// ==============================================================================

import React, { useEffect, useState } from 'react';
import type { SavedPlanDetail, PlanApiResponse } from '../../types/form';
import { fetchPlanById } from '../../services/api';
import SubmissionPreview from '../forms/SubmissionPreview';
import { LuArrowLeft, LuCircleAlert, LuRefreshCw } from 'react-icons/lu';

interface PlanDetailViewProps {
  planId: number;
  onBack: () => void;
  onNewPlan: () => void;
}

export const PlanDetailView: React.FC<PlanDetailViewProps> = ({
  planId,
  onBack,
  onNewPlan,
}) => {
  const [planDetail, setPlanDetail] = useState<SavedPlanDetail | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadPlan = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchPlanById(planId);
      setPlanDetail(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : `Failed to load plan #${planId} from server.`
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPlan();
  }, [planId]);

  if (isLoading) {
    return (
      <div className="p-12 text-center rounded-2xl bg-[#111111] border border-[#262626] space-y-4">
        <div className="w-8 h-8 mx-auto text-[#A1A1A1] animate-spin flex items-center justify-center">
          <LuRefreshCw className="w-6 h-6" />
        </div>
        <p className="text-xs text-[#888888]">Loading curriculum details...</p>
      </div>
    );
  }

  if (error || !planDetail) {
    return (
      <div className="p-8 rounded-2xl bg-[#111111] border border-[#262626] space-y-4 text-left">
        <div className="flex items-center gap-2 text-red-400 text-sm">
          <LuCircleAlert className="w-4 h-4 flex-shrink-0" />
          <span className="font-semibold">Unable to load plan #{planId}</span>
        </div>
        <p className="text-xs text-[#888888]">{error || 'Record not found.'}</p>
        <div className="flex items-center gap-3 pt-2">
          <button
            type="button"
            onClick={onBack}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-[#1C1C1C] hover:bg-[#262626] border border-[#333333] rounded-lg transition-colors cursor-pointer"
          >
            <LuArrowLeft className="w-3.5 h-3.5" />
            <span>Back to My Plans</span>
          </button>
          <button
            type="button"
            onClick={loadPlan}
            className="px-3 py-1.5 text-xs font-medium text-black bg-white hover:bg-[#E5E5E5] rounded-lg transition-colors cursor-pointer"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Format into standard PlanApiResponse expected by SubmissionPreview
  const totalDays = planDetail.plan_data.days?.length || 1;
  const estimatedTotalHours = planDetail.plan_data.days?.reduce(
    (sum, day) => sum + (Number(day.estimatedHours) || 0),
    0
  ) || 0;

  const durationDays = Number(
    planDetail.input_data?.durationDays || totalDays
  );
  const hoursPerDay = Number(
    planDetail.input_data?.hoursPerDay || (totalDays > 0 ? estimatedTotalHours / totalDays : 2)
  );
  const startDate =
    typeof planDetail.input_data?.startDate === 'string'
      ? planDetail.input_data.startDate
      : planDetail.plan_data.days?.[0]?.date || new Date().toISOString().split('T')[0];

  const planApiResponse: PlanApiResponse = {
    message: 'Plan loaded from database',
    planId: planDetail.id,
    plan_id: planDetail.id,
    data: {
      feasible: true,
      feasibilityMessage: `Plan #${planDetail.id} • Saved in PostgreSQL`,
      estimatedRequiredHours: estimatedTotalHours,
      availableHours: durationDays * hoursPerDay,
      recommendations: [],
      plan: planDetail.plan_data,
    },
  };

  const planConstraints = {
    durationDays,
    hoursPerDay,
    startDate,
  };

  return (
    <SubmissionPreview
      response={planApiResponse}
      planConstraints={planConstraints}
      initialGoogleDocUrl={planDetail.google_doc_url}
      onBackToDashboard={onBack}
      onReset={onNewPlan}
    />
  );
};

export default PlanDetailView;
