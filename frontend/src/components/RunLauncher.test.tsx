import { afterEach, expect, test, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'

import { RunLauncher } from './RunLauncher'
import type { PresetSummary } from '../types'

const presets: PresetSummary[] = [
  {
    key: 'customer-churn',
    display_name: 'Customer Churn Baseline',
    description: 'Synthetic churn fixture',
    dataset_name: 'Synthetic Customer Churn',
    task_type: 'classification',
    model_name: 'Gradient Boosting Classifier',
    config: {},
  },
  {
    key: 'demand-forecasting',
    display_name: 'Demand Forecasting Regressor',
    description: 'Chronological demand fixture',
    dataset_name: 'Synthetic Retail Demand',
    task_type: 'regression',
    model_name: 'Gradient Boosting Regressor',
    config: {},
  },
]

afterEach(cleanup)

test('loads a JSON override and launches the selected workload', async () => {
  const onLaunch = vi.fn().mockResolvedValue(undefined)
  render(<RunLauncher presets={presets} onLaunch={onLaunch} />)

  fireEvent.change(screen.getByLabelText('Display name'), { target: { value: 'Forecast review' } })
  fireEvent.change(screen.getByLabelText('Epochs'), { target: { value: '12' } })
  fireEvent.change(screen.getByLabelText('Seed'), { target: { value: '77' } })
  const file = new File(['{"preset_key":"demand-forecasting","noise":8}'], 'forecast.json', {
    type: 'application/json',
  })
  fireEvent.change(screen.getByLabelText('Config file'), { target: { files: [file] } })

  await screen.findByText('Loaded config: forecast.json')
  fireEvent.click(screen.getByRole('button', { name: 'Launch experiment' }))

  await waitFor(() => {
    expect(onLaunch).toHaveBeenCalledWith({
      preset_key: 'demand-forecasting',
      display_name: 'Forecast review',
      epochs: 12,
      seed: 77,
      config: { preset_key: 'demand-forecasting', noise: 8 },
    })
  })
  expect(await screen.findByText('Experiment queued successfully.')).toBeInTheDocument()
})

test('shows invalid JSON feedback without launching', async () => {
  const onLaunch = vi.fn()
  render(<RunLauncher presets={presets} onLaunch={onLaunch} />)
  const file = new File(['not json'], 'broken.json', { type: 'application/json' })
  fireEvent.change(screen.getByLabelText('Config file'), { target: { files: [file] } })
  expect(await screen.findByText('Config file is not valid JSON.')).toBeInTheDocument()
  expect(onLaunch).not.toHaveBeenCalled()
})
