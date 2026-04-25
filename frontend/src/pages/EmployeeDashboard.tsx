import {
  AlertCircle,
  CalendarDays,
  CheckCircle2,
  Clock3,
  LogOut,
  RefreshCcw,
  Save,
  ShieldCheck,
} from 'lucide-react'
import {
  addDays,
  endOfWeek,
  format,
  isPast,
  isWithinInterval,
  parseISO,
  startOfWeek,
} from 'date-fns'
import { ru } from 'date-fns/locale'
import { useEffect, useMemo, useState } from 'react'

import { getApiErrorMessage } from '../api/client'
import {
  useCurrentPeriodQuery,
  useMyScheduleQuery,
  useMyScheduleSummaryQuery,
  useMyScheduleValidationQuery,
  useUpdateMyScheduleMutation,
} from '../api/queries'
import { backendScheduleToLocal, localScheduleToBackend } from '../api/scheduleMapper'
import type { User } from '../api/types'
import ShiftCell from '../components/schedule/ShiftCell'
import { useScheduleStore } from '../store/useScheduleStore'
import type { DateInput, ScheduleByDate } from '../types/schedule'
import {
  MAX_WORKING_DAYS_IN_ROW,
  WEEKLY_HOURS_NORM,
  calculateShiftHours,
  normalizeDateInput,
  toDateKey,
} from '../utils/time-calculations'

interface WeekViewModel {
  id: string
  startDate: Date
  endDate: Date
  days: Date[]
  totalHours: number
  workingDays: number
  progress: number
  hints: string[]
  isValid: boolean
}

const weekdayLabels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

interface EmployeeDashboardProps {
  user: User
  onLogout: () => void
}

