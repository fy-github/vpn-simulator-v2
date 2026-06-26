import { useEffect, useState, useCallback } from 'react'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  ChartData,
  TooltipItem,
  CategoryScale,
  LinearScale,
  BarElement,
} from 'chart.js'
import { Doughnut, Bar } from 'react-chartjs-2'
import api from '../api/client'
import { ArrowRightIcon } from './Icons'

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement)

interface ProtocolInfo {
  name: string
  category: string
  default_ports: number[]
  description: string
  threat_level: string
  is_encrypted: boolean
  common_domains: string[]
}

interface DPIResult {
  id: string
  timestamp: string
  protocol: string
  category: string
  confidence: number
  src_ip: string
  dst_ip: string
  src_port: number
  dst_port: number
  payload_size: number
  is_encrypted: boolean
  threat_level: string
  metadata: Record<string, unknown>
  matched_rules: string[]
}

interface Statistics {
  total_packets: number
  protocol_counts: Record<string, number>
  category_counts: Record<string, number>
  threat_counts: Record<string, number>
  total_bytes: number
  protocol_bytes: Record<string, number>
  avg_confidence: number
  anomaly_count: number
}

interface Classification {
  category: string
  protocols: string[]
  packet_count: number
  byte_count: number
  percentage: number
  avg_confidence: number
}

interface Distribution {
  protocols: string[]
  counts: number[]
  percentages: number[]
  total: number
}

interface Anomaly {
  id: string
  timestamp: string
  anomaly_type: string
  severity: string
  description: string
  source_ip: string
  protocol: string
  details: Record<string, unknown>
}

const CATEGORY_COLORS: Record<string, string> = {
  application: 'rgb(34, 211, 238)',
  streaming: 'rgb(168, 85, 247)',
  vpn: 'rgb(34, 197, 94)',
  p2p: 'rgb(239, 68, 68)',
  messaging: 'rgb(249, 115, 22)',
  gaming: 'rgb(236, 72, 153)',
  unknown: 'rgb(107, 114, 128)',
}

const THREAT_COLORS: Record<string, string> = {
  safe: 'text-green-400',
  low: 'text-yellow-400',
  medium: 'text-orange-400',
  high: 'text-red-400',
  critical: 'text-red-600',
}

const THREAT_BG_COLORS: Record<string, string> = {
  safe: 'bg-green-500/20',
  low: 'bg-yellow-500/20',
  medium: 'bg-orange-500/20',
  high: 'bg-red-500/20',
  critical: 'bg-red-600/20',
}

