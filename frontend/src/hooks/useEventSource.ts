import { useEffect, useState } from 'react'

import type { LogEvent } from '../types'
import { apiBaseUrl } from '../api/client'

export function useEventSource(runId: string | null): LogEvent[] {
  const [stream, setStream] = useState<{ runId: string | null; events: LogEvent[] }>({ runId: null, events: [] })

  useEffect(() => {
    if (!runId) return
    const eventSource = new EventSource(`${apiBaseUrl()}/runs/${runId}/logs`)
    eventSource.onmessage = (event) => {
      const payload = JSON.parse(event.data) as LogEvent
      setStream((current) => ({
        runId,
        events: [...(current.runId === runId ? current.events.slice(-99) : []), payload],
      }))
    }
    eventSource.onerror = () => {
      eventSource.close()
    }

    return () => {
      eventSource.close()
    }
  }, [runId])

  return stream.runId === runId ? stream.events : []
}
