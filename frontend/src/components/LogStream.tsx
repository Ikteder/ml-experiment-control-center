import type { LogEvent } from '../types'

export function LogStream({ events }: { events: LogEvent[] }) {
  return (
    <section className="panel logs-panel">
      <div className="section-heading">
        <p className="eyebrow">Observe</p>
        <h2>Structured logs</h2>
      </div>
      <div className="log-shell">
        {events.length === 0 ? (
          <p className="empty-copy">Select or launch a run to stream live logs here.</p>
        ) : (
          events.map((event) => (
            <article key={`${event.timestamp}-${event.message}`} className="log-entry">
              <header>
                <span className="log-level">{event.level}</span>
                <span>{new Date(event.timestamp).toLocaleTimeString()}</span>
              </header>
              <p>{event.message}</p>
              {Object.keys(event.payload).length > 0 ? (
                <pre>{JSON.stringify(event.payload, null, 2)}</pre>
              ) : null}
            </article>
          ))
        )}
      </div>
    </section>
  )
}
