import { create } from 'zustand'

const ACCESS_TOKEN_STORAGE_KEY = 't2_schedule_access_token'

interface AuthStoreState {
  token: string | null
  setToken: (token: string) => void
  clearToken: () => void
}

export type DemoRole = 'manager' | 'user'

export const useAuthStore = create<AuthStoreState>((set) => ({
  token: readStoredToken(),

  setToken: (token) => {
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
