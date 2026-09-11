// ==============================================================================
// File: client/src/components/forms/SubmissionPreview.tsx
// Purpose: Displays the confirmed response received from FastAPI (POST /api/plan).
//
// What this component does:
// 1. Confirms successful communication with the backend.
// 2. Displays the server's confirmation message and echoed validated data.
// 3. Offers a collapsible JSON viewer to inspect the actual HTTP response payload.
// 4. Provides a button to return to the form to edit or create another plan.
// ==============================================================================

import React, { useState } from 'react';
import type { PlanApiResponse } from '../../types/form';
import { LuCheck, LuArrowLeft, LuCode, LuCalendar, LuClock, LuTarget, LuBookOpen } from 'react-icons/lu';

interface SubmissionPreviewProps {
  response: PlanApiResponse;
  onReset: () => void;
}

export const SubmissionPreview: React.FC<SubmissionPreviewProps> = ({ response, onReset }) => {
  const [showJson, setShowJson] = useState(false);
  const { data, message } = response;

  return (
    <div className="bg-[#111111] border border-[#262626] rounded-2xl p-6 sm:p-9 space-y-7 shadow-2xl text-left animate-fadeIn">
      {/* Top Banner with Server Status */}
      <div className="flex items-center justify-between pb-5 border-b border-[#222222]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center">
            <LuCheck className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-semibold text-white tracking-[-0.02em]">
                {message}
              </h3>
              <span className="px-2 py-0.5 text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full">
                HTTP 200 OK
              </span>
            </div>
            <p className="text-xs text-[#888888]">Validated by FastAPI Backend</p>
          </div>
        </div>

        <button
          type="button"
          onClick={onReset}
          className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-[#000000] bg-[#FFFFFF] hover:bg-[#E5E5E5] active:bg-[#CCCCCC] rounded-lg transition-colors cursor-pointer"
        >
          <LuArrowLeft className="w-3.5 h-3.5 text-[#000000]" />
          <span>Edit Inputs</span>
        </button>
      </div>

      {/* Summary Grid: Displays the Server's Validated Data */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        <div className="p-3.5 rounded-lg bg-[#000000] border border-[#262626] space-y-1">
          <div className="flex items-center gap-1.5 text-xs font-medium text-[#888888]">
            <LuTarget className="w-3.5 h-3.5 text-[#A1A1A1]" />
            <span>Learning Goal</span>
          </div>
          <p className="text-[#FFFFFF] font-medium break-words text-sm">{data.goal}</p>
        </div>

        <div className="p-3.5 rounded-lg bg-[#000000] border border-[#262626] space-y-1">
          <div className="flex items-center gap-1.5 text-xs font-medium text-[#888888]">
            <LuBookOpen className="w-3.5 h-3.5 text-[#A1A1A1]" />
            <span>Current Experience</span>
          </div>
          <p className="text-[#FFFFFF] font-medium break-words text-sm">{data.experience}</p>
        </div>

        <div className="p-3.5 rounded-lg bg-[#000000] border border-[#262626] space-y-1">
          <div className="flex items-center gap-1.5 text-xs font-medium text-[#888888]">
            <LuClock className="w-3.5 h-3.5 text-[#A1A1A1]" />
            <span>Schedule</span>
          </div>
          <p className="text-[#FFFFFF] font-medium text-sm">
            {data.durationDays} days • {data.hoursPerDay} hours/day
          </p>
        </div>

        <div className="p-3.5 rounded-lg bg-[#000000] border border-[#262626] space-y-1">
          <div className="flex items-center gap-1.5 text-xs font-medium text-[#888888]">
            <LuCalendar className="w-3.5 h-3.5 text-[#A1A1A1]" />
            <span>Start Date</span>
          </div>
          <p className="text-[#FFFFFF] font-medium text-sm">{data.startDate}</p>
        </div>
      </div>

      {/* Preferences Pill List */}
      <div className="p-3.5 rounded-lg bg-[#000000] border border-[#262626] space-y-2">
        <span className="text-xs font-medium text-[#888888]">
          Resource Preferences
        </span>
        <div className="flex flex-wrap gap-2 pt-0.5">
          {data.resourcePreferences && data.resourcePreferences.length > 0 ? (
            data.resourcePreferences.map((pref) => (
              <span
                key={pref}
                className="px-2.5 py-1 text-xs rounded-md font-medium bg-[#171717] text-[#EDEDED] border border-[#262626] capitalize"
              >
                {pref}
              </span>
            ))
          ) : (
            <span className="text-xs text-[#666666] italic">No specific preferences (Any)</span>
          )}
        </div>
      </div>

      {/* Raw FastAPI Response Inspector */}
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

export default SubmissionPreview;
