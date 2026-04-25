import {
  CalendarX,
  Clock,
  GitBranch,
  Plane,
  Save,
  Trash2,
  X,
} from 'lucide-react'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import {
  useEffect,
  useMemo,
  useState,
  type FormEvent,
  type InputHTMLAttributes,
} from 'react'
import type { LucideIcon } from 'lucide-react'

import { useScheduleStore } from '../../store/useScheduleStore'
import type {
  DateInput,
  ScheduleShift,
  ShiftType,
  TimeString,
} from '../../types/schedule'
import {
  calculateShiftHours,
  normalizeDateInput,
  toDateKey,
} from '../../utils/time-calculations'

interface ShiftFormProps {
  date: DateInput
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface ShiftTypeOption {
  type: ShiftType
  label: string
  description: string
  Icon: LucideIcon
}

interface ShiftDraft {
  type: ShiftType
  normalStart: TimeString
  normalEnd: TimeString
  splitStart1: TimeString
  splitEnd1: TimeString
  splitStart2: TimeString
  splitEnd2: TimeString
}

type TimeDraftKey = Exclude<keyof ShiftDraft, 'type'>

const shiftTypeOptions: readonly ShiftTypeOption[] = [
  {
    type: 'normal',
    label: 'Обычная',
    description: 'Один рабочий интервал',
    Icon: Clock,
  },
  {
    type: 'split',
    label: 'С перерывом',
    description: 'Два рабочих интервала',
    Icon: GitBranch,
  },
  {
    type: 'day_off',
    label: 'Выходной',
    description: 'Без рабочих часов',
    Icon: CalendarX,
  },
  {
    type: 'vacation',
    label: 'Отпуск',
    description: 'Отпускной день',
    Icon: Plane,
  },
]

const defaultDraft: ShiftDraft = {
  type: 'normal',
  normalStart: '09:00',
  normalEnd: '18:00',
  splitStart1: '09:00',
  splitEnd1: '13:00',
  splitStart2: '14:00',
  splitEnd2: '18:00',
}

export default function ShiftForm({
  date,
  open,
  onOpenChange,
}: ShiftFormProps) {
  const dateKey = toDateKey(date)
  const normalizedDate = normalizeDateInput(dateKey)
  const shift = useScheduleStore((state) => state.shiftsByDate[dateKey])
  const setShift = useScheduleStore((state) => state.setShift)
  const [draft, setDraft] = useState<ShiftDraft>(() => createDraft(shift))

  useEffect(() => {
    if (!open) {
      return
    }

    const previousOverflow = document.body.style.overflow
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onOpenChange(false)
      }
    }

    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [onOpenChange, open])

  const previewShift = useMemo(() => createShiftFromDraft(draft), [draft])
  const previewHours = calculateShiftHours(previewShift, dateKey)
  const selectedOption = shiftTypeOptions.find(
    (option) => option.type === draft.type,
  )

  if (!open) {
    return null
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setShift(dateKey, createShiftFromDraft(draft))
    onOpenChange(false)
  }

  function handleClear() {
    setShift(dateKey, null)
    onOpenChange(false)
  }

  function updateTimeField(field: TimeDraftKey, value: string) {
    setDraft((currentDraft) => ({
      ...currentDraft,
      [field]: value as TimeString,
    }))
  }

