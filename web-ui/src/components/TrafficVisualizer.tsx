import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import PacketAnimation from './PacketAnimation'
import { ArrowRightIcon } from './Icons'

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

interface TrafficStats {
  capturing: boolean
  statistics: {
    packets_per_second: number
    bytes_per_second: number
    total_packets: number
    total_bytes: number
    protocol_counts: Record<string, number>
    active_flows: number
    capture_duration: number
  }
  timestamp: string
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

const PROTOCOL_COLORS: Record<string, string> = {
  tcp: 'text-blue-400',
  udp: 'text-green-400',
  icmp: 'text-yellow-400',
  arp: 'text-red-400',
}

const PROTOCOL_BG_COLORS: Record<string, string> = {
  tcp: 'bg-blue-500/20',
  udp: 'bg-green-500/20',
  icmp: 'bg-yellow-500/20',
  arp: 'bg-red-500/20',
}

export default function TrafficVisualizer() {
  const { i18n } = useTranslation()
  const isZh = i18n.language === 'zh-CN'

  const [packets, setPackets] = useState<Packet[]>([])
  const [stats, setStats] = useState<TrafficStats | null>(null)
  const [capturing, setCapturing] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [paused, setPaused] = useState(false)
  const [selectedProtocols, setSelectedProtocols] = useState<string[]>(['tcp', 'udp', 'icmp', 'arp'])
  const [error, setError] = useState<string | null>(null)
  const [connected, setConnected] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const statsIntervalRef = useRef<ReturnType<typeof setInterval>>()

  // Default topology nodes
  const [nodes] = useState<Node[]>([
    { id: 'client1', x: 100, y: 200, label: 'Client 1', type: 'client' },
    { id: 'client2', x: 100, y: 400, label: 'Client 2', type: 'client' },
    { id: 'firewall', x: 300, y: 300, label: 'Firewall', type: 'firewall' },
    { id: 'router', x: 500, y: 300, label: 'Router', type: 'router' },
    { id: 'server', x: 700, y: 300, label: 'VPN Server', type: 'server' },
  ])

  const [edges] = useState<Edge[]>([
    { id: 'e1', source: 'client1', target: 'firewall' },
    { id: 'e2', source: 'client2', target: 'firewall' },
    { id: 'e3', source: 'firewall', target: 'router' },
    { id: 'e4', source: 'router', target: 'server' },
  ])

  // Connect to WebSocket
  const intentionalCloseRef = useRef(false)

  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    intentionalCloseRef.current = false
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/v1/traffic/stream`

    try {
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        setConnected(true)
        setError(null)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type !== 'keepalive') {
            setPackets((prev) => {
              const newPackets = [...prev, data]
              return newPackets.slice(-200) // Keep last 200 packets
            })
          }
        } catch (err) {
          console.error('Failed to parse packet:', err)
        }
      }

      ws.onerror = () => {
        if (!intentionalCloseRef.current) {
          setError(isZh ? 'WebSocket 连接错误' : 'WebSocket connection error')
        }
        setConnected(false)
      }

      ws.onclose = () => {
        setConnected(false)
        // Only reconnect if not intentionally closed
        if (!intentionalCloseRef.current) {
          setTimeout(connectWebSocket, 3000)
        }
      }

      wsRef.current = ws
    } catch (err) {
      setError(isZh ? '无法连接到流量服务' : 'Cannot connect to traffic service')
    }
  }, [isZh])

  // Disconnect WebSocket
  const disconnectWebSocket = useCallback(() => {
    intentionalCloseRef.current = true
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  // Fetch statistics
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/traffic/statistics')
      if (response.ok) {
        const data = await response.json()
        setStats(data)
        setCapturing(data.capturing)
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }, [])

  // Start capture
  const handleStartCapture = useCallback(async () => {
    try {
      setError(null)
      const response = await fetch('/api/v1/traffic/capture', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ protocols: selectedProtocols }),
      })

      if (response.ok) {
        setCapturing(true)
        setPackets([])
        connectWebSocket()
      } else {
        const data = await response.json()
        setError(data.detail || (isZh ? '启动捕获失败' : 'Failed to start capture'))
      }
    } catch (err) {
      setError(isZh ? '无法连接到服务器' : 'Cannot connect to server')
    }
  }, [selectedProtocols, connectWebSocket, isZh])

  // Stop capture
  const handleStopCapture = useCallback(async () => {
    try {
      setError(null)
      const response = await fetch('/api/v1/traffic/stop', {
        method: 'POST',
      })

      if (response.ok) {
        setCapturing(false)
        disconnectWebSocket()
        await fetchStats()
      }
    } catch (err) {
      setError(isZh ? '停止捕获失败' : 'Failed to stop capture')
    }
  }, [disconnectWebSocket, fetchStats, isZh])

  // Toggle protocol filter
  const toggleProtocol = useCallback((protocol: string) => {
    setSelectedProtocols((prev) =>
      prev.includes(protocol)
        ? prev.filter((p) => p !== protocol)
        : [...prev, protocol]
    )
  }, [])

  // Format bytes
  const formatBytes = useCallback((bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }, [])

  // Format duration
  const formatDuration = useCallback((seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }, [])

  // Setup and cleanup
  useEffect(() => {
    fetchStats()

    statsIntervalRef.current = setInterval(fetchStats, 2000)

    return () => {
      if (statsIntervalRef.current) {
        clearInterval(statsIntervalRef.current)
      }
      disconnectWebSocket()
    }
  }, [fetchStats, disconnectWebSocket])

  return (
    <div className="flex flex-col h-full bg-dark-900">
      {/* Header */}
      <div className="px-4 py-3 border-b border-dark-700 bg-dark-800/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <h2 className="text-lg font-bold text-white">
              {isZh ? '流量可视化' : 'Traffic Visualizer'}
            </h2>
            <div className={`flex items-center space-x-1 px-2 py-0.5 rounded text-xs ${
              connected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
            }`}>
              <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'}`} />
              <span>{connected ? (isZh ? '已连接' : 'Connected') : (isZh ? '未连接' : 'Disconnected')}</span>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {/* Speed Control */}
            <div className="flex items-center space-x-1 bg-dark-700 rounded-lg p-1">
              <button
                onClick={() => setSpeed(0.5)}
                className={`px-2 py-1 text-xs rounded ${
                  speed === 0.5
                    ? 'bg-neon-cyan text-dark-900 font-bold'
                    : 'text-dark-300 hover:text-white'
                }`}
              >
                0.5x
              </button>
              <button
                onClick={() => setSpeed(1)}
                className={`px-2 py-1 text-xs rounded ${
                  speed === 1
                    ? 'bg-neon-cyan text-dark-900 font-bold'
                    : 'text-dark-300 hover:text-white'
                }`}
              >
                1x
              </button>
              <button
                onClick={() => setSpeed(2)}
                className={`px-2 py-1 text-xs rounded ${
                  speed === 2
                    ? 'bg-neon-cyan text-dark-900 font-bold'
                    : 'text-dark-300 hover:text-white'
                }`}
              >
                2x
              </button>
            </div>

