import { apiClient } from './client'
import type {
  BackendScheduleByDate,
  CollectionPeriod,
  CollectionPeriodCreatePayload,
  CollectionPeriodFromTemplatePayload,
  EmployeeRegisterPayload,
  ExportedFile,
  LoginPayload,
  ManagerDashboard,
  PeriodStats,
  PeriodSubmissions,
  PeriodTemplate,
  ScheduleBulkUpdatePayload,
  ScheduleForUser,
  ScheduleSummary,
  ScheduleTemplate,
  ScheduleTemplateCreatePayload,
  ScheduleValidationResult,
  TokenResponse,
  User,
  VacationDaysModerationPayload,
  VerificationPayload,
  ScheduleStatePayload,
  ScheduleChangeRequestPayload,
  PendingScheduleChangeRequest,
  ScheduleChangeRequestManagerApproval
} from './types'

export const authApi = {
  async login(payload: LoginPayload): Promise<TokenResponse> {
    const formData = new URLSearchParams()
    formData.set('username', payload.email)
    formData.set('password', payload.password)

    const response = await apiClient.post<TokenResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    return response.data
  },

  async register(payload: EmployeeRegisterPayload): Promise<User> {
    const response = await apiClient.post<User>('/auth/register', payload)
    return response.data
  },

  async me(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me')
    return response.data
  },

  async verify(payload: VerificationPayload): Promise<User> {
    const response = await apiClient.post<User>('/auth/verify', payload)
    return response.data
  },
}

export const periodApi = {
  async getCurrent(): Promise<CollectionPeriod | null> {
    const response = await apiClient.get<CollectionPeriod | null>('/periods/current')
    return response.data
  },

  async getTemplates(): Promise<PeriodTemplate[]> {
    const response = await apiClient.get<PeriodTemplate[]>('/periods/templates')
    return response.data
  },

  async create(payload: CollectionPeriodCreatePayload): Promise<CollectionPeriod> {
    const response = await apiClient.post<CollectionPeriod>('/periods', payload)
    return response.data
  },

  async createFromTemplate(payload: CollectionPeriodFromTemplatePayload): Promise<CollectionPeriod> {
    const response = await apiClient.post<CollectionPeriod>('/periods/from-template', payload)
    return response.data
  },

  async close(periodId: number): Promise<CollectionPeriod> {
    const response = await apiClient.post<CollectionPeriod>(`/periods/${periodId}/close`)
    return response.data
  },

  async getStats(): Promise<PeriodStats> {
    const response = await apiClient.get<PeriodStats>('/periods/current/stats')
    return response.data
  },

  async getSubmissions(): Promise<PeriodSubmissions> {
    const response = await apiClient.get<PeriodSubmissions>('/periods/current/submissions')
    return response.data
  },

  async getHistory(): Promise<CollectionPeriod[]> {
    const response = await apiClient.get<CollectionPeriod[]>('/periods/history')
    return response.data
  },
}

export const scheduleApi = {
  async getMine(): Promise<BackendScheduleByDate> {
    const response = await apiClient.get<BackendScheduleByDate>('/schedules/me')
    return response.data
  },

  async getMineState(): Promise<ScheduleStatePayload> {
    const response = await apiClient.get<ScheduleStatePayload>('/schedules/me/state')
    return response.data
  },

  async updateMine(payload: ScheduleBulkUpdatePayload): Promise<BackendScheduleByDate> {
    const response = await apiClient.put<BackendScheduleByDate>('/schedules/me', payload)
    return response.data
  },

  async createChangeRequest(payload: ScheduleChangeRequestPayload): Promise<void> {
    const response = await apiClient.post('/schedules/change-request', payload)
    return response.data
  },

  async getMineChangeRequest(): Promise<PendingScheduleChangeRequest | null> {
    const response = await apiClient.get<PendingScheduleChangeRequest | null>('/schedules/change-request/me')
    return response.data
  },

  async getMineSummary(): Promise<ScheduleSummary> {
    const response = await apiClient.get<ScheduleSummary>('/schedules/me/summary')
    return response.data
  },

  async getMineValidation(): Promise<ScheduleValidationResult> {
    const response = await apiClient.get<ScheduleValidationResult>('/schedules/me/validation')
    return response.data
  },

  async getByUser(userId: number): Promise<ScheduleForUser> {
    const response = await apiClient.get<ScheduleForUser>(`/schedules/by-user/${userId}`)
    return response.data
  },

  async getSummaryByUser(userId: number): Promise<ScheduleSummary> {
    const response = await apiClient.get<ScheduleSummary>(`/schedules/by-user/${userId}/summary`)
    return response.data
  },

  async getValidationByUser(userId: number): Promise<ScheduleValidationResult> {
    const response = await apiClient.get<ScheduleValidationResult>(`/schedules/by-user/${userId}/validation`)
    return response.data
  },
}

