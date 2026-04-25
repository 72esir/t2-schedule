export type ISODateString = string
export type TimeString = `${number}${number}:${number}${number}`
export type DateInput = Date | ISODateString

export type ShiftType = 'normal' | 'split' | 'day_off' | 'vacation'
export type PeriodStatus = 'open' | 'closed'
export type ScheduleSubmissionStatus = 'draft' | 'submitted'

export interface TimeInterval {
  start: TimeString
  end: TimeString
}

export interface BaseShift {
  type: ShiftType
  comment?: string
}

export interface NormalShift extends BaseShift {
  type: 'normal'
  start: TimeString
  end: TimeString
}

export interface SplitShift extends BaseShift {
  type: 'split'
  intervals: readonly [TimeInterval, TimeInterval]
}

export interface DayOffShift extends BaseShift {
  type: 'day_off'
}

export interface VacationShift extends BaseShift {
  type: 'vacation'
}

export type ScheduleShift =
  | NormalShift
  | SplitShift
  | DayOffShift
  | VacationShift

export type ScheduleByDate = Partial<Record<ISODateString, ScheduleShift>>

export interface SchedulePeriod {
  startDate: ISODateString
  endDate: ISODateString
  deadline: ISODateString
  allianceName: string
  status: PeriodStatus
  editingReopened: boolean
}

export interface ScheduleRuleViolations {
  weeklyHoursNorm: boolean
  sixWorkingDaysInRow: boolean
}
