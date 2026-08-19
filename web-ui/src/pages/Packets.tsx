import { useRef } from 'react'

import PacketViewer from '../components/PacketViewer'

const Packets = () => {
  const containerRef = useRef<HTMLDivElement>(null)

  return (
    <div ref={containerRef} className="h-full">
      <PacketViewer />
    </div>
  )
}

export default Packets
