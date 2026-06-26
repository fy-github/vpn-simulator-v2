import { useRef, useEffect } from 'react'

import ObfuscationTester from '../components/ObfuscationTester'

const Obfuscation = () => {
  const headerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (headerRef.current) {
    }
  }, [])

  return (
    <div className="space-y-6">
      <div ref={headerRef} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">流量混淆测试</h1>
          <p className="text-muted-foreground mt-1">测试 VPN 流量混淆技术对抗 DPI 检测的效果</p>
        </div>
      </div>
      <ObfuscationTester />
    </div>
  )
}

export default Obfuscation
