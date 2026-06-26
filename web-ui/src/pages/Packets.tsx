import { useRef, useEffect } from 'react'

import PacketViewer from '../components/PacketViewer'

const Packets = () => {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (containerRef.current) {
    }
  }, [])

  return (
    <div ref={containerRef} className="h-full">
      <PacketViewer />
    </div>
  )
}

export default Packets
