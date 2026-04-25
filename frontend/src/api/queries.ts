import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryKey,
} from '@tanstack/react-query'

import {
  authApi,
  exportApi,
  managerApi,
  periodApi,
  scheduleApi,
} from './backend'
import type {
  CollectionPeriodFromTemplatePayload,
  EmployeeRegisterPayload,
  LoginPayload,
  ScheduleBulkUpdatePayload,
  VacationDaysModerationPayload,
  ScheduleChangeRequestPayload,
  ScheduleChangeRequestManagerApproval
} from './types'
import { useAuthStore } from '../store/useAuthStore'

export const queryKeys = {
  me: ['auth', 'me'] as const,
  currentPeriod: ['periods', 'current'] as const,
  periodTemplates: ['periods', 'templates'] as const,
  periodStats: ['periods', 'current', 'stats'] as const,
  periodSubmissions: ['periods', 'current', 'submissions'] as const,
  periodHistory: ['periods', 'history'] as const,
  mySchedule: ['schedules', 'me'] as const,
  myScheduleSummary: ['schedules', 'me', 'summary'] as const,
  myScheduleValidation: ['schedules', 'me', 'validation'] as const,
  managerDashboard: ['manager', 'dashboard'] as const,
  managerUsers: ['manager', 'users'] as const,
  pendingVacationDays: ['manager', 'vacation-days', 'pending'] as const,
  pendingVerificationUsers: ['manager', 'users', 'pending-verification'] as const,
  pendingChangeRequests: ['manager', 'schedule-change-requests', 'pending'] as const,
  templates: ['templates'] as const,
  myScheduleState: ['schedules', 'me', 'state'] as const,
  myChangeRequest: ['schedules', 'change-request', 'me'] as const,
}

export function useMeQuery() {
  const token = useAuthStore((state) => state.token)

  return useQuery({
    queryKey: queryKeys.me,
    queryFn: authApi.me,
    enabled: Boolean(token),
    retry: false,
  })
}

export function useLoginMutation() {
  const queryClient = useQueryClient()
  const setToken = useAuthStore((state) => state.setToken)

  return useMutation({
    mutationFn: (payload: LoginPayload) => authApi.login(payload),
    onSuccess: (tokenResponse) => {
      setToken(tokenResponse.access_token)
      void queryClient.invalidateQueries({ queryKey: queryKeys.me })
    },
  })
}

export function useRegisterMutation() {
  return useMutation({
    mutationFn: (payload: EmployeeRegisterPayload) => authApi.register(payload),
  })
}

export function useCurrentPeriodQuery(enabled = true) {
  return useAuthedQuery({
    queryKey: queryKeys.currentPeriod,
    queryFn: periodApi.getCurrent,
    enabled,
  })
}

export function usePeriodTemplatesQuery(enabled = true) {
  return useAuthedQuery({
    queryKey: queryKeys.periodTemplates,
    queryFn: periodApi.getTemplates,
    enabled,
  })
}

export function useMyScheduleQuery(enabled = true) {
  return useAuthedQuery({
    queryKey: queryKeys.mySchedule,
    queryFn: scheduleApi.getMine,
    enabled,
  })
}

export function useMyScheduleSummaryQuery(enabled = true) {
  return useAuthedQuery({
    queryKey: queryKeys.myScheduleSummary,
    queryFn: scheduleApi.getMineSummary,
    enabled,
  })
}

export function useMyScheduleValidationQuery(enabled = true) {
  return useAuthedQuery({
    queryKey: queryKeys.myScheduleValidation,
    queryFn: scheduleApi.getMineValidation,
    enabled,
  })
}

export function useMyScheduleStateQuery(enabled = true) {
  return useAuthedQuery({
    queryKey: queryKeys.myScheduleState,
    queryFn: scheduleApi.getMineState,
    enabled,
  })
}

export function useMyChangeRequestQuery(enabled = true) {
  return useAuthedQuery({
    queryKey: queryKeys.myChangeRequest,
    queryFn: scheduleApi.getMineChangeRequest,
    enabled,
  })
}

export function useCreateChangeRequestMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: ScheduleChangeRequestPayload) =>
      scheduleApi.createChangeRequest(payload),
    onSuccess: () => {
      invalidateMany(queryClient, [
        queryKeys.myChangeRequest,
        queryKeys.managerDashboard,
        queryKeys.pendingChangeRequests,
      ])
    },
  })
}

export function useUpdateMyScheduleMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: ScheduleBulkUpdatePayload) =>
      scheduleApi.updateMine(payload),
    onSuccess: () => {
      invalidateMany(queryClient, [
        queryKeys.mySchedule,
        queryKeys.myScheduleSummary,
        queryKeys.myScheduleValidation,
        queryKeys.managerDashboard,
        queryKeys.periodSubmissions,
        queryKeys.periodStats,
      ])
    },
  })
}

