import { expect, test, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

import { RunsTable } from './RunsTable'
import type { RunSummary } from '../types'

const sampleRuns: RunSummary[] = [
  {
    run_id: 'run-1',
    display_name: 'Churn baseline',
    preset_key: 'customer-churn',
    dataset_name: 'Synthetic Customer Churn',
    task_type: 'classification',
    model_name: 'Gradient Boosting Classifier',
    status: 'completed',
    seed: 13,
    latest_message: 'done',
    created_at: new Date().toISOString(),
    started_at: new Date().toISOString(),
    finished_at: new Date().toISOString(),
    scorecard: { f1: 0.88 },
  },
]

test('renders rows and toggles compare state', () => {
  const handleSelect = vi.fn()
  const handleToggle = vi.fn()

  render(
    <RunsTable
      runs={sampleRuns}
      selectedRunId={null}
      compareIds={[]}
      onSelect={handleSelect}
      onToggleCompare={handleToggle}
    />,
  )

  fireEvent.click(screen.getByText('Churn baseline'))
  expect(handleSelect).toHaveBeenCalledWith('run-1')

  fireEvent.click(screen.getByLabelText('Compare Churn baseline'))
  expect(handleToggle).toHaveBeenCalledWith('run-1')
})
