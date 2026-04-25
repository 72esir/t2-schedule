import { useState, type FormEvent } from 'react'

const todayEvents = [
  { time: '09:00', title: 'Синхронизация', meta: 'Команда расписания' },
  { time: '12:30', title: 'Окно заявок', meta: '4 новых изменения' },
  { time: '16:00', title: 'Публикация', meta: 'Смена на завтра' },
]

const roles = [
  { value: 'staff', label: 'Сотрудник' },
  { value: 'admin', label: 'Администратор' },
] as const

export default function authForm() {
  const [role, setRole] = useState<'staff' | 'admin'>('staff')
  const [email, setEmail] = useState('manager@company.ru')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(true)
  const [notice, setNotice] = useState('')

  const canSubmit = email.trim().length > 0 && password.trim().length > 0

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setNotice(
      canSubmit
        ? `Готово: пример входа для роли "${
            role === 'staff' ? 'Сотрудник' : 'Администратор'
          }".`
        : 'Заполни почту и пароль для примера входа.',
    )
  }

  return (
    <main className="min-h-screen bg-[#f3f3f5] px-4 py-5 text-black sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-40px)] w-full max-w-6xl flex-col">
        <header className="flex items-center justify-between pb-5">
          <a href="/" className="flex items-center gap-3 font-black">
            <span className="grid size-10 place-items-center rounded-full bg-black text-xl leading-none text-white">
              p<span className="text-[#ff3495]">2</span>
            </span>
            <span className="text-sm uppercase leading-none">
              Schedule
              <br />
              Planner
            </span>
          </a>
          <span className="hidden rounded-full border border-black/10 bg-white px-4 py-2 text-sm font-medium text-black/70 sm:inline-flex">
            Рабочая среда
          </span>
        </header>

        <section className="grid flex-1 overflow-hidden rounded-[28px] border border-black/10 bg-white shadow-[0_24px_80px_rgba(0,0,0,0.08)] lg:grid-cols-[0.95fr_1.05fr]">
          <aside className="bg-black p-6 text-white sm:p-8 lg:p-10">
            <div className="flex h-full flex-col justify-between gap-10">
              <div>
                <div className="mb-8 h-5 w-5 bg-[#ff3495]" />
                <p className="mb-4 text-sm font-medium text-white/60">
                  Планирование смен
                </p>
                <h1 className="max-w-md text-4xl font-black uppercase leading-[0.95] sm:text-5xl">
                  Вход в расписание
                </h1>
              </div>

              <div className="space-y-3">
                <div className="grid grid-cols-[92px_1fr] overflow-hidden rounded-2xl border border-white/15">
                  <div className="bg-[#ff3495] p-4 text-sm font-black text-white">
                    Сегодня
                  </div>
                  <div className="bg-white p-4 text-black">
                    <p className="text-2xl font-black leading-none">18 смен</p>
                    <p className="mt-1 text-sm text-black/55">3 требуют проверки</p>
                  </div>
                </div>

                <div className="divide-y divide-white/10 rounded-2xl border border-white/15">
                  {todayEvents.map((event) => (
                    <div
                      key={event.time}
                      className="grid grid-cols-[72px_1fr] gap-4 px-4 py-3"
                    >
                      <span className="font-black text-[#a7fc00]">
                        {event.time}
                      </span>
                      <div>
                        <p className="font-bold">{event.title}</p>
                        <p className="text-sm text-white/55">{event.meta}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </aside>

          <div className="flex items-center justify-center p-5 sm:p-8 lg:p-12">
            <form
              onSubmit={handleSubmit}
              className="w-full max-w-md"
              aria-label="Форма входа"
            >
              <div className="mb-8">
                <p className="mb-3 text-sm font-bold text-black/45">Аккаунт</p>
                <h2 className="text-3xl font-black uppercase leading-none sm:text-4xl">
                  Войти
                </h2>
              </div>

              <div className="mb-6 grid grid-cols-2 rounded-2xl bg-[#f0f0f2] p-1">
                {roles.map(({ value, label }) => (
                  <button
                    key={value}
                    type="button"
                    aria-pressed={role === value}
                    onClick={() => setRole(value)}
                    className={`rounded-xl px-4 py-3 text-sm font-bold transition ${
                      role === value
                        ? 'bg-black text-white'
                        : 'text-black/55 hover:text-black'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              <label className="mb-4 block">
                <span className="mb-2 block text-sm font-bold text-black/65">
                  Почта
                </span>
                <input
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  type="email"
                  className="h-14 w-full rounded-2xl border border-black/10 bg-[#f7f7f8] px-4 text-base font-medium outline-none transition placeholder:text-black/35 focus:border-[#ff3495] focus:bg-white focus:ring-4 focus:ring-[#ff3495]/15"
                  placeholder="name@company.ru"
                />
              </label>

              <label className="mb-5 block">
                <span className="mb-2 block text-sm font-bold text-black/65">
                  Пароль
                </span>
                <input
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  type="password"
                  className="h-14 w-full rounded-2xl border border-black/10 bg-[#f7f7f8] px-4 text-base font-medium outline-none transition placeholder:text-black/35 focus:border-[#ff3495] focus:bg-white focus:ring-4 focus:ring-[#ff3495]/15"
                  placeholder="Введите пароль"
                />
              </label>

              <div className="mb-7 flex flex-wrap items-center justify-between gap-3">
                <label className="flex cursor-pointer items-center gap-3 text-sm font-medium text-black/70">
                  <input
                    checked={remember}
                    onChange={(event) => setRemember(event.target.checked)}
                    type="checkbox"
                    className="size-5 rounded border-black/20 accent-[#ff3495]"
                  />
                  Запомнить меня
                </label>
                <a
                  href="#restore"
                  className="text-sm font-bold text-black underline decoration-[#ff3495] decoration-2 underline-offset-4"
                >
                  Забыли пароль?
                </a>
              </div>

              <button
                type="submit"
                className="h-14 w-full rounded-full bg-[#a7fc00] px-6 text-sm font-black uppercase text-black transition hover:bg-[#95e700] focus:outline-none focus:ring-4 focus:ring-[#a7fc00]/40"
              >
                Войти
              </button>

              <button
                type="button"
                onClick={() => setNotice('SSO-кнопка показана как второй сценарий входа.')}
                className="mt-3 h-14 w-full rounded-full border border-black/15 bg-white px-6 text-sm font-black uppercase text-black transition hover:border-black"
              >
                Войти через SSO
              </button>

              <p
                className={`mt-5 min-h-6 text-sm font-bold ${
                  notice ? 'text-black' : 'text-black/45'
                }`}
              >
                {notice}
              </p>
            </form>
          </div>
        </section>
      </div>
    </main>
  )
}


