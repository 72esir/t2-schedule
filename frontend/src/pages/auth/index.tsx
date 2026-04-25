import { useState, type FormEvent } from 'react'
import {
  CalendarDays,
  KeyRound,
  LogIn,
  UserPlus,
} from 'lucide-react'

import { getApiErrorMessage } from '../../api/client'
import { useLoginMutation, useRegisterMutation } from '../../api/queries'
import t2Logo from '../../assets/t2-logo.svg'

type EntryRole = 'manager' | 'user'
type AuthMode = 'login' | 'register'

interface AuthPageProps {
  sessionNotice?: string
}

const roles: { value: EntryRole; label: string }[] = [
  { value: 'user', label: 'Сотрудник' },
  { value: 'manager', label: 'Менеджер' },
]

export default function AuthPage({ sessionNotice = '' }: AuthPageProps) {
  const [entryRole, setEntryRole] = useState<EntryRole>('user')
  const [mode, setMode] = useState<AuthMode>('login')
  const [loginEmail, setLoginEmail] = useState('manager@company.ru')
  const [loginPassword, setLoginPassword] = useState('')
  const [registerEmail, setRegisterEmail] = useState('')
  const [registerPassword, setRegisterPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [alliance, setAlliance] = useState('')
  const [vacationDays, setVacationDays] = useState('')
  const [notice, setNotice] = useState(sessionNotice)
  const loginMutation = useLoginMutation()
  const registerMutation = useRegisterMutation()

  function handleRoleChange(nextRole: EntryRole) {
    setEntryRole(nextRole)
    setNotice('')

    if (nextRole === 'manager') {
      setMode('login')
    }
  }

  function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setNotice('')

    loginMutation.mutate(
      {
        email: loginEmail.trim(),
        password: loginPassword,
      },
      {
        onError: (error) => setNotice(getApiErrorMessage(error)),
      },
    )
  }

  function handleRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setNotice('')

    const declaredDays = vacationDays.trim()
      ? Number(vacationDays.trim())
      : undefined

    registerMutation.mutate(
      {
        email: registerEmail.trim(),
        password: registerPassword,
        full_name: optionalText(fullName),
        alliance: optionalText(alliance),
        vacation_days_declared: Number.isFinite(declaredDays)
          ? declaredDays
          : undefined,
      },
      {
        onSuccess: (user) => {
          setMode('login')
          setLoginEmail(user.email ?? registerEmail)
          setNotice('Аккаунт создан. После подтверждения менеджером можно работать с графиком.')
        },
        onError: (error) => setNotice(getApiErrorMessage(error)),
      },
    )
  }

  const isLoginDisabled =
    loginMutation.isPending ||
    loginEmail.trim().length === 0 ||
    loginPassword.length === 0
  const isRegisterDisabled =
    registerMutation.isPending ||
    registerEmail.trim().length === 0 ||
    registerPassword.length === 0

  return (
    <main className="min-h-screen bg-[#f3f3f5] px-4 py-5 text-black sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-40px)] w-full max-w-6xl flex-col">
        <header className="flex items-center justify-between pb-5">
          <a href="/" className="flex items-center gap-3 font-black">
            <img src={t2Logo} alt="t2 logo" className="size-10 rounded-md" />
            <span className="text-sm uppercase leading-none">
              Schedule
              <br />
              Planner
            </span>
          </a>
        </header>

        <section className="grid flex-1 overflow-hidden rounded-lg border border-black/10 bg-white shadow-[0_24px_80px_rgba(0,0,0,0.08)] lg:grid-cols-[0.95fr_1.05fr]">
          <aside className="bg-black p-6 text-white sm:p-8 lg:p-10">
            <div className="flex h-full flex-col justify-center gap-10">
              <div>
                <div className="mb-8 grid size-12 place-items-center rounded-md bg-[#ff3495]">
                  <CalendarDays size={24} aria-hidden="true" />
                </div>
                <p className="mb-4 text-sm font-bold text-white/60">
                  Планирование смен
                </p>
                <h1 className="max-w-md text-4xl font-black uppercase leading-[0.95] sm:text-5xl">
                  Вход в расписание
                </h1>
              </div>
            </div>
          </aside>

          <div className="flex items-center justify-center p-5 sm:p-8 lg:p-12">
            <div className="w-full max-w-md">

              <div className="mb-6 grid grid-cols-2 rounded-lg bg-[#f0f0f2] p-1">
                {roles.map(({ value, label }) => (
                  <button
                    key={value}
                    type="button"
                    aria-pressed={entryRole === value}
                    onClick={() => handleRoleChange(value)}
                    className={`rounded-md px-4 py-3 text-sm font-black uppercase transition ${entryRole === value
                      ? 'bg-black text-white'
                      : 'text-black/55 hover:text-black'
                      }`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {entryRole === 'user' && (
                <div className="mb-6 grid grid-cols-2 gap-2">
                  <ModeButton
                    active={mode === 'login'}
                    Icon={KeyRound}
                    label="Вход"
                    onClick={() => {
                      setMode('login')
                      setNotice('')
                    }}
                  />
                  <ModeButton
                    active={mode === 'register'}
                    Icon={UserPlus}
                    label="Регистрация"
                    onClick={() => {
                      setMode('register')
                      setNotice('')
                    }}
                  />
                </div>
              )}

              {mode === 'login' && (
                <form onSubmit={handleLogin} aria-label="Форма входа">
                  <div className="mb-8">
                    <p className="mb-3 text-sm font-bold text-black/45">
                      {entryRole === 'manager' ? 'Аккаунт менеджера' : 'Аккаунт сотрудника'}
                    </p>
                    <h2 className="text-3xl font-black uppercase leading-none sm:text-4xl">
                      Войти
                    </h2>
                  </div>

                  <TextField
                    label="Почта"
                    type="email"
                    value={loginEmail}
                    autoComplete="email"
                    placeholder="name@company.ru"
                    onChange={setLoginEmail}
                  />
                  <TextField
                    label="Пароль"
                    type="password"
                    value={loginPassword}
                    autoComplete="current-password"
                    placeholder="Введите пароль"
                    onChange={setLoginPassword}
                  />

                  <button
                    type="submit"
                    disabled={isLoginDisabled}
                    className="mt-3 inline-flex h-14 w-full items-center justify-center gap-2 rounded-md bg-[#a7fc00] px-6 text-sm font-black uppercase text-black transition hover:bg-[#95e700] focus:outline-none focus:ring-4 focus:ring-[#a7fc00]/40 disabled:cursor-not-allowed disabled:bg-black/10 disabled:text-black/35"
                  >
                    <LogIn size={17} aria-hidden="true" />
                    {loginMutation.isPending ? 'Входим' : 'Войти'}
                  </button>
                </form>
              )}

              {mode === 'register' && entryRole === 'user' && (
                <form onSubmit={handleRegister} aria-label="Форма регистрации">
                  <div className="mb-8">
                    <p className="mb-3 text-sm font-bold text-black/45">
                      Новый сотрудник
                    </p>
                    <h2 className="text-3xl font-black uppercase leading-none sm:text-4xl">
                      Регистрация
                    </h2>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <TextField
                      label="Почта"
                      type="email"
                      value={registerEmail}
                      autoComplete="email"
                      placeholder="name@company.ru"
                      onChange={setRegisterEmail}
                    />
                    <TextField
                      label="Пароль"
                      type="password"
                      value={registerPassword}
                      autoComplete="new-password"
                      placeholder="Не длиннее 72 байт"
                      onChange={setRegisterPassword}
                    />
                  </div>

                  <TextField
                    label="ФИО"
                    value={fullName}
                    placeholder="Иван Иванов"
                    onChange={setFullName}
                  />
                  <div className="grid gap-4 sm:grid-cols-2">
                    <TextField
                      label="Альянс"
                      value={alliance}
                      placeholder="Alliance 1"
                      onChange={setAlliance}
                    />
                    <TextField
                      label="Дней отпуска"
                      type="number"
                      value={vacationDays}
                      placeholder="14"
                      min={0}
                      max={365}
                      onChange={setVacationDays}
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={isRegisterDisabled}
                    className="mt-3 inline-flex h-14 w-full items-center justify-center gap-2 rounded-md bg-[#a7fc00] px-6 text-sm font-black uppercase text-black transition hover:bg-[#95e700] focus:outline-none focus:ring-4 focus:ring-[#a7fc00]/40 disabled:cursor-not-allowed disabled:bg-black/10 disabled:text-black/35"
                  >
                    <UserPlus size={17} aria-hidden="true" />
                    {registerMutation.isPending ? 'Создаём' : 'Создать аккаунт'}
                  </button>
                </form>
              )}

              <p
                className={`mt-5 min-h-6 text-sm font-bold ${notice ? 'text-black' : 'text-transparent'
                  }`}
              >
                {notice || 'Нет уведомления'}
              </p>
            </div>
          </div>
        </section>
      </div>
    </main>
  )
}

interface TextFieldProps {
  label: string
  value: string
  onChange: (value: string) => void
  type?: string
  placeholder?: string
  autoComplete?: string
  min?: number
  max?: number
}

function TextField({
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
  autoComplete,
  min,
  max,
}: TextFieldProps) {
  return (
    <label className="mb-4 block">
      <span className="mb-2 block text-sm font-bold text-black/65">
        {label}
      </span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        type={type}
        min={min}
        max={max}
        autoComplete={autoComplete}
        className="h-14 w-full rounded-md border border-black/10 bg-[#f7f7f8] px-4 text-base font-medium outline-none transition placeholder:text-black/35 focus:border-[#ff3495] focus:bg-white focus:ring-4 focus:ring-[#ff3495]/15"
        placeholder={placeholder}
      />
    </label>
  )
}

interface ModeButtonProps {
  active: boolean
  Icon: typeof KeyRound
  label: string
  onClick: () => void
}

function ModeButton({ active, Icon, label, onClick }: ModeButtonProps) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`inline-flex h-12 items-center justify-center gap-2 rounded-md border text-sm font-black uppercase transition ${active
        ? 'border-black bg-black text-white'
        : 'border-black/10 bg-white text-black/55 hover:border-black/35 hover:text-black'
        }`}
    >
      <Icon size={16} aria-hidden="true" />
      {label}
    </button>
  )
}


function optionalText(value: string): string | undefined {
  const trimmedValue = value.trim()

  return trimmedValue.length > 0 ? trimmedValue : undefined
}
