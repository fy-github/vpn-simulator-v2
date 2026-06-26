import { useState, useEffect, useCallback, useRef } from 'react'
import axios from 'axios'
import ThroughputChart from './ThroughputChart'
import LatencyChart from './LatencyChart'
import PacketLossChart from './PacketLossChart'
import ConnectionsChart from './ConnectionsChart'
import ProtocolDistributionChart from './ProtocolDistributionChart'

const API_BASE = '/api/v1/metrics'
const TIME_RANGES = ['1m', '5m', '15m', '1h'] as const
const TIME_RANGE_LABELS: Record<string, string> = {
  '1m': '1 Min',
  '5m': '5 Min',
  '15m': '15 Min',
  '1h': '1 Hour',
}
const REFRESH_INTERVAL = 3000

interface ThroughputData {
  timestamps: string[]
  values: number[]
  unit: string
  time_range: string
  protocol: string
}

interface LatencyData {
  timestamps: string[]
  values: number[]
  min_values: number[]
  max_values: number[]
  unit: string
  time_range: string
  protocol: string
}

interface PacketLossData {
  timestamps: string[]
  values: number[]
  unit: string
  time_range: string
  protocol: string
}

interface ConnectionsData {
  timestamps: string[]
  total: number[]
  protocols: Record<string, number[]>
  unit: string
  time_range: string
}

interface DistributionData {
  protocols: string[]
  counts: number[]
  percentages: number[]
  total: number
}

interface StatisticsData {
  throughput: { stats: Record<string, number>; unit: string }
  latency: { stats: Record<string, number>; unit: string }
  packet_loss: { stats: Record<string, number>; unit: string }
  connections: { current: number; peak: number; average: number }
  time_range: string
  protocol: string
  data_points: number
}