export default function EmployeeDashboard({
  user,
  onLogout,
}: EmployeeDashboardProps) {
  const [submitNotice, setSubmitNotice] = useState('')
  const periodQuery = useCurrentPeriodQuery(user.is_verified)
  const currentBackendPeriod = periodQuery.data
  const hasActivePeriod = Boolean(currentBackendPeriod)
  const scheduleQuery = useMyScheduleQuery(user.is_verified && hasActivePeriod)
  const summaryQuery = useMyScheduleSummaryQuery(
    user.is_verified && hasActivePeriod,
  )
  const validationQuery = useMyScheduleValidationQuery(
    user.is_verified && hasActivePeriod,
  )
  const updateScheduleMutation = useUpdateMyScheduleMutation()
  const currentPeriod = useScheduleStore((state) => state.currentPeriod)
  const shiftsByDate = useScheduleStore((state) => state.shiftsByDate)
  const setCurrentPeriod = useScheduleStore((state) => state.setCurrentPeriod)
  const setSchedule = useScheduleStore((state) => state.setSchedule)
  const clearSchedule = useScheduleStore((state) => state.clearSchedule)
  const getRuleViolations = useScheduleStore((state) => state.getRuleViolations)

  useEffect(() => {
    if (!currentBackendPeriod) {
      clearSchedule()
      return
    }

    setCurrentPeriod({
      startDate: currentBackendPeriod.period_start,
      endDate: currentBackendPeriod.period_end,
      deadline: currentBackendPeriod.deadline,
      allianceName: currentBackendPeriod.alliance,
      status: currentBackendPeriod.is_open ? 'open' : 'closed',
      editingReopened: false,
    })
  }, [clearSchedule, currentBackendPeriod, setCurrentPeriod])

  useEffect(() => {
    if (!scheduleQuery.data) {
      return
    }

    setSchedule(backendScheduleToLocal(scheduleQuery.data))
  }, [scheduleQuery.data, setSchedule])

  const periodStart = normalizeDateInput(currentPeriod.startDate)
  const periodEnd = normalizeDateInput(currentPeriod.endDate)
  const periodRuleViolations = getRuleViolations(currentPeriod.startDate)
  const weekSummaries = useMemo(
    () =>
      createWeekViewModels(
        periodStart,
        periodEnd,
        shiftsByDate,
        getRuleViolations,
      ),
    [getRuleViolations, periodEnd, periodStart, shiftsByDate],
  )
  const periodHours = weekSummaries.reduce(
    (total, week) => total + week.totalHours,
    0,
  )
  const backendSummary = summaryQuery.data
  const backendValidation = validationQuery.data
  const displayPeriodHours = backendSummary?.period_total_hours ?? periodHours
  const deadlinePassed = currentBackendPeriod
    ? isPast(parseISO(currentBackendPeriod.deadline))
    : false
  const plannedDays = countPlannedDays(shiftsByDate, periodStart, periodEnd)
  const invalidWeeks = weekSummaries.filter((week) => !week.isValid).length
  const invalidIssues =
    backendValidation?.violations.length ??
    invalidWeeks + (periodRuleViolations.sixWorkingDaysInRow ? 1 : 0)
  const canEditSchedule =
    user.is_verified &&
    hasActivePeriod &&
    !deadlinePassed &&
    !scheduleQuery.isPending
  const canSubmit =
    canEditSchedule &&
    !updateScheduleMutation.isPending

  function handleSubmit() {
    if (!canSubmit) {
      setSubmitNotice(
        deadlinePassed
          ? 'Дедлайн редактирования прошёл.'
          : 'График сейчас нельзя сохранить.',
      )
      return
    }

    updateScheduleMutation.mutate(localScheduleToBackend(shiftsByDate), {
      onSuccess: () => setSubmitNotice('График сохранён в backend.'),
      onError: (error) => setSubmitNotice(getApiErrorMessage(error)),
    })
  }

  if (!user.is_verified) {
    return (
      <EmployeeState
        Icon={ShieldCheck}
        title="Аккаунт ожидает подтверждения"
        text="Менеджер должен подтвердить сотрудника перед доступом к графику."
        onLogout={onLogout}
      />
    )
  }

  if (periodQuery.isPending) {
    return (
      <EmployeeState
        Icon={RefreshCcw}
        title="Загружаем период"
        text="Синхронизируем данные текущего периода."
        onLogout={onLogout}
      />
    )
  }

  if (periodQuery.isError) {
    return (
      <EmployeeState
        Icon={AlertCircle}
        title="Backend недоступен"
        text={getApiErrorMessage(periodQuery.error)}
        onLogout={onLogout}
        onRetry={() => void periodQuery.refetch()}
      />
    )
  }

  if (!currentBackendPeriod) {
    return (
      <EmployeeState
        Icon={CalendarDays}
        title="Активного периода нет"
        text="Когда менеджер создаст период, здесь появится календарь."
        onLogout={onLogout}
        onRetry={() => void periodQuery.refetch()}
      />
    )
  }

  return (
    <main className="min-h-screen bg-[#f3f3f5] px-3 py-4 text-black sm:px-5 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-32px)] w-full max-w-[1480px] flex-col gap-4">
        <header className="grid gap-4 rounded-lg border border-black/10 bg-white px-4 py-4 shadow-sm lg:grid-cols-[1fr_auto] lg:items-center lg:px-6">
          <div className="min-w-0">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="grid size-10 place-items-center rounded-md bg-black text-sm font-black text-white">
                t<span className="text-[#ff3495]">2</span>
              </span>
              <span className="rounded-md bg-[#a7fc00] px-3 py-2 text-xs font-black uppercase text-black">
                График сотрудника
              </span>
              <span className="rounded-md border border-black/10 px-3 py-2 text-xs font-black uppercase text-black/55">
                {format(periodStart, 'd MMM', { locale: ru })} -{' '}
                {format(periodEnd, 'd MMM', { locale: ru })}
              </span>
            </div>

            <h1 className="text-3xl font-black uppercase leading-none sm:text-4xl">
              Мой рабочий период
            </h1>
          </div>

          <div className="grid gap-2 sm:min-w-[520px]">
            <div className="grid grid-cols-3 gap-2">
              <MetricTile
                Icon={Clock3}
                label="Часы"
                value={formatHours(displayPeriodHours)}
              />
              <MetricTile
                Icon={CalendarDays}
                label="Заполнено"
                value={`${plannedDays} дн.`}
              />
              <MetricTile
                Icon={ShieldCheck}
                label="Статус"
                value={formatScheduleStatus(
                  canSubmit,
                  deadlinePassed,
                  invalidIssues,
                  updateScheduleMutation.isPending,
                )}
                tone={canSubmit && invalidIssues === 0 ? 'success' : 'warning'}
              />
            </div>
            <button
              type="button"
              onClick={onLogout}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-black px-4 text-sm font-black uppercase text-white transition hover:bg-black/85 focus:outline-none focus:ring-4 focus:ring-black/20"
            >
              <LogOut size={16} aria-hidden="true" />
              Выйти
            </button>
          </div>
        </header>

        <section className="min-h-0 flex-1 overflow-hidden rounded-lg border border-black/10 bg-white shadow-sm">
          <div className="flex h-full flex-col">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-black/10 px-4 py-3 lg:px-6">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.12em] text-black/45">
                  Планирование
                </p>
                <p className="mt-1 text-sm font-bold text-black/65">
                  {deadlinePassed
                    ? 'Дедлайн прошёл, график открыт только для просмотра.'
                    : 'Выберите день, чтобы изменить смену. Итоги обновятся сразу.'}
                </p>
              </div>
              <SubmitButton
                canSubmit={canSubmit}
                isPending={updateScheduleMutation.isPending}
                onClick={handleSubmit}
              />
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3 lg:px-5">
              {scheduleQuery.isError && (
                <InlineAlert text={getApiErrorMessage(scheduleQuery.error)} />
              )}

              {backendValidation && !backendValidation.is_valid && (
                <div className="mb-4 space-y-2">
                  {backendValidation.violations.map((violation) => (
                    <InlineAlert key={violation.code} text={violation.message} />
                  ))}
                </div>
              )}

              {periodRuleViolations.sixWorkingDaysInRow && (
                <div className="mb-4 flex items-center gap-2 rounded-lg border border-[#ff3495]/20 bg-[#ff3495]/10 px-4 py-3 text-sm font-bold text-black">
                  <AlertCircle
                    size={16}
                    aria-hidden="true"
                    className="shrink-0 text-[#ff3495]"
                  />
                  В периоде есть 7 рабочих дней подряд. Добавьте выходной.
                </div>
              )}

              <div className="space-y-4">
                {weekSummaries.map((week, index) => (
                  <WeekSection
                    key={week.id}
                    week={week}
                    weekIndex={index}
                    periodStart={periodStart}
                    periodEnd={periodEnd}
                    readOnly={!canEditSchedule}
                  />
                ))}
              </div>
            </div>
          </div>
        </section>

        <p
          className={`min-h-6 px-1 text-sm font-bold ${
            submitNotice
              ? canSubmit
                ? 'text-black'
                : 'text-black/55'
              : 'text-transparent'
          }`}
        >
          {submitNotice || 'Нет уведомления'}
        </p>
      </div>
    </main>
  )
}

