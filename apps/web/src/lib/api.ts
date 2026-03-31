import type {
  ApiErrorEnvelope,
  AuthSessionResponse,
  BarkConfigRecord,
  BootstrapStatusResponse,
  CollectorDiagnosticsPayload,
  CollectorDiagnosticsResponse,
  CookieProfileRecord,
  DiscoverModelsPayload,
  DiscoverModelsResponse,
  CreateCookieProfilePayload,
  CreateModelProviderPayload,
  CreateTrackedAccountPayload,
  DashboardOverviewResponse,
  JobRunRecord,
  LoginPayload,
  ManualSyncResponse,
  ModelProviderRecord,
  OptionalBarkConfigResponse,
  OptionalTelegramConfigResponse,
  SetupPayload,
  TelegramConfigRecord,
  TestTelegramPushResponse,
  TrackedAccountRecord,
  UpsertBarkConfigPayload,
  UpsertTelegramConfigPayload,
} from './types'

const configuredApiBase = import.meta.env.VITE_API_BASE_URL?.trim()
const API_BASE = normalizeApiBase(
  configuredApiBase && configuredApiBase.length > 0
    ? configuredApiBase
    : import.meta.env.DEV
      ? 'http://127.0.0.1:8787'
      : '',
)

type RequestOptions = Omit<RequestInit, 'body' | 'headers'> & {
  body?: unknown
  headers?: HeadersInit
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers, ...rest } = options
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...rest,
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(headers ?? {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) {
    let message = `Request failed with status ${response.status}.`

    try {
      const payload = (await response.json()) as ApiErrorEnvelope
      message = payload.error.message
    } catch {
      // Ignore non-JSON error bodies.
    }

    throw new Error(message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  const text = await response.text()
  return (text ? (JSON.parse(text) as T) : (undefined as T))
}

export const api = {
  bootstrapStatus: () =>
    request<BootstrapStatusResponse>('/api/auth/bootstrap-status'),
  setup: (payload: SetupPayload) =>
    request<AuthSessionResponse>('/api/auth/setup', {
      method: 'POST',
      body: payload,
    }),
  login: (payload: LoginPayload) =>
    request<AuthSessionResponse>('/api/auth/login', {
      method: 'POST',
      body: payload,
    }),
  logout: () =>
    request<void>('/api/auth/logout', {
      method: 'POST',
    }),
  me: () => request<AuthSessionResponse>('/api/auth/me'),
  overview: () => request<DashboardOverviewResponse>('/api/dashboard/overview'),
  listAccounts: () => request<TrackedAccountRecord[]>('/api/settings/accounts'),
  createAccount: (payload: CreateTrackedAccountPayload) =>
    request<TrackedAccountRecord>('/api/settings/accounts', {
      method: 'POST',
      body: payload,
    }),
  listCookieProfiles: () =>
    request<CookieProfileRecord[]>('/api/settings/cookies'),
  createCookieProfile: (payload: CreateCookieProfilePayload) =>
    request<CookieProfileRecord>('/api/settings/cookies', {
      method: 'POST',
      body: payload,
    }),
  listModelProviders: () =>
    request<ModelProviderRecord[]>('/api/settings/model-providers'),
  createModelProvider: (payload: CreateModelProviderPayload) =>
    request<ModelProviderRecord>('/api/settings/model-providers', {
      method: 'POST',
      body: payload,
    }),
  getBarkConfig: () =>
    request<OptionalBarkConfigResponse>('/api/settings/bark'),
  saveBarkConfig: (payload: UpsertBarkConfigPayload) =>
    request<BarkConfigRecord>('/api/settings/bark', {
      method: 'PUT',
      body: payload,
    }),
  getTelegramConfig: () =>
    request<OptionalTelegramConfigResponse>('/api/settings/telegram'),
  saveTelegramConfig: (payload: UpsertTelegramConfigPayload) =>
    request<TelegramConfigRecord>('/api/settings/telegram', {
      method: 'PUT',
      body: payload,
    }),
  discoverModels: (payload: DiscoverModelsPayload) =>
    request<DiscoverModelsResponse>('/api/settings/model-providers/discover-models', {
      method: 'POST',
      body: payload,
    }),
  manualSync: () =>
    request<ManualSyncResponse>('/api/tasks/manual-sync', {
      method: 'POST',
    }),
  listRuns: () => request<JobRunRecord[]>('/api/tasks/runs'),
  collectorDiagnostics: (payload: CollectorDiagnosticsPayload) =>
    request<CollectorDiagnosticsResponse>('/api/tasks/collector-diagnostics', {
      method: 'POST',
      body: payload,
    }),
  testTelegramPush: () =>
    request<TestTelegramPushResponse>('/api/tasks/test-telegram-push', {
      method: 'POST',
    }),
}

function normalizeApiBase(value: string) {
  return value.replace(/\/+$/, '')
}
