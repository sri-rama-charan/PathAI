// ==============================================================================
// File: client/src/types/form.ts
// Purpose: TypeScript type definitions for form inputs and structured AI outputs.
//
// What this file does:
// 1. LearningPathFormData: Internal React form state.
// 2. PlanApiRequest: Payload sent to POST /api/plan.
// 3. DayPlan: Structured day-by-day learning schedule item.
// 4. LearningPlan: Full structured curriculum from Gemini.
// 5. PlanResult: Feasibility assessment and optional LearningPlan.
// 6. PlanApiResponse: Top-level API response from FastAPI.
// ==============================================================================

export type ResourcePreference = 'Videos' | 'Documentation' | 'Courses' | 'Projects';

export interface LearningPathFormData {
  goal: string;
  experience: string;
  durationDays: number | '';
  hoursPerDay: number | '';
  startDate: string;
  preferences: ResourcePreference[];
}

export type FormErrors = Partial<Record<keyof LearningPathFormData, string>>;

export interface PlanApiRequest {
  goal: string;
  experience: string;
  durationDays: number;
  hoursPerDay: number;
  startDate: string;
  resourcePreferences: string[];
}

export interface DayPlan {
  day: number;
  date: string;
  topic: string;
  objectives: string[];
  tasks: string[];
  estimatedHours: number;
}

export interface LearningPlan {
  title: string;
  overview: string;
  prerequisites: string[];
  days: DayPlan[];
}

export interface PlanResult {
  feasible: boolean;
  feasibilityMessage: string;
  estimatedRequiredHours: number;
  availableHours: number;
  recommendations: string[];
  plan?: LearningPlan | null;
}

export interface PlanApiResponse {
  message: string;
  data: PlanResult;
  planId?: number | null;
  plan_id?: number | null;
}

export interface SavedPlanSummary {
  id: number;
  title: string;
  goal: string;
  durationDays?: number | null;
  google_doc_url?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface SavedPlanDetail {
  id: number;
  title: string;
  goal: string;
  input_data: Record<string, any>;
  plan_data: LearningPlan;
  google_doc_url?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface PlanPatchApiRequest {
  feedback: string;
  currentPlan?: LearningPlan;
  durationDays?: number;
  hoursPerDay?: number;
  startDate?: string;
}


/**
 * Tracks where the user is in the human-approval flow for a generated plan.
 *
 * "awaiting_approval" — plan has been generated; user has not yet acted.
 * "approved"          — user clicked "Approve Plan".
 */
export type ApprovalStatus = 'awaiting_approval' | 'approved';

/**
 * Request payload for POST /api/plan/modify.
 * Mirrors the PlanModifyRequest Pydantic schema on the backend.
 */
export interface PlanModifyApiRequest {
  currentPlan: LearningPlan;
  feedback: string;
  durationDays: number;
  hoursPerDay: number;
  startDate: string; // YYYY-MM-DD
}

/**
 * Response payload from POST /api/plan/create-doc.
 */
export interface DocCreateApiResponse {
  message: string;
  documentId: string;
  documentUrl: string;
  verified: boolean;
}

export interface CalendarEventMeta {
  day: number;
  topic: string;
  date: string;
  eventId?: string | null;
  htmlLink?: string | null;
  created: boolean;
  verified: boolean;
  error?: string | null;
}

/**
 * Response payload from POST /api/plan/create-calendar supporting full, partial, or failure outcomes.
 */
export interface CalendarCreateApiResponse {
  message: string;
  status: 'success' | 'partial_success' | 'failure';
  eventsCount: number;
  createdCount: number;
  verifiedCount: number;
  failedCount: number;
  eventIds: string[];
  events: CalendarEventMeta[];
}


