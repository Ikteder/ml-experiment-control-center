import { startTransition, useDeferredValue, useEffect, useMemo, useState } from 'react'

import { getMetrics, getRun, launchRun, listPresets, listRuns } from './api/client'
import { ArtifactBrowser } from './components/ArtifactBrowser'
import { CompareStrip } from './components/CompareStrip'
import { LogStream } from './components/LogStream'
import { MetricChart } from './components/MetricChart'
import { RunLauncher } from './components/RunLauncher'
import { RunsTable } from './components/RunsTable'
import { StatCards } from './components/StatCards'
import { formatTimestamp, statusTone } from './lib/format'
import { useEventSource } from './hooks/useEventSource'
import type {
  LaunchRunRequest,
  MetricPoint,
  PresetSummary,
  RunDetailResponse,
  RunSummary,
} from './types'

const API_ORIGIN = import.meta.env.VITE_API_ORIGIN ?? 'http://127.0.0.1:8000'

function App() {
  const [presets, setPresets] = useState<PresetSummary[]>([])
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [selectedRunDetail, setSelectedRunDetail] = useState<RunDetailResponse | null>(null)
  const [metricPoints, setMetricPoints] = useState<MetricPoint[]>([])
  const [compareIds, setCompareIds] = useState<string[]>([])
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [presetFilter, setPresetFilter] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [errorMessage, setErrorMessage] = useState('')

  const deferredSearch = useDeferredValue(search)
  const liveLogs = useEventSource(selectedRunId)

  async function refreshRuns() {
    const params = new URLSearchParams({ limit: '20', offset: '0' })
    if (deferredSearch) params.set('search', deferredSearch)
    if (statusFilter) params.set('status', statusFilter)
    if (presetFilter) params.set('preset_key', presetFilter)
    const response = await listRuns(params)
    setRuns(response.items)
    if (!selectedRunId && response.items.length > 0) {
      setSelectedRunId(response.items[0].run_id)
    }
  }

  useEffect(() => {
    Promise.all([listPresets(), refreshRuns()])
      .then(([presetItems]) => {
        setPresets(presetItems)
      })
      .catch((error: Error) => {
        setErrorMessage(error.message)
      })
  }, [])

  useEffect(() => {
    refreshRuns().catch((error: Error) => setErrorMessage(error.message))
  }, [deferredSearch, statusFilter, presetFilter])

  useEffect(() => {
    const timer = window.setInterval(() => {
      refreshRuns().catch(() => undefined)
    }, 2500)
    return () => window.clearInterval(timer)
  }, [deferredSearch, statusFilter, presetFilter])

  useEffect(() => {
    if (!selectedRunId) return
    Promise.all([getRun(selectedRunId), getMetrics(selectedRunId)])
      .then(([detail, metrics]) => {
        setSelectedRunDetail(detail)
        setMetricPoints(metrics)
      })
      .catch((error: Error) => {
        setErrorMessage(error.message)
      })
  }, [selectedRunId, runs])

  const displayedRuns = useMemo(() => {
    if (!dateFilter) return runs
    const cutoff = new Date(dateFilter)
    return runs.filter((run) => new Date(run.created_at) >= cutoff)
  }, [dateFilter, runs])

  const compareRuns = displayedRuns.filter((run) => compareIds.includes(run.run_id)).slice(0, 2)
  const previewArtifact = selectedRunDetail?.artifacts.find((artifact) => artifact.mime_type.startsWith('image/'))

  async function handleLaunch(payload: LaunchRunRequest) {
    setErrorMessage('')
    const run = await launchRun(payload)
    await refreshRuns()
    setSelectedRunId(run.run_id)
  }

  function toggleCompare(runId: string) {
    setCompareIds((current) => {
      if (current.includes(runId)) {
        return current.filter((item) => item !== runId)
      }
      return [...current, runId].slice(-2)
    })
  }

  return (
    <div className="app-shell">
      <header className="hero-shell">
        <div>
          <p className="eyebrow">ML Experiment Control Center</p>
          <h1>Launch, track, compare, and export experiments from one industrial-grade dashboard.</h1>
          <p className="hero-copy">
            Lightweight internal ML platform built with FastAPI, React, SQLite, live logs, reproducible run configs,
            artifact storage, and side-by-side experiment review.
          </p>
        </div>
        <div className="hero-callout panel">
          <span className={`status-badge ${statusTone(selectedRunDetail?.run.status ?? 'queued')}`}>
            {selectedRunDetail?.run.status ?? 'waiting'}
          </span>
          <h3>{selectedRunDetail?.run.display_name ?? 'No run selected'}</h3>
          <p>{selectedRunDetail?.run.latest_message ?? 'Launch a workload to start collecting logs and artifacts.'}</p>
        </div>
      </header>

      {errorMessage ? <div className="error-banner">{errorMessage}</div> : null}

      <StatCards runs={displayedRuns} />

      <div className="content-grid">
        <RunLauncher presets={presets} onLaunch={handleLaunch} />

        <section className="panel filters-panel">
          <div className="section-heading">
            <p className="eyebrow">Discover</p>
            <h2>Search and filter</h2>
          </div>
          <div className="filter-grid">
            <label className="field">
              <span>Search</span>
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Run ID, model, name" />
            </label>
            <label className="field">
              <span>Status</span>
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                <option value="">All</option>
                <option value="queued">Queued</option>
                <option value="running">Running</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </label>
            <label className="field">
              <span>Preset</span>
              <select value={presetFilter} onChange={(event) => setPresetFilter(event.target.value)}>
                <option value="">All</option>
                {presets.map((preset) => (
                  <option key={preset.key} value={preset.key}>
                    {preset.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Date</span>
              <input type="date" value={dateFilter} onChange={(event) => setDateFilter(event.target.value)} />
            </label>
          </div>
        </section>

        <RunsTable
          runs={displayedRuns}
          selectedRunId={selectedRunId}
          compareIds={compareIds}
          onSelect={(runId) => startTransition(() => setSelectedRunId(runId))}
          onToggleCompare={toggleCompare}
        />

        <CompareStrip runs={compareRuns} />

        <MetricChart points={metricPoints} taskType={selectedRunDetail?.run.task_type ?? 'classification'} />

        <section className="panel detail-panel">
          <div className="section-heading">
            <p className="eyebrow">Review</p>
            <h2>Run summary</h2>
          </div>
          {selectedRunDetail ? (
            <div className="detail-stack">
              <div className="detail-meta">
                <div>
                  <span>Dataset</span>
                  <strong>{selectedRunDetail.run.dataset_name}</strong>
                </div>
                <div>
                  <span>Model</span>
                  <strong>{selectedRunDetail.run.model_name}</strong>
                </div>
                <div>
                  <span>Created</span>
                  <strong>{formatTimestamp(selectedRunDetail.run.created_at)}</strong>
                </div>
              </div>
              <pre className="config-block">{JSON.stringify(selectedRunDetail.config, null, 2)}</pre>
              {previewArtifact ? (
                <img
                  className="artifact-preview"
                  src={`${API_ORIGIN}${previewArtifact.download_url}`}
                  alt={previewArtifact.name}
                />
              ) : null}
            </div>
          ) : (
            <p className="empty-copy">Select a run to inspect its config, timestamps, and primary artifact preview.</p>
          )}
        </section>

        <ArtifactBrowser artifacts={selectedRunDetail?.artifacts ?? []} />

        <LogStream events={liveLogs} />
      </div>
    </div>
  )
}

export default App
