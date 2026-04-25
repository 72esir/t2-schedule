import type {
  BackendScheduleByDate,
  BackendScheduleDay,
  ScheduleBulkUpdatePayload,
} from './types'
import type {
  ScheduleByDate,
  ScheduleShift,
  TimeInterval,
  TimeString,
} from '../types/schedule'

const TIME_PATTERN = /^([01]\d|2[0-3]):([0-5]\d)$/

export function backendScheduleToLocal(
  schedule: BackendScheduleByDate,
): ScheduleByDate {
  return Object.entries(schedule).reduce<ScheduleByDate>(
    (localSchedule, [dateKey, day]) => {
      localSchedule[dateKey] = backendDayToLocalShift(day)

      return localSchedule
    },
    {},
  )
}

export function localScheduleToBackend(
  schedule: ScheduleByDate,
): ScheduleBulkUpdatePayload {
  const days = Object.entries(schedule).reduce<BackendScheduleByDate>(
    (backendSchedule, [dateKey, shift]) => {
      if (shift) {
        backendSchedule[dateKey] = localShiftToBackendDay(shift)
      }

      return backendSchedule
    },
    {},
  )

  return { days }
}

function backendDayToLocalShift(day: BackendScheduleDay): ScheduleShift {
  switch (day.status) {
    case 'shift':
      return {
        type: 'normal',
        start: toTimeString(day.meta.shiftStart, '09:00'),
        end: toTimeString(day.meta.shiftEnd, '18:00'),
      }
    case 'split':
      return {
        type: 'split',
        intervals: [
          {
            start: toTimeString(day.meta.splitStart1, '09:00'),
            end: toTimeString(day.meta.splitEnd1, '13:00'),
          },
          {
            start: toTimeString(day.meta.splitStart2, '14:00'),
            end: toTimeString(day.meta.splitEnd2, '18:00'),
          },
        ] satisfies readonly [TimeInterval, TimeInterval],
      }
    case 'dayoff':
      return { type: 'day_off' }
    case 'vacation':
      return { type: 'vacation' }
    default:
      return assertNever(day)
  }
}

function localShiftToBackendDay(shift: ScheduleShift): BackendScheduleDay {
  switch (shift.type) {
    case 'normal':
      return {
        status: 'shift',
        meta: {
          shiftStart: shift.start,
          shiftEnd: shift.end,
        },
      }
    case 'split':
      return {
        status: 'split',
        meta: {
          splitStart1: shift.intervals[0].start,
          splitEnd1: shift.intervals[0].end,
          splitStart2: shift.intervals[1].start,
          splitEnd2: shift.intervals[1].end,
        },
      }
    case 'day_off':
      return {
        status: 'dayoff',
        meta: null,
      }
    case 'vacation':
      return {
        status: 'vacation',
        meta: null,
      }
    default:
      return assertNever(shift)
  }
}

function toTimeString(value: string, fallback: TimeString): TimeString {
  if (TIME_PATTERN.test(value)) {
    return value as TimeString
  }

  return fallback
}

function assertNever(value: never): never {
  throw new Error(`Unsupported schedule payload: ${JSON.stringify(value)}`)
}
