import {
  CalendarX,
  Clock,
  GitBranch,
  Plane,
  Plus,
  Sparkles,
} from 'lucide-react'
import { format, isToday } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useState } from 'react'
import type { LucideIcon } from 'lucide-react'

import { useScheduleStore } from '../../store/useScheduleStore'
import type { DateInput, ScheduleShift, ShiftType } from '../../types/schedule'
import {
  calculateShiftHours,
  normalizeDateInput,
  toDateKey,
} from '../../utils/time-calculations'
import ShiftForm from './ShiftForm'

interface ShiftCellProps {
  date: DateInput
  className?: string
  isMuted?: boolean
}

interface ShiftVisualConfig {
  label: string
  Icon: LucideIcon
  cellClassName: string
  iconClassName: string
  metaClassName: string
}

const shiftVisualConfig: Record<ShiftType, ShiftVisualConfig> = {
  normal: {
    label: 'Обычная',
    Icon: Clock,
    cellClassName: 'border-black bg-black text-white',
    iconClassName: 'bg-[#a7fc00] text-black',
    metaClassName: 'text-white/62',
  },
  split: {
    label: 'С перерывом',
    Icon: GitBranch,
    cellClassName: 'border-[#ff3495] bg-[#ff3495] text-white',
    iconClassName: 'bg-white text-[#ff3495]',
    metaClassName: 'text-white/70',
  },
  day_off: {
    label: 'Выходной',
    Icon: CalendarX,
    cellClassName: 'border-black/10 bg-white text-black',
    iconClassName: 'bg-[#a7fc00] text-black',
    metaClassName: 'text-black/45',
  },
  vacation: {
    label: 'Отпуск',
    Icon: Plane,
    cellClassName: 'border-black/10 bg-[#f7f7f8] text-black',
    iconClassName: 'bg-black text-white',
    metaClassName: 'text-black/45',
  },
}

const emptyCellConfig: ShiftVisualConfig = {
  label: 'Добавить',
  Icon: Plus,
  cellClassName: 'border-black/10 bg-white text-black hover:border-black/35',
  iconClassName: 'bg-[#f0f0f2] text-black',
  metaClassName: 'text-black/40',
}

export default function ShiftCell({
  date,
  className = '',
  isMuted = false,
}: ShiftCellProps) {
  const [isEditorOpen, setIsEditorOpen] = useState(false)
  const dateKey = toDateKey(date)
  const normalizedDate = normalizeDateInput(dateKey)
  const shift = useScheduleStore((state) => state.shiftsByDate[dateKey])
  const hours = calculateShiftHours(shift, dateKey)
  const visualConfig = getVisualConfig(shift)
  const Icon = visualConfig.Icon
  const isCurrentDay = isToday(normalizedDate)

  return (
    <div className={className}>
      <button
        type="button"
        onClick={() => setIsEditorOpen(true)}
        className={classNames(
          'group grid min-h-32 w-full grid-rows-[auto_1fr_auto] rounded-lg border p-3 text-left shadow-sm transition duration-200 focus:outline-none focus:ring-4 focus:ring-[#ff3495]/20',
          visualConfig.cellClassName,
          isMuted ? 'opacity-45' : '',
        )}
        aria-label={`Редактировать смену за ${dateKey}`}
      >
        <span className="flex items-start justify-between gap-2">
          <span>
            <span className="block text-2xl font-black leading-none">
              {format(normalizedDate, 'd')}
            </span>
            <span
              className={classNames(
                'mt-1 block text-xs font-black uppercase',
                visualConfig.metaClassName,
              )}
            >
              {format(normalizedDate, 'EEE', { locale: ru })}
            </span>
          </span>

          <span
            className={classNames(
              'grid size-9 shrink-0 place-items-center rounded-md transition group-hover:scale-105',
              visualConfig.iconClassName,
            )}
            aria-hidden="true"
          >
            <Icon size={17} />
          </span>
        </span>

        <span className="mt-4 min-h-10">
          <span className="block text-sm font-black uppercase leading-tight">
            {visualConfig.label}
          </span>
          <span
            className={classNames(
              'mt-1 line-clamp-2 block text-xs font-semibold leading-snug',
              visualConfig.metaClassName,
            )}
          >
            {getShiftMeta(shift)}
          </span>
        </span>

        <span className="mt-3 flex items-end justify-between gap-2">
          <span
            className={classNames(
              'inline-flex h-7 items-center rounded-md px-2 text-xs font-black uppercase',
              shift?.type === 'normal' || shift?.type === 'split'
                ? 'bg-white text-black'
                : 'bg-black/5 text-black/45',
              shift?.type === 'normal' ? 'bg-[#a7fc00]' : '',
            )}
          >
            {shift?.type === 'normal' || shift?.type === 'split'
              ? formatHours(hours)
              : '0 ч'}
          </span>

          {isCurrentDay && (
            <span
              className="grid size-7 place-items-center rounded-md bg-[#a7fc00] text-black"
              aria-label="Сегодня"
            >
              <Sparkles size={14} aria-hidden="true" />
            </span>
          )}
        </span>
      </button>

      {isEditorOpen && (
        <ShiftForm
          date={dateKey}
          open={isEditorOpen}
          onOpenChange={setIsEditorOpen}
        />
      )}
    </div>
  )
}

function getVisualConfig(shift: ScheduleShift | undefined): ShiftVisualConfig {
  if (!shift) {
    return emptyCellConfig
  }

  return shiftVisualConfig[shift.type]
}

function getShiftMeta(shift: ScheduleShift | undefined): string {
  if (!shift) {
    return 'Запланировать'
  }

  switch (shift.type) {
    case 'normal':
      return `${shift.start} - ${shift.end}`
    case 'split':
      return `${shift.intervals[0].start} - ${shift.intervals[0].end} / ${shift.intervals[1].start} - ${shift.intervals[1].end}`
    case 'day_off':
      return 'День отдыха'
    case 'vacation':
      return 'Отпускной день'
    default:
      return assertNever(shift)
  }
}

function formatHours(hours: number): string {
  if (Number.isInteger(hours)) {
    return `${hours} ч`
  }

  return `${hours.toFixed(1).replace('.', ',')} ч`
}

function classNames(...classes: string[]): string {
  return classes.filter(Boolean).join(' ')
}

function assertNever(value: never): never {
  throw new Error(`Unexpected shift cell value: ${JSON.stringify(value)}`)
}
