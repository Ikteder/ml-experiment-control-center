import { useState } from 'react'

import type { LaunchRunRequest, PresetSummary } from '../types'

interface RunLauncherProps {
  presets: PresetSummary[]
  onLaunch: (payload: LaunchRunRequest) => Promise<void>
}

export function RunLauncher({ presets, onLaunch }: RunLauncherProps) {
  const [selectedPreset, setSelectedPreset] = useState<string>(presets[0]?.key ?? '')
  const [displayName, setDisplayName] = useState('')
  const [epochs, setEpochs] = useState(14)
  const [seed, setSeed] = useState(42)
  const [configOverride, setConfigOverride] = useState<Record<string, unknown> | null>(null)

  async function handleSubmit() {
    await onLaunch({
      preset_key: selectedPreset,
      display_name: displayName || undefined,
      epochs,
      seed,
      config: configOverride ?? undefined,
    })
    setDisplayName('')
  }

  function handleFileUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    file.text().then((text) => {
      try {
        const parsed = JSON.parse(text) as Record<string, unknown>
        setConfigOverride(parsed)
        if (typeof parsed.preset_key === 'string') {
          setSelectedPreset(parsed.preset_key)
        }
      } catch {
        setConfigOverride(null)
      }
    })
  }

  const preset = presets.find((item) => item.key === selectedPreset)

  return (
    <section className="panel launcher-panel">
      <div className="section-heading">
        <p className="eyebrow">Launch</p>
        <h2>Run composer</h2>
      </div>
      <label className="field">
        <span>Preset</span>
        <select value={selectedPreset} onChange={(event) => setSelectedPreset(event.target.value)}>
          {presets.map((item) => (
            <option key={item.key} value={item.key}>
              {item.display_name}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>Display name</span>
        <input
          value={displayName}
          placeholder="Optional experiment label"
          onChange={(event) => setDisplayName(event.target.value)}
        />
      </label>
      <div className="field-row">
        <label className="field">
          <span>Epochs</span>
          <input
            type="number"
            min={4}
            max={40}
            value={epochs}
            onChange={(event) => setEpochs(Number(event.target.value))}
          />
        </label>
        <label className="field">
          <span>Seed</span>
          <input
            type="number"
            value={seed}
            onChange={(event) => setSeed(Number(event.target.value))}
          />
        </label>
      </div>
      <label className="field">
        <span>Config file</span>
        <input type="file" accept=".json,application/json" onChange={handleFileUpload} />
      </label>
      <div className="preset-card">
        <p className="preset-title">{preset?.display_name}</p>
        <p>{preset?.description}</p>
      </div>
      <button className="primary-button" onClick={handleSubmit}>
        Launch experiment
      </button>
    </section>
  )
}
