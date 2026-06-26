import { useRef, useEffect } from 'react'

import IoTSimulator from '../components/IoTSimulator'

const IoT = () => {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (containerRef.current) {
    }
  }, [])

  return (
    <div ref={containerRef} className="space-y-6">
      <IoTSimulator />
    </div>
  )
}

export default IoT