const ProtocolAnalyzer = () => {
  const [protocols, setProtocols] = useState<ProtocolInfo[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [classification, setClassification] = useState<Classification[]>([])
  const [distribution, setDistribution] = useState<Distribution | null>(null)
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [recentResults, setRecentResults] = useState<DPIResult[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [activeTab, setActiveTab] = useState<'overview' | 'classification' | 'anomalies' | 'protocols'>('overview')

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, classRes, distRes, anomRes, resultsRes] = await Promise.all([
        api.get('/dpi/statistics'),
        api.get('/dpi/classification'),
        api.get('/dpi/distribution'),
        api.get('/dpi/anomalies'),
        api.get('/dpi/results'),
      ])
      setStatistics(statsRes.data)
      setClassification(classRes.data)
      setDistribution(distRes.data)
      setAnomalies(anomRes.data)
      setRecentResults(resultsRes.data)
    } catch (err) {
      console.error('Failed to fetch DPI data:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const fetchProtocols = async () => {
      try {
        const res = await api.get('/dpi/protocols')
        setProtocols(res.data)
      } catch (err) {
        console.error('Failed to fetch protocols:', err)
      }
    }
    fetchProtocols()
    fetchData()
  }, [fetchData])

  const handleGenerateSamples = async () => {
    setGenerating(true)
    try {
      await api.post('/dpi/samples?count=100')
      await fetchData()
    } catch (err) {
      console.error('Failed to generate samples:', err)
    } finally {
      setGenerating(false)
    }
  }

  const handleClear = async () => {
    try {
      await api.delete('/dpi')
      await fetchData()
    } catch (err) {
      console.error('Failed to clear DPI data:', err)
    }
  }

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
  }

  const chartData = distribution && distribution.protocols.length > 0
    ? {
        labels: distribution.protocols,
        datasets: [
          {
            data: distribution.counts,
            backgroundColor: [
              'rgb(34, 211, 238)', 'rgb(168, 85, 247)', 'rgb(34, 197, 94)',
              'rgb(239, 68, 68)', 'rgb(249, 115, 22)', 'rgb(236, 72, 153)',
              'rgb(59, 130, 246)', 'rgb(234, 179, 8)', 'rgb(20, 184, 166)',
              'rgb(244, 63, 94)', 'rgb(139, 92, 246)', 'rgb(16, 185, 129)',
            ],
            borderColor: 'rgba(15, 23, 42, 0.8)',
            borderWidth: 2,
            hoverOffset: 8,
          },
        ],
      }
    : null

  const categoryChartData = classification.length > 0
    ? {
        labels: classification.map((c) => c.category.toUpperCase()),
        datasets: [
          {
            label: '数据包数量',
            data: classification.map((c) => c.packet_count),
            backgroundColor: classification.map(
              (c) => CATEGORY_COLORS[c.category] || 'rgb(107, 114, 128)'
            ),
            borderColor: 'rgba(15, 23, 42, 0.8)',
            borderWidth: 1,
          },
        ],
      }
    : null

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-neon-cyan"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="text-sm text-dark-400">总数据包</div>
          <div className="text-2xl font-bold text-white">{statistics?.total_packets || 0}</div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-dark-400">识别协议数</div>
          <div className="text-2xl font-bold text-white">
            {statistics ? Object.keys(statistics.protocol_counts).length : 0}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-dark-400">平均置信度</div>
          <div className="text-2xl font-bold text-neon-cyan">
            {statistics ? `${(statistics.avg_confidence * 100).toFixed(1)}%` : '0%'}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-dark-400">异常事件</div>
          <div className="text-2xl font-bold text-red-400">{statistics?.anomaly_count || 0}</div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={handleGenerateSamples}
          disabled={generating}
          className="btn-primary px-4 py-2 disabled:opacity-50"
        >
          {generating ? '生成中...' : '生成模拟流量'}
        </button>
        <button onClick={fetchData} className="bg-dark-700 hover:bg-dark-600 text-white px-4 py-2 rounded-lg">
          刷新
        </button>
        <button onClick={handleClear} className="btn-danger px-4 py-2">
          清除数据
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-dark-700">
        {(['overview', 'classification', 'anomalies', 'protocols'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'text-neon-cyan border-b-2 border-neon-cyan'
                : 'text-dark-400 hover:text-white'
            }`}
          >
            {tab === 'overview' && '概览'}
            {tab === 'classification' && '流量分类'}
            {tab === 'anomalies' && '异常检测'}
            {tab === 'protocols' && '协议库'}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Protocol Distribution */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-white mb-4">协议分布</h3>
            {chartData ? (
              <div className="relative h-[300px]">
                <Doughnut
                  data={chartData as ChartData<'doughnut', number[], string>}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '55%',
                    plugins: {
                      legend: {
                        display: true,
                        position: 'right',
                        labels: {
                          color: '#94a3b8',
                          font: { size: 11 },
                          padding: 12,
                          usePointStyle: true,
                          generateLabels: (chart) => {
                            const d = chart.data as ChartData<'doughnut', number[], string>
                            return (d.labels ?? []).map((label, i) => ({
                              text: `${label} (${distribution?.percentages[i]}%)`,
                              fillStyle: (d.datasets[0].backgroundColor as string[])[i],
                              strokeStyle: 'transparent',
                              lineWidth: 0,
                              hidden: false,
                              index: i,
                              pointStyle: 'circle' as const,
                            }))
                          },
                        },
                      },
                      tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#e2e8f0',
                        bodyColor: '#cbd5e1',
                        callbacks: {
                          label: (ctx: TooltipItem<'doughnut'>) => {
                            const idx = ctx.dataIndex
                            return ` ${ctx.label}: ${distribution?.counts[idx]} 包 (${distribution?.percentages[idx]}%)`
                          },
                        },
                      },
                    },
                  }}
                />
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-white">{distribution?.total || 0}</div>
                    <div className="text-xs text-dark-400">Total</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-dark-400">
                暂无数据，点击"生成模拟流量"开始
              </div>
            )}
          </div>

          {/* Recent Results */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-white mb-4">最近分析结果</h3>
            <div className="space-y-2 max-h-[300px] overflow-y-auto">
              {recentResults.slice(0, 15).map((r) => (
                <div
                  key={r.id}
                  className="flex items-center justify-between p-3 bg-dark-800 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        r.is_encrypted ? 'bg-green-500/20 text-green-400' : 'bg-dark-600 text-dark-300'
                      }`}
                    >
                      {r.is_encrypted ? '加密' : '明文'}
                    </span>
                    <div>
                      <div className="text-sm font-medium text-white">{r.protocol}</div>
                      <div className="text-xs text-dark-400">
                        {r.src_ip}:{r.src_port} <ArrowRightIcon className="w-3 h-3 inline" /> {r.dst_ip}:{r.dst_port}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-neon-cyan">{(r.confidence * 100).toFixed(0)}%</div>
                    <div className="text-xs text-dark-400">{r.category}</div>
                  </div>
                </div>
              ))}
              {recentResults.length === 0 && (
                <div className="text-center text-dark-400 py-8">暂无分析结果</div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'classification' && (
        <div className="space-y-6">
          {/* Category Bar Chart */}
          {categoryChartData && (
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-white mb-4">流量类别分布</h3>
              <div className="h-[250px]">
                <Bar
                  data={categoryChartData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: { display: false },
                      tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#e2e8f0',
                        bodyColor: '#cbd5e1',
                      },
                    },
                    scales: {
                      x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,0.1)' } },
                      y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,0.1)' } },
                    },
                  }}
                />
              </div>
            </div>
          )}

          {/* Classification Table */}
          <div className="card">
            <div className="px-6 py-4 border-b border-dark-700">
              <h3 className="text-lg font-semibold text-white">流量分类详情</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-dark-700">
                    <th className="px-6 py-3 text-left text-xs font-medium text-dark-400 uppercase">类别</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-dark-400 uppercase">协议</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-dark-400 uppercase">数据包</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-dark-400 uppercase">字节数</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-dark-400 uppercase">占比</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-dark-400 uppercase">置信度</th>
                  </tr>
                </thead>
                <tbody>
                  {classification.map((c) => (
                    <tr key={c.category} className="border-b border-dark-800 hover:bg-dark-800/50">
                      <td className="px-6 py-4">
                        <span
                          className="px-2 py-1 rounded text-xs font-medium"
                          style={{
                            backgroundColor: `${CATEGORY_COLORS[c.category] || '#6b7280'}20`,
                            color: CATEGORY_COLORS[c.category] || '#6b7280',
                          }}
                        >
                          {c.category.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-dark-300">{c.protocols.join(', ')}</td>
                      <td className="px-6 py-4 text-sm text-white text-right">{c.packet_count}</td>
                      <td className="px-6 py-4 text-sm text-dark-300 text-right">{formatBytes(c.byte_count)}</td>
                      <td className="px-6 py-4 text-sm text-neon-cyan text-right">{c.percentage.toFixed(1)}%</td>
                      <td className="px-6 py-4 text-sm text-dark-300 text-right">{(c.avg_confidence * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                  {classification.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-6 py-8 text-center text-dark-400">
                        暂无分类数据
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'anomalies' && (
        <div className="card">
          <div className="px-6 py-4 border-b border-dark-700">
            <h3 className="text-lg font-semibold text-white">异常检测 ({anomalies.length})</h3>
          </div>
          <div className="space-y-2 p-4 max-h-[500px] overflow-y-auto">
            {anomalies.map((a) => (
              <div key={a.id} className="p-4 bg-dark-800 rounded-lg border-l-4 border-l-orange-500">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${THREAT_BG_COLORS[a.severity]} ${THREAT_COLORS[a.severity]}`}>
                      {a.severity.toUpperCase()}
                    </span>
                    <span className="text-sm font-medium text-white">{a.anomaly_type}</span>
                  </div>
                  <span className="text-xs text-dark-400">{new Date(a.timestamp).toLocaleTimeString()}</span>
                </div>
                <p className="text-sm text-dark-300">{a.description}</p>
                <div className="mt-2 flex gap-4 text-xs text-dark-400">
                  {a.source_ip && <span>来源: {a.source_ip}</span>}
                  {a.protocol && <span>协议: {a.protocol}</span>}
                </div>
              </div>
            ))}
            {anomalies.length === 0 && (
              <div className="text-center text-dark-400 py-8">暂无异常事件</div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'protocols' && (
        <div className="card">
          <div className="px-6 py-4 border-b border-dark-700">
            <h3 className="text-lg font-semibold text-white">支持的协议 ({protocols.length})</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
            {protocols.map((p) => (
              <div
                key={p.name}
                className="p-4 bg-dark-800 rounded-lg border border-dark-700 hover:border-neon-cyan/30 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold text-white">{p.name}</h4>
                  <div className="flex gap-1">
                    <span
                      className="px-2 py-0.5 rounded text-xs"
                      style={{
                        backgroundColor: `${CATEGORY_COLORS[p.category] || '#6b7280'}20`,
                        color: CATEGORY_COLORS[p.category] || '#6b7280',
                      }}
                    >
                      {p.category}
                    </span>
                    {p.is_encrypted && (
                      <span className="px-2 py-0.5 rounded text-xs bg-green-500/20 text-green-400">
                        加密
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-xs text-dark-400 mb-2">{p.description}</p>
                <div className="text-xs text-dark-500">
                  端口: {p.default_ports.join(', ')}
                </div>
                <div className="mt-1">
                  <span className={`text-xs ${THREAT_COLORS[p.threat_level]}`}>
                    威胁: {p.threat_level}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default ProtocolAnalyzer