const PerformanceCharts = () => {
  const [timeRange, setTimeRange] = useState<string>('5m')
  const [protocol, setProtocol] = useState<string>('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [fullscreen, setFullscreen] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [throughputData, setThroughputData] = useState<ThroughputData | null>(null)
  const [latencyData, setLatencyData] = useState<LatencyData | null>(null)
  const [packetLossData, setPacketLossData] = useState<PacketLossData | null>(null)
  const [connectionsData, setConnectionsData] = useState<ConnectionsData | null>(null)
  const [distributionData, setDistributionData] = useState<DistributionData | null>(null)
  const [statistics, setStatistics] = useState<StatisticsData | null>(null)

  const containerRef = useRef<HTMLDivElement>(null)

  const fetchAllData = useCallback(async () => {
    try {
      const params = { time_range: timeRange, protocol: protocol || undefined }
      const [tp, lat, pl, conn, dist, stats] = await Promise.all([
        axios.get(`${API_BASE}/throughput`, { params }),
        axios.get(`${API_BASE}/latency`, { params }),
        axios.get(`${API_BASE}/packet-loss`, { params }),
        axios.get(`${API_BASE}/connections`, { params: { time_range: timeRange } }),
        axios.get(`${API_BASE}/distribution`),
        axios.get(`${API_BASE}/statistics`, { params }),
      ])

      setThroughputData(tp.data)
      setLatencyData(lat.data)
      setPacketLossData(pl.data)
      setConnectionsData(conn.data)
      setDistributionData(dist.data)
      setStatistics(stats.data)
      setLoading(false)
    } catch (err) {
      console.error('Failed to fetch metrics:', err)
      setLoading(false)
    }
  }, [timeRange, protocol])

  useEffect(() => {
    fetchAllData()
  }, [fetchAllData])

  useEffect(() => {
    if (!autoRefresh) return
    const timer = setInterval(fetchAllData, REFRESH_INTERVAL)
    return () => clearInterval(timer)
  }, [autoRefresh, fetchAllData])

  const exportChartAsPng = useCallback((chartId: string) => {
    const canvas = document.querySelector(`#${chartId} canvas`) as HTMLCanvasElement
    if (!canvas) return
    const link = document.createElement('a')
    link.download = `${chartId}-${timeRange}-${new Date().toISOString().slice(0, 19)}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
  }, [timeRange])

  const exportAllAsCsv = useCallback(() => {
    if (!throughputData || !latencyData || !packetLossData) return

    const rows = [['timestamp', 'throughput_mbps', 'latency_ms', 'packet_loss_pct']]
    const len = throughputData.values.length
    for (let i = 0; i < len; i++) {
      rows.push([
        throughputData.timestamps[i],
        throughputData.values[i].toString(),
        latencyData.values[i]?.toString() || '',
        packetLossData.values[i]?.toString() || '',
      ])
    }

    const csv = rows.map((r) => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const link = document.createElement('a')
    link.download = `metrics-${timeRange}-${new Date().toISOString().slice(0, 19)}.csv`
    link.href = URL.createObjectURL(blob)
    link.click()
    URL.revokeObjectURL(link.href)
  }, [throughputData, latencyData, packetLossData, timeRange])

  const toggleFullscreen = useCallback((chartId: string) => {
    if (fullscreen === chartId) {
      setFullscreen(null)
      if (document.exitFullscreen) {
        document.exitFullscreen()
      }
    } else {
      setFullscreen(chartId)
      const el = document.getElementById(chartId)
      if (el?.requestFullscreen) {
        el.requestFullscreen()
      }
    }
  }, [fullscreen])

  useEffect(() => {
    const handler = () => {
      if (!document.fullscreenElement) {
        setFullscreen(null)
      }
    }
    document.addEventListener('fullscreenchange', handler)
    return () => document.removeEventListener('fullscreenchange', handler)
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-neon-cyan"></div>
      </div>
    )
  }

  const protocols = ['', 'pptp', 'l2tp', 'openvpn', 'ipsec', 'ikev2', 'wireguard']

  return (
    <div ref={containerRef} className="space-y-6">
      {/* Controls Bar */}
      <div className="card p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            {/* Time Range Selector */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-dark-400">Time Range:</span>
              <div className="flex bg-dark-800 rounded-lg p-1">
                {TIME_RANGES.map((tr) => (
                  <button
                    key={tr}
                    onClick={() => setTimeRange(tr)}
                    className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                      timeRange === tr
                        ? 'bg-neon-cyan/20 text-neon-cyan'
                        : 'text-dark-400 hover:text-white'
                    }`}
                  >
                    {TIME_RANGE_LABELS[tr]}
                  </button>
                ))}
              </div>
            </div>

            {/* Protocol Filter */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-dark-400">Protocol:</span>
              <select
                value={protocol}
                onChange={(e) => setProtocol(e.target.value)}
                className="bg-dark-800 text-white text-sm rounded-lg px-3 py-1.5 border border-dark-700 focus:border-neon-cyan focus:outline-none"
              >
                <option value="">All Protocols</option>
                {protocols.filter(Boolean).map((p) => (
                  <option key={p} value={p}>{p.toUpperCase()}</option>
                ))}
              </select>
            </div>

            {/* Auto Refresh Toggle */}
            <label className="flex items-center gap-2 cursor-pointer">
              <div
                className={`relative w-10 h-5 rounded-full transition-colors ${
                  autoRefresh ? 'bg-neon-cyan/30' : 'bg-dark-700'
                }`}
                onClick={() => setAutoRefresh(!autoRefresh)}
              >
                <div
                  className={`absolute top-0.5 w-4 h-4 rounded-full transition-transform ${
                    autoRefresh
                      ? 'translate-x-5 bg-neon-cyan'
                      : 'translate-x-0.5 bg-dark-400'
                  }`}
                />
              </div>
              <span className="text-sm text-dark-400">Auto Refresh</span>
            </label>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={exportAllAsCsv}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-dark-800 hover:bg-dark-700 text-dark-300 hover:text-white text-sm rounded-lg transition-colors border border-dark-700"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Export CSV
            </button>
            <button
              onClick={fetchAllData}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-dark-800 hover:bg-dark-700 text-dark-300 hover:text-white text-sm rounded-lg transition-colors border border-dark-700"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Statistics Summary */}
      {statistics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card p-4">
            <div className="text-sm text-dark-400">Avg Throughput</div>
            <div className="text-xl font-bold text-neon-cyan">
              {statistics.throughput.stats.avg}
              <span className="text-sm font-normal text-dark-400 ml-1">Mbps</span>
            </div>
            <div className="text-xs text-dark-500 mt-1">
              P95: {statistics.throughput.stats.p95} Mbps
            </div>
          </div>
          <div className="card p-4">
            <div className="text-sm text-dark-400">Avg Latency</div>
            <div className="text-xl font-bold text-purple-400">
              {statistics.latency.stats.avg}
              <span className="text-sm font-normal text-dark-400 ml-1">ms</span>
            </div>
            <div className="text-xs text-dark-500 mt-1">
              P95: {statistics.latency.stats.p95} ms
            </div>
          </div>
          <div className="card p-4">
            <div className="text-sm text-dark-400">Avg Packet Loss</div>
            <div className="text-xl font-bold text-red-400">
              {statistics.packet_loss.stats.avg}
              <span className="text-sm font-normal text-dark-400 ml-1">%</span>
            </div>
            <div className="text-xs text-dark-500 mt-1">
              Max: {statistics.packet_loss.stats.max}%
            </div>
          </div>
          <div className="card p-4">
            <div className="text-sm text-dark-400">Connections</div>
            <div className="text-xl font-bold text-green-400">
              {statistics.connections.current}
              <span className="text-sm font-normal text-dark-400 ml-1">active</span>
            </div>
            <div className="text-xs text-dark-500 mt-1">
              Peak: {statistics.connections.peak}
            </div>
          </div>
        </div>
      )}

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Throughput Chart */}
        <div id="throughput-chart" className="card">
          <div className="flex items-center justify-between px-4 py-3 border-b border-dark-700">
            <h3 className="text-sm font-semibold text-white">Throughput</h3>
            <div className="flex items-center gap-1">
              <button
                onClick={() => exportChartAsPng('throughput-chart')}
                className="p-1.5 text-dark-400 hover:text-white rounded transition-colors"
                title="Export PNG"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </button>
              <button
                onClick={() => toggleFullscreen('throughput-chart')}
                className="p-1.5 text-dark-400 hover:text-white rounded transition-colors"
                title="Fullscreen"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                </svg>
              </button>
            </div>
          </div>
          <div className="p-4">
            {throughputData && <ThroughputChart data={throughputData} timeRange={timeRange} />}
          </div>
        </div>

        {/* Latency Chart */}
        <div id="latency-chart" className="card">
          <div className="flex items-center justify-between px-4 py-3 border-b border-dark-700">
            <h3 className="text-sm font-semibold text-white">Latency</h3>
            <div className="flex items-center gap-1">
              <button
                onClick={() => exportChartAsPng('latency-chart')}
                className="p-1.5 text-dark-400 hover:text-white rounded transition-colors"
                title="Export PNG"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </button>
              <button
                onClick={() => toggleFullscreen('latency-chart')}
                className="p-1.5 text-dark-400 hover:text-white rounded transition-colors"
                title="Fullscreen"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                </svg>
              </button>
            </div>
          </div>
          <div className="p-4">
            {latencyData && <LatencyChart data={latencyData} timeRange={timeRange} />}
          </div>
        </div>

        {/* Packet Loss Chart */}
        <div id="packetloss-chart" className="card">
          <div className="flex items-center justify-between px-4 py-3 border-b border-dark-700">
            <h3 className="text-sm font-semibold text-white">Packet Loss</h3>
            <div className="flex items-center gap-1">
              <button
                onClick={() => exportChartAsPng('packetloss-chart')}
                className="p-1.5 text-dark-400 hover:text-white rounded transition-colors"
                title="Export PNG"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </button>
              <button
                onClick={() => toggleFullscreen('packetloss-chart')}
                className="p-1.5 text-dark-400 hover:text-white rounded transition-colors"
                title="Fullscreen"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                </svg>
              </button>
            </div>
          </div>
          <div className="p-4">
            {packetLossData && <PacketLossChart data={packetLossData} timeRange={timeRange} />}
          </div>
        </div>

        {/* Connections Chart */}
        <div id="connections-chart" className="card">
          <div className="flex items-center justify-between px-4 py-3 border-b border-dark-700">
            <h3 className="text-sm font-semibold text-white">Connections</h3>
            <div className="flex items-center gap-1">
              <button
                onClick={() => exportChartAsPng('connections-chart')}
                className="p-1.5 text-dark-400 hover:text-white rounded transition-colors"
                title="Export PNG"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </button>
              <button
                onClick={() => toggleFullscreen('connections-chart')}
                className="p-1.5 text-dark-400 hover:text-white rounded transition-colors"
                title="Fullscreen"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                </svg>
              </button>
            </div>
          </div>
          <div className="p-4">
            {connectionsData && <ConnectionsChart data={connectionsData} timeRange={timeRange} />}
          </div>
        </div>
      </div>

      {/* Protocol Distribution */}
      <div id="distribution-chart" className="card">
        <div className="flex items-center justify-between px-4 py-3 border-b border-dark-700">
          <h3 className="text-sm font-semibold text-white">Protocol Distribution</h3>
          <button
            onClick={() => exportChartAsPng('distribution-chart')}
            className="p-1.5 text-dark-400 hover:text-white rounded transition-colors"
            title="Export PNG"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </button>
        </div>
        <div className="p-4">
          {distributionData && <ProtocolDistributionChart data={distributionData} />}
        </div>
      </div>
    </div>
  )
}

export default PerformanceCharts
