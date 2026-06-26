import { useEffect, useState, useCallback } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
} from 'chart.js'
import { Bar, Radar } from 'react-chartjs-2'
import api from '../api/client'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler
)

interface TechniqueInfo {
  name: string
  technique: string
  description: string
  transport_protocol: string
  default_port: number
  encryption: string
  resistance_level: string
  use_cases: string[]
}

interface TrafficFeatures {
  avg_packet_size: number
  packet_size_std: number
  avg_interval_ms: number
  interval_std_ms: number
  burst_ratio: number
  protocol_distribution: Record<string, number>
  port_distribution: Record<string, number>
}

interface ShannonEntropy {
  payload_entropy: number
  header_entropy: number
  overall_entropy: number
  randomness_score: number
}

interface TestResult {
  id: string
  timestamp: string
  technique: string
  detection_rate: number
  false_positive_rate: number
  traffic_features: TrafficFeatures
  shannon_entropy: ShannonEntropy
  detection_difficulty: string
  detection_score: number
  packets_analyzed: number
  duration_seconds: number
  metadata: Record<string, unknown>
}

interface ComparisonMetrics {
  avg_detection_rate: number
  avg_false_positive_rate: number
  avg_detection_score: number
  avg_entropy: number
  test_count: number
}

interface RankingItem {
  rank: number
  technique: string
  score: number
}

interface ComparisonData {
  techniques: string[]
  metrics: Record<string, ComparisonMetrics>
  rankings: Record<string, RankingItem[]>
}

const DIFFICULTY_COLORS: Record<string, string> = {
  trivial: 'text-red-400',
  easy: 'text-orange-400',
  medium: 'text-yellow-400',
  hard: 'text-green-400',
  very_hard: 'text-emerald-400',
}

const DIFFICULTY_BG_COLORS: Record<string, string> = {
  trivial: 'bg-red-500/20',
  easy: 'bg-orange-500/20',
  medium: 'bg-yellow-500/20',
  hard: 'bg-green-500/20',
  very_hard: 'bg-emerald-500/20',
}

const TECHNIQUE_COLORS: Record<string, string> = {
  obfs4: 'rgb(34, 211, 238)',
  shadowsocks: 'rgb(168, 85, 247)',
  udp2raw: 'rgb(239, 68, 68)',
  meek: 'rgb(34, 197, 94)',
  snowflake: 'rgb(249, 115, 22)',
}

