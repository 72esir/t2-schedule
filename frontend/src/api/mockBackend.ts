import type {
  BackendScheduleByDate,
  CollectionPeriod,
  CollectionPeriodCreatePayload,
  CollectionPeriodFromTemplatePayload,
  ExportedFile,
  ManagerDashboard,
  PeriodStats,
  PeriodSubmissions,
  PeriodTemplate,
  ScheduleBulkUpdatePayload,
  ScheduleForUser,
  ScheduleSummary,
  ScheduleValidationResult,
  User,
  VacationDaysModerationPayload,
} from './types'
import type { DemoRole } from '../store/useAuthStore'

interface DemoState {
  period: CollectionPeriod
  schedule: BackendScheduleByDate
  pendingVerificationUsers: User[]
  pendingVacationUsers: User[]
}

const DEMO_STATE_STORAGE_KEY = 't2_schedule_demo_state_v1'
const ALLIANCE_NAME = 'Alliance 1'
const HOUR_NORM = 40

export const demoPeriodTemplates: PeriodTemplate[] = [
  {
    type: 'week',
    label: '1 неделя',
    description: '7 дней от даты начала',
    requires_period_end: false,
  },
  {
    type: 'two_weeks',
    label: '2 недели',
    description: '14 дней от даты начала',
    requires_period_end: false,
  },
  {
    type: 'month',
    label: 'Месяц',
    description: 'До последнего дня месяца',
    requires_period_end: false,
  },
  {
    type: 'custom',
    label: 'Период',
    description: 'Своя дата окончания',
    requires_period_end: true,
  },
]

export const demoUsers: Record<DemoRole, User> = {
  manager: {
    id: 1,
    external_id: 'm-demo-1',
    full_name: 'Мария Менеджер',
    alliance: ALLIANCE_NAME,
    category: 'manager',
    email: 'manager@demo.local',
    registered: true,
    is_verified: true,
    role: 'manager',
    vacation_days_declared: null,
    vacation_days_approved: null,
    vacation_days_status: 'approved',
  },
  user: {
    id: 2,
    external_id: 'u-demo-1',
    full_name: 'Иван Сотрудник',
    alliance: ALLIANCE_NAME,
    category: 'operator',
    email: 'employee@demo.local',
    registered: true,
    is_verified: true,
    role: 'user',
    vacation_days_declared: 14,
    vacation_days_approved: 14,
    vacation_days_status: 'approved',
  },
}

export const mockAuthApi = {
  async me(role: DemoRole): Promise<User> {
    return delay(demoUsers[role])
  },
}

export const mockPeriodApi = {
  async getCurrent(): Promise<CollectionPeriod | null> {
    const state = readDemoState()

    return delay(state.period.is_open ? state.period : null)
  },

  async getTemplates(): Promise<PeriodTemplate[]> {
    return delay(demoPeriodTemplates)
  },

  async create(payload: CollectionPeriodCreatePayload): Promise<CollectionPeriod> {
    const state = readDemoState()
    const period = createPeriod({
      periodStart: payload.period_start,
      periodEnd: payload.period_end,
      deadline: payload.deadline,
    })

    writeDemoState({ ...state, period })

    return delay(period)
  },

  async createFromTemplate(
    payload: CollectionPeriodFromTemplatePayload,
  ): Promise<CollectionPeriod> {
    const state = readDemoState()
    const periodEnd = resolvePeriodEnd(payload)
    const period = createPeriod({
      periodStart: payload.period_start,
      periodEnd,
      deadline: payload.deadline,
    })

    writeDemoState({
      ...state,
      period,
      schedule: createDefaultSchedule(period.period_start, period.period_end),
    })

    return delay(period)
  },

  async close(periodId: number): Promise<CollectionPeriod> {
    const state = readDemoState()
    const period = {
      ...state.period,
      id: periodId,
      is_open: false,
      updated_at: new Date().toISOString(),
    }

    writeDemoState({ ...state, period })

    return delay(period)
  },

  async getStats(): Promise<PeriodStats> {
    const state = readDemoState()
    const submittedCount = Object.keys(state.schedule).length > 0 ? 4 : 3

    return delay({
      total_employees: 6,
      submitted_count: submittedCount,
      pending_count: 6 - submittedCount,
    })
  },

  async getSubmissions(): Promise<PeriodSubmissions> {
    return delay({
      submitted: [
        demoUsers.user,
        createUser(5, 'Ольга Петрова', 'olga@demo.local', true),
      ],
      pending: [
        createUser(6, 'Павел Смирнов', 'pavel@demo.local', true),
      ],
    })
  },

  async getHistory(): Promise<CollectionPeriod[]> {
    return delay([readDemoState().period])
  },
}

