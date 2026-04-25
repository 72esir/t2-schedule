import { create } from 'zustand'

const ACCESS_TOKEN_STORAGE_KEY = 't2_schedule_access_token'

export type DemoRole = 'manager' | 'user'

const DEMO_MANAGER_TOKEN = 'demo-manager-token'
const DEMO_USER_TOKEN = 'demo-user-token'

interface AuthStoreState {
  token: string | null
  setToken: (token: string) => void
  loginAsDemo: (role: DemoRole) => void
  clearToken: () => void
}

export const useAuthStore = create<AuthStoreState>((set) => ({
  token: readStoredToken(),

  setToken: (token) => {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token)
    set({ token })
  },

  loginAsDemo: (role) => {
    const token = role === 'manager' ? DEMO_MANAGER_TOKEN : DEMO_USER_TOKEN

    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token)
    set({ token })
  },

  clearToken: () => {
    window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
    set({ token: null })
  },
}))

function readStoredToken(): string | null {
  if (typeof window === 'undefined') {
    return null
  }

  return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)
}

export function getDemoRole(token = useAuthStore.getState().token): DemoRole | null {
  if (token === DEMO_MANAGER_TOKEN) {
    return 'manager'
  }

  if (token === DEMO_USER_TOKEN) {
    return 'user'
  }

  return null
}
