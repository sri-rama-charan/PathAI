// ==============================================================================
// File: client/src/components/forms/PlanApproval.tsx
// Purpose: Human-approval UI for a generated learning plan, Google OAuth & Docs creation + verification.
//
// States:
//   "awaiting_approval" — Shows Review/Approve/Modify buttons.
//   "approved"          — Shows green plan confirmation banner, Google OAuth status,
//                         and "Create Google Doc" action when account is connected.
//
// Modification flow:
//   User clicks "Modify Plan" → textarea appears.
//   User types feedback → "Regenerate Plan" button enables.
//   User clicks "Regenerate Plan" → POST /api/plan/modify → revised plan replaces current.
//   Approval status resets to "awaiting_approval" after successful regeneration.
//
// OAuth flow:
//   User approves plan → "Connect Google Account" button appears.
//   User clicks button → calls GET /api/auth/google (redirects to Google consent screen).
//   On return → Backend exchanges code, stores in memory, redirects back with ?auth=success.
//   UI displays "✓ Google Account Connected".
//
// Google Docs creation & verification flow:
//   User approves plan & Google account is connected → "Create Google Doc" button enables.
//   User clicks button → POST /api/plan/create-doc (create → insert → verify).
//   If verified: UI displays "✓ Google Doc Created" with "Open Google Doc" button.
//   If unverified: UI displays "Google Doc was created, but PathAI could not verify it." with link.
// ==============================================================================

import React, { useState, useEffect } from 'react';
import {
  LuCheck,
  LuCircleAlert,
  LuPencil,
  LuRefreshCw,
  LuShieldCheck,
  LuGlobe,
  LuFileText,
  LuExternalLink,
} from 'react-icons/lu';
import type { ApprovalStatus, LearningPlan, PlanApiResponse } from '../../types/form';
import {
  modifyLearningPlan,
  checkGoogleAuthStatus,
  initiateGoogleAuth,
  createGoogleDocForPlan,
} from '../../services/api';

interface PlanConstraints {
  durationDays: number;
  hoursPerDay: number;
  startDate: string;
}

interface PlanApprovalProps {
  /** Current approval state, controlled by SubmissionPreview. */
  status: ApprovalStatus;
  /** The full LearningPlan currently displayed (needed to send to /api/plan/modify and /api/plan/create-doc). */
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

  // Google OAuth state
  const [isGoogleConnected, setIsGoogleConnected] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Google Docs Creation & Verification state
  const [isCreatingDoc, setIsCreatingDoc] = useState(false);
  const [docCreateError, setDocCreateError] = useState<string | null>(null);
  const [createdDocUrl, setCreatedDocUrl] = useState<string | null>(null);
  const [createdDocId, setCreatedDocId] = useState<string | null>(null);
  const [isDocVerified, setIsDocVerified] = useState<boolean | null>(null);

  useEffect(() => {
    // 1. Check URL query parameters for OAuth redirect status
    const params = new URLSearchParams(window.location.search);
    const authParam = params.get('auth');
    const authErrorParam = params.get('auth_error');

    if (authParam === 'success') {
      setIsGoogleConnected(true);
      setAuthError(null);
      // Clean query params from browser URL without reloading page
      const cleanUrl = window.location.pathname;
      window.history.replaceState({}, document.title, cleanUrl);
    } else if (authErrorParam) {
      if (authErrorParam === 'access_denied') {
        setAuthError('Google authorization was cancelled or denied.');
      } else if (authErrorParam === 'missing_code') {
        setAuthError('Missing authorization code from Google OAuth callback.');
      } else if (authErrorParam === 'token_exchange_failed') {
        setAuthError('Failed to exchange authorization code for Google tokens.');
      } else {
        setAuthError(`Google OAuth connection failed (${authErrorParam}).`);
      }
      const cleanUrl = window.location.pathname;
      window.history.replaceState({}, document.title, cleanUrl);
    } else {
      // 2. Fetch current OAuth connection status from backend server memory
      checkGoogleAuthStatus().then((res) => {
        if (res.connected) {
          setIsGoogleConnected(true);
        }
      });
    }
  }, []);

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

      // Success — reset the modify panel and let the parent swap the plan
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

  const handleCreateDocClick = async () => {
    if (!currentPlan || isCreatingDoc) return;
    setIsCreatingDoc(true);
    setDocCreateError(null);
    setIsDocVerified(null);

    try {
      const response = await createGoogleDocForPlan(currentPlan);
      setCreatedDocUrl(response.documentUrl);
      setCreatedDocId(response.documentId);
      setIsDocVerified(response.verified !== false);

      if (response.verified === false) {
        setDocCreateError('Google Doc was created, but PathAI could not verify it.');
      }
    } catch (err) {
      setDocCreateError(
        err instanceof Error
          ? err.message
          : 'Failed to create Google Doc. Please check your account connection and try again.'
      );
    } finally {
      setIsCreatingDoc(false);
    }
  };

