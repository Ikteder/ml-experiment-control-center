import { formatMetric } from '../lib/format'
import type { RunSummary } from '../types'

export function CompareStrip({ runs }: { runs: RunSummary[] }) {
  if (runs.length < 2) {
    return (
      <section className="panel compare-panel muted-panel">
        <div className="section-heading">
          <p className="eyebrow">Compare</p>
          <h2>Side-by-side review</h2>
        </div>
        <p className="empty-copy">Select two runs in the table to compare scorecards, presets, and status at a glance.</p>
      </section>
    )
  }

  return (
    <section className="panel compare-panel">
      <div className="section-heading">
        <p className="eyebrow">Compare</p>
        <h2>Side-by-side review</h2>
      </div>
      <div className="compare-grid">
        {runs.map((run) => (
          <article key={run.run_id} className="compare-card">
            <p className="compare-kicker">{run.preset_key}</p>
            <h3>{run.display_name}</h3>
            <dl>
              {Object.entries(run.scorecard).map(([key, value]) => (
                <div key={key}>
                  <dt>{key}</dt>
                  <dd>{formatMetric(value)}</dd>
                </div>
              ))}
            </dl>
          </article>
        ))}
      </div>
    </section>
  )
}
