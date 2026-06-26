import { useTranslation } from 'react-i18next'
import { useRef, useEffect } from 'react'

import ProtocolComparator from '../components/ProtocolComparator'

const Comparison = () => {
  const { t } = useTranslation()
  const headerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (headerRef.current) {
    }
  }, [])

  return (
    <div className="h-[calc(100vh-7rem)] flex flex-col">
      <div ref={headerRef} className="mb-4">
        <h2 className="text-xl font-bold">{t('comparison.title')}</h2>
        <p className="text-sm text-muted-foreground mt-1">{t('comparison.subtitle')}</p>
      </div>
      <div className="flex-1 rounded-lg border bg-card overflow-hidden">
        <ProtocolComparator />
      </div>
    </div>
  )
}

export default Comparison
