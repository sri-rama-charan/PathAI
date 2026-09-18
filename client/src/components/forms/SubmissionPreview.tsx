// ==============================================================================
// File: client/src/components/forms/SubmissionPreview.tsx
// Purpose: Displays the AI-generated learning plan or feasibility recommendation.
//
// What this component does:
// 1. Infeasible view: Displays why time is insufficient, required vs available hours,
//    and actionable recommendations to adjust scope or duration.
// 2. Feasible view: Displays the full curriculum, prerequisites, and day-by-day
//    breakdown of topics, objectives, tasks, and hours.
// 3. Adheres strictly to the Vercel Geist Design System (#000000, #111111, #EDEDED).
// ==============================================================================

import React, { useState } from 'react';
import type { ApprovalStatus, LearningPlan, PlanApiResponse } from '../../types/form';
import PlanApproval from './PlanApproval';
import {
  LuCheck,
  LuArrowLeft,
  LuCode,
  LuCalendar,
  LuClock,
  LuTriangleAlert,
  LuBookOpen,
  LuListChecks,
  LuSparkles,
  LuLightbulb,
} from 'react-icons/lu';

/** The original schedule constraints captured at submission time. */
interface PlanConstraints {
  durationDays: number;
  hoursPerDay: number;
  startDate: string;
}

interface SubmissionPreviewProps {
  response: PlanApiResponse;
  onReset: () => void;
  planConstraints: PlanConstraints;
}

