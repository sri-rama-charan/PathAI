// ==============================================================================
// File: client/src/components/forms/PlanApproval.tsx
// Purpose: Human-approval UI for a generated learning plan.
//
// States:
//   "awaiting_approval" â€” Shows Review/Approve/Modify buttons.
//   "approved"          â€” Shows a green confirmation banner; buttons hidden.
//
// Modification flow:
//   User clicks "Modify Plan" â†’ textarea appears.
//   User types feedback â†’ "Regenerate Plan" button enables.
//   User clicks "Regenerate Plan" â†’ POST /api/plan/modify â†’ revised plan replaces current.
//   Approval status resets to "awaiting_approval" after successful regeneration.
// ==============================================================================

import React, { useState } from 'react';
import {
  LuCheck,
  LuCircleAlert,
  LuPencil,
  LuRefreshCw,
  LuShieldCheck,
} from 'react-icons/lu';
import type { ApprovalStatus, LearningPlan, PlanApiResponse } from '../../types/form';
import { modifyLearningPlan } from '../../services/api';

interface PlanConstraints {
  durationDays: number;
  hoursPerDay: number;
  startDate: string;
}

interface PlanApprovalProps {
  /** Current approval state, controlled by SubmissionPreview. */
  status: ApprovalStatus;
  /** The full LearningPlan currently displayed (needed to send to /api/plan/modify). */
  currentPlan: LearningPlan;
  /** Original scheduling constraints from the form submission. */
  planConstraints: PlanConstraints;
  /** Called when the user clicks "Approve Plan". */
  onApprove: () => void;
  /**
   * Called with the revised PlanApiResponse after a successful regeneration.
   * SubmissionPreview uses this to replace the displayed plan and reset approval.
   */
  onRegenerate: (revisedResponse: PlanApiResponse) => void;
}

export const PlanApproval: React.FC<PlanApprovalProps> = ({
  status,
  currentPlan,
  planConstraints,
  onApprove,
  onRegenerate,
}) => {
  const [showModifyPanel, setShowModifyPanel] = useState(false);
  const [modifyFeedback, setModifyFeedback] = useState('');
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [regenError, setRegenError] = useState<string | null>(null);

  const handleRegenerateClick = async () => {
    const feedback = modifyFeedback.trim();
    if (!feedback || isRegenerating) return;

    setIsRegenerating(true);
    setRegenError(null);

    try {
      const revised = await modifyLearningPlan({
        currentPlan,
        feedback,
        durationDays: planConstraints.durationDays,
        hoursPerDay: planConstraints.hoursPerDay,
        startDate: planConstraints.startDate,
      });

      // Success â€” reset the modify panel and let the parent swap the plan
      setModifyFeedback('');
      setShowModifyPanel(false);
      onRegenerate(revised);
    } catch (err) {
      setRegenError(
        err instanceof Error
          ? err.message
          : 'An unexpected error occurred. Please try again.'
      );
    } finally {
      setIsRegenerating(false);
    }
  };

  // â”€â”€ APPROVED state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  if (status === 'approved') {
    return (
      <div
        id="plan-approval-confirmed"
        className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/25 flex items-center gap-3"
      >
        <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center flex-shrink-0">
          <LuShieldCheck className="w-4 h-4" />
        </div>
        <div>
          <p className="text-sm font-semibold text-emerald-400 tracking-[-0.01em]">
            âœ“ Plan Approved
          </p>
          <p className="text-xs text-[#666666] mt-0.5">
            Your learning path is confirmed. Integration with Google Calendar and Docs coming soon.
          </p>
        </div>
      </div>
    );
  }

  // â”€â”€ AWAITING APPROVAL state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  return (
    <div
      id="plan-approval-section"
      className="p-5 rounded-xl bg-[#000000] border border-[#262626] space-y-4"
    >
      {/* Section heading */}
      <div className="space-y-0.5">
        <p className="text-sm font-semibold text-white tracking-[-0.01em]">
          Review Your Learning Path
        </p>
        <p className="text-xs text-[#666666]">
          Review the generated schedule before continuing.
        </p>
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap gap-2.5">
        {/* Approve Plan */}
        <button
          id="btn-approve-plan"
          type="button"
          onClick={onApprove}
          disabled={isRegenerating}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold
                     bg-emerald-500 hover:bg-emerald-400 active:bg-emerald-600
                     text-black transition-colors cursor-pointer
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <LuCheck className="w-3.5 h-3.5" />
          Approve Plan
        </button>

        {/* Modify Plan toggle */}
        <button
          id="btn-modify-plan"
          type="button"
          disabled={isRegenerating}
          onClick={() => {
            setShowModifyPanel((prev) => !prev);
            setRegenError(null);
          }}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold
                     bg-[#1A1A1A] hover:bg-[#222222] active:bg-[#2A2A2A]
                     text-[#EDEDED] border border-[#333333]
                     transition-colors cursor-pointer
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <LuPencil className="w-3.5 h-3.5" />
          {showModifyPanel ? 'Cancel' : 'Modify Plan'}
        </button>
      </div>

      {/* Modify feedback panel */}
      {showModifyPanel && (
        <div
          id="plan-modify-panel"
          className="space-y-3 pt-1 border-t border-[#1A1A1A]"
        >
          <label
            htmlFor="modify-feedback-input"
            className="block text-xs font-medium text-[#A1A1A1]"
          >
            What would you like to change?
          </label>

          <textarea
            id="modify-feedback-input"
            value={modifyFeedback}
            onChange={(e) => {
              setModifyFeedback(e.target.value);
              if (regenError) setRegenError(null);
            }}
            disabled={isRegenerating}
            placeholder="e.g. Add more hands-on projects and reduce the amount of theory."
            rows={3}
            className="w-full bg-[#111111] border border-[#2A2A2A] rounded-lg px-3 py-2.5
                       text-xs text-[#EDEDED] placeholder-[#444444]
                       focus:outline-none focus:border-[#444444]
                       resize-none transition-colors
                       disabled:opacity-50"
          />

          {/* Error banner */}
          {regenError && (
            <div
              id="regen-error"
              className="flex items-start gap-2 p-3 rounded-lg bg-rose-500/5 border border-rose-500/20 text-xs text-rose-400"
            >
              <LuCircleAlert className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
              <span>{regenError}</span>
            </div>
          )}

          {/* Regenerate Plan button */}
          <button
            id="btn-regenerate-plan"
            type="button"
            disabled={!modifyFeedback.trim() || isRegenerating}
            onClick={handleRegenerateClick}
            className={[
              'flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-colors',
              modifyFeedback.trim() && !isRegenerating
                ? 'bg-[#FFFFFF] text-[#000000] hover:bg-[#E5E5E5] active:bg-[#CCCCCC] cursor-pointer border border-transparent'
                : 'bg-[#111111] text-[#444444] border border-[#222222] cursor-not-allowed opacity-60',
            ].join(' ')}
          >
            <LuRefreshCw className={`w-3.5 h-3.5 ${isRegenerating ? 'animate-spin' : ''}`} />
            {isRegenerating ? 'Regeneratingâ€¦' : 'Regenerate Plan'}
          </button>
        </div>
      )}
    </div>
  );
};

export default PlanApproval;
