import { useTranslation } from 'react-i18next'
import { useRef, useEffect } from 'react'

import TrafficVisualizer from '../components/TrafficVisualizer'

const Traffic = () => {
  const { t } = useTranslation()
  const headerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (headerRef.current) {
    }
  }, [])

  return (
    <div className="h-full">
      <div ref={headerRef} className="mb-4">
        <h1 className="text-2xl font-bold">
          {t('nav.traffic', 'Traffic Visualization')}
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Real-time packet flow animation with protocol filtering and speed control
        </p>
      </div>

      <TrafficVisualizer />
    </div>
  )
}

export default Traffic
