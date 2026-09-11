// ==============================================================================
// File: client/src/components/forms/LearningPathForm.tsx
// Purpose: Form component that collects user constraints, validates them,
//          and communicates with the FastAPI backend via POST /api/plan.
//
// What this component does:
// 1. Maintains local React state (formData) for the 6 learning constraint fields.
// 2. Client-side validates required inputs before sending a network request.
// 3. Manages network loading, error, and response states (isLoading, serverError, apiResponse).
// 4. Prevents duplicate submissions while a request is in flight.
// 5. Switches to SubmissionPreview to show the confirmed response from FastAPI.
//
// Data Flow:
// [User Clicks Submit] ──> validateForm()
//   ├── Has Errors: Displays red field errors (stays on client)
//   └── Valid:
//         ├── Sets isLoading = true (disables button, shows spinner)
//         ├── Calls submitLearningPlan(formData) ──> POST http://localhost:8000/api/plan
//         ├── Success: Receives PlanApiResponse ──> Shows <SubmissionPreview />
//         └── Failure: Catches error ──> Displays red server error banner
// ==============================================================================

import React, { useState } from 'react';
import type { LearningPathFormData, FormErrors, ResourcePreference, PlanApiResponse } from '../../types/form';
import { submitLearningPlan } from '../../services/api';
import FormField from '../ui/FormField';
import PreferenceChip from '../ui/PreferenceChip';
import SubmissionPreview from './SubmissionPreview';
import { LuSparkles, LuClock, LuCalendar, LuTarget, LuBookOpen, LuCircleAlert } from 'react-icons/lu';

const AVAILABLE_PREFERENCES: ResourcePreference[] = ['Videos', 'Documentation', 'Courses', 'Projects'];