export const mockScheduleApi = {
  async getMine(): Promise<BackendScheduleByDate> {
    return delay(readDemoState().schedule)
  },

  async updateMine(
    payload: ScheduleBulkUpdatePayload,
  ): Promise<BackendScheduleByDate> {
    const state = readDemoState()

    writeDemoState({ ...state, schedule: payload.days })

    return delay(payload.days)
  },

  async getMineSummary(): Promise<ScheduleSummary> {
    return delay(buildScheduleSummary(readDemoState().schedule))
  },

  async getMineValidation(): Promise<ScheduleValidationResult> {
    return delay(buildScheduleValidation(readDemoState().schedule))
  },

  async getByUser(userId: number): Promise<ScheduleForUser> {
    return delay({
      user: userId === demoUsers.user.id ? demoUsers.user : createUser(userId, 'Ольга Петрова', 'olga@demo.local', true),
      entries: readDemoState().schedule,
      vacation_work: null,
    })
  },

  async getSummaryByUser(): Promise<ScheduleSummary> {
    return delay(buildScheduleSummary(readDemoState().schedule))
  },

  async getValidationByUser(): Promise<ScheduleValidationResult> {
    return delay(buildScheduleValidation(readDemoState().schedule))
  },
}

export const mockManagerApi = {
  async getDashboard(): Promise<ManagerDashboard> {
    const state = readDemoState()
    const validation = buildScheduleValidation(state.schedule)
    const hasViolations = validation.violations.length > 0

    return delay({
      current_period: state.period.is_open ? state.period : null,
      total_employees: 6,
      submitted_count: 4,
      pending_count: 2,
      pending_verification_count: state.pendingVerificationUsers.length,
      pending_vacation_moderation_count: state.pendingVacationUsers.length,
      employees_with_violations_count: hasViolations ? 1 : 0,
      problem_employees: hasViolations
        ? [
            {
              user_id: demoUsers.user.id,
              full_name: demoUsers.user.full_name ?? 'Сотрудник',
              email: demoUsers.user.email,
              violation_count: validation.violations.length,
              violation_codes: validation.violations.map((item) => item.code),
              summary: validation.summary,
            },
          ]
        : [],
    })
  },

  async getUsers(): Promise<User[]> {
    const state = readDemoState()

    return delay([
      demoUsers.user,
      ...state.pendingVerificationUsers,
      ...state.pendingVacationUsers,
    ])
  },

  async getPendingVacationDays(): Promise<User[]> {
    return delay(readDemoState().pendingVacationUsers)
  },

  async getPendingVerificationUsers(): Promise<User[]> {
    return delay(readDemoState().pendingVerificationUsers)
  },

  async verifyUser(userId: number): Promise<User> {
    const state = readDemoState()
    const user = state.pendingVerificationUsers.find((item) => item.id === userId)
    const verifiedUser = {
      ...(user ?? createUser(userId, 'Новый сотрудник', null, false)),
      is_verified: true,
    }

    writeDemoState({
      ...state,
      pendingVerificationUsers: state.pendingVerificationUsers.filter(
        (item) => item.id !== userId,
      ),
    })

    return delay(verifiedUser)
  },

  async moderateVacationDays(
    userId: number,
    payload: VacationDaysModerationPayload,
  ): Promise<User> {
    const state = readDemoState()
    const user = state.pendingVacationUsers.find((item) => item.id === userId)
    const moderatedUser = {
      ...(user ?? createUser(userId, 'Сотрудник', null, true)),
      vacation_days_approved:
        payload.status === 'rejected' ? null : payload.approved_days,
      vacation_days_status: payload.status,
    }

    writeDemoState({
      ...state,
      pendingVacationUsers: state.pendingVacationUsers.filter(
        (item) => item.id !== userId,
      ),
    })

    return delay(moderatedUser)
  },
}

export const mockExportApi = {
  async schedule(): Promise<ExportedFile> {
    const rows = [
      'Employee,Total hours,Vacation days',
      `${demoUsers.user.full_name},${buildScheduleSummary(readDemoState().schedule).period_total_hours},2`,
    ]

    return delay({
      blob: new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8' }),
      filename: 'demo_schedule.csv',
    })
  },
}

export function resetDemoState(): void {
  writeDemoState(createInitialState())
}

