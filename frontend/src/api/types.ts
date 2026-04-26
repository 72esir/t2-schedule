export type UserRole = 'manager' | 'user'

export type VacationDaysStatus =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'adjusted'

export type BackendScheduleStatus = 'shift' | 'split' | 'dayoff' | 'vacation'

export type PeriodTemplateType = 'week' | 'two_weeks' | 'month' | 'custom'

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface UserBase {
  external_id: string | null
  full_name: string | null
  alliance: string | null
  category: string | null
}

export interface User extends UserBase {
  id: number
  email: string | null
  registered: boolean
  is_verified: boolean
  role: UserRole
  vacation_days_declared: number | null
  vacation_days_approved: number | null
  vacation_days_status: VacationDaysStatus
}

export interface LoginPayload {
  email: string
  password: string
}

export interface EmployeeRegisterPayload {
  email: string
  password: string
  external_id?: string
  full_name?: string
  alliance?: string
  category?: string
  vacation_days_declared?: number
}

export interface VerificationPayload {
  token: string
}

export interface StreakHistoryItem {
  period_id: number
  period_start: string
  period_end: string
  deadline: string
  success: boolean
  reason: string
}

export interface UserStreak {
  current_streak: number
  longest_streak: number
  completed_periods_count: number
  evaluated_periods_count: number
  bonus_balance: number
  redeemable_sets: number
  history: StreakHistoryItem[]
}

export interface RedeemStreakResult {
  converted_streak: number
  awarded_bonus: number
  bonus_balance: number
  current_streak: number
  redeemable_sets: number
}

export interface CollectionPeriod {
  id: number
  alliance: string
  period_start: string
  period_end: string
  deadline: string
  is_open: boolean
  created_at: string
  updated_at: string
}

export interface ShiftScheduleDay {
  status: 'shift'
  meta: {
    shiftStart: string
    shiftEnd: string
  }
}

export interface SplitScheduleDay {
  status: 'split'
  meta: {
    splitStart1: string
    splitEnd1: string
    splitStart2: string
    splitEnd2: string
  }
}

export interface EmptyScheduleDay {
  status: 'dayoff' | 'vacation'
  meta: null
}

export type BackendScheduleDay =
  | ShiftScheduleDay
  | SplitScheduleDay
  | EmptyScheduleDay

export type BackendScheduleByDate = Record<string, BackendScheduleDay>

export interface ScheduleBulkUpdatePayload {
  days: BackendScheduleByDate
}

export interface ScheduleForUser {
  user: User
  entries: BackendScheduleByDate
  vacation_work: Record<string, unknown> | null
}

export interface ScheduleSummary {
  daily_hours: Record<string, number>
  weekly_hours: Record<string, number>
  period_total_hours: number
  vacation_days_count: number
  max_work_streak: number
}

export interface ScheduleViolation {
  code: string
  level: string
  message: string
  context: Record<string, unknown>
}

export interface ScheduleValidationResult {
  is_valid: boolean
  violations: ScheduleViolation[]
  summary: ScheduleSummary
}

export interface PeriodTemplate {
  type: PeriodTemplateType
  label: string
  description: string
  requires_period_end: boolean
}

export interface CollectionPeriodCreatePayload {
  period_start: string
  period_end: string
  deadline: string
}

export interface CollectionPeriodFromTemplatePayload {
  template_type: PeriodTemplateType
  period_start: string
  period_end?: string
  deadline: string
}

export interface PeriodStats {
  total_employees: number
  submitted_count: number
  pending_count: number
}

export interface PeriodSubmissions {
  submitted: User[]
  pending: User[]
}

export interface ManagerProblemEmployee {
  user_id: number
  full_name: string
  email: string | null
  violation_count: number
  violation_codes: string[]
  summary: ScheduleSummary | null
}

export interface ManagerDashboard {
  current_period: CollectionPeriod | null
  total_employees: number
  submitted_count: number
  pending_count: number
  pending_verification_count: number
  pending_vacation_moderation_count: number
  employees_with_violations_count: number
  problem_employees: ManagerProblemEmployee[]
}

export interface VacationDaysModerationPayload {
  approved_days: number
  status: VacationDaysStatus
}

export interface ScheduleTemplateCreatePayload {
  name: string
  work_days: number
  rest_days: number
  shift_start: string
  shift_end: string
  has_break: boolean
  break_start?: string | null
  break_end?: string | null
}

export interface ScheduleTemplate {
  id: number
  user_id: number
  name: string
  work_days: number
  rest_days: number
  shift_start: string
  shift_end: string
  has_break: boolean
  break_start: string | null
  break_end: string | null
  created_at: string
  updated_at: string
}

export interface ExportedFile {
  blob: Blob
  filename: string
}

export interface ScheduleStatePayload {
  days: BackendScheduleByDate
  last_saved_at: string | null
}

export interface ScheduleChangeRequestPayload {
  employee_comment?: string
  days: BackendScheduleByDate
}

export interface PendingScheduleChangeRequest {
  id: number
  user_id: number
  status: 'pending' | 'approved' | 'rejected'
  employee_comment: string | null
  manager_comment: string | null
  current_days: BackendScheduleByDate
  proposed_days: BackendScheduleByDate
  changed_days: string[]
  created_at: string
  full_name?: string | null
  email?: string | null
  alliance?: string | null
}

export interface ScheduleChangeRequestManagerApproval {
  manager_comment?: string
}

export interface SuggestedTemplate {
  has_suggestion: boolean
  period_id: number | null
  match_count: number
  source_period_ids: number[]
  days: BackendScheduleByDate
}