            {/* Pause/Resume */}
            <button
              onClick={() => setPaused(!paused)}
              className={`px-3 py-1.5 text-xs font-medium rounded ${
                paused
                  ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                  : 'bg-dark-700 text-dark-300 border border-dark-600'
              }`}
            >
              {paused ? (isZh ? '继续' : 'Resume') : (isZh ? '暂停' : 'Pause')}
            </button>

            {/* Start/Stop Capture */}
            {capturing ? (
              <button
                onClick={handleStopCapture}
                className="px-3 py-1.5 text-xs font-medium rounded bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30"
              >
                {isZh ? '停止捕获' : 'Stop Capture'}
              </button>
            ) : (
              <button
                onClick={handleStartCapture}
                className="px-3 py-1.5 text-xs font-medium rounded bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30"
              >
                {isZh ? '开始捕获' : 'Start Capture'}
              </button>
            )}
          </div>
        </div>

        {/* Protocol Filters */}
        <div className="mt-2 flex items-center space-x-2">
          <span className="text-xs text-dark-400">{isZh ? '协议过滤:' : 'Protocols:'}</span>
          {['tcp', 'udp', 'icmp', 'arp'].map((protocol) => (
            <button
              key={protocol}
              onClick={() => toggleProtocol(protocol)}
              className={`px-2 py-1 text-xs rounded border ${
                selectedProtocols.includes(protocol)
                  ? `${PROTOCOL_BG_COLORS[protocol]} ${PROTOCOL_COLORS[protocol]} border-current`
                  : 'bg-dark-700 text-dark-400 border-dark-600'
              }`}
            >
              {protocol.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="px-4 py-2 bg-red-900/30 border-b border-red-800 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Animation Area */}
        <div className="flex-1 p-4">
          <PacketAnimation
            packets={packets}
            nodes={nodes}
            edges={edges}
            speed={speed}
            paused={paused}
            capturing={capturing}
            width={800}
            height={500}
          />
        </div>

        {/* Stats Panel */}
        <div className="w-80 border-l border-dark-700 bg-dark-800/30 overflow-y-auto">
          {/* Live Statistics */}
          <div className="p-4 border-b border-dark-700">
            <h3 className="text-sm font-semibold text-white mb-3">
              {isZh ? '实时统计' : 'Live Statistics'}
            </h3>

            {stats ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-dark-700/50 rounded-lg p-2">
                    <div className="text-xs text-dark-400">{isZh ? '每秒包数' : 'PPS'}</div>
                    <div className="text-lg font-bold text-neon-cyan">
                      {stats.statistics.packets_per_second}
                    </div>
                  </div>
                  <div className="bg-dark-700/50 rounded-lg p-2">
                    <div className="text-xs text-dark-400">{isZh ? '每秒字节' : 'BPS'}</div>
                    <div className="text-lg font-bold text-neon-green">
                      {formatBytes(stats.statistics.bytes_per_second)}
                    </div>
                  </div>
                </div>

                <div className="bg-dark-700/50 rounded-lg p-2">
                  <div className="text-xs text-dark-400">{isZh ? '总数据包' : 'Total Packets'}</div>
                  <div className="text-lg font-bold text-white">
                    {stats.statistics.total_packets.toLocaleString()}
                  </div>
                </div>

                <div className="bg-dark-700/50 rounded-lg p-2">
                  <div className="text-xs text-dark-400">{isZh ? '总字节数' : 'Total Bytes'}</div>
                  <div className="text-lg font-bold text-white">
                    {formatBytes(stats.statistics.total_bytes)}
                  </div>
                </div>

                <div className="bg-dark-700/50 rounded-lg p-2">
                  <div className="text-xs text-dark-400">{isZh ? '活跃流' : 'Active Flows'}</div>
                  <div className="text-lg font-bold text-purple-400">
                    {stats.statistics.active_flows}
                  </div>
                </div>

                <div className="bg-dark-700/50 rounded-lg p-2">
                  <div className="text-xs text-dark-400">{isZh ? '捕获时长' : 'Duration'}</div>
                  <div className="text-lg font-bold text-yellow-400">
                    {formatDuration(stats.statistics.capture_duration)}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-dark-400 text-sm">
                {isZh ? '无数据' : 'No data'}
              </div>
            )}
          </div>

          {/* Protocol Distribution */}
          <div className="p-4 border-b border-dark-700">
            <h3 className="text-sm font-semibold text-white mb-3">
              {isZh ? '协议分布' : 'Protocol Distribution'}
            </h3>

            {stats?.statistics.protocol_counts ? (
              <div className="space-y-2">
                {Object.entries(stats.statistics.protocol_counts).map(([protocol, count]) => {
                  const total = Object.values(stats.statistics.protocol_counts).reduce((a, b) => a + b, 0)
                  const percentage = total > 0 ? (count / total * 100).toFixed(1) : '0'

                  return (
                    <div key={protocol} className="flex items-center space-x-2">
                      <span className={`text-xs font-medium w-12 ${PROTOCOL_COLORS[protocol]}`}>
                        {protocol.toUpperCase()}
                      </span>
                      <div className="flex-1 bg-dark-700 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            protocol === 'tcp' ? 'bg-blue-500' :
                            protocol === 'udp' ? 'bg-green-500' :
                            protocol === 'icmp' ? 'bg-yellow-500' :
                            'bg-red-500'
                          }`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                      <span className="text-xs text-dark-400 w-16 text-right">
                        {count} ({percentage}%)
                      </span>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-dark-400 text-sm">
                {isZh ? '无数据' : 'No data'}
              </div>
            )}
          </div>

          {/* Recent Packets */}
          <div className="p-4">
            <h3 className="text-sm font-semibold text-white mb-3">
              {isZh ? '最近数据包' : 'Recent Packets'}
            </h3>

            <div className="space-y-1 max-h-60 overflow-y-auto">
              {packets.slice(-20).reverse().map((packet) => (
                <div
                  key={packet.id}
                  className="flex items-center space-x-2 p-1.5 bg-dark-700/30 rounded text-xs"
                >
                  <span className={`font-medium ${PROTOCOL_COLORS[packet.protocol]}`}>
                    {packet.protocol.toUpperCase()}
                  </span>
                  <span className="text-dark-400 font-mono truncate flex-1">
                    {packet.src_ip}:{packet.src_port} <ArrowRightIcon className="w-4 h-4 inline" /> {packet.dst_ip}:{packet.dst_port}
                  </span>
                  <span className="text-dark-500">
                    {packet.size}B
                  </span>
                </div>
              ))}

              {packets.length === 0 && (
                <div className="text-dark-400 text-sm text-center py-4">
                  {isZh ? '等待数据包...' : 'Waiting for packets...'}
                </div>
              )}
            </div>
          </div>

          {/* Legend */}
          <div className="p-4 border-t border-dark-700">
            <h3 className="text-sm font-semibold text-white mb-2">
              {isZh ? '图例' : 'Legend'}
            </h3>
            <div className="space-y-1 text-xs">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-blue-500" />
                <span className="text-dark-300">TCP</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span className="text-dark-300">UDP</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <span className="text-dark-300">ICMP</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <span className="text-dark-300">ARP</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