interface EmployeeStateProps {
  Icon: typeof ShieldCheck
  title: string
  text: string
  onLogout: () => void
  onRetry?: () => void
}

function EmployeeState({
  Icon,
  title,
  text,
  onLogout,
  onRetry,
}: EmployeeStateProps) {
  return (
    <main className="grid min-h-screen place-items-center bg-[#f3f3f5] px-4 text-black">
      <section className="w-full max-w-md rounded-lg border border-black/10 bg-white p-5 shadow-sm">
        <span className="mb-4 grid size-12 place-items-center rounded-md bg-black text-white">
          <Icon size={22} aria-hidden="true" />
        </span>
        <h1 className="text-2xl font-black uppercase leading-none">{title}</h1>
        <p className="mt-3 text-sm font-bold text-black/55">{text}</p>
        <div className="mt-5 flex flex-wrap gap-2">
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-[#a7fc00] px-4 text-sm font-black uppercase text-black transition hover:bg-[#95e700]"
            >
              <RefreshCcw size={16} aria-hidden="true" />
              Обновить
            </button>
          )}
          <button
            type="button"
            onClick={onLogout}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-black px-4 text-sm font-black uppercase text-white transition hover:bg-black/85"
          >
            <LogOut size={16} aria-hidden="true" />
            Выйти
          </button>
        </div>
      </section>
    </main>
  )
}

function InlineAlert({ text }: { text: string }) {
  return (
    <div className="mb-4 flex items-center gap-2 rounded-lg border border-[#ff3495]/20 bg-[#ff3495]/10 px-4 py-3 text-sm font-bold text-black">
      <AlertCircle
        size={16}
        aria-hidden="true"
        className="shrink-0 text-[#ff3495]"
      />
      {text}
    </div>
  )
}

interface WeekSectionProps {
  week: WeekViewModel
  weekIndex: number
  periodStart: Date
  periodEnd: Date
  readOnly: boolean
}