function readDemoState(): DemoState {
  if (typeof window === 'undefined') {
    return createInitialState()
  }

  const storedState = window.localStorage.getItem(DEMO_STATE_STORAGE_KEY)

  if (!storedState) {
    const initialState = createInitialState()

    writeDemoState(initialState)

    return initialState
  }

  try {
    return JSON.parse(storedState) as DemoState
  } catch {
    const initialState = createInitialState()

    writeDemoState(initialState)

    return initialState
  }
}

function writeDemoState(state: DemoState): void {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(DEMO_STATE_STORAGE_KEY, JSON.stringify(state))
}

function createInitialState(): DemoState {
  const today = new Date()
  const start = new Date(today.getFullYear(), today.getMonth(), 1)
  const end = new Date(today.getFullYear(), today.getMonth() + 1, 0)
  const period = createPeriod({
    periodStart: toDateKey(start),
    periodEnd: toDateKey(end),
    deadline: addDays(today, 10).toISOString(),
  })

  return {
    period,
    schedule: createDefaultSchedule(period.period_start, period.period_end),
    pendingVerificationUsers: [
      createUser(3, 'Анна Новикова', 'anna@demo.local', false),
      createUser(4, 'Дмитрий Волков', 'dmitry@demo.local', false),
    ],
    pendingVacationUsers: [
      {
        ...createUser(7, 'Елена Морозова', 'elena@demo.local', true),
        vacation_days_declared: 21,
      },
      {
        ...createUser(8, 'Никита Орлов', 'nikita@demo.local', true),
        vacation_days_declared: 9,
      },
    ],
  }
}

function createPeriod({
  periodStart,
  periodEnd,
  deadline,
}: {
  periodStart: string
  periodEnd: string
  deadline: string
}): CollectionPeriod {
  const now = new Date().toISOString()

  return {
    id: Date.now(),
    alliance: ALLIANCE_NAME,
    period_start: periodStart,
    period_end: periodEnd,
    deadline,
    is_open: true,
    created_at: now,
    updated_at: now,
  }
}

function createDefaultSchedule(
  periodStart: string,
  periodEnd: string,
): BackendScheduleByDate {
  return getDateRange(periodStart, periodEnd).reduce<BackendScheduleByDate>(
    (schedule, dateKey) => {
      const date = parseDateKey(dateKey)
      const dayOfWeek = date.getDay()
      const dayOfMonth = date.getDate()

      if (dayOfWeek === 0 || dayOfWeek === 6) {
        schedule[dateKey] = { status: 'dayoff', meta: null }
      } else if (dayOfMonth === 15 || dayOfMonth === 16) {
        schedule[dateKey] = { status: 'vacation', meta: null }
      } else if (dayOfWeek === 3) {
        schedule[dateKey] = {
          status: 'split',
          meta: {
            splitStart1: '09:00',
            splitEnd1: '13:00',
            splitStart2: '14:00',
            splitEnd2: '18:00',
          },
        }
      } else {
        schedule[dateKey] = {
          status: 'shift',
          meta: {
            shiftStart: '09:00',
            shiftEnd: '17:00',
          },
        }
      }

      return schedule
    },
    {},
  )
}

function buildScheduleSummary(schedule: BackendScheduleByDate): ScheduleSummary {
  const dailyHours = Object.entries(schedule).reduce<Record<string, number>>(
    (hoursByDay, [dateKey, day]) => {
      hoursByDay[dateKey] = getDayHours(day)

      return hoursByDay
    },
    {},
  )
  const weeklyHours = Object.entries(dailyHours).reduce<Record<string, number>>(
    (hoursByWeek, [dateKey, hours]) => {
      const weekStart = getWeekStart(dateKey)

      hoursByWeek[weekStart] = roundHours((hoursByWeek[weekStart] ?? 0) + hours)

      return hoursByWeek
    },
    {},
  )

  return {
    daily_hours: dailyHours,
    weekly_hours: weeklyHours,
    period_total_hours: roundHours(
      Object.values(dailyHours).reduce((total, hours) => total + hours, 0),
    ),
    vacation_days_count: Object.values(schedule).filter(
      (day) => day.status === 'vacation',
    ).length,
    max_work_streak: getMaxWorkStreak(schedule),
  }
}

