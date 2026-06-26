import { useTranslation } from 'react-i18next'
import { useRef, useEffect } from 'react'

import VoiceSimulator from '../components/VoiceSimulator'

const Voice = () => {
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
          {t('nav.voice', 'Voice Simulator')}
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          VoIP call simulation with codec support and real-time quality metrics
        </p>
      </div>

      <VoiceSimulator />
    </div>
  )
}

export default Voice