export const LearningPathForm: React.FC = () => {
  // ----------------------------------------------------------------------------
  // 1. State Definition
  // ----------------------------------------------------------------------------
  const initialFormData: LearningPathFormData = {
    goal: '',
    experience: '',
    durationDays: 30,
    hoursPerDay: 2,
    startDate: new Date().toISOString().split('T')[0],
    preferences: ['Videos', 'Projects'],
  };

  const [formData, setFormData] = useState<LearningPathFormData>(initialFormData);
  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [apiResponse, setApiResponse] = useState<PlanApiResponse | null>(null);

  // ----------------------------------------------------------------------------
  // 2. Input Change Handler
  // ----------------------------------------------------------------------------
  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;

    setFormData((prev) => ({
      ...prev,
      [name]: type === 'number' ? (value === '' ? '' : Number(value)) : value,
    }));

    // Clear validation error when user edits the field
    if (errors[name as keyof LearningPathFormData]) {
      setErrors((prev) => ({
        ...prev,
        [name]: undefined,
      }));
    }

    // Clear server error when user makes changes
    if (serverError) {
      setServerError(null);
    }
  };

  // ----------------------------------------------------------------------------
  // 3. Toggle Resource Preferences
  // ----------------------------------------------------------------------------
  const handleTogglePreference = (preference: ResourcePreference) => {
    setFormData((prev) => {
      const exists = prev.preferences.includes(preference);
      const updated = exists
        ? prev.preferences.filter((p) => p !== preference)
        : [...prev.preferences, preference];

      return { ...prev, preferences: updated };
    });
  };

  // ----------------------------------------------------------------------------
  // 4. Client-side Form Validation
  // ----------------------------------------------------------------------------
  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.goal.trim()) {
      newErrors.goal = 'Please specify your target learning goal.';
    }

    if (!formData.experience.trim()) {
      newErrors.experience = 'Please mention your background or write "Beginner".';
    }

    if (formData.durationDays === '' || formData.durationDays <= 0) {
      newErrors.durationDays = 'Duration must be at least 1 day.';
    } else if (formData.durationDays > 365) {
      newErrors.durationDays = 'Duration cannot exceed 365 days.';
    }

    if (formData.hoursPerDay === '' || formData.hoursPerDay <= 0) {
      newErrors.hoursPerDay = 'Please allocate at least 0.5 hours per day.';
    } else if (formData.hoursPerDay > 16) {
      newErrors.hoursPerDay = 'Maximum 16 hours per day.';
    }

    if (!formData.startDate) {
      newErrors.startDate = 'Please pick a target start date.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // ----------------------------------------------------------------------------
  // 5. Submit Handler (Sends Request to FastAPI via fetch)
  // ----------------------------------------------------------------------------
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Prevent duplicate clicks while request is running
    if (isLoading) {
      return;
    }

    // Validate inputs locally first
    if (!validateForm()) {
      return;
    }

    setServerError(null);
    setIsLoading(true);

    try {
      // Call our API service which uses native fetch()
      const response = await submitLearningPlan(formData);
      console.log('FastAPI Response Received:', response);

      // Save backend response and transition to preview
      setApiResponse(response);
    } catch (err) {
      console.error('Failed to submit learning plan:', err);
      setServerError(
        err instanceof Error
          ? err.message
          : 'Unable to reach the PathAI backend server. Please check your connection.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  // ----------------------------------------------------------------------------
  // 6. Reset Handler
  // ----------------------------------------------------------------------------
  const handleReset = () => {
    setApiResponse(null);
    setServerError(null);
  };

  // If a valid response was received from the backend, show the response screen
  if (apiResponse) {
    return (
      <SubmissionPreview
        response={apiResponse}
        onReset={handleReset}
        planConstraints={{
          durationDays: Number(formData.durationDays),
          hoursPerDay: Number(formData.hoursPerDay),
          startDate: formData.startDate,
        }}
      />
    );

  }

  // ----------------------------------------------------------------------------
  // 7. Form UI Render
  // ----------------------------------------------------------------------------
  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="bg-[#111111] border border-[#262626] rounded-2xl p-6 sm:p-9 space-y-7 shadow-2xl text-left"
    >
      {/* Card Header */}
      <div className="border-b border-[#222222] pb-6 space-y-2">
        <h2 className="text-xl sm:text-2xl font-semibold tracking-[-0.02em] text-[#FFFFFF]">
          Configure Learning Plan
        </h2>
        <p className="text-sm text-[#888888] font-normal leading-relaxed">
          Set your objectives and constraints. The agent will research and construct your personalized curriculum.
        </p>
      </div>

      {/* Backend Error Banner */}
      {serverError && (
        <div className="p-4 rounded-xl bg-[#EE0000]/10 border border-[#EE0000]/30 text-[#EE0000] text-xs font-medium flex items-start gap-2.5 animate-fadeIn">
          <LuCircleAlert className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div className="space-y-1 text-left">
            <p className="font-semibold text-white">Backend Communication Error</p>
            <p className="text-[#D4D4D4] leading-relaxed">{serverError}</p>
            <p className="text-[#737373] text-[11px] pt-0.5">
              Make sure your FastAPI server is running at <span className="font-mono text-[#A1A1A1]">http://localhost:8000</span>.
            </p>
          </div>
        </div>
      )}

      {/* Field 1: Learning Goal */}
      <FormField
        id="goal"
        label="Target Learning Goal"
        required
        hint="e.g. Generative AI, Rust Systems, Kubernetes"
        error={errors.goal}
      >
        <div className="relative">
          <input
            id="goal"
            name="goal"
            type="text"
            disabled={isLoading}
            value={formData.goal}
            onChange={handleChange}
            placeholder='e.g., "Learn Generative AI with LangGraph and RAG"'
            className={`w-full pl-10 pr-4 py-2.5 rounded-lg bg-[#000000] border text-[#EDEDED] placeholder:text-[#555555] text-sm focus:outline-none transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
              errors.goal
                ? 'border-[#EE0000] focus:border-[#EE0000]'
                : 'border-[#262626] hover:border-[#383838] focus:border-[#EDEDED] focus:ring-1 focus:ring-[#EDEDED]'
            }`}
          />
          <LuTarget className="w-4 h-4 text-[#737373] absolute left-3.5 top-3 pointer-events-none" />
        </div>
      </FormField>

      {/* Field 2: Current Experience */}
      <FormField
        id="experience"
        label="Current Knowledge & Experience"
        required
        hint="Prevents redundant prerequisites"
        error={errors.experience}
      >
        <div className="relative">
          <textarea
            id="experience"
            name="experience"
            rows={3}
            disabled={isLoading}
            value={formData.experience}
            onChange={handleChange}
            placeholder='e.g., "3 years Python experience, familiar with linear regression and PyTorch basics"'
            className={`w-full pl-10 pr-4 py-2.5 rounded-lg bg-[#000000] border text-[#EDEDED] placeholder:text-[#555555] text-sm focus:outline-none transition-all resize-y disabled:opacity-50 disabled:cursor-not-allowed ${
              errors.experience
                ? 'border-[#EE0000] focus:border-[#EE0000]'
                : 'border-[#262626] hover:border-[#383838] focus:border-[#EDEDED] focus:ring-1 focus:ring-[#EDEDED]'
            }`}
          />
          <LuBookOpen className="w-4 h-4 text-[#737373] absolute left-3.5 top-3 pointer-events-none" />
        </div>
      </FormField>

      {/* Fields 3, 4, 5: Schedule Constraints Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Duration */}
        <FormField
          id="durationDays"
          label="Duration (Days)"
          required
          error={errors.durationDays}
        >
          <div className="relative">
            <input
              id="durationDays"
              name="durationDays"
              type="number"
              min={1}
              max={365}
              disabled={isLoading}
              value={formData.durationDays}
              onChange={handleChange}
              placeholder="30"
              className={`w-full pl-10 pr-3 py-2.5 rounded-lg bg-[#000000] border text-[#EDEDED] placeholder:text-[#555555] text-sm focus:outline-none transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
                errors.durationDays
                  ? 'border-[#EE0000] focus:border-[#EE0000]'
                  : 'border-[#262626] hover:border-[#383838] focus:border-[#EDEDED] focus:ring-1 focus:ring-[#EDEDED]'
              }`}
            />
            <LuClock className="w-4 h-4 text-[#737373] absolute left-3.5 top-3 pointer-events-none" />
          </div>
        </FormField>

        {/* Hours / Day */}
        <FormField
          id="hoursPerDay"
          label="Hours / Day"
          required
          error={errors.hoursPerDay}
        >
          <div className="relative">
            <input
              id="hoursPerDay"
              name="hoursPerDay"
              type="number"
              min={0.5}
              max={16}
              step={0.5}
              disabled={isLoading}
              value={formData.hoursPerDay}
              onChange={handleChange}
              placeholder="2"
              className={`w-full pl-10 pr-3 py-2.5 rounded-lg bg-[#000000] border text-[#EDEDED] placeholder:text-[#555555] text-sm focus:outline-none transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
                errors.hoursPerDay
                  ? 'border-[#EE0000] focus:border-[#EE0000]'
                  : 'border-[#262626] hover:border-[#383838] focus:border-[#EDEDED] focus:ring-1 focus:ring-[#EDEDED]'
              }`}
            />
            <LuClock className="w-4 h-4 text-[#737373] absolute left-3.5 top-3 pointer-events-none" />
          </div>
        </FormField>

        {/* Start Date */}
        <FormField
          id="startDate"
          label="Target Start Date"
          required
          error={errors.startDate}
        >
          <div className="relative">
            <input
              id="startDate"
              name="startDate"
              type="date"
              disabled={isLoading}
              value={formData.startDate}
              onChange={handleChange}
              className={`w-full pl-10 pr-3 py-2.5 rounded-lg bg-[#000000] border text-[#EDEDED] text-sm focus:outline-none transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
                errors.startDate
                  ? 'border-[#EE0000] focus:border-[#EE0000]'
                  : 'border-[#262626] hover:border-[#383838] focus:border-[#EDEDED] focus:ring-1 focus:ring-[#EDEDED]'
              }`}
            />
            <LuCalendar className="w-4 h-4 text-[#737373] absolute left-3.5 top-3 pointer-events-none" />
          </div>
        </FormField>
      </div>

      {/* Field 6: Resource Preferences */}
      <div className="space-y-2.5 text-left">
        <label className="block text-xs font-medium text-[#A1A1A1] tracking-normal">
          Resource Preferences <span className="text-[#666666] font-normal">(optional)</span>
        </label>
        <div className="flex flex-wrap gap-2.5 pt-0.5">
          {AVAILABLE_PREFERENCES.map((pref) => (
            <PreferenceChip
              key={pref}
              label={pref}
              selected={formData.preferences.includes(pref)}
              onToggle={handleTogglePreference}
            />
          ))}
        </div>
      </div>

      {/* Submit Button with Loading State */}
      <div className="pt-5 border-t border-[#222222]">
        <button
          type="submit"
          disabled={isLoading}
          className={`w-full py-3 px-6 rounded-lg font-medium text-sm text-[#000000] bg-[#FFFFFF] transition-all duration-150 flex items-center justify-center gap-2 shadow-sm ${
            isLoading
              ? 'opacity-70 cursor-not-allowed'
              : 'hover:bg-[#E5E5E5] active:bg-[#CCCCCC] cursor-pointer'
          }`}
        >
          {isLoading ? (
            <>
              {/* Spinner animation */}
              <span className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" />
              <span>Sending to PathAI Server...</span>
            </>
          ) : (
            <>
              <LuSparkles className="w-4 h-4 text-[#000000]" />
              <span>Generate Learning Path</span>
            </>
          )}
        </button>
      </div>
    </form>
  );
};

export default LearningPathForm;
