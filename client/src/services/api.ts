// ==============================================================================
// File: client/src/services/api.ts
// Purpose: API service handling network requests between React and FastAPI.
//
// What this file does:
// 1. Takes user form data from React.
// 2. Maps the fields into the exact JSON format expected by FastAPI.
// 3. Uses the browser's native fetch() to send a POST request to http://localhost:8000/api/plan.
// 4. Returns the parsed JSON response or throws an error with helpful server details.
//
// Flow:
// [React Form Data] ──> submitLearningPlan() ──> fetch(POST /api/plan) ──> [FastAPI Backend]
// ==============================================================================

import type { LearningPathFormData, PlanApiRequest, PlanApiResponse, PlanModifyApiRequest } from '../types/form';

// The base URL of our running FastAPI server
const API_BASE_URL = 'http://localhost:8000';

/**
 * Sends the user's learning plan configuration to the FastAPI backend.
 * 
 * @param formData - The local React form data.
 * @returns Promise<PlanApiResponse> - The confirmed response from FastAPI.
 */
export async function submitLearningPlan(formData: LearningPathFormData): Promise<PlanApiResponse> {
  // 1. Map frontend form state to the exact API schema
  const payload: PlanApiRequest = {
    goal: formData.goal.trim(),
    experience: formData.experience.trim(),
    durationDays: Number(formData.durationDays),
    hoursPerDay: Number(formData.hoursPerDay),
    startDate: formData.startDate,
    // Convert uppercase labels (e.g. "Videos") to lowercase (e.g. "videos")
    resourcePreferences: formData.preferences.map((pref) => pref.toLowerCase()),
  };

  // 2. Perform the HTTP POST request using native fetch()
  const response = await fetch(`${API_BASE_URL}/api/plan`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  // 3. Handle non-200 HTTP responses (like 422 validation errors or 500 server errors)
  if (!response.ok) {
    let errorDetail = `Server returned status ${response.status}`;

    try {
      const errorJson = await response.json();
      // If FastAPI returns structured Pydantic errors: { detail: [{ loc: [...], msg: "..." }] }
      if (Array.isArray(errorJson.detail)) {
        errorDetail = errorJson.detail
          .map((item: { loc?: string[]; msg?: string }) => {
            const field = item.loc ? item.loc[item.loc.length - 1] : 'field';
            return `${field}: ${item.msg}`;
          })
          .join(', ');
      } else if (typeof errorJson.detail === 'string') {
        errorDetail = errorJson.detail;
      }
    } catch {
      // Response was not JSON, keep default status message
    }

    throw new Error(errorDetail);
  }

  // 4. Parse and return the successful JSON response
  const data: PlanApiResponse = await response.json();
  return data;
}

/**
 * Sends the existing plan + user feedback to POST /api/plan/modify.
 * Returns the revised PlanApiResponse containing the modified plan.
 *
 * @param payload - The current plan, feedback string, and original schedule constraints.
 * @returns Promise<PlanApiResponse> - The revised plan response.
 */
export async function modifyLearningPlan(payload: PlanModifyApiRequest): Promise<PlanApiResponse> {
  const response = await fetch(`${API_BASE_URL}/api/plan/modify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorDetail = `Server returned status ${response.status}`;
    try {
      const errorJson = await response.json();
      if (Array.isArray(errorJson.detail)) {
        errorDetail = errorJson.detail
          .map((item: { loc?: string[]; msg?: string }) => {
            const field = item.loc ? item.loc[item.loc.length - 1] : 'field';
            return `${field}: ${item.msg}`;
          })
          .join(', ');
      } else if (typeof errorJson.detail === 'string') {
        errorDetail = errorJson.detail;
      }
    } catch {
      // Response was not JSON
    }
    throw new Error(errorDetail);
  }

  const data: PlanApiResponse = await response.json();
  return data;
}

