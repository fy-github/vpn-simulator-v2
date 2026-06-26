import { useRef, useEffect } from 'react'

import ProtocolAnalyzer from '../components/ProtocolAnalyzer'

const DPI = () => {
  const headerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (headerRef.current) {
    }
  }, [])

  return (
    <div className="space-y-6">
      <div ref={headerRef} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">深度包检测 (DPI)</h1>
          <p className="text-sm text-muted-foreground mt-1">
            协议识别、流量分类与异常检测
          </p>
        </div>
      </div>
      <ProtocolAnalyzer />
    </div>
  )
}

export default DPI