  // ── APPROVED state ────────────────────────────────────────────────────────
  if (status === 'approved') {
    return (
      <div id="plan-approval-confirmed-container" className="space-y-3">
        {/* Confirmed Plan Banner */}
        <div
          id="plan-approval-confirmed"
          className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/25 flex items-center gap-3"
        >
          <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center flex-shrink-0">
            <LuShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <p className="text-sm font-semibold text-emerald-400 tracking-[-0.01em]">
              ✓ Plan Approved
            </p>
            <p className="text-xs text-[#666666] mt-0.5">
              Your learning path is confirmed. Export your approved plan to Google Docs below.
            </p>
          </div>
        </div>

        {/* Google OAuth & Docs Section */}
        <div
          id="google-integration-section"
          className="p-4 rounded-xl bg-[#000000] border border-[#262626] space-y-3"
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-lg bg-[#141414] border border-[#262626] text-[#A1A1A1] flex items-center justify-center flex-shrink-0 mt-0.5 sm:mt-0">
                <LuGlobe className="w-3.5 h-3.5" />
              </div>
              <div>
                <p className="text-xs font-semibold text-[#EDEDED] tracking-[-0.01em]">
                  Google Integration
                </p>
                <p className="text-[11px] text-[#666666] mt-0.5">
                  Export your approved curriculum directly into Google Docs.
                </p>
              </div>
            </div>

            {/* Connection badge or Connect button */}
            {isGoogleConnected ? (
              <div
                id="google-connected-badge"
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium self-start sm:self-auto"
              >
                <LuCheck className="w-3.5 h-3.5" />
                <span>✓ Google Account Connected</span>
              </div>
            ) : (
              <button
                id="btn-connect-google"
                type="button"
                onClick={initiateGoogleAuth}
                className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold
                           bg-[#1A1A1A] hover:bg-[#222222] active:bg-[#2A2A2A]
                           text-[#EDEDED] border border-[#333333]
                           transition-colors cursor-pointer self-start sm:self-auto"
              >
                Connect Google Account
              </button>
            )}
          </div>

          {/* Create Google Doc Action Section */}
          {isGoogleConnected && (
            <div
              id="google-docs-action-container"
              className="pt-3 border-t border-[#1A1A1A] flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            >
              {createdDocUrl ? (
                isDocVerified !== false ? (
                  /* Successful & Verified Banner */
                  <div
                    id="google-doc-created-banner"
                    className="w-full p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-between gap-3"
                  >
                    <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
                      <LuCheck className="w-4 h-4 flex-shrink-0" />
                      <span>✓ Google Doc Created</span>
                      {createdDocId && (
                        <span className="text-[11px] font-normal text-emerald-400/70 hidden sm:inline">
                          (ID: {createdDocId})
                        </span>
                      )}
                    </div>
                    <a
                      id="btn-open-google-doc"
                      href={createdDocUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold
                                 bg-emerald-500 hover:bg-emerald-400 active:bg-emerald-600
                                 text-black transition-colors cursor-pointer flex-shrink-0"
                    >
                      <span>Open Google Doc</span>
                      <LuExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                ) : (
                  /* Unverified Warning Banner */
                  <div
                    id="google-doc-unverified-banner"
                    className="w-full p-3 rounded-lg bg-amber-500/10 border border-amber-500/25 flex items-center justify-between gap-3"
                  >
                    <div className="flex items-center gap-2 text-xs font-semibold text-amber-400">
                      <LuCircleAlert className="w-4 h-4 flex-shrink-0" />
                      <span>Google Doc was created, but PathAI could not verify it.</span>
                      {createdDocId && (
                        <span className="text-[11px] font-normal text-amber-400/70 hidden sm:inline">
                          (ID: {createdDocId})
                        </span>
                      )}
                    </div>
                    <a
                      id="btn-open-google-doc-unverified"
                      href={createdDocUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold
                                 bg-amber-500 hover:bg-amber-400 active:bg-amber-600
                                 text-black transition-colors cursor-pointer flex-shrink-0"
                    >
                      <span>Open Google Doc</span>
                      <LuExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                )
              ) : (
                <div className="w-full flex items-center justify-between gap-3">
                  <span className="text-xs text-[#A1A1A1]">
                    Generate a Google Doc formatted with overview, prerequisites, and daily schedule.
                  </span>
                  <button
                    id="btn-create-google-doc"
                    type="button"
                    disabled={isCreatingDoc}
                    onClick={handleCreateDocClick}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold
                               bg-[#FFFFFF] hover:bg-[#E5E5E5] active:bg-[#CCCCCC]
                               text-[#000000] transition-colors cursor-pointer
                               disabled:opacity-60 disabled:cursor-not-allowed flex-shrink-0"
                  >
                    {isCreatingDoc ? (
                      <>
                        <LuRefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Creating Document…</span>
                      </>
                    ) : (
                      <>
                        <LuFileText className="w-3.5 h-3.5" />
                        <span>Create Google Doc</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* OAuth Error Alert */}
        {authError && (
          <div
            id="google-auth-error"
            className="flex items-center gap-2 p-3 rounded-lg bg-rose-500/5 border border-rose-500/20 text-xs text-rose-400"
          >
            <LuCircleAlert className="w-3.5 h-3.5 flex-shrink-0" />
            <span>{authError}</span>
          </div>
        )}

        {/* Doc Creation Error Alert */}
        {docCreateError && (
          <div
            id="google-doc-create-error"
            className="flex items-start gap-2 p-3 rounded-lg bg-rose-500/5 border border-rose-500/20 text-xs text-rose-400"
          >
            <LuCircleAlert className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
            <span>{docCreateError}</span>
          </div>
        )}
      </div>
    );
  }

  // ── AWAITING APPROVAL state ───────────────────────────────────────────────
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
            {isRegenerating ? 'Regenerating…' : 'Regenerate Plan'}
          </button>
        </div>
      )}
    </div>
  );
};

export default PlanApproval;