const ObfuscationTester = () => {
  const [techniques, setTechniques] = useState<TechniqueInfo[]>([])
  const [results, setResults] = useState<TestResult[]>([])
  const [comparison, setComparison] = useState<ComparisonData | null>(null)
  const [loading, setLoading] = useState(true)
  const [testing, setTesting] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'techniques' | 'results' | 'comparison'>('techniques')

  const fetchData = useCallback(async () => {
    try {
      const [techRes, resultsRes, compRes] = await Promise.all([
        api.get('/obfuscation/techniques'),
        api.get('/obfuscation/results'),
        api.get('/obfuscation/comparison'),
      ])
      setTechniques(techRes.data)
      setResults(resultsRes.data)
      setComparison(compRes.data)
    } catch (err) {
      console.error('Failed to fetch obfuscation data:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleRunTest = async (technique: string) => {
    setTesting(technique)
    try {
      await api.post('/obfuscation/test', {
        technique,
        packet_count: 1000,
        duration_seconds: 10.0,
      })
      await fetchData()
    } catch (err) {
      console.error('Failed to run test:', err)
    } finally {
      setTesting(null)
    }
  }

  const handleRunAllTests = async () => {
    setTesting('all')
    try {
      for (const tech of techniques) {
        await api.post('/obfuscation/test', {
          technique: tech.technique,
          packet_count: 1000,
          duration_seconds: 10.0,
        })
      }
      await fetchData()
    } catch (err) {
      console.error('Failed to run all tests:', err)
    } finally {
      setTesting(null)
    }
  }

  const handleClear = async () => {
    try {
      await api.delete('/obfuscation')
      await fetchData()
    } catch (err) {
      console.error('Failed to clear data:', err)
    }
  }

  const formatPercentage = (value: number): string => {
    return `${(value * 100).toFixed(1)}%`
  }

  const comparisonChartData = comparison && comparison.techniques.length > 0
    ? {
        labels: comparison.techniques.map(t => t.charAt(0).toUpperCase() + t.slice(1)),
        datasets: [
          {
            label: '检测难度评分',
            data: comparison.techniques.map(t => comparison.metrics[t]?.avg_detection_score || 0),
            backgroundColor: comparison.techniques.map(t => TECHNIQUE_COLORS[t] || 'rgb(107, 114, 128)'),
            borderColor: 'rgba(15, 23, 42, 0.8)',
            borderWidth: 1,
          },
        ],
      }
    : null

  const radarChartData = comparison && comparison.techniques.length > 0
    ? {
        labels: ['检测率', '误报率', '检测难度', '熵值'],
        datasets: comparison.techniques.map(t => ({
          label: t.charAt(0).toUpperCase() + t.slice(1),
          data: [
            comparison.metrics[t]?.avg_detection_rate || 0,
            comparison.metrics[t]?.avg_false_positive_rate || 0,
            (comparison.metrics[t]?.avg_detection_score || 0) / 100,
            (comparison.metrics[t]?.avg_entropy || 0) / 8,
          ],
          backgroundColor: `${TECHNIQUE_COLORS[t] || '#6b7280'}20`,
          borderColor: TECHNIQUE_COLORS[t] || '#6b7280',
          borderWidth: 2,
          pointBackgroundColor: TECHNIQUE_COLORS[t] || '#6b7280',
        })),
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="text-sm text-dark-400">支持技术</div>
          <div className="text-2xl font-bold text-white">{techniques.length}</div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-dark-400">测试结果</div>
          <div className="text-2xl font-bold text-white">{results.length}</div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-dark-400">平均检测难度</div>
          <div className="text-2xl font-bold text-neon-cyan">
            {results.length > 0
              ? (results.reduce((sum, r) => sum + r.detection_score, 0) / results.length).toFixed(1)
              : 'N/A'}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-dark-400">最佳技术</div>
          <div className="text-2xl font-bold text-emerald-400">
            {comparison?.rankings.by_detection_difficulty?.[0]?.technique || 'N/A'}
          </div>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={handleRunAllTests}
          disabled={testing !== null}
          className="btn-primary px-4 py-2 disabled:opacity-50"
        >
          {testing === 'all' ? '测试中...' : '运行所有测试'}
        </button>
        <button onClick={fetchData} className="bg-dark-700 hover:bg-dark-600 text-white px-4 py-2 rounded-lg">
          刷新
        </button>
        <button onClick={handleClear} className="btn-danger px-4 py-2">
          清除数据
        </button>
      </div>

      <div className="flex border-b border-dark-700">
        {(['techniques', 'results', 'comparison'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'text-neon-cyan border-b-2 border-neon-cyan'
                : 'text-dark-400 hover:text-white'
            }`}
          >
            {tab === 'techniques' && '混淆技术'}
            {tab === 'results' && '测试结果'}
            {tab === 'comparison' && '对比分析'}
          </button>
        ))}
      </div>

      {activeTab === 'techniques' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {techniques.map((tech) => (
            <div
              key={tech.technique}
              className="p-4 bg-dark-800 rounded-lg border border-dark-700 hover:border-neon-cyan/30 transition-colors"
            >
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold text-white text-lg">{tech.name}</h4>
                <span className="px-2 py-1 rounded text-xs font-medium bg-neon-cyan/20 text-neon-cyan">
                  {tech.transport_protocol}
                </span>
              </div>
              <p className="text-sm text-dark-300 mb-3">{tech.description}</p>
              <div className="space-y-2 text-xs text-dark-400">
                <div className="flex justify-between">
                  <span>默认端口:</span>
                  <span className="text-white">{tech.default_port}</span>
                </div>
                <div className="flex justify-between">
                  <span>加密方式:</span>
                  <span className="text-white">{tech.encryption}</span>
                </div>
                <div className="flex justify-between">
                  <span>抗检测能力:</span>
                  <span className="text-emerald-400">{tech.resistance_level}</span>
                </div>
              </div>
              <div className="mt-3">
                <div className="text-xs text-dark-400 mb-1">适用场景:</div>
                <div className="flex flex-wrap gap-1">
                  {tech.use_cases.map((use_case, idx) => (
                    <span key={idx} className="px-2 py-0.5 rounded text-xs bg-dark-600 text-dark-300">
                      {use_case}
                    </span>
                  ))}
                </div>
              </div>
              <button
                onClick={() => handleRunTest(tech.technique)}
                disabled={testing !== null}
                className="mt-4 w-full bg-dark-700 hover:bg-dark-600 text-white px-3 py-2 rounded-lg text-sm disabled:opacity-50"
              >
                {testing === tech.technique ? '测试中...' : '运行测试'}
              </button>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'results' && (
        <div className="space-y-4">
          {results.length === 0 ? (
            <div className="card p-8 text-center text-dark-400">
              暂无测试结果，请先运行混淆测试
            </div>
          ) : (
            results.slice().reverse().map((result) => (
              <div key={result.id} className="card p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <h4 className="font-semibold text-white text-lg">
                      {result.technique.charAt(0).toUpperCase() + result.technique.slice(1)}
                    </h4>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${DIFFICULTY_BG_COLORS[result.detection_difficulty]} ${DIFFICULTY_COLORS[result.detection_difficulty]}`}>
                      {result.detection_difficulty.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>
                  <span className="text-xs text-dark-400">
                    {new Date(result.timestamp).toLocaleString()}
                  </span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                  <div>
                    <div className="text-xs text-dark-400">检测率</div>
                    <div className="text-lg font-semibold text-red-400">
                      {formatPercentage(result.detection_rate)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-dark-400">误报率</div>
                    <div className="text-lg font-semibold text-orange-400">
                      {formatPercentage(result.false_positive_rate)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-dark-400">检测难度评分</div>
                    <div className="text-lg font-semibold text-neon-cyan">
                      {result.detection_score.toFixed(1)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-dark-400">Shannon 熵</div>
                    <div className="text-lg font-semibold text-emerald-400">
                      {result.shannon_entropy.overall_entropy.toFixed(2)}
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-dark-400">
                  <div>
                    <span>平均包大小: </span>
                    <span className="text-white">{result.traffic_features.avg_packet_size.toFixed(0)} B</span>
                  </div>
                  <div>
                    <span>平均间隔: </span>
                    <span className="text-white">{result.traffic_features.avg_interval_ms.toFixed(1)} ms</span>
                  </div>
                  <div>
                    <span>突发比率: </span>
                    <span className="text-white">{(result.traffic_features.burst_ratio * 100).toFixed(1)}%</span>
                  </div>
                  <div>
                    <span>数据包数量: </span>
                    <span className="text-white">{result.packets_analyzed}</span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'comparison' && (
        <div className="space-y-6">
          {comparison && comparison.techniques.length > 0 ? (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">检测难度评分对比</h3>
                  {comparisonChartData && (
                    <div className="h-[300px]">
                      <Bar
                        data={comparisonChartData}
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
                            y: {
                              ticks: { color: '#94a3b8' },
                              grid: { color: 'rgba(148,163,184,0.1)' },
                              min: 0,
                              max: 100,
                            },
                          },
                        }}
                      />
                    </div>
                  )}
                </div>
                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">多维度对比</h3>
                  {radarChartData && (
                    <div className="h-[300px]">
                      <Radar
                        data={radarChartData}
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          plugins: {
                            legend: {
                              position: 'bottom',
                              labels: { color: '#94a3b8', font: { size: 11 } },
                            },
                            tooltip: {
                              backgroundColor: 'rgba(15, 23, 42, 0.9)',
                              titleColor: '#e2e8f0',
                              bodyColor: '#cbd5e1',
                            },
                          },
                          scales: {
                            r: {
                              ticks: { color: '#94a3b8', backdropColor: 'transparent' },
                              grid: { color: 'rgba(148,163,184,0.2)' },
                              pointLabels: { color: '#94a3b8' },
                              min: 0,
                              max: 1,
                            },
                          },
                        }}
                      />
                    </div>
                  )}
                </div>
              </div>

              <div className="card">
                <div className="px-6 py-4 border-b border-dark-700">
                  <h3 className="text-lg font-semibold text-white">详细对比数据</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-dark-700">
                        <th className="px-6 py-3 text-left text-xs font-medium text-dark-400 uppercase">技术</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-dark-400 uppercase">检测率</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-dark-400 uppercase">误报率</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-dark-400 uppercase">难度评分</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-dark-400 uppercase">熵值</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-dark-400 uppercase">测试次数</th>
                      </tr>
                    </thead>
                    <tbody>
                      {comparison.techniques.map((tech) => {
                        const metrics = comparison.metrics[tech]
                        if (!metrics) return null
                        return (
                          <tr key={tech} className="border-b border-dark-800 hover:bg-dark-800/50">
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-2">
                                <div
                                  className="w-3 h-3 rounded-full"
                                  style={{ backgroundColor: TECHNIQUE_COLORS[tech] || '#6b7280' }}
                                />
                                <span className="text-sm font-medium text-white">
                                  {tech.charAt(0).toUpperCase() + tech.slice(1)}
                                </span>
                              </div>
                            </td>
                            <td className="px-6 py-4 text-sm text-red-400 text-right">
                              {formatPercentage(metrics.avg_detection_rate)}
                            </td>
                            <td className="px-6 py-4 text-sm text-orange-400 text-right">
                              {formatPercentage(metrics.avg_false_positive_rate)}
                            </td>
                            <td className="px-6 py-4 text-sm text-neon-cyan text-right">
                              {metrics.avg_detection_score.toFixed(1)}
                            </td>
                            <td className="px-6 py-4 text-sm text-emerald-400 text-right">
                              {metrics.avg_entropy.toFixed(2)}
                            </td>
                            <td className="px-6 py-4 text-sm text-dark-300 text-right">
                              {metrics.test_count}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="card p-6">
                <h3 className="text-lg font-semibold text-white mb-4">检测难度排名</h3>
                <div className="space-y-3">
                  {comparison.rankings.by_detection_difficulty?.map((item) => (
                    <div key={item.technique} className="flex items-center justify-between p-3 bg-dark-800 rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl font-bold text-neon-cyan w-8">#{item.rank}</span>
                        <div>
                          <div className="font-medium text-white">
                            {item.technique.charAt(0).toUpperCase() + item.technique.slice(1)}
                          </div>
                          <div className="text-xs text-dark-400">
                            {techniques.find(t => t.technique === item.technique)?.description}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-semibold text-emerald-400">{item.score.toFixed(1)}</div>
                        <div className="text-xs text-dark-400">难度评分</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="card p-8 text-center text-dark-400">
              暂无对比数据，请先运行混淆测试
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ObfuscationTester