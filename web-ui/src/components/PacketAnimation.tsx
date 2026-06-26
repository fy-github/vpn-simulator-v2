import { useRef, useEffect, useCallback, useState } from 'react'

interface Packet {
  id: string
  timestamp: string
  protocol: string
  src_ip: string
  dst_ip: string
  src_port: number
  dst_port: number
  size: number
  ttl: number
  flags: string[]
  payload_preview: string
}

interface Node {
  id: string
  x: number
  y: number
  label: string
  type: 'router' | 'server' | 'client' | 'firewall'
}

interface Edge {
  id: string
  source: string
  target: string
}

interface AnimatedPacket {
  id: string
  protocol: string
  sourceId: string
  targetId: string
  progress: number
  speed: number
  color: string
  size: number
}

interface PacketAnimationProps {
  packets: Packet[]
  nodes: Node[]
  edges: Edge[]
  speed: number
  paused: boolean
  width?: number
  height?: number
}

const PROTOCOL_COLORS: Record<string, string> = {
  tcp: '#3b82f6', // blue
  udp: '#22c55e', // green
  icmp: '#eab308', // yellow
  arp: '#ef4444', // red
}

const NODE_COLORS: Record<string, string> = {
  router: '#8b5cf6',
  server: '#06b6d4',
  client: '#f59e0b',
  firewall: '#ef4444',
}

