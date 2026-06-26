import { useTranslation } from 'react-i18next'
import { useRef, useEffect } from 'react'

import PerformanceCharts from '../components/PerformanceCharts'

const Metrics = () => {
  const { t } = useTranslation()
  const headerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (headerRef.current) {
    }
  }, [])

  return (
    <div className="space-y-6">
      <div ref={headerRef} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t('nav.metrics', 'Performance Metrics')}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time performance visualization with throughput, latency, packet loss, and connection monitoring
          </p>
        </div>
      </div>

      <PerformanceCharts />
    </div>
  )
}

export default Metrics
