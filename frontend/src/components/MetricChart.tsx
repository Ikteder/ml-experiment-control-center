import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { MetricPoint, TaskType } from '../types'

function metricKeys(taskType: TaskType) {
  return taskType === 'classification'
    ? ['loss', 'accuracy', 'f1', 'auroc']
    : ['loss', 'mae', 'rmse', 'r2']
}

export function MetricChart({ points, taskType }: { points: MetricPoint[]; taskType: TaskType }) {
  const keys = metricKeys(taskType)

  return (
    <section className="panel chart-panel">
      <div className="section-heading">
        <p className="eyebrow">Analyze</p>
        <h2>Metric history</h2>
      </div>
      <div className="chart-shell">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={points}>
            <CartesianGrid strokeDasharray="3 3" stroke="#31435b" />
            <XAxis dataKey="step" stroke="#a7b4c5" />
            <YAxis stroke="#a7b4c5" />
            <Tooltip />
            {keys.map((metric, index) => (
              <Line
                key={metric}
                dataKey={metric}
                dot={false}
                stroke={['#f4a261', '#2a9d8f', '#ffd166', '#89c2d9'][index % 4]}
                strokeWidth={2.4}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