export default function PacketAnimation({
  packets,
  nodes,
  edges,
  speed,
  paused,
  width = 800,
  height = 600,
}: PacketAnimationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>()
  const animatedPacketsRef = useRef<AnimatedPacket[]>([])
  const lastPacketIndexRef = useRef(0)
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)

  const nodeMap = useRef(new Map<string, Node>())
  const edgeMap = useRef(new Map<string, Edge>())

  // Build node and edge maps
  useEffect(() => {
    nodeMap.current.clear()
    nodes.forEach((node) => nodeMap.current.set(node.id, node))

    edgeMap.current.clear()
    edges.forEach((edge) => {
      edgeMap.current.set(edge.id, edge)
      edgeMap.current.set(`${edge.source}-${edge.target}`, edge)
    })
  }, [nodes, edges])

  // Find path between two nodes
  const findPath = useCallback((sourceId: string, targetId: string): string[] => {
    // Simple BFS to find path
    const visited = new Set<string>()
    const queue: string[][] = [[sourceId]]

    while (queue.length > 0) {
      const path = queue.shift()!
      const current = path[path.length - 1]

      if (current === targetId) {
        return path
      }

      if (visited.has(current)) continue
      visited.add(current)

      // Find connected nodes
      edges.forEach((edge) => {
        let next: string | null = null
        if (edge.source === current && !visited.has(edge.target)) {
          next = edge.target
        } else if (edge.target === current && !visited.has(edge.source)) {
          next = edge.source
        }

        if (next) {
          queue.push([...path, next])
        }
      })
    }

    return [sourceId, targetId]
  }, [edges])

  // Create animated packet from packet data
  const createAnimatedPacket = useCallback((packet: Packet): AnimatedPacket | null => {
    // Find source and target nodes
    const sourceNode = nodes.find((n) =>
      n.type === 'client' || n.type === 'server'
    )
    const targetNode = nodes.find((n) =>
      (n.type === 'server' || n.type === 'router') && n.id !== sourceNode?.id
    )

    if (!sourceNode || !targetNode) return null

    const path = findPath(sourceNode.id, targetNode.id)
    if (path.length < 2) return null

    return {
      id: packet.id,
      protocol: packet.protocol,
      sourceId: path[0],
      targetId: path[1],
      progress: 0,
      speed: (0.5 + Math.random() * 1.5) * speed,
      color: PROTOCOL_COLORS[packet.protocol] || '#ffffff',
      size: Math.max(4, Math.min(12, packet.size / 100)),
    }
  }, [nodes, speed, findPath])

  // Update animation state
  const updateAnimation = useCallback(() => {
    if (paused) return

    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Update existing packets
    animatedPacketsRef.current = animatedPacketsRef.current
      .map((packet) => ({
        ...packet,
        progress: packet.progress + packet.speed * 0.02,
      }))
      .filter((packet) => packet.progress < 1)

    // Add new packets from input
    if (packets.length > 0) {
      const newIndex = Math.min(
        lastPacketIndexRef.current + Math.ceil(speed),
        packets.length
      )

      for (let i = lastPacketIndexRef.current; i < newIndex; i++) {
        const packet = packets[i % packets.length]
        const animated = createAnimatedPacket(packet)
        if (animated) {
          animatedPacketsRef.current.push(animated)
        }
      }

      lastPacketIndexRef.current = newIndex % packets.length
    }

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Draw background
    ctx.fillStyle = '#0f172a'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    // Draw grid
    ctx.strokeStyle = '#1e293b'
    ctx.lineWidth = 1
    for (let x = 0; x < canvas.width; x += 40) {
      ctx.beginPath()
      ctx.moveTo(x, 0)
      ctx.lineTo(x, canvas.height)
      ctx.stroke()
    }
    for (let y = 0; y < canvas.height; y += 40) {
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(canvas.width, y)
      ctx.stroke()
    }

    // Draw edges
    edges.forEach((edge) => {
      const source = nodeMap.current.get(edge.source)
      const target = nodeMap.current.get(edge.target)

      if (source && target) {
        ctx.beginPath()
        ctx.moveTo(source.x, source.y)
        ctx.lineTo(target.x, target.y)
        ctx.strokeStyle = '#334155'
        ctx.lineWidth = 2
        ctx.stroke()
      }
    })

    // Draw nodes
    nodes.forEach((node) => {
      const isHovered = hoveredNode === node.id
      const radius = isHovered ? 28 : 24
      const color = NODE_COLORS[node.type] || '#64748b'

      // Node glow
      if (isHovered) {
        const gradient = ctx.createRadialGradient(
          node.x, node.y, radius,
          node.x, node.y, radius * 2
        )
        gradient.addColorStop(0, color + '40')
        gradient.addColorStop(1, color + '00')
        ctx.fillStyle = gradient
        ctx.beginPath()
        ctx.arc(node.x, node.y, radius * 2, 0, Math.PI * 2)
        ctx.fill()
      }

      // Node circle
      ctx.beginPath()
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2)
      ctx.fillStyle = isHovered ? color : color + 'cc'
      ctx.fill()
      ctx.strokeStyle = color
      ctx.lineWidth = 2
      ctx.stroke()

      // Node label
      ctx.fillStyle = '#ffffff'
      ctx.font = isHovered ? 'bold 12px sans-serif' : '11px sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(node.label, node.x, node.y)

      // Node type indicator
      ctx.fillStyle = '#94a3b8'
      ctx.font = '9px sans-serif'
      ctx.fillText(node.type, node.x, node.y + radius + 12)
    })

    // Draw animated packets
    animatedPacketsRef.current.forEach((packet) => {
      const source = nodeMap.current.get(packet.sourceId)
      const target = nodeMap.current.get(packet.targetId)

      if (source && target) {
        const x = source.x + (target.x - source.x) * packet.progress
        const y = source.y + (target.y - source.y) * packet.progress

        // Packet trail
        const trailLength = 5
        for (let i = 0; i < trailLength; i++) {
          const trailProgress = Math.max(0, packet.progress - i * 0.05)
          const trailX = source.x + (target.x - source.x) * trailProgress
          const trailY = source.y + (target.y - source.y) * trailProgress
          const alpha = (1 - i / trailLength) * 0.3

          ctx.beginPath()
          ctx.arc(trailX, trailY, packet.size * 0.8, 0, Math.PI * 2)
          ctx.fillStyle = packet.color + Math.floor(alpha * 255).toString(16).padStart(2, '0')
          ctx.fill()
        }

        // Packet glow
        const gradient = ctx.createRadialGradient(
          x, y, packet.size,
          x, y, packet.size * 3
        )
        gradient.addColorStop(0, packet.color + '40')
        gradient.addColorStop(1, packet.color + '00')
        ctx.fillStyle = gradient
        ctx.beginPath()
        ctx.arc(x, y, packet.size * 3, 0, Math.PI * 2)
        ctx.fill()

        // Packet dot
        ctx.beginPath()
        ctx.arc(x, y, packet.size, 0, Math.PI * 2)
        ctx.fillStyle = packet.color
        ctx.fill()

        // Protocol label
        ctx.fillStyle = '#ffffff'
        ctx.font = 'bold 8px sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(packet.protocol.toUpperCase(), x, y)
      }
    })

    // Draw stats overlay
    ctx.fillStyle = '#0f172a' + 'cc'
    ctx.fillRect(10, 10, 160, 60)
    ctx.strokeStyle = '#334155'
    ctx.lineWidth = 1
    ctx.strokeRect(10, 10, 160, 60)

    ctx.fillStyle = '#e2e8f0'
    ctx.font = 'bold 11px sans-serif'
    ctx.textAlign = 'left'
    ctx.fillText('Active Packets', 20, 30)

    ctx.fillStyle = '#94a3b8'
    ctx.font = '10px sans-serif'
    ctx.fillText(`Count: ${animatedPacketsRef.current.length}`, 20, 48)
    ctx.fillText(`Speed: ${speed}x`, 20, 62)

  }, [paused, packets, nodes, edges, speed, hoveredNode, createAnimatedPacket])

  // Animation loop
  useEffect(() => {
    const animate = () => {
      updateAnimation()
      animationRef.current = requestAnimationFrame(animate)
    }

    animationRef.current = requestAnimationFrame(animate)

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [updateAnimation])

  // Handle mouse move for node hovering
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    let foundNode: string | null = null
    nodes.forEach((node) => {
      const dx = node.x - x
      const dy = node.y - y
      const distance = Math.sqrt(dx * dx + dy * dy)
      if (distance < 24) {
        foundNode = node.id
      }
    })

    setHoveredNode(foundNode)
  }, [nodes])

  // Handle resize
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    canvas.width = width
    canvas.height = height
  }, [width, height])

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="rounded-lg border border-dark-700 bg-dark-900 cursor-crosshair"
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setHoveredNode(null)}
    />
  )
}
