import type {
  LaunchRunRequest,
  MetricPoint,
  PresetSummary,
  RunDetailResponse,
  RunListResponse,
  RunSummary,
} from '../types'

const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000/api/v1'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || `Request failed with ${response.status}`)
  }

  return response.json() as Promise<T>
}

export function apiBaseUrl(): string {
  return API_BASE
}

export function listPresets(): Promise<PresetSummary[]> {
  return request<PresetSummary[]>('/presets')
}

export function listRuns(params: URLSearchParams): Promise<RunListResponse> {
  return request<RunListResponse>(`/runs?${params.toString()}`)
}

export function launchRun(payload: LaunchRunRequest): Promise<RunSummary> {
  return request<RunSummary>('/runs', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getRun(runId: string): Promise<RunDetailResponse> {
  return request<RunDetailResponse>(`/runs/${runId}`)
}

export function getMetrics(runId: string): Promise<MetricPoint[]> {
  return request<MetricPoint[]>(`/runs/${runId}/metrics`)
}