  return (
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        aria-label="Закрыть редактор смены"
        className="absolute inset-0 h-full w-full bg-black/45 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />

      <form
        onSubmit={handleSubmit}
        role="dialog"
        aria-modal="true"
        aria-label={`Редактировать смену за ${dateKey}`}
        className="absolute inset-x-3 bottom-3 max-h-[calc(100vh-24px)] overflow-auto rounded-lg border border-white/20 bg-[#f7f7f8] text-black shadow-[0_24px_80px_rgba(0,0,0,0.22)] sm:bottom-4 sm:left-auto sm:right-4 sm:top-4 sm:w-[432px]"
      >
        <header className="sticky top-0 z-10 border-b border-black/10 bg-[#f7f7f8]/95 px-5 py-4 backdrop-blur">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.12em] text-[#ff3495]">
                Редактирование смены
              </p>
              <h2 className="mt-1 text-2xl font-black uppercase leading-none">
                {format(normalizedDate, 'EEEE, d MMMM', { locale: ru })}
              </h2>
            </div>
            <button
              type="button"
              aria-label="Закрыть"
              onClick={() => onOpenChange(false)}
              className="grid size-10 shrink-0 place-items-center rounded-md border border-black/10 bg-white text-black transition hover:border-black focus:outline-none focus:ring-4 focus:ring-[#ff3495]/20"
            >
              <X size={18} aria-hidden="true" />
            </button>
          </div>
        </header>

        <div className="space-y-5 px-5 py-5">
          <section aria-label="Тип смены">
            <div className="grid grid-cols-2 gap-2">
              {shiftTypeOptions.map(({ type, label, description, Icon }) => {
                const isSelected = draft.type === type

                return (
                  <button
                    key={type}
                    type="button"
                    aria-pressed={isSelected}
                    onClick={() =>
                      setDraft((currentDraft) => ({
                        ...currentDraft,
                        type,
                      }))
                    }
                    className={`min-h-24 rounded-lg border p-3 text-left transition focus:outline-none focus:ring-4 focus:ring-[#ff3495]/20 ${isSelected
                      ? 'border-black bg-black text-white'
                      : 'border-black/10 bg-white text-black hover:border-black/35'
                      }`}
                  >
                    <span
                      className={`mb-3 grid size-8 place-items-center rounded-md ${isSelected
                        ? 'bg-[#ff3495] text-white'
                        : 'bg-[#f0f0f2] text-black'
                        }`}
                    >
                      <Icon size={17} aria-hidden="true" />
                    </span>
                    <span className="block text-sm font-black uppercase">
                      {label}
                    </span>
                    <span
                      className={`mt-1 block text-xs font-medium ${isSelected ? 'text-white/58' : 'text-black/50'
                        }`}
                    >
                      {description}
                    </span>
                  </button>
                )
              })}
            </div>
          </section>

          <section
            aria-label="Время смены"
            className="rounded-lg border border-black/10 bg-white p-4"
          >
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.12em] text-black/45">
                  {selectedOption?.label ?? 'Смена'}
                </p>
                <p className="mt-1 text-xl font-black leading-none">
                  {formatHours(previewHours)}
                </p>
              </div>
              <span className="grid size-10 place-items-center rounded-md bg-[#ff3495] text-white">
                {selectedOption ? (
                  <selectedOption.Icon size={18} aria-hidden="true" />
                ) : (
                  <Clock size={18} aria-hidden="true" />
                )}
              </span>
            </div>

            {draft.type === 'normal' && (
              <div className="grid grid-cols-2 gap-3">
                <TimeField
                  id="normal-start"
                  label="Начало"
                  value={draft.normalStart}
                  onChange={(value) => updateTimeField('normalStart', value)}
                />
                <TimeField
                  id="normal-end"
                  label="Конец"
                  value={draft.normalEnd}
                  onChange={(value) => updateTimeField('normalEnd', value)}
                />
              </div>
            )}

            {draft.type === 'split' && (
              <div className="space-y-4">
                <div>
                  <p className="mb-2 text-xs font-black uppercase tracking-[0.12em] text-black/45">
                    Интервал 1
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <TimeField
                      id="split-start-1"
                      label="Начало"
                      value={draft.splitStart1}
                      onChange={(value) =>
                        updateTimeField('splitStart1', value)
                      }
                    />
                    <TimeField
                      id="split-end-1"
                      label="Конец"
                      value={draft.splitEnd1}
                      onChange={(value) => updateTimeField('splitEnd1', value)}
                    />
                  </div>
                </div>

                <div>
                  <p className="mb-2 text-xs font-black uppercase tracking-[0.12em] text-black/45">
                    Интервал 2
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <TimeField
                      id="split-start-2"
                      label="Начало"
                      value={draft.splitStart2}
                      onChange={(value) =>
                        updateTimeField('splitStart2', value)
                      }
                    />
                    <TimeField
                      id="split-end-2"
                      label="Конец"
                      value={draft.splitEnd2}
                      onChange={(value) => updateTimeField('splitEnd2', value)}
                    />
                  </div>
                </div>
              </div>
            )}