export function useManagerDashboardQuery(enabled = true) {
  return useAuthedQuery({
    queryKey: queryKeys.managerDashboard,
    queryFn: managerApi.getDashboard,
    enabled,
  })
}

export function usePendingVacationDaysQuery(enabled = true) {
  return useAuthedQuery({
    queryKey: queryKeys.pendingVacationDays,
    queryFn: managerApi.getPendingVacationDays,
    enabled,
  })
}

export function usePendingVerificationUsersQuery(enabled = true) {
  return useAuthedQuery({
    queryKey: queryKeys.pendingVerificationUsers,
    queryFn: managerApi.getPendingVerificationUsers,
    enabled,
  })
}

export function usePendingChangeRequestsQuery(enabled = true) {
  return useAuthedQuery({
    queryKey: queryKeys.pendingChangeRequests,
    queryFn: managerApi.getPendingChangeRequests,
    enabled,
  })
}

export function useApproveChangeRequestMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      requestId,
      payload,
    }: {
      requestId: number
      payload: ScheduleChangeRequestManagerApproval
    }) => managerApi.approveChangeRequest(requestId, payload),
    onSuccess: () => {
      invalidateMany(queryClient, [
        queryKeys.pendingChangeRequests,
        queryKeys.managerDashboard,
        queryKeys.myChangeRequest,
        queryKeys.mySchedule,
        queryKeys.myScheduleSummary,
        queryKeys.myScheduleValidation,
      ])
    },
  })
}

export function useRejectChangeRequestMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      requestId,
      payload,
    }: {
      requestId: number
      payload: ScheduleChangeRequestManagerApproval
    }) => managerApi.rejectChangeRequest(requestId, payload),
    onSuccess: () => {
      invalidateMany(queryClient, [
        queryKeys.pendingChangeRequests,
        queryKeys.managerDashboard,
        queryKeys.myChangeRequest,
      ])
    },
  })
}

export function useCreatePeriodFromTemplateMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CollectionPeriodFromTemplatePayload) =>
      periodApi.createFromTemplate(payload),
    onSuccess: () => {
      invalidateManagerPeriodQueries(queryClient)
    },
  })
}

export function useClosePeriodMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (periodId: number) => periodApi.close(periodId),
    onSuccess: () => {
      invalidateManagerPeriodQueries(queryClient)
    },
  })
}

export function useVerifyUserMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (userId: number) => managerApi.verifyUser(userId),
    onSuccess: () => {
      invalidateMany(queryClient, [
        queryKeys.pendingVerificationUsers,
        queryKeys.managerUsers,
        queryKeys.managerDashboard,
        queryKeys.periodStats,
        queryKeys.periodSubmissions,
      ])
    },
  })
}

export function useRejectUserMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (userId: number) => managerApi.rejectUser(userId),
    onSuccess: () => {
      invalidateMany(queryClient, [
        queryKeys.pendingVerificationUsers,
        queryKeys.managerUsers,
        queryKeys.managerDashboard,
        queryKeys.periodStats,
        queryKeys.periodSubmissions,
      ])
    },
  })
}

export function useModerateVacationDaysMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      userId,
      payload,
    }: {
      userId: number
      payload: VacationDaysModerationPayload
    }) => managerApi.moderateVacationDays(userId, payload),
    onSuccess: () => {
      invalidateMany(queryClient, [
        queryKeys.pendingVacationDays,
        queryKeys.managerUsers,
        queryKeys.managerDashboard,
      ])
    },
  })
}

export function useExportScheduleMutation() {
  return useMutation({
    mutationFn: (periodId?: number) => exportApi.schedule(periodId),
  })
}

function useAuthedQuery<TData>({
  queryKey,
  queryFn,
  enabled,
}: {
  queryKey: QueryKey
  queryFn: () => Promise<TData>
  enabled: boolean
}) {
  const token = useAuthStore((state) => state.token)

  return useQuery({
    queryKey,
    queryFn,
    enabled: Boolean(token) && enabled,
  })
}

function invalidateManagerPeriodQueries(queryClient: ReturnType<typeof useQueryClient>) {
  invalidateMany(queryClient, [
    queryKeys.currentPeriod,
    queryKeys.periodHistory,
    queryKeys.periodStats,
    queryKeys.periodSubmissions,
    queryKeys.managerDashboard,
  ])
}

function invalidateMany(
  queryClient: ReturnType<typeof useQueryClient>,
  queryKeysToInvalidate: readonly QueryKey[],
) {
  queryKeysToInvalidate.forEach((queryKey) => {
    void queryClient.invalidateQueries({ queryKey })
  })
}
