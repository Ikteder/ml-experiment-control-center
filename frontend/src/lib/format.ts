export function formatTimestamp(value: string | null): string {
  if (!value) {
    return 'Not started'
  }
  return new Date(value).toLocaleString()
}

export function formatMetric(value: number | undefined): string {
  if (value === undefined || Number.isNaN(value)) {
    return '--'
  }
  return value.toFixed(3)
}

export function statusTone(status: string): string {
  if (status === 'completed') return 'success'
  if (status === 'running') return 'active'
  if (status === 'failed') return 'danger'
  return 'muted'
}
