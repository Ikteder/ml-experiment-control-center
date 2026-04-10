import { useEffect, useState } from 'react'

import type { LogEvent } from '../types'
import { apiBaseUrl } from '../api/client'

export function useEventSource(runId: string | null): LogEvent[] {
  const [events, setEvents] = useState<LogEvent[]>([])

  useEffect(() => {
    if (!runId) {
      setEvents([])
      return
    }

    setEvents([])
    const eventSource = new EventSource(`${apiBaseUrl()}/runs/${runId}/logs`)
    eventSource.onmessage = (event) => {
      const payload = JSON.parse(event.data) as LogEvent
      setEvents((current) => [...current.slice(-99), payload])
    }
    eventSource.onerror = () => {
      eventSource.close()
    }

    return () => {
      eventSource.close()
    }
  }, [runId])

  return events
}
