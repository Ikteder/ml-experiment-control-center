import type { Artifact } from '../types'

const API_ORIGIN = import.meta.env.VITE_API_ORIGIN ?? 'http://127.0.0.1:8000'

export function ArtifactBrowser({ artifacts }: { artifacts: Artifact[] }) {
  return (
    <section className="panel artifact-panel">
      <div className="section-heading">
        <p className="eyebrow">Inspect</p>
        <h2>Artifacts</h2>
      </div>
      <div className="artifact-list">
        {artifacts.length === 0 ? (
          <p className="empty-copy">Artifacts appear here once a run produces reports, plots, or CSV outputs.</p>
        ) : (
          artifacts.map((artifact) => (
            <a
              key={artifact.name}
              className="artifact-row"
              href={`${API_ORIGIN}${artifact.download_url}`}
              target="_blank"
              rel="noreferrer"
            >
              <div>
                <strong>{artifact.name}</strong>
                <p>{artifact.artifact_type}</p>
              </div>
              <span>Open</span>
            </a>
          ))
        )}
      </div>
    </section>
  )
}
