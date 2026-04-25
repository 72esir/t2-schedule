import { useQueryClient } from '@tanstack/react-query'

import { getApiErrorMessage } from './api/client'
import { useMeQuery } from './api/queries'
import { useAuthStore } from './store/useAuthStore'
import EmployeeDashboard from './pages/EmployeeDashboard'
import ManagerDashboard from './pages/ManagerDashboard'
import AuthPage from './pages/auth'

function App() {
  const queryClient = useQueryClient()
  const token = useAuthStore((state) => state.token)
  const clearToken = useAuthStore((state) => state.clearToken)
  const meQuery = useMeQuery()
  const sessionNotice = meQuery.isError
    ? getApiErrorMessage(meQuery.error)
    : ''

  function handleLogout() {
    clearToken()
    queryClient.clear()
  }

  if (!token || meQuery.isError) {
    return <AuthPage sessionNotice={sessionNotice} />
  }

  if (meQuery.isPending) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#f3f3f5] px-4 text-black">
        <div className="rounded-lg border border-black/10 bg-white px-6 py-5 text-sm font-black uppercase shadow-sm">
          Загрузка аккаунта
        </div>
      </main>
    )
  }

  if (!meQuery.data) {
    return <AuthPage sessionNotice="Не удалось получить профиль." />
  }

  if (meQuery.data.role === 'manager') {
    return <ManagerDashboard user={meQuery.data} onLogout={handleLogout} />
  }

  return <EmployeeDashboard user={meQuery.data} onLogout={handleLogout} />
}

export default App