function buildScheduleValidation(
  schedule: BackendScheduleByDate,
): ScheduleValidationResult {
  const summary = buildScheduleSummary(schedule)
  const weeklyViolations = Object.entries(summary.weekly_hours)
    .filter(([, hours]) => Math.abs(hours - HOUR_NORM) > 0.001)
    .map(([weekStart, hours]) => ({
      code: hours < HOUR_NORM ? 'WEEKLY_HOURS_UNDER' : 'WEEKLY_HOURS_OVER',
      level: 'warning',
      message:
        hours < HOUR_NORM
          ? `Недобор часов за неделю с ${weekStart}`
          : `Перебор часов за неделю с ${weekStart}`,
      context: {
        week_start: weekStart,
        actual_hours: hours,
        required_hours: HOUR_NORM,
        difference: roundHours(Math.abs(HOUR_NORM - hours)),
      },
    }))
  const streakViolation =
    summary.max_work_streak > 6
      ? [
          {
            code: 'WORK_STREAK_OVER_6',
            level: 'warning',
            message: 'Больше 6 рабочих дней подряд',
            context: {
              max_work_streak: summary.max_work_streak,
            },
          },
        ]
      : []
  const violations = [...weeklyViolations, ...streakViolation]

  return {
    is_valid: violations.length === 0,
    violations,
    summary,
  }
}

function getDayHours(day: BackendScheduleByDate[string]): number {
  if (day.status === 'shift') {
    return getIntervalHours(day.meta.shiftStart, day.meta.shiftEnd)
  }

  if (day.status === 'split') {
    return roundHours(
      getIntervalHours(day.meta.splitStart1, day.meta.splitEnd1) +
        getIntervalHours(day.meta.splitStart2, day.meta.splitEnd2),
    )
  }

  return 0
}

function getIntervalHours(start: string, end: string): number {
  const startMinutes = timeToMinutes(start)
  const endMinutes = timeToMinutes(end)
  const duration = endMinutes >= startMinutes
    ? endMinutes - startMinutes
    : endMinutes + 24 * 60 - startMinutes

  return roundHours(duration / 60)
}

function timeToMinutes(value: string): number {
  const [hours, minutes] = value.split(':').map(Number)

  return hours * 60 + minutes
}

function getMaxWorkStreak(schedule: BackendScheduleByDate): number {
  let currentStreak = 0
  let maxStreak = 0

  Object.keys(schedule)
    .sort()
    .forEach((dateKey) => {
      if (getDayHours(schedule[dateKey]) > 0) {
        currentStreak += 1
        maxStreak = Math.max(maxStreak, currentStreak)
      } else {
        currentStreak = 0
      }
    })

  return maxStreak
}

function resolvePeriodEnd(payload: CollectionPeriodFromTemplatePayload): string {
  const start = parseDateKey(payload.period_start)

  if (payload.template_type === 'week') {
    return toDateKey(addDays(start, 6))
  }

  if (payload.template_type === 'two_weeks') {
    return toDateKey(addDays(start, 13))
  }

  if (payload.template_type === 'month') {
    return toDateKey(new Date(start.getFullYear(), start.getMonth() + 1, 0))
  }

  return payload.period_end ?? payload.period_start
}

function createUser(
  id: number,
  fullName: string,
  email: string | null,
  isVerified: boolean,
): User {
  return {
    id,
    external_id: `demo-${id}`,
    full_name: fullName,
    alliance: ALLIANCE_NAME,
    category: 'operator',
    email,
    registered: true,
    is_verified: isVerified,
    role: 'user',
    vacation_days_declared: 14,
    vacation_days_approved: null,
    vacation_days_status: 'pending',
  }
}

function getDateRange(startDate: string, endDate: string): string[] {
  const dates: string[] = []
  const currentDate = parseDateKey(startDate)
  const end = parseDateKey(endDate)

  while (currentDate <= end) {
    dates.push(toDateKey(currentDate))
    currentDate.setDate(currentDate.getDate() + 1)
  }

  return dates
}

function getWeekStart(dateKey: string): string {
  const date = parseDateKey(dateKey)
  const day = date.getDay()
  const diff = day === 0 ? -6 : 1 - day

  date.setDate(date.getDate() + diff)

  return toDateKey(date)
}

function parseDateKey(dateKey: string): Date {
  return new Date(`${dateKey}T00:00:00`)
}

function toDateKey(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')

  return `${year}-${month}-${day}`
}

function addDays(date: Date, amount: number): Date {
  const nextDate = new Date(date)

  nextDate.setDate(nextDate.getDate() + amount)

  return nextDate
}

function roundHours(hours: number): number {
  return Math.round(hours * 10) / 10
}

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => {
    window.setTimeout(() => resolve(value), 180)
  })
}