            {(draft.type === 'day_off' || draft.type === 'vacation') && (
              <div className="rounded-lg border border-dashed border-black/15 bg-[#f7f7f8] px-4 py-5">
                <p className="text-sm font-bold text-black/65">
                  Для этого статуса время не указывается.
                </p>
              </div>
            )}
          </section>
        </div>

        <footer className="sticky bottom-0 grid grid-cols-[1fr_1.4fr] gap-3 border-t border-black/10 bg-[#f7f7f8]/95 px-5 py-4 backdrop-blur">
          <button
            type="button"
            onClick={handleClear}
            className="inline-flex h-12 items-center justify-center gap-2 rounded-md border border-black/15 bg-white px-4 text-sm font-black uppercase text-black transition hover:border-black focus:outline-none focus:ring-4 focus:ring-black/10"
          >
            <Trash2 size={16} aria-hidden="true" />
            Очистить
          </button>
          <button
            type="submit"
            className="inline-flex h-12 items-center justify-center gap-2 rounded-md bg-black px-4 text-sm font-black uppercase text-white transition hover:bg-black/85 focus:outline-none focus:ring-4 focus:ring-black/20"
          >
            <Save size={16} aria-hidden="true" />
            Сохранить
          </button>
        </footer>
      </form>
    </div>
  )
}

interface TimeFieldProps
  extends Pick<InputHTMLAttributes<HTMLInputElement>, 'id' | 'value'> {
  label: string
  onChange: (value: string) => void
}

function TimeField({ id, label, value, onChange }: TimeFieldProps) {
  return (
    <label className="block" htmlFor={id}>
      <span className="mb-2 block text-xs font-black uppercase tracking-[0.12em] text-black/45">
        {label}
      </span>
      <input
        id={id}
        type="time"
        required
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-12 w-full rounded-md border border-black/10 bg-[#f7f7f8] px-3 text-sm font-black text-black outline-none transition focus:border-[#ff3495] focus:bg-white focus:ring-4 focus:ring-[#ff3495]/15"
      />
    </label>
  )
}

function createDraft(shift: ScheduleShift | undefined): ShiftDraft {
  if (!shift) {
    return defaultDraft
  }

  switch (shift.type) {
    case 'normal':
      return {
        ...defaultDraft,
        type: 'normal',
        normalStart: shift.start,
        normalEnd: shift.end,
      }
    case 'split':
      return {
        ...defaultDraft,
        type: 'split',
        splitStart1: shift.intervals[0].start,
        splitEnd1: shift.intervals[0].end,
        splitStart2: shift.intervals[1].start,
        splitEnd2: shift.intervals[1].end,
      }
    case 'day_off':
      return {
        ...defaultDraft,
        type: 'day_off',
      }
    case 'vacation':
      return {
        ...defaultDraft,
        type: 'vacation',
      }
    default:
      return assertNever(shift)
  }
}

function createShiftFromDraft(draft: ShiftDraft): ScheduleShift {
  switch (draft.type) {
    case 'normal':
      return {
        type: 'normal',
        start: draft.normalStart,
        end: draft.normalEnd,
      }
    case 'split':
      return {
        type: 'split',
        intervals: [
          {
            start: draft.splitStart1,
            end: draft.splitEnd1,
          },
          {
            start: draft.splitStart2,
            end: draft.splitEnd2,
          },
        ],
      }
    case 'day_off':
      return {
        type: 'day_off',
      }
    case 'vacation':
      return {
        type: 'vacation',
      }
    default:
      return assertNever(draft.type)
  }
}

function formatHours(hours: number): string {
  if (hours === 0) {
    return '0 ч'
  }

  if (Number.isInteger(hours)) {
    return `${hours} ч`
  }

  return `${hours.toFixed(1).replace('.', ',')} ч`
}

function assertNever(value: never): never {
  throw new Error(`Unexpected shift form value: ${JSON.stringify(value)}`)
}
