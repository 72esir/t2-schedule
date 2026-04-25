import { eachDayOfInterval, getDay } from 'date-fns'

import type {
  ScheduleByDate,
  SchedulePeriod,
  ScheduleShift,
} from '../types/schedule'
import { normalizeDateInput, toDateKey } from '../utils/time-calculations'

export function createMockSchedule(period: SchedulePeriod): ScheduleByDate {
  const start = normalizeDateInput(period.startDate)
  const end = normalizeDateInput(period.endDate)

  return eachDayOfInterval({ start, end }).reduce<ScheduleByDate>(
    (schedule, date) => {
      schedule[toDateKey(date)] = createMockShift(date)

      return schedule
    },
    {},
  )
}

function createMockShift(date: Date): ScheduleShift {
  const dayOfWeek = getDay(date)
  const dayOfMonth = date.getDate()

  if (dayOfWeek === 0 || dayOfWeek === 6) {
    return { type: 'day_off' }
  }

  if (dayOfMonth === 15 || dayOfMonth === 16) {
    return { type: 'vacation' }
  }

  if (dayOfWeek === 3) {
    return {
      type: 'split',
      intervals: [
        { start: '09:00', end: '13:00' },
        { start: '14:00', end: '18:00' },
      ],
    }
  }

  return {
    type: 'normal',
    start: '09:00',
    end: '17:00',
  }
}
