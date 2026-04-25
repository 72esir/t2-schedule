import {
  addDays,
  differenceInMinutes,
  eachDayOfInterval,
  endOfWeek,
  format,
  isAfter,
  isEqual,
  parseISO,
  set,
  startOfDay,
  startOfWeek,
} from 'date-fns'

import type {
  DateInput,
  ISODateString,
  ScheduleByDate,
  ScheduleRuleViolations,
  ScheduleShift,
  TimeInterval,
  TimeString,
} from '../types/schedule'

export const WEEKLY_HOURS_NORM = 40
export const MAX_WORKING_DAYS_IN_ROW = 6
export const DATE_KEY_FORMAT = 'yyyy-MM-dd'

const MINUTES_IN_HOUR = 60
const TIME_PATTERN = /^([01]\d|2[0-3]):([0-5]\d)$/
const HOURS_EPSILON = 0.001

export const normalizeDateInput = (date: DateInput): Date =>
  date instanceof Date ? date : parseISO(date)

export const toDateKey = (date: DateInput): ISODateString =>
  format(normalizeDateInput(date), DATE_KEY_FORMAT)

export const getWeekRange = (date: DateInput): { start: Date; end: Date } => {
  const normalizedDate = normalizeDateInput(date)

  return {
    start: startOfWeek(normalizedDate, { weekStartsOn: 1 }),
    end: endOfWeek(normalizedDate, { weekStartsOn: 1 }),
  }
}

export const getDateRange = (
  startDate: DateInput,
  endDate: DateInput,
): Date[] =>
  eachDayOfInterval({
    start: normalizeDateInput(startDate),
    end: normalizeDateInput(endDate),
  })

export const calculateIntervalHours = (
  interval: TimeInterval,
  date: DateInput = new Date(),
): number => {
  const baseDate = normalizeDateInput(date)
  const startDate = toDateAtTime(baseDate, interval.start)
  const rawEndDate = toDateAtTime(baseDate, interval.end)

  if (isEqual(rawEndDate, startDate)) {
    return 0
  }

  const endDate = isAfter(rawEndDate, startDate)
    ? rawEndDate
    : addDays(rawEndDate, 1)

  return differenceInMinutes(endDate, startDate) / MINUTES_IN_HOUR
}

export const calculateShiftHours = (
  shift: ScheduleShift | undefined,
  date: DateInput = new Date(),
): number => {
  if (!shift) {
    return 0
  }

  switch (shift.type) {
    case 'normal':
      return calculateIntervalHours(
        { start: shift.start, end: shift.end },
        date,
      )
    case 'split':
      return shift.intervals.reduce(
        (total, interval) => total + calculateIntervalHours(interval, date),
        0,
      )
    case 'day_off':
    case 'vacation':
      return 0
    default:
      return assertNever(shift)
  }
}

export const calculateWeeklyTotalHours = (
  schedule: ScheduleByDate,
  weekDate: DateInput = new Date(),
): number => {
  const { start, end } = getWeekRange(weekDate)

  return getDateRange(start, end).reduce((total, date) => {
    const dateKey = toDateKey(date)

    return total + calculateShiftHours(schedule[dateKey], date)
  }, 0)
}

export const isWorkingShift = (
  shift: ScheduleShift | undefined,
  date: DateInput = new Date(),
): boolean => calculateShiftHours(shift, date) > 0

export const hasSixWorkingDaysInRowViolation = (
  schedule: ScheduleByDate,
  startDate?: DateInput,
  endDate?: DateInput,
): boolean => {
  const dates = getDatesForConsecutiveCheck(schedule, startDate, endDate)
  let workingDaysInRow = 0

  for (const date of dates) {
    const dateKey = toDateKey(date)

    if (isWorkingShift(schedule[dateKey], date)) {
      workingDaysInRow += 1

      if (workingDaysInRow > MAX_WORKING_DAYS_IN_ROW) {
        return true
      }
    } else {
      workingDaysInRow = 0
    }
  }

  return false
}

export const getScheduleRuleViolations = (
  schedule: ScheduleByDate,
  weekDate: DateInput = new Date(),
  periodStartDate?: DateInput,
  periodEndDate?: DateInput,
): ScheduleRuleViolations => {
  const weeklyTotalHours = calculateWeeklyTotalHours(schedule, weekDate)

  return {
    weeklyHoursNorm:
      Math.abs(weeklyTotalHours - WEEKLY_HOURS_NORM) > HOURS_EPSILON,
    sixWorkingDaysInRow: hasSixWorkingDaysInRowViolation(
      schedule,
      periodStartDate,
      periodEndDate,
    ),
  }
}

export const isScheduleRuleViolated = (
  schedule: ScheduleByDate,
  weekDate: DateInput = new Date(),
  periodStartDate?: DateInput,
  periodEndDate?: DateInput,
): boolean => {
  const violations = getScheduleRuleViolations(
    schedule,
    weekDate,
    periodStartDate,
    periodEndDate,
  )

  return violations.weeklyHoursNorm || violations.sixWorkingDaysInRow
}

const toDateAtTime = (date: Date, time: TimeString): Date => {
  const [hours, minutes] = parseTime(time)

  return set(startOfDay(date), {
    hours,
    minutes,
    seconds: 0,
    milliseconds: 0,
  })
}

const parseTime = (time: TimeString): [hours: number, minutes: number] => {
  const match = TIME_PATTERN.exec(time)

  if (!match) {
    throw new Error(`Invalid time format "${time}". Expected HH:mm.`)
  }

  return [Number(match[1]), Number(match[2])]
}

const getDatesForConsecutiveCheck = (
  schedule: ScheduleByDate,
  startDate?: DateInput,
  endDate?: DateInput,
): Date[] => {
  if (startDate && endDate) {
    return getDateRange(startDate, endDate)
  }

  const sortedDateKeys = Object.keys(schedule).sort()

  if (sortedDateKeys.length === 0) {
    return []
  }

  return getDateRange(sortedDateKeys[0], sortedDateKeys[sortedDateKeys.length - 1])
}

const assertNever = (shift: never): never => {
  throw new Error(`Unsupported shift type: ${JSON.stringify(shift)}`)
}
