export type TaskType = 'classification' | 'regression'

export interface PresetSummary {
  key: string
  display_name: string
  description: string
  dataset_name: string
  task_type: TaskType
  model_name: string
  config: Record<string, unknown>
}

export interface RunSummary {
  run_id: string
  display_name: string
  preset_key: string
  dataset_name: string
  task_type: TaskType
  model_name: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  seed: number
  latest_message: string
  created_at: string
  started_at: string | null
  finished_at: string | null
  scorecard: Record<string, number>
}

export interface RunListResponse {
  total: number
  limit: number
  offset: number
  items: RunSummary[]
}

export interface MetricPoint {
  step: number
  split: string
  loss?: number | null
  accuracy?: number | null
  f1?: number | null
  auroc?: number | null
  mae?: number | null
  rmse?: number | null
  r2?: number | null
  created_at: string
}

export interface Artifact {
  name: string
  artifact_type: string
  mime_type: string
  relative_path: string
  download_url: string
}

export interface RunDetailResponse {
  run: RunSummary
  config: Record<string, unknown>
  artifacts: Artifact[]
}

export interface LaunchRunRequest {
  preset_key?: string
  display_name?: string
  seed?: number
  epochs?: number
  config?: Record<string, unknown>
}

export interface LogEvent {
  timestamp: string
  level: string
  message: string
  payload: Record<string, unknown>
}
