import clsx from 'clsx'

import { formatMetric, formatTimestamp, statusTone } from '../lib/format'
import type { RunSummary } from '../types'

interface RunsTableProps {
  runs: RunSummary[]
  selectedRunId: string | null
  compareIds: string[]
  onSelect: (runId: string) => void
  onToggleCompare: (runId: string) => void
}

export function RunsTable({ runs, selectedRunId, compareIds, onSelect, onToggleCompare }: RunsTableProps) {
  return (
    <section className="panel table-panel">
      <div className="section-heading">
        <p className="eyebrow">Monitor</p>
        <h2>Experiment runs</h2>
      </div>
      <div className="table-shell">
        <table>
          <thead>
            <tr>
              <th>Compare</th>
              <th>Run</th>
              <th>Preset</th>
              <th>Status</th>
              <th>Model</th>
              <th>Primary metric</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => {
              const primaryMetric = run.task_type === 'classification' ? run.scorecard.f1 : run.scorecard.rmse
              return (
                <tr
                  key={run.run_id}
                  className={clsx({ selected: selectedRunId === run.run_id })}
                  onClick={() => onSelect(run.run_id)}
                >
                  <td>
                    <input
                      aria-label={`Compare ${run.display_name}`}
                      type="checkbox"
                      checked={compareIds.includes(run.run_id)}
                      onChange={(event) => {
                        event.stopPropagation()
                        onToggleCompare(run.run_id)
                      }}
                    />
                  </td>
                  <td>
                    <div className="run-name">{run.display_name}</div>
                    <div className="run-subtitle">{run.run_id}</div>
                  </td>
                  <td>{run.preset_key}</td>
                  <td>
                    <span className={`status-badge ${statusTone(run.status)}`}>{run.status}</span>
                  </td>
                  <td>{run.model_name}</td>
                  <td>{formatMetric(primaryMetric)}</td>
                  <td>{formatTimestamp(run.created_at)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
