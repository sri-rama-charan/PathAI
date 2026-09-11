// ==============================================================================
// File: client/src/types/form.ts
// Purpose: Type definitions for the Learning Path input form and API communication.
//
// What this file does:
// 1. LearningPathFormData: Defines what data we collect in React state.
// 2. FormErrors: Tracks any validation error messages for each field.
// 3. PlanApiRequest: Defines the exact JSON payload sent to FastAPI (POST /api/plan).
// 4. PlanApiResponse: Defines the response received back from FastAPI.
// ==============================================================================

/**
 * Allowed resource preferences the user can select.
 */
export type ResourcePreference = 'Videos' | 'Documentation' | 'Courses' | 'Projects';

/**
 * The internal React form state structure.
 */
export interface LearningPathFormData {
  goal: string;                      // E.g., "Learn Generative AI"
  experience: string;                // E.g., "Python, basic ML"
  durationDays: number | '';         // E.g., 30 (days)
  hoursPerDay: number | '';          // E.g., 2 (hours/day)
  startDate: string;                 // E.g., "2026-09-15" (YYYY-MM-DD)
  preferences: ResourcePreference[]; // E.g., ['Videos', 'Projects']
}

/**
 * Error messages mapped to form field names.
 * If a field has no error, its value is undefined.
 */
export type FormErrors = Partial<Record<keyof LearningPathFormData, string>>;

/**
 * The exact JSON payload sent across the network to POST /api/plan.
 */
export interface PlanApiRequest {
  goal: string;
  experience: string;
  durationDays: number;
  hoursPerDay: number;
  startDate: string;
  resourcePreferences: string[];
}

/**
 * The response returned by our FastAPI backend.
 */
export interface PlanApiResponse {
  message: string;
  data: PlanApiRequest;
}
