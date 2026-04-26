import { useState, type FormEvent, type ReactNode } from 'react'
import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  Download,
  FileQuestion,
  LogOut,
  RefreshCcw,
  ShieldCheck,
  UserCheck,
  Users,
  XCircle,
} from 'lucide-react'

import { getApiErrorMessage } from '../api/client'
import {
  useClosePeriodMutation,
  useCreatePeriodFromTemplateMutation,
  useExportScheduleMutation,
  useManagerDashboardQuery,
  useModerateVacationDaysMutation,
  usePendingChangeRequestsQuery,
  usePendingVacationDaysQuery,
  usePendingVerificationUsersQuery,
  usePeriodTemplatesQuery,
  useApproveChangeRequestMutation,
  useRejectChangeRequestMutation,
  useVerifyUserMutation,
  useRejectUserMutation,
} from '../api/queries'
import type {
  PeriodTemplate,
  PeriodTemplateType,
  User,
  VacationDaysStatus,
  PendingScheduleChangeRequest,
} from '../api/types'
import t2Logo from '../assets/t2-logo.svg'
import { useToast } from '../components/Toast'

interface ManagerDashboardProps {
  user: User
  onLogout: () => void
}

const fallbackTemplates: PeriodTemplate[] = [
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

export default function ManagerDashboard({
  user,
  onLogout,
}: ManagerDashboardProps) {
  const dashboardQuery = useManagerDashboardQuery()
  const templatesQuery = usePeriodTemplatesQuery()
  const pendingVacationQuery = usePendingVacationDaysQuery()
  const pendingVerificationQuery = usePendingVerificationUsersQuery()
  const pendingChangeRequestsQuery = usePendingChangeRequestsQuery()

  const createPeriodMutation = useCreatePeriodFromTemplateMutation()
  const closePeriodMutation = useClosePeriodMutation()
  const verifyUserMutation = useVerifyUserMutation()
  const rejectUserMutation = useRejectUserMutation()
  const moderateVacationMutation = useModerateVacationDaysMutation()
  const exportScheduleMutation = useExportScheduleMutation()
  const approveChangeRequestMutation = useApproveChangeRequestMutation()
  const rejectChangeRequestMutation = useRejectChangeRequestMutation()
  const [templateType, setTemplateType] =
    useState<PeriodTemplateType>('two_weeks')
  const [periodStart, setPeriodStart] = useState(toDateInput(new Date()))
  const [periodEnd, setPeriodEnd] = useState(toDateInput(addDays(new Date(), 13)))
  const [deadline, setDeadline] = useState(toDateTimeInput(new Date()))
  const toast = useToast()
  const dashboard = dashboardQuery.data
  const currentPeriod = dashboard?.current_period ?? null
  const templates = templatesQuery.data?.length
    ? templatesQuery.data
    : fallbackTemplates

  function handleCreatePeriod(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    createPeriodMutation.mutate(
      {
        template_type: templateType,
        period_start: periodStart,
        period_end: templateType === 'custom' ? periodEnd : undefined,
        deadline: new Date(deadline).toISOString(),
      },
      {
        onSuccess: () => toast('Период создан. Предыдущий активный период закрыт.'),
        onError: (error) => toast(getApiErrorMessage(error), 'error'),
      },
    )
  }

  function handleClosePeriod() {
    if (!currentPeriod) {
      return
    }

    closePeriodMutation.mutate(currentPeriod.id, {
      onSuccess: () => toast('Период закрыт.'),
      onError: (error) => toast(getApiErrorMessage(error), 'error'),
    })
  }

  function handleVerifyUser(userId: number) {
    verifyUserMutation.mutate(userId, {
      onSuccess: () => toast('Сотрудник подтверждён.'),
      onError: (error) => toast(getApiErrorMessage(error), 'error'),
    })
  }

  function handleRejectUser(userId: number) {
    if (!window.confirm('Вы уверены, что хотите отклонить и удалить данного сотрудника?')) {
      return
    }
    rejectUserMutation.mutate(userId, {
      onSuccess: () => toast('Заявка на регистрацию отклонена.', 'error'),
      onError: (error) => toast(getApiErrorMessage(error), 'error'),
    })
  }

  function handleModerateVacationDays(
    userId: number,
    approvedDays: number,
    status: VacationDaysStatus,
  ) {
    moderateVacationMutation.mutate(
      {
        userId,
        payload: {
          approved_days: approvedDays,
          status,
        },
      },
      {
        onSuccess: () => toast('Дни отпуска обновлены.'),
        onError: (error) => toast(getApiErrorMessage(error), 'error'),
      },
    )
  }

  function handleApproveChangeRequest(requestId: number, managerComment: string) {
    approveChangeRequestMutation.mutate(
      { requestId, payload: { manager_comment: managerComment } },
      {
        onSuccess: () => toast('Заявка на изменение одобрена.'),
        onError: (error) => toast(getApiErrorMessage(error), 'error'),
      },
    )
  }

  function handleRejectChangeRequest(requestId: number, managerComment: string) {
    rejectChangeRequestMutation.mutate(
      { requestId, payload: { manager_comment: managerComment } },
      {
        onSuccess: () => toast('Заявка на изменение отклонена.', 'error'),
        onError: (error) => toast(getApiErrorMessage(error), 'error'),
      },
    )
  }

  function handleExportSchedule() {
    exportScheduleMutation.mutate(currentPeriod?.id, {
      onSuccess: ({ blob, filename }) => {
        const fileUrl = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = fileUrl
        link.download = filename
        link.click()
        URL.revokeObjectURL(fileUrl)
        toast('Экспорт сформирован.')
      },
      onError: (error) => toast(getApiErrorMessage(error), 'error'),
    })
  }

  const isBusy =
    createPeriodMutation.isPending ||
    closePeriodMutation.isPending ||
    exportScheduleMutation.isPending

  return (
    <main className="min-h-screen bg-[#f3f3f5] px-3 py-4 text-black sm:px-5 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-32px)] w-full max-w-[1480px] flex-col gap-4">
        <header className="grid gap-4 rounded-lg border border-black/10 bg-white px-4 py-4 shadow-sm lg:grid-cols-[1fr_auto] lg:items-center lg:px-6">
          <div className="min-w-0">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <img src={t2Logo} alt="t2" className="size-10 rounded-md" />
              <span className="rounded-md bg-black px-3 py-2 text-xs font-black uppercase text-white">
                Панель менеджера
              </span>
              <span className="rounded-md border border-black/10 px-3 py-2 text-xs font-black uppercase text-black/55">
                {user.alliance ?? 'Альянс не указан'}
              </span>
            </div>

            <h1 className="text-3xl font-black uppercase leading-none sm:text-4xl">
              Управление графиком
            </h1>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void dashboardQuery.refetch()}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-md border border-black/10 bg-white px-4 text-sm font-black uppercase transition hover:border-black focus:outline-none focus:ring-4 focus:ring-black/10"
            >
              <RefreshCcw size={16} aria-hidden="true" />
              Обновить
            </button>
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

        {dashboardQuery.isError && (
          <AlertBlock text={getApiErrorMessage(dashboardQuery.error)} />
        )}

        <section className="grid grid-cols-4 gap-2 md:gap-3">
          <MetricTile
            Icon={Users}
            label="Сотрудники"
            value={formatNumber(dashboard?.total_employees)}
          />
          <MetricTile
            Icon={CheckCircle2}
            label="Отправили"
            value={formatNumber(dashboard?.submitted_count)}
            tone="success"
          />
          <MetricTile
            Icon={UserCheck}
            label="Верификация"
            value={formatNumber(dashboard?.pending_verification_count)}
            tone="warning"
          />
          <MetricTile
            Icon={AlertTriangle}
            label="Нарушения"
            value={formatNumber(dashboard?.employees_with_violations_count)}
            tone={
              dashboard?.employees_with_violations_count ? 'warning' : 'success'
            }
          />
        </section>

        <section className="grid flex-1 gap-4 xl:grid-cols-[1fr_1fr] items-start">
          <div className="grid gap-4 h-full grid-rows-[auto_auto_1fr]">
            <Panel title="Текущий период">
              {currentPeriod ? (
                <div className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-3">
                    <Fact label="Старт" value={formatDate(currentPeriod.period_start)} />
                    <Fact label="Финиш" value={formatDate(currentPeriod.period_end)} />
                    <Fact
                      label="Дедлайн"
                      value={formatDateTime(currentPeriod.deadline)}
                    />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={handleExportSchedule}
                      disabled={isBusy}
                      className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-black px-4 text-sm font-black uppercase text-white transition hover:bg-black/85 disabled:cursor-not-allowed disabled:bg-black/10 disabled:text-black/35 focus:outline-none focus:ring-4 focus:ring-black/20"
                    >
                      <Download size={16} aria-hidden="true" />
                      Экспорт
                    </button>
                    <button
                      type="button"
                      onClick={handleClosePeriod}
                      disabled={isBusy}
                      className="inline-flex h-11 items-center justify-center gap-2 rounded-md border border-black/15 bg-white px-4 text-sm font-black uppercase text-black transition hover:border-black disabled:cursor-not-allowed disabled:text-black/35"
                    >
                      <XCircle size={16} aria-hidden="true" />
                      Закрыть
                    </button>
                  </div>
                </div>
              ) : (
                <EmptyState
                  Icon={CalendarDays}
                  title="Активного периода нет"
                  text="Создайте новый период сбора графиков."
                />
              )}
            </Panel>

            <Panel title="Создание периода">
              <form onSubmit={handleCreatePeriod} className="space-y-4">
                <div className="grid gap-2 sm:grid-cols-4">
                  {templates.map((template) => {
                    const translations: Record<string, { label: string; description: string }> = {
                      week: {
                        label: '1 НЕДЕЛЯ',
                        description: 'Создает 7-дневный период, начиная с даты начала.',
                      },
                      two_weeks: {
                        label: '2 НЕДЕЛИ',
                        description: 'Создает 14-дневный период, начиная с даты начала.',
                      },
                      month: {
                        label: 'КАЛЕНДАРНЫЙ МЕСЯЦ',
                        description: 'Создает период с даты начала до последнего дня этого месяца.',
                      },
                      custom: {
                        label: 'СВОЙ ДИАПАЗОН',
                        description: 'Создает период с указанными датами начала и конца.',
                      },
                    }

                    const localizedLabel = translations[template.type]?.label ?? template.label
                    const localizedDesc = translations[template.type]?.description ?? template.description

                    return (
                      <button
                        key={template.type}
                        type="button"
                        aria-pressed={templateType === template.type}
                        onClick={() => setTemplateType(template.type)}
                        className={`min-h-24 rounded-lg border p-3 text-left transition ${templateType === template.type
                          ? 'border-black bg-black text-white'
                          : 'border-black/10 bg-white text-black hover:border-black/35'
                          }`}
                      >
                        <span className="block text-sm font-black uppercase">
                          {localizedLabel}
                        </span>
                        <span
                          className={`mt-2 block text-xs font-bold ${templateType === template.type
                            ? 'text-white/60'
                            : 'text-black/45'
                            }`}
                        >
                          {localizedDesc}
                        </span>
                      </button>
                    )
                  })}
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  <DateField
                    label="Начало"
                    type="date"
                    value={periodStart}
                    onChange={setPeriodStart}
                  />
                  <DateField
                    label="Конец"
                    type="date"
                    value={periodEnd}
                    onChange={setPeriodEnd}
                    disabled={templateType !== 'custom'}
                  />
                  <DateField
                    label="Дедлайн"
                    type="datetime-local"
                    value={deadline}
                    onChange={setDeadline}
                  />
                </div>

                <button
                  type="submit"
                  disabled={createPeriodMutation.isPending}
                  className="inline-flex h-12 items-center justify-center gap-2 rounded-md bg-black px-5 text-sm font-black uppercase text-white transition hover:bg-black/85 disabled:cursor-not-allowed disabled:bg-black/15"
                >
                  <ShieldCheck size={16} aria-hidden="true" />
                  {createPeriodMutation.isPending ? 'Создаём' : 'Создать период'}
                </button>
              </form>
            </Panel>

            <Panel title="Проблемные графики">
              {dashboard?.problem_employees.length ? (
                <div className="space-y-2 max-h-[460px] pr-2 overflow-y-auto">
                  {dashboard.problem_employees.map((employee) => (
                    <div
                      key={employee.user_id}
                      className="rounded-lg border-2 border-[#ff3495] bg-white p-3"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <p className="font-black">{employee.full_name}</p>
                          <p className="text-sm font-bold text-black/55">
                            {employee.email ?? 'Почта не указана'}
                          </p>
                        </div>
                        <span className="rounded-md bg-white px-3 py-2 text-xs font-black uppercase text-black">
                          {employee.violation_count} наруш.
                        </span>
                      </div>
                      <p className="mt-2 text-sm font-bold text-black/65">
                        {employee.violation_codes.map(formatViolationCode).join(', ')}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  Icon={CheckCircle2}
                  title="Нарушений нет"
                  text="Сотрудников с проблемными графиками сейчас нет."
                />
              )}
            </Panel>
          </div>

          <div className="space-y-4">
            <Panel title="Запросы на изменение графика">
              <ChangeRequestQueue
                requests={pendingChangeRequestsQuery.data ?? []}
                actionPending={
                  approveChangeRequestMutation.isPending ||
                  rejectChangeRequestMutation.isPending
                }
                onApprove={handleApproveChangeRequest}
                onReject={handleRejectChangeRequest}
              />
            </Panel>

            <Panel title="Ожидают подтверждения">
              <UserQueue
                users={pendingVerificationQuery.data ?? []}
                emptyText="Нет сотрудников на подтверждение."
                actionLabel="Подтвердить"
                actionPending={verifyUserMutation.isPending || rejectUserMutation.isPending}
                onAction={(employee) => handleVerifyUser(employee.id)}
                onReject={(employee) => handleRejectUser(employee.id)}
              />
            </Panel>

            <Panel title="Модерация отпуска">
              <VacationQueue
                users={pendingVacationQuery.data ?? []}
                actionPending={moderateVacationMutation.isPending}
                onModerate={handleModerateVacationDays}
              />
            </Panel>
          </div>
        </section>

      </div>
    </main>
  )
}

interface PanelProps {
  title: string
  children: ReactNode
}

function Panel({ title, children }: PanelProps) {
  return (
    <section className="rounded-lg border border-black/10 bg-white p-4 shadow-sm lg:p-5">
      <h2 className="mb-4 text-base sm:text-lg font-black uppercase leading-none">{title}</h2>
      {children}
    </section>
  )
}

interface MetricTileProps {
  Icon: typeof Users
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
      className={`rounded-lg border p-2 sm:p-5 shadow-sm flex flex-col justify-between ${tone === 'success'
        ? 'border-[#a7fc00] bg-[#a7fc00] text-black'
        : tone === 'warning'
          ? 'border-2 border-[#ff3495] bg-white'
          : 'border-black/10 bg-white'
        }`}
    >
      <div className="mb-2 grid size-8 sm:size-10 shrink-0 place-items-center rounded-md bg-white text-black self-start">
        <Icon size={18} aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <p className="text-[9px] sm:text-xs font-black uppercase text-black/45 leading-tight truncate">{label}</p>
        <p className="mt-1 truncate text-base sm:text-3xl font-black leading-none">{value}</p>
      </div>
    </div>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-black/10 bg-[#f7f7f8] p-3">
      <p className="text-xs font-black uppercase text-black/45">{label}</p>
      <p className="mt-1 text-lg font-black leading-none">{value}</p>
    </div>
  )
}

interface DateFieldProps {
  label: string
  type: 'date' | 'datetime-local'
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

function DateField({
  label,
  type,
  value,
  onChange,
  disabled = false,
}: DateFieldProps) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-black uppercase tracking-[0.12em] text-black/45">
        {label}
      </span>
      <input
        type={type}
        required
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="h-12 w-full rounded-md border border-black/10 bg-[#f7f7f8] px-3 text-sm font-black text-black outline-none transition focus:border-[#ff3495] focus:bg-white focus:ring-4 focus:ring-[#ff3495]/15 disabled:cursor-not-allowed disabled:text-black/35"
      />
    </label>
  )
}

interface UserQueueProps {
  users: User[]
  emptyText: string
  actionLabel: string
  actionPending: boolean
  onAction: (user: User) => void
  onReject?: (user: User) => void
}

function UserQueue({
  users,
  emptyText,
  actionLabel,
  actionPending,
  onAction,
  onReject,
}: UserQueueProps) {
  if (!users.length) {
    return <EmptyState Icon={UserCheck} title={emptyText} text="Очередь пуста." />
  }

  return (
    <div className="space-y-2 max-h-[460px] pr-2 overflow-y-auto">
      {users.map((employee) => (
        <div
          key={employee.id}
          className="grid gap-3 rounded-lg border border-black/10 bg-[#f7f7f8] p-3 sm:grid-cols-[1fr_auto] sm:items-center"
        >
          <UserSummary user={employee} />
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={actionPending}
              onClick={() => onAction(employee)}
              className="inline-flex h-10 items-center justify-center rounded-md bg-black px-4 text-xs font-black uppercase text-white transition hover:bg-black/85 disabled:cursor-not-allowed disabled:bg-black/15"
            >
              {actionLabel}
            </button>
            {onReject && (
              <button
                type="button"
                disabled={actionPending}
                onClick={() => onReject(employee)}
                className="inline-flex h-10 items-center justify-center rounded-md border border-[#ff3495] bg-white px-4 text-xs font-black uppercase text-[#ff3495] transition hover:bg-[#ff3495] hover:text-white disabled:cursor-not-allowed disabled:text-black/35"
              >
                Отклонить
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}


interface VacationQueueProps {
  users: User[]
  actionPending: boolean
  onModerate: (
    userId: number,
    approvedDays: number,
    status: VacationDaysStatus,
  ) => void
}

function VacationQueue({
  users,
  actionPending,
  onModerate,
}: VacationQueueProps) {
  const [approvedByUser, setApprovedByUser] = useState<Record<number, string>>({})

  if (!users.length) {
    return (
      <EmptyState
        Icon={ShieldCheck}
        title="Заявок на отпуск нет"
        text="Очередь модерации пуста."
      />
    )
  }

  return (
    <div className="space-y-2 max-h-[460px] pr-2 overflow-y-auto">
      {users.map((employee) => {
        const declaredDays = employee.vacation_days_declared ?? 0
        const approvedValue = approvedByUser[employee.id] ?? String(declaredDays)
        const approvedDays = Number(approvedValue)

        return (
          <div
            key={employee.id}
            className="rounded-lg border border-black/10 bg-[#f7f7f8] p-3"
          >
            <div className="grid gap-3 sm:grid-cols-[1fr_120px] sm:items-start">
              <UserSummary user={employee} />
              <label>
                <span className="mb-2 block text-xs font-black uppercase text-black/45">
                  Дней
                </span>
                <input
                  type="number"
                  min={0}
                  max={365}
                  value={approvedValue}
                  onChange={(event) =>
                    setApprovedByUser((current) => ({
                      ...current,
                      [employee.id]: event.target.value,
                    }))
                  }
                  className="h-10 w-full rounded-md border border-black/10 bg-white px-3 text-sm font-black outline-none focus:border-[#ff3495] focus:ring-4 focus:ring-[#ff3495]/15"
                />
              </label>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                disabled={actionPending || !Number.isFinite(approvedDays)}
                onClick={() =>
                  onModerate(employee.id, approvedDays, 'approved')
                }
                className="inline-flex h-10 items-center justify-center rounded-md bg-black px-4 text-xs font-black uppercase text-white transition hover:bg-black/85 disabled:cursor-not-allowed disabled:bg-black/10 disabled:text-black/35 focus:outline-none focus:ring-4 focus:ring-black/20"
              >
                Одобрить
              </button>
              <button
                type="button"
                disabled={actionPending || !Number.isFinite(approvedDays)}
                onClick={() =>
                  onModerate(employee.id, approvedDays, 'adjusted')
                }
                className="inline-flex h-10 items-center justify-center rounded-md border border-black/15 bg-white px-4 text-xs font-black uppercase text-black transition hover:border-black disabled:cursor-not-allowed disabled:text-black/35"
              >
                Скорректировать
              </button>
              <button
                type="button"
                disabled={actionPending}
                onClick={() => onModerate(employee.id, 0, 'rejected')}
                className="inline-flex h-10 items-center justify-center rounded-md border border-[#ff3495] bg-white px-4 text-xs font-black uppercase text-[#ff3495] transition hover:bg-[#ff3495] hover:text-white disabled:cursor-not-allowed disabled:text-black/35"
              >
                Отклонить
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function UserSummary({ user }: { user: User }) {
  return (
    <div className="min-w-0">
      <p className="truncate font-black">{user.full_name ?? user.email ?? `ID ${user.id}`}</p>
      <p className="mt-1 truncate text-sm font-bold text-black/55">
        {user.email ?? 'Почта не указана'}
      </p>
      <p className="mt-1 text-xs font-black uppercase text-black/35">
        {user.category ?? 'Категория не указана'}
        {user.vacation_days_declared !== null
          ? ` · ${user.vacation_days_declared} дн. отпуска`
          : ''}
      </p>
    </div>
  )
}

interface EmptyStateProps {
  Icon: typeof CalendarDays
  title: string
  text: string
}

function EmptyState({ Icon, title, text }: EmptyStateProps) {
  return (
    <div className="rounded-lg border border-dashed border-black/15 bg-[#f7f7f8] p-4">
      <span className="mb-3 grid size-10 place-items-center rounded-md bg-white text-black">
        <Icon size={18} aria-hidden="true" />
      </span>
      <p className="font-black">{title}</p>
      <p className="mt-1 text-sm font-bold text-black/50">{text}</p>
    </div>
  )
}

function AlertBlock({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border-2 border-[#ff3495] bg-white px-4 py-3 text-sm font-bold text-black">
      <AlertTriangle size={17} aria-hidden="true" className="text-[#ff3495]" />
      {text}
    </div>
  )
}

function toDateInput(date: Date): string {
  return date.toISOString().slice(0, 10)
}

function toDateTimeInput(date: Date): string {
  return date.toISOString().slice(0, 16)
}

function addDays(date: Date, amount: number): Date {
  const nextDate = new Date(date)

  nextDate.setDate(nextDate.getDate() + amount)

  return nextDate
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value))
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatNumber(value: number | undefined): string {
  return typeof value === 'number' ? String(value) : '...'
}

function formatViolationCode(code: string): string {
  switch (code) {
    case 'WEEKLY_HOURS_UNDER':
      return 'Недобор часов за неделю'
    case 'WEEKLY_HOURS_OVER':
      return 'Перебор часов за неделю'
    case 'WORK_STREAK_OVER_6':
      return 'Больше 6 рабочих дней подряд'
    case 'NO_SCHEDULE':
      return 'График не заполнен'
    default:
      return code
        .replaceAll('_', ' ')
        .toLowerCase()
        .replace(/^\w/u, (char) => char.toUpperCase())
  }
}

interface ChangeRequestQueueProps {
  requests: PendingScheduleChangeRequest[]
  actionPending: boolean
  onApprove: (requestId: number, comment: string) => void
  onReject: (requestId: number, comment: string) => void
}

function ChangeRequestQueue({
  requests,
  actionPending,
  onApprove,
  onReject,
}: ChangeRequestQueueProps) {
  const [comments, setComments] = useState<Record<number, string>>({})

  if (!requests.length) {
    return (
      <EmptyState
        Icon={FileQuestion}
        title="Нет заявок"
        text="Нет ожидающих заявок на изменение графика."
      />
    )
  }

  return (
    <div className="space-y-2 max-h-[460px] pr-2 overflow-y-auto">
      {requests.map((request) => {
        const comment = comments[request.id] ?? ''

        return (
          <div
            key={request.id}
            className="rounded-lg border border-black/10 bg-[#f7f7f8] p-3 text-sm"
          >
            <div className="mb-2">
              <p className="font-black text-black">
                {request.full_name ?? request.email ?? `ID: ${request.user_id}`}
              </p>
              <p className="mt-1 text-xs font-bold text-black/65">
                <span className="font-black uppercase text-black/45">Причина: </span>
                {request.employee_comment}
              </p>
              <p className="mt-1 text-xs font-bold text-black/65">
                <span className="font-black uppercase text-black/45">Изменённые дни: </span>
                {request.changed_days.map(formatDate).join(', ')}
              </p>
            </div>

            <label className="mb-2 block">
              <span className="mb-1 block text-xs font-black uppercase text-black/45">
                Комментарий менеджера
              </span>
              <input
                type="text"
                value={comment}
                placeholder="Опционально..."
                onChange={(e) =>
                  setComments((prev) => ({ ...prev, [request.id]: e.target.value }))
                }
                className="h-10 w-full rounded-md border border-black/10 bg-white px-3 text-sm font-bold outline-none focus:border-[#ff3495] focus:ring-4 focus:ring-[#ff3495]/15"
              />
            </label>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={actionPending}
                onClick={() => onApprove(request.id, comment.trim())}
                className="inline-flex h-9 items-center justify-center rounded-md bg-black px-4 text-xs font-black uppercase text-white transition hover:bg-black/85 disabled:cursor-not-allowed disabled:bg-black/10 disabled:text-black/35 focus:outline-none focus:ring-4 focus:ring-black/20"
              >
                Одобрить
              </button>
              <button
                type="button"
                disabled={actionPending}
                onClick={() => onReject(request.id, comment.trim())}
                className="inline-flex h-9 items-center justify-center rounded-md border border-[#ff3495] bg-white px-4 text-xs font-black uppercase text-[#ff3495] transition hover:bg-[#ff3495] hover:text-white disabled:cursor-not-allowed disabled:text-black/35"
              >
                Отклонить
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
