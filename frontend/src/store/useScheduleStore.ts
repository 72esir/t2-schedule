import { endOfMonth, startOfMonth } from 'date-fns'
import { create } from 'zustand'

import type {
  DateInput,
  ScheduleByDate,
  SchedulePeriod,
  ScheduleRuleViolations,
  ScheduleShift,
} from '../types/schedule'
import {
  calculateWeeklyTotalHours,
  getScheduleRuleViolations,
  isScheduleRuleViolated,
  toDateKey,
} from '../utils/time-calculations'

const initialPeriod = createDefaultPeriod()

export interface ScheduleStoreState {
  currentPeriod: SchedulePeriod
  shiftsByDate: ScheduleByDate
  setCurrentPeriod: (period: SchedulePeriod) => void
  setSchedule: (schedule: ScheduleByDate) => void
  setShift: (date: DateInput, data: ScheduleShift | null | undefined) => void
  clearSchedule: () => void
  weeklyTotalHours: (weekDate?: DateInput) => number
  getRuleViolations: (weekDate?: DateInput) => ScheduleRuleViolations
  isRuleViolated: (weekDate?: DateInput) => boolean
}

export const useScheduleStore = create<ScheduleStoreState>((set, get) => ({
  currentPeriod: initialPeriod,
  shiftsByDate: {},

  setCurrentPeriod: (period) => {
    set({ currentPeriod: period })
  },

  setSchedule: (schedule) => {
    set({ shiftsByDate: schedule })
  },

  setShift: (date, data) => {
    const dateKey = toDateKey(date)

    set((state) => {
      if (!data) {
        const nextShiftsByDate = { ...state.shiftsByDate }

        delete nextShiftsByDate[dateKey]

        return { shiftsByDate: nextShiftsByDate }
      }

      return {
        shiftsByDate: {
          ...state.shiftsByDate,
          [dateKey]: data,
        },
      }
    })
  },

  clearSchedule: () => {
    set({ shiftsByDate: {} })
  },

  weeklyTotalHours: (weekDate) => {
    const { currentPeriod, shiftsByDate } = get()

    return calculateWeeklyTotalHours(
      shiftsByDate,
      weekDate ?? currentPeriod.startDate,
    )
  },

  getRuleViolations: (weekDate) => {
    const { currentPeriod, shiftsByDate } = get()

    return getScheduleRuleViolations(
      shiftsByDate,
      weekDate ?? currentPeriod.startDate,
      currentPeriod.startDate,
      currentPeriod.endDate,
    )
  },

  isRuleViolated: (weekDate) => {
    const { currentPeriod, shiftsByDate } = get()

    return isScheduleRuleViolated(
      shiftsByDate,
      weekDate ?? currentPeriod.startDate,
      currentPeriod.startDate,
      currentPeriod.endDate,
    )
  },
}))

function createDefaultPeriod(): SchedulePeriod {
  const today = new Date()
  const startDate = startOfMonth(today)
  const endDate = endOfMonth(today)

  return {
    startDate: toDateKey(startDate),
    endDate: toDateKey(endDate),
    deadline: endDate.toISOString(),
    allianceName: '',
    status: 'closed',
    editingReopened: false,
  }
}