function WeekSection({
  week,
  weekIndex,
  periodStart,
  periodEnd,
  readOnly,
}: WeekSectionProps) {
  return (
    <article className="rounded-lg border border-black/10 bg-[#f7f7f8]">
      <div className="grid gap-3 border-b border-black/10 p-3 lg:grid-cols-[1fr_420px] lg:items-center lg:p-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-black uppercase leading-none">
              Неделя {weekIndex + 1}
            </h2>
            <span className="rounded-md border border-black/10 bg-white px-2 py-1 text-xs font-black uppercase text-black/55">
              {format(week.startDate, 'd MMM', { locale: ru })} -{' '}
              {format(week.endDate, 'd MMM', { locale: ru })}
            </span>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {week.hints.map((hint) => (
              <HintPill key={hint} isValid={week.isValid} text={hint} />
            ))}
          </div>
        </div>

        <WeeklySummaryBar week={week} />
      </div>

      <div className="overflow-x-auto p-3 lg:p-4">
        <div className="mb-2 grid min-w-[760px] grid-cols-7 gap-2 lg:min-w-0">
          {weekdayLabels.map((label) => (
            <span
              key={label}
              className="px-1 text-xs font-black uppercase tracking-[0.12em] text-black/35"
            >
              {label}
            </span>
          ))}
        </div>

        <div className="grid min-w-[760px] grid-cols-7 gap-2 lg:min-w-0">
          {week.days.map((day) => {
            const isMuted = !isWithinInterval(day, {
              start: periodStart,
              end: periodEnd,
            })

            return (
              <ShiftCell
                key={toDateKey(day)}
                date={day}
                isMuted={isMuted}
                readOnly={readOnly || isMuted}
              />
            )
          })}
        </div>
      </div>
    </article>
  )
}

function WeeklySummaryBar({ week }: { week: WeekViewModel }) {
  return (
    <div className="rounded-lg border border-black/10 bg-white p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.12em] text-black/45">
            Итого за неделю
          </p>
          <p className="mt-1 text-2xl font-black leading-none">
            {formatHours(week.totalHours)}
          </p>
        </div>
        <span
          className={`inline-flex h-9 items-center rounded-md px-3 text-xs font-black uppercase ${
            week.isValid
              ? 'bg-[#a7fc00] text-black'
              : 'bg-[#ff3495]/10 text-[#b0005a]'
          }`}
        >
          {week.isValid ? 'Норма' : 'Проверьте'}
        </span>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-black/10">
        <div
          className={`h-full rounded-full transition-[width] duration-300 ${
            week.isValid ? 'bg-[#a7fc00]' : 'bg-[#ff3495]'
          }`}
          style={{ width: `${week.progress}%` }}
        />
      </div>

      <p className="mt-2 text-xs font-bold text-black/50">
        {week.workingDays} раб. дн. / норма {WEEKLY_HOURS_NORM} ч
      </p>
    </div>
  )
}

interface MetricTileProps {
  Icon: typeof Clock3
  label: string
  value: string
  tone?: 'default' | 'success' | 'warning'
}

function MetricTile({
  Icon,
  label,
  value,
  tone = 'default',
}: MetricTileProps) {
  return (
    <div
      className={`rounded-lg border p-3 ${
        tone === 'success'
          ? 'border-[#a7fc00] bg-[#a7fc00]'
          : tone === 'warning'
            ? 'border-[#ff3495]/25 bg-[#ff3495]/10'
            : 'border-black/10 bg-[#f7f7f8]'
      }`}
    >
      <div className="mb-3 grid size-8 place-items-center rounded-md bg-white text-black">
        <Icon size={16} aria-hidden="true" />
      </div>
      <p className="text-xs font-black uppercase text-black/45">{label}</p>
      <p className="mt-1 truncate text-xl font-black leading-none">{value}</p>
    </div>
  )
}

function HintPill({ isValid, text }: { isValid: boolean; text: string }) {
  const Icon = isValid ? CheckCircle2 : AlertCircle

  return (
    <span
      className={`inline-flex min-h-8 items-center gap-2 rounded-md px-3 text-xs font-bold ${
        isValid
          ? 'bg-white text-black/55'
          : 'bg-white text-black shadow-[inset_0_0_0_1px_rgba(255,52,149,0.22)]'
      }`}
    >
      <Icon
        size={14}
        aria-hidden="true"
        className={isValid ? 'text-black/35' : 'text-[#ff3495]'}
      />
      {text}
    </span>
  )
}

function SubmitButton({
  canSubmit,
  isPending,
  onClick,
}: {
  canSubmit: boolean
  isPending: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!canSubmit}
      className={`inline-flex h-12 items-center justify-center gap-2 rounded-md px-5 text-sm font-black uppercase transition focus:outline-none focus:ring-4 ${
        canSubmit
          ? 'bg-[#a7fc00] text-black hover:bg-[#95e700] focus:ring-[#a7fc00]/40'
          : 'cursor-not-allowed border border-black/10 bg-[#f0f0f2] text-black/35 focus:ring-black/5'
      }`}
    >
      <Save size={16} aria-hidden="true" />
      {isPending ? 'Сохраняем' : 'Сохранить'}
    </button>
  )
}