export const SubmissionPreview: React.FC<SubmissionPreviewProps> = ({ response, onReset, planConstraints }) => {
  const [showJson, setShowJson] = useState(false);
  
  // Approval state: initialized from sessionStorage if returning from OAuth redirect
  const [approvalStatus, setApprovalStatus] = useState<ApprovalStatus>(() => {
    try {
      const saved = sessionStorage.getItem('pathai_approval_status');
      return (saved as ApprovalStatus) || 'awaiting_approval';
    } catch {
      return 'awaiting_approval';
    }
  });

  // Hold the displayed plan in local state so it can be replaced after regeneration.
  const [currentResponse, setCurrentResponse] = useState<PlanApiResponse>(response);

  const { data } = currentResponse;
  const { feasible, feasibilityMessage, estimatedRequiredHours, availableHours, recommendations, plan } = data;

  // ============================================================================
  // VIEW A: INFEASIBLE (Time is insufficient for the goal)
  // ============================================================================
  if (!feasible) {
    return (
      <div className="bg-[#111111] border border-[#262626] rounded-2xl p-6 sm:p-9 space-y-7 shadow-2xl text-left animate-fadeIn">
        {/* Infeasible Header Banner */}
        <div className="flex items-center justify-between pb-5 border-b border-[#222222]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 flex items-center justify-center">
              <LuTriangleAlert className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-semibold text-white tracking-[-0.02em]">
                  Schedule Not Feasible
                </h3>
                <span className="px-2 py-0.5 text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-full">
                  Scope Notice
                </span>
              </div>
              <p className="text-xs text-[#888888]">More time needed to achieve this goal realistically</p>
            </div>
          </div>

          <button
            type="button"
            onClick={onReset}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-[#000000] bg-[#FFFFFF] hover:bg-[#E5E5E5] active:bg-[#CCCCCC] rounded-lg transition-colors cursor-pointer"
          >
            <LuArrowLeft className="w-3.5 h-3.5 text-[#000000]" />
            <span>Adjust Schedule</span>
          </button>
        </div>

        {/* Feasibility Explanation Message */}
        <div className="p-4 rounded-xl bg-[#000000] border border-[#262626] space-y-2">
          <span className="text-xs font-medium text-[#888888] uppercase tracking-wider">
            AI Feasibility Analysis
          </span>
          <p className="text-sm text-[#EDEDED] leading-relaxed">
            {feasibilityMessage}
          </p>
        </div>

        {/* Hours Comparison Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
          <div className="p-3.5 rounded-lg bg-[#000000] border border-[#262626] space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-medium text-[#888888]">
              <LuClock className="w-3.5 h-3.5 text-[#A1A1A1]" />
              <span>Available Time</span>
            </div>
            <p className="text-xl font-bold text-white">{availableHours} hrs</p>
            <p className="text-[11px] text-[#666666]">duration × daily hours</p>
          </div>

          <div className="p-3.5 rounded-lg bg-[#000000] border border-[#262626] space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-medium text-[#888888]">
              <LuBookOpen className="w-3.5 h-3.5 text-amber-400" />
              <span>Estimated Needed</span>
            </div>
            <p className="text-xl font-bold text-amber-400">~{estimatedRequiredHours} hrs</p>
            <p className="text-[11px] text-[#666666]">realistic study effort</p>
          </div>

          <div className="p-3.5 rounded-lg bg-[#000000] border border-[#262626] space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-medium text-[#888888]">
              <LuTriangleAlert className="w-3.5 h-3.5 text-rose-400" />
              <span>Estimated Gap</span>
            </div>
            <p className="text-xl font-bold text-rose-400">
              +{Math.max(0, round(estimatedRequiredHours - availableHours, 1))} hrs
            </p>
            <p className="text-[11px] text-[#666666]">additional effort suggested</p>
          </div>
        </div>

        {/* Practical Recommendations */}
        {recommendations && recommendations.length > 0 && (
          <div className="p-4 rounded-xl bg-[#000000] border border-[#262626] space-y-3">
            <div className="flex items-center gap-2 text-xs font-medium text-[#A1A1A1]">
              <LuLightbulb className="w-4 h-4 text-amber-400" />
              <span>Practical Recommendations to Make This Feasible:</span>
            </div>
            <ul className="space-y-2 text-xs text-[#EDEDED]">
              {recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-2.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Raw JSON Inspector */}
        <div className="space-y-2 pt-2 border-t border-[#222222]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-medium text-[#888888]">
              <LuCode className="w-3.5 h-3.5 text-[#A1A1A1]" />
              <span>FastAPI Response JSON</span>
            </div>
            <button
              type="button"
              onClick={() => setShowJson(!showJson)}
              className="text-xs text-[#EDEDED] hover:underline font-medium cursor-pointer"
            >
              {showJson ? 'Hide JSON' : 'Show JSON'}
            </button>
          </div>

          {showJson && (
            <pre className="p-4 rounded-lg bg-[#000000] text-amber-400 text-xs font-mono overflow-x-auto border border-[#262626]">
              {JSON.stringify(response, null, 2)}
            </pre>
          )}
        </div>
      </div>
    );
  }

  // ============================================================================
  // VIEW B: FEASIBLE (Structured Learning Plan Generated)
  // ============================================================================
  return (
    <div className="bg-[#111111] border border-[#262626] rounded-2xl p-6 sm:p-9 space-y-7 shadow-2xl text-left animate-fadeIn">
      {/* Top Banner */}
      <div className="flex items-center justify-between pb-5 border-b border-[#222222]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center">
            <LuCheck className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-semibold text-white tracking-[-0.02em]">
                {plan?.title || 'Personalized Learning Plan'}
              </h3>
              <span className="px-2 py-0.5 text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full">
                Feasible
              </span>
            </div>
            <p className="text-xs text-[#888888]">{feasibilityMessage}</p>
          </div>
        </div>

        <button
          type="button"
          onClick={onReset}
          className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-[#000000] bg-[#FFFFFF] hover:bg-[#E5E5E5] active:bg-[#CCCCCC] rounded-lg transition-colors cursor-pointer"
        >
          <LuArrowLeft className="w-3.5 h-3.5 text-[#000000]" />
          <span>New Plan</span>
        </button>
      </div>

      {/* Curriculum Overview */}
      {plan?.overview && (
        <div className="p-4 rounded-xl bg-[#000000] border border-[#262626] space-y-2">
          <span className="text-xs font-medium text-[#888888] uppercase tracking-wider">
            Curriculum Overview
          </span>
          <p className="text-sm text-[#EDEDED] leading-relaxed">{plan.overview}</p>
        </div>
      )}

      {/* Prerequisites */}
      {plan?.prerequisites && plan.prerequisites.length > 0 && (
        <div className="p-4 rounded-xl bg-[#000000] border border-[#262626] space-y-2.5">
          <div className="flex items-center gap-2 text-xs font-medium text-[#A1A1A1]">
            <LuSparkles className="w-3.5 h-3.5 text-[#EDEDED]" />
            <span>Key Prerequisites & Assumptions:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {plan.prerequisites.map((prereq, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 text-xs rounded-md font-medium bg-[#171717] text-[#EDEDED] border border-[#262626]"
              >
                {prereq}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Day-by-Day Learning Schedule */}
      <div className="space-y-3.5 pt-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-[#A3A3A3]">
            Daily Learning Schedule ({plan?.days?.length || 0} Days)
          </span>
          <span className="text-xs text-[#666666]">
            Total {availableHours} hrs allocated
          </span>
        </div>

        <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
          {plan?.days?.map((day) => (
            <div
              key={day.day}
              className="p-4 rounded-xl bg-[#000000] border border-[#262626] space-y-3 hover:border-[#383838] transition-colors"
            >
              {/* Day Header */}
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#1A1A1A] pb-2.5">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 text-xs font-bold bg-[#171717] text-white border border-[#333333] rounded-md">
                    Day {day.day}
                  </span>
                  <h4 className="text-sm font-semibold text-white">{day.topic}</h4>
                </div>
                <div className="flex items-center gap-3 text-xs text-[#888888]">
                  <span className="flex items-center gap-1">
                    <LuCalendar className="w-3.5 h-3.5 text-[#666666]" />
                    {day.date}
                  </span>
                  <span className="flex items-center gap-1">
                    <LuClock className="w-3.5 h-3.5 text-[#666666]" />
                    {day.estimatedHours} hrs
                  </span>
                </div>
              </div>

              {/* Objectives */}
              {day.objectives && day.objectives.length > 0 && (
                <div className="space-y-1">
                  <span className="text-[11px] font-semibold text-[#888888] uppercase tracking-wider">
                    Objectives:
                  </span>
                  <ul className="space-y-1 text-xs text-[#D4D4D4]">
                    {day.objectives.map((obj, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="w-1 h-1 rounded-full bg-[#EDEDED] mt-1.5 flex-shrink-0" />
                        <span>{obj}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Tasks */}
              {day.tasks && day.tasks.length > 0 && (
                <div className="space-y-1 pt-1 border-t border-[#141414]">
                  <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[#888888] uppercase tracking-wider">
                    <LuListChecks className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Hands-On Tasks:</span>
                  </div>
                  <ul className="space-y-1 text-xs text-[#A3A3A3]">
                    {day.tasks.map((task, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-emerald-400 font-mono text-[10px]">▸</span>
                        <span>{task}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Human Approval Section */}
      <PlanApproval
        status={approvalStatus}
        currentPlan={plan as LearningPlan}
        planConstraints={planConstraints}
        onApprove={() => {
          try {
            sessionStorage.setItem('pathai_approval_status', 'approved');
          } catch {}
          setApprovalStatus('approved');
        }}
        onRegenerate={(revisedResponse) => {
          try {
            sessionStorage.setItem('pathai_plan_response', JSON.stringify(revisedResponse));
            sessionStorage.setItem('pathai_approval_status', 'awaiting_approval');
          } catch {}
          setCurrentResponse(revisedResponse);
          setApprovalStatus('awaiting_approval');
        }}
      />

      {/* Raw JSON Inspector */}
      <div className="space-y-2 pt-2 border-t border-[#222222]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-medium text-[#888888]">
            <LuCode className="w-3.5 h-3.5 text-[#A1A1A1]" />
            <span>FastAPI Server Response JSON</span>
          </div>
          <button
            type="button"
            onClick={() => setShowJson(!showJson)}
            className="text-xs text-[#EDEDED] hover:underline font-medium cursor-pointer"
          >
            {showJson ? 'Hide JSON' : 'Show JSON'}
          </button>
        </div>

        {showJson && (
          <pre className="p-4 rounded-lg bg-[#000000] text-emerald-400 text-xs font-mono overflow-x-auto border border-[#262626]">
            {JSON.stringify(response, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
};

// Helper function to round numbers cleanly
function round(value: number, decimals: number): number {
  return Number(Math.round(Number(value + 'e' + decimals)) + 'e-' + decimals);
}

export default SubmissionPreview;