export const managerApi = {
  async getDashboard(): Promise<ManagerDashboard> {
    const response = await apiClient.get<ManagerDashboard>('/manager/dashboard')
    return response.data
  },

  async getPendingChangeRequests(): Promise<PendingScheduleChangeRequest[]> {
    const response = await apiClient.get<PendingScheduleChangeRequest[]>('/manager/schedule-change-requests/pending')
    return response.data
  },

  async approveChangeRequest(requestId: number, payload: ScheduleChangeRequestManagerApproval): Promise<void> {
    const response = await apiClient.put(`/manager/schedule-change-requests/${requestId}/approve`, payload)
    return response.data
  },

  async rejectChangeRequest(requestId: number, payload: ScheduleChangeRequestManagerApproval): Promise<void> {
    const response = await apiClient.put(`/manager/schedule-change-requests/${requestId}/reject`, payload)
    return response.data
  },

  async getUsers(params?: {
    verified?: boolean
    alliance?: string
    role?: 'manager' | 'user'
    vacation_days_status?: string
  }): Promise<User[]> {
    const response = await apiClient.get<User[]>('/manager/users', { params })
    return response.data
  },

  async getPendingVacationDays(): Promise<User[]> {
    const response = await apiClient.get<User[]>('/manager/vacation-days/pending')
    return response.data
  },

  async getPendingVerificationUsers(): Promise<User[]> {
    const response = await apiClient.get<User[]>('/manager/users/pending-verification')
    return response.data
  },

  async verifyUser(userId: number): Promise<User> {
    const response = await apiClient.put<User>(`/manager/users/${userId}/verify`, {})
    return response.data
  },

  async rejectUser(userId: number): Promise<void> {
    await apiClient.delete(`/manager/users/${userId}/reject`)
  },

  async moderateVacationDays(userId: number, payload: VacationDaysModerationPayload): Promise<User> {
    const response = await apiClient.put<User>(`/manager/users/${userId}/vacation-days`, payload)
    return response.data
  },
}

export const templateApi = {
  async getMine(): Promise<ScheduleTemplate[]> {
    const response = await apiClient.get<ScheduleTemplate[]>('/templates')
    return response.data
  },

  async create(payload: ScheduleTemplateCreatePayload): Promise<ScheduleTemplate> {
    const response = await apiClient.post<ScheduleTemplate>('/templates', payload)
    return response.data
  },

  async delete(templateId: number): Promise<void> {
    await apiClient.delete(`/templates/${templateId}`)
  },
}

export const exportApi = {
  async schedule(periodId?: number): Promise<ExportedFile> {
    const response = await apiClient.get<Blob>('/export/schedule', {
      params: periodId ? { period_id: periodId } : undefined,
      responseType: 'blob',
    })

    return {
      blob: response.data,
      filename: parseDownloadFilename(response.headers['content-disposition']),
    }
  },
}

function parseDownloadFilename(contentDisposition: unknown): string {
  if (typeof contentDisposition !== 'string') {
    return 'schedule.xlsx'
  }
  const filenameMatch = /filename="?([^";]+)"?/i.exec(contentDisposition)
  return filenameMatch?.[1] ?? 'schedule.xlsx'
}