function createWeekViewModels(
  periodStart: Date,
  periodEnd: Date,
  schedule: ScheduleByDate,
  getRuleViolations: (weekDate?: DateInput) => {
    weeklyHoursNorm: boolean
    sixWorkingDaysInRow: boolean
  },
): WeekViewModel[] {
  const gridStart = startOfWeek(periodStart, { weekStartsOn: 1 })
  const gridEnd = endOfWeek(periodEnd, { weekStartsOn: 1 })
  const weeks: WeekViewModel[] = []

  for (
    let weekStart = gridStart;
    weekStart <= gridEnd;
    weekStart = addDays(weekStart, 7)
  ) {
    const days = Array.from({ length: 7 }, (_, index) =>
      addDays(weekStart, index),
    )
    const totalHours = days.reduce((total, day) => {
      const dateKey = toDateKey(day)

      return total + calculateShiftHours(schedule[dateKey], dateKey)
    }, 0)
    const workingDays = days.filter((day) => {
      const dateKey = toDateKey(day)

      return calculateShiftHours(schedule[dateKey], dateKey) > 0
    }).length
    const ruleViolations = getRuleViolations(weekStart)
    const hasConsecutiveViolation = hasWorkingDaysInRowViolation(days, schedule)
    const weeklyHoursNorm = ruleViolations.weeklyHoursNorm
    const isValid = !weeklyHoursNorm && !hasConsecutiveViolation

    weeks.push({
      id: toDateKey(weekStart),
      startDate: weekStart,
      endDate: addDays(weekStart, 6),
      days,
      totalHours,
      workingDays,
      progress: Math.min((totalHours / WEEKLY_HOURS_NORM) * 100, 100),
      hints: createHints(totalHours, hasConsecutiveViolation),
      isValid,
    })
  }

  return weeks
}

function createHints(totalHours: number, hasConsecutiveViolation: boolean) {
  const hints: string[] = []
  const difference = roundHours(WEEKLY_HOURS_NORM - totalHours)

  if (difference > 0) {
    hints.push(`Не хватает ${formatHours(difference)}`)
  } else if (difference < 0) {
    hints.push(`Перебор на ${formatHours(Math.abs(difference))}`)
  } else {
    hints.push('Норма 40 ч выполнена')
  }

  if (hasConsecutiveViolation) {
    hints.push('7 рабочих дней подряд')
  } else {
    hints.push('Правило 6/1 соблюдено')
  }

  return hints
}

function hasWorkingDaysInRowViolation(
  days: Date[],
  schedule: ScheduleByDate,
): boolean {
  let workingDaysInRow = 0

  for (const day of days) {
    const dateKey = toDateKey(day)
    const hours = calculateShiftHours(schedule[dateKey], dateKey)

    if (hours > 0) {
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

function countPlannedDays(
  schedule: ScheduleByDate,
  periodStart: Date,
  periodEnd: Date,
): number {
  return Object.keys(schedule).filter((dateKey) => {
    const date = normalizeDateInput(dateKey)

    return isWithinInterval(date, {
      start: periodStart,
      end: periodEnd,
    })
  }).length
}

function formatHours(hours: number): string {
  const roundedHours = roundHours(hours)

  if (Number.isInteger(roundedHours)) {
    return `${roundedHours} ч`
  }

  return `${roundedHours.toFixed(1).replace('.', ',')} ч`
}

function roundHours(hours: number): number {
  return Math.round(hours * 10) / 10
}

function formatIssueCount(count: number): string {
  const lastDigit = count % 10
  const lastTwoDigits = count % 100

  if (lastDigit === 1 && lastTwoDigits !== 11) {
    return 'правка'
  }

  if (lastDigit >= 2 && lastDigit <= 4 && ![12, 13, 14].includes(lastTwoDigits)) {
    return 'правки'
  }

  return 'правок'
}

function formatScheduleStatus(
  canSubmit: boolean,
  deadlinePassed: boolean,
  invalidIssues: number,
  isPending: boolean,
): string {
  if (isPending) {
    return 'Сохраняем'
  }

  if (deadlinePassed) {
    return 'Дедлайн'
  }

  if (invalidIssues > 0) {
    return `${invalidIssues} ${formatIssueCount(invalidIssues)}`
  }

  return canSubmit ? 'Готов' : 'Закрыт'
}
