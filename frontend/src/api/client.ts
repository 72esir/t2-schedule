import axios from 'axios'

import { useAuthStore } from '../store/useAuthStore'

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim().replace(
  /\/+$/,
  '',
)

if (!configuredApiBaseUrl) {
  throw new Error(
    'VITE_API_BASE_URL is not set. Create frontend/.env from .env.example.',
  )
}

export const API_BASE_URL = configuredApiBaseUrl

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    Accept: 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

export function getApiErrorMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return 'Не удалось выполнить запрос. Попробуйте ещё раз.'
  }

  if (!error.response) {
    return `Backend недоступен. Проверьте доступность API: ${API_BASE_URL}.`
  }

  const detail = error.response.data?.detail

  if (detail) {
    return normalizeDetail(detail)
  }

  return `Backend вернул ошибку ${error.response.status}.`
}

function normalizeDetail(detail: unknown): string {
  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') {
          return item
        }

        if (
          item &&
          typeof item === 'object' &&
          'msg' in item &&
          typeof item.msg === 'string'
        ) {
          return item.msg
        }

        return JSON.stringify(item)
      })
      .join('; ')
  }

  return JSON.stringify(detail)
}
