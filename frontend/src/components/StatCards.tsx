import type { RunSummary } from '../types'

function countByStatus(runs: RunSummary[], status: RunSummary['status']) {
  return runs.filter((run) => run.status === status).length
}

export function StatCards({ runs }: { runs: RunSummary[] }) {
  const completed = countByStatus(runs, 'completed')
  const running = countByStatus(runs, 'running')
  const failed = countByStatus(runs, 'failed')
  const latest = runs[0]

  return (
    <section className="stats-grid">
      <article className="panel stat-card">
        <p>Total runs</p>
        <strong>{runs.length}</strong>
      </article>
      <article className="panel stat-card">
        <p>Active now</p>
        <strong>{running}</strong>
      </article>
      <article className="panel stat-card">
        <p>Completed</p>
        <strong>{completed}</strong>
      </article>
      <article className="panel stat-card">
        <p>Failed</p>
        <strong>{failed}</strong>
      </article>
      <article className="panel stat-card wide">
        <p>Latest run</p>
        <strong>{latest?.display_name ?? 'No runs yet'}</strong>
        <span>{latest?.latest_message ?? 'Create your first experiment to populate the control center.'}</span>
      </article>
    </section>
  )
}
