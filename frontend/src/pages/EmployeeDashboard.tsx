import {
  AlertCircle,
  CalendarDays,
  CheckCircle2,
  Clock3,
  FileQuestion,
  LogOut,
  RefreshCcw,
  Save,
  Send,
  ShieldCheck,
  Sparkles,
  X,
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
  useMyChangeRequestQuery,
  useMyScheduleQuery,
  useMyScheduleSummaryQuery,
  useMyScheduleValidationQuery,
  useUpdateMyScheduleMutation,
  useCreateChangeRequestMutation,
  useSuggestedTemplateQuery,
  useApplySuggestedTemplateMutation,
} from '../api/queries'
import { useToast } from '../components/Toast'
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
import t2Logo from '../assets/t2-logo.svg'

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
  const changeRequestQuery = useMyChangeRequestQuery(
    user.is_verified && hasActivePeriod,
  )
  const updateScheduleMutation = useUpdateMyScheduleMutation()
  const createRequestMutation = useCreateChangeRequestMutation()
  const toast = useToast()

  const suggestedQuery = useSuggestedTemplateQuery(user.is_verified && hasActivePeriod)
  const applySuggestedMutation = useApplySuggestedTemplateMutation()
  const [hideSuggestion, setHideSuggestion] = useState(false)

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
  const [isRequestMode, setIsRequestMode] = useState(false)
  const [requestComment, setRequestComment] = useState('')

  const currentRequest = changeRequestQuery.data
  const canEditSchedule =
    user.is_verified &&
    hasActivePeriod &&
    !currentRequest &&
    !scheduleQuery.isPending
  const isPendingSubmit =
    updateScheduleMutation.isPending || createRequestMutation.isPending
  const canSubmit = canEditSchedule && !isPendingSubmit

  function handleApplySuggestion() {
    applySuggestedMutation.mutate(undefined, {
      onSuccess: () => {
        toast('Расписание заполнено по шаблону из прошлых периодов.')
        setHideSuggestion(true)
      },
      onError: (error) => toast(getApiErrorMessage(error), 'error'),
    })
  }

  function handleSubmit() {
    if (!currentBackendPeriod) return

    if (deadlinePassed) {
      if (!isRequestMode) {
        setIsRequestMode(true)
        return
      }

      if (!requestComment.trim()) {
        toast('Напишите комментарий к вашей заявке на изменение графика.', 'error')
        return
      }

      createRequestMutation.mutate(
        {
          employee_comment: requestComment.trim(),
          days: localScheduleToBackend(shiftsByDate).days,
        },
        {
          onSuccess: () => {
            setIsRequestMode(false)
            setRequestComment('')
            toast('Заявка на изменение отправлена.')
          },
          onError: (error) => toast(getApiErrorMessage(error), 'error'),
        },
      )
      return
    }

    updateScheduleMutation.mutate(localScheduleToBackend(shiftsByDate), {
      onSuccess: () => toast('График успешно сохранён.'),
      onError: (error) => toast(getApiErrorMessage(error), 'error'),
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
              <img src={t2Logo} alt="t2" className="size-10 rounded-md" />
              <span className="rounded-md bg-black px-3 py-2 text-xs font-black uppercase text-white">
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
                  isPendingSubmit,
                  currentRequest,
                )}
                tone={
                  currentRequest && currentRequest.status === 'pending'
                    ? 'warning'
                    : canSubmit && invalidIssues === 0
                      ? 'success'
                      : 'warning'
                }
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
              <div className="flex-1">
                <p className="text-xs font-black uppercase tracking-[0.12em] text-black/45">
                  Планирование
                </p>
                <p className="mt-1 text-sm font-bold text-black/65">
                  {currentRequest
                    ? 'Вы уже подали заявку на изменение графика в этом периоде.'
                    : deadlinePassed
                      ? 'Дедлайн прошёл. Вы можете подать одну заявку на изменение графика.'
                      : 'Выберите день, чтобы изменить смену. Итоги обновятся сразу.'}
                </p>
              </div>

              {!currentRequest && isRequestMode && (
                <div className="flex w-full items-center gap-2 sm:w-auto">
                  <input
                    value={requestComment}
                    onChange={(e) => setRequestComment(e.target.value)}
                    placeholder="Причина изменения..."
                    className="h-12 w-full min-w-[240px] rounded-md border border-black/10 bg-[#f7f7f8] px-3 text-sm outline-none focus:border-[#ff3495] focus:bg-white focus:ring-4 focus:ring-[#ff3495]/15"
                    disabled={isPendingSubmit}
                    autoFocus
                  />
                  <button
                    type="button"
                    onClick={() => setIsRequestMode(false)}
                    className="flex h-12 w-12 items-center justify-center rounded-md border border-black/10 text-black/55 hover:bg-black/5 hover:text-black"
                  >
                    <X size={18} />
                  </button>
                </div>
              )}

              {!currentRequest && (
                <SubmitButton
                  canSubmit={canSubmit}
                  isPending={isPendingSubmit}
                  isRequestMode={isRequestMode}
                  deadlinePassed={deadlinePassed}
                  onClick={handleSubmit}
                />
              )}
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

              {currentRequest && currentRequest.status === 'pending' && (
                <div className="mb-4 flex items-center gap-2 rounded-lg rounded-lg border border-black/10 bg-[#f7f7f8] px-4 py-3 text-sm font-bold text-black">
                  <FileQuestion
                    size={16}
                    aria-hidden="true"
                    className="shrink-0 text-black/45"
                  />
                  Ваша заявка на изменение графика рассматривается менеджером.
                </div>
              )}

              {currentRequest && currentRequest.status === 'rejected' && (
                <div className="mb-4 flex items-center gap-2 rounded-lg border-2 border-[#ff3495] bg-white px-4 py-3 text-sm font-bold text-black">
                  <AlertCircle
                    size={16}
                    aria-hidden="true"
                    className="shrink-0 text-[#ff3495]"
                  />
                  Менеджер отклонил вашу заявку: {currentRequest.manager_comment || 'Без комментария'}.
                </div>
              )}

              {periodRuleViolations.sixWorkingDaysInRow && (
                <div className="mb-4 flex items-center gap-2 rounded-lg border-2 border-[#ff3495] bg-white px-4 py-3 text-sm font-bold text-black">
                  <AlertCircle
                    size={16}
                    aria-hidden="true"
                    className="shrink-0 text-[#ff3495]"
                  />
                  В периоде есть 7 рабочих дней подряд. Добавьте выходной.
                </div>
              )}

              {suggestedQuery.data?.has_suggestion && !hideSuggestion && !deadlinePassed && (
                <div className="relative mb-6 overflow-hidden rounded-xl border border-black/10 bg-white p-5 shadow-lg transition-all animate-in slide-in-from-top-4 duration-500">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-start gap-4 min-w-0">
                      <div className="grid size-10 shrink-0 sm:size-12 place-items-center rounded-full bg-[#ff3495]/10 text-[#ff3495]">
                        <Sparkles size={20} />
                      </div>
                      <div className="min-w-0">
                        <h3 className="truncate text-base font-black uppercase tracking-tight text-black">
                          Найдено похожее расписание
                        </h3>
                        <p className="mt-1 text-xs sm:text-sm font-bold text-black/60">
                          Система нашла {suggestedQuery.data.match_count} прошлых периода с идентичным заполнением. Хотите применить этот шаблон?
                        </p>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-3">
                      <button
                        type="button"
                        onClick={handleApplySuggestion}
                        disabled={applySuggestedMutation.isPending}
                        className="inline-flex h-12 items-center justify-center rounded-md bg-[#ff3495] px-5 text-sm font-black uppercase text-white shadow-lg shadow-[#ff3495]/20 transition hover:bg-[#e00075] hover:scale-105 active:scale-95 disabled:opacity-50"
                      >
                        {applySuggestedMutation.isPending ? 'Применяем...' : 'Применить шаблон'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setHideSuggestion(true)}
                        className="flex size-12 shrink-0 items-center justify-center rounded-md border border-black/10 text-black/45 hover:bg-black/5 hover:text-black transition-colors"
                        aria-label="Скрыть предложение"
                      >
                        <X size={18} />
                      </button>
                    </div>
                  </div>
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
              className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-white border border-black/10 px-4 text-sm font-black uppercase text-black transition hover:border-black"
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
    <div className="mb-4 flex items-center gap-2 rounded-lg border-2 border-[#ff3495] bg-white px-4 py-3 text-sm font-bold text-black">
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
          className={`inline-flex h-9 items-center rounded-md px-3 text-[10px] sm:text-xs font-black uppercase ${week.isValid
            ? 'bg-[#a7fc00] text-black'
            : 'bg-white text-[#ff3495] border border-[#ff3495]'
            }`}
        >
          {week.isValid ? 'Норма' : 'Проверьте'}
        </span>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-black/10">
        <div
          className={`h-full rounded-full transition-[width] duration-300 ${week.isValid ? 'bg-[#a7fc00]' : 'bg-[#ff3495]'
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
      className={`rounded-lg border p-3 ${tone === 'success'
        ? 'border-[#a7fc00] bg-[#a7fc00] text-black'
        : tone === 'warning'
          ? 'border-2 border-[#ff3495] bg-white'
          : 'border-black/10 bg-[#f7f7f8]'
        }`}
    >
      <div className={`mb-2 grid size-7 sm:size-8 shrink-0 place-items-center rounded-md bg-white text-black self-start`}>
        <Icon size={16} aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <p className={`text-[9px] sm:text-xs font-black uppercase leading-tight truncate text-black/45`}>{label}</p>
        <p className={`mt-1 truncate text-base sm:text-xl font-black leading-none text-black`}>{value}</p>
      </div>
    </div>
  )
}

function HintPill({ isValid, text }: { isValid: boolean; text: string }) {
  const Icon = isValid ? CheckCircle2 : AlertCircle

  return (
    <span
      className={`inline-flex min-h-8 items-center gap-2 rounded-md px-3 text-xs font-bold ${isValid
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
  isRequestMode,
  deadlinePassed,
  onClick,
}: {
  canSubmit: boolean
  isPending: boolean
  isRequestMode: boolean
  deadlinePassed: boolean
  onClick: () => void
}) {
  const Icon = deadlinePassed ? Send : Save
  const label = isPending
    ? (deadlinePassed ? 'Отправляем' : 'Сохраняем')
    : (deadlinePassed ? (isRequestMode ? 'Отправить' : 'Запросить замену') : 'Сохранить')

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!canSubmit}
      className={`inline-flex h-12 items-center justify-center gap-2 rounded-md px-5 text-sm font-black uppercase transition focus:outline-none focus:ring-4 ${canSubmit
        ? isRequestMode
          ? 'bg-[#ff3495] text-white hover:bg-[#e00075] focus:ring-[#ff3495]/20'
          : 'bg-black text-white hover:bg-black/85 focus:ring-black/20'
        : 'cursor-not-allowed border border-black/10 bg-[#f0f0f2] text-black/35 focus:ring-black/5'
        }`}
    >
      <Icon size={16} aria-hidden="true" />
      {label}
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
  currentRequest: any,
): string {
  if (isPending) {
    return 'Обработка'
  }

  if (currentRequest) {
    if (currentRequest.status === 'pending') return 'Заявка на проверке'
    if (currentRequest.status === 'approved') return 'Заявка одобрена'
    if (currentRequest.status === 'rejected') return 'Заявка отклонена'
  }

  if (deadlinePassed) {
    return 'Дедлайн закрыт'
  }

  if (invalidIssues > 0) {
    return `${invalidIssues} ${formatIssueCount(invalidIssues)}`
  }

  return canSubmit ? 'Готов' : 'Закрыт'
}
