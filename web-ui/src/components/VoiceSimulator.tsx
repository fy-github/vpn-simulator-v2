import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { VoiceIcon, ArrowRightIcon } from './Icons'

interface Codec {
  id: string
  name: string
  description: string
  bitrate_kbps: number
  sample_rate_hz: number
  frame_size_ms: number
  packet_size_bytes: number
  bandwidth_range: {
    min_kbps: number
    max_kbps: number
  }
}

interface QualityMetrics {
  mos: number
  r_factor: number
  jitter_ms: number
  packet_loss_percent: number
  latency_ms: number
  packets_sent: number
  packets_received: number
  packets_lost: number
  bytes_sent: number
  bytes_received: number
}

interface QualityHistory {
  timestamp: number
  mos: number
  r_factor: number
  jitter_ms: number
  packet_loss_percent: number
  latency_ms: number
}

interface CallStatus {
  call_id: string
  codec: string
  caller_ip: string
  callee_ip: string
  state: string
  started_at: number
  uptime_seconds: number
  network_conditions: {
    latency_ms: number
    jitter_ms: number
    packet_loss_percent: number
    bandwidth_kbps: number
  }
  quality_metrics: QualityMetrics
}

interface CallQuality {
  call_id: string
  codec: string
  quality_metrics: QualityMetrics
  quality_history: QualityHistory[]
  timestamp: string
}

const MOS_COLORS: Record<string, string> = {
  excellent: 'text-green-400',
  good: 'text-blue-400',
  fair: 'text-yellow-400',
  poor: 'text-orange-400',
  bad: 'text-red-400',
}

const MOS_BG_COLORS: Record<string, string> = {
  excellent: 'bg-green-500/20',
  good: 'bg-blue-500/20',
  fair: 'bg-yellow-500/20',
  poor: 'bg-orange-500/20',
  bad: 'bg-red-500/20',
}

function getMosCategory(mos: number): string {
  if (mos >= 4.5) return 'excellent'
  if (mos >= 4.0) return 'good'
  if (mos >= 3.5) return 'fair'
  if (mos >= 3.0) return 'poor'
  return 'bad'
}

function getMosLabel(mos: number, isZh: boolean): string {
  if (mos >= 4.5) return isZh ? '优秀' : 'Excellent'
  if (mos >= 4.0) return isZh ? '良好' : 'Good'
  if (mos >= 3.5) return isZh ? '一般' : 'Fair'
  if (mos >= 3.0) return isZh ? '较差' : 'Poor'
  return isZh ? '很差' : 'Bad'
}

export default function VoiceSimulator() {
  const { i18n } = useTranslation()
  const isZh = i18n.language === 'zh-CN'

  const [codecs, setCodecs] = useState<Codec[]>([])
  const [selectedCodec, setSelectedCodec] = useState('g711')
  const [activeCall, setActiveCall] = useState<CallStatus | null>(null)
  const [callQuality, setCallQuality] = useState<CallQuality | null>(null)
  const [callHistory, setCallHistory] = useState<CallStatus[]>([])

  const [callerIp, setCallerIp] = useState('192.168.1.100')
  const [calleeIp, setCalleeIp] = useState('10.0.0.50')
  const [latency, setLatency] = useState(50)
  const [jitter, setJitter] = useState(10)
  const [packetLoss, setPacketLoss] = useState(0)
  const [bandwidth, setBandwidth] = useState(1000)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const qualityIntervalRef = useRef<ReturnType<typeof setInterval>>()

  // Fetch available codecs
  const fetchCodecs = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/voice/codecs')
      if (response.ok) {
        const data = await response.json()
        setCodecs(data.codecs)
      }
    } catch (err) {
      console.error('Failed to fetch codecs:', err)
    }
  }, [])

  // Fetch call quality
  const fetchCallQuality = useCallback(async (callId: string) => {
    try {
      const response = await fetch(`/api/v1/voice/calls/${callId}/quality`)
      if (response.ok) {
        const data = await response.json()
        setCallQuality(data)
      }
    } catch (err) {
      console.error('Failed to fetch call quality:', err)
    }
  }, [])

  // Start call
  const handleStartCall = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/v1/voice/calls', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          codec: selectedCodec,
          caller_ip: callerIp,
          callee_ip: calleeIp,
          latency_ms: latency,
          jitter_ms: jitter,
          packet_loss_percent: packetLoss,
          bandwidth_kbps: bandwidth,
        }),
      })

      if (response.ok) {
        const data = await response.json()
        // Fetch call status
        const statusResponse = await fetch(`/api/v1/voice/calls/${data.call_id}/status`)
        if (statusResponse.ok) {
          const status = await statusResponse.json()
          setActiveCall(status)
          // Start quality polling
          qualityIntervalRef.current = setInterval(() => fetchCallQuality(data.call_id), 1000)
        }
      } else {
        const data = await response.json()
        setError(data.detail || (isZh ? '启动通话失败' : 'Failed to start call'))
      }
    } catch (err) {
      setError(isZh ? '无法连接到服务器' : 'Cannot connect to server')
    } finally {
      setLoading(false)
    }
  }, [selectedCodec, callerIp, calleeIp, latency, jitter, packetLoss, bandwidth, fetchCallQuality, isZh])

  // Stop call
  const handleStopCall = useCallback(async () => {
    if (!activeCall) return

    setLoading(true)
    try {
      const response = await fetch(`/api/v1/voice/calls/${activeCall.call_id}/stop`, {
        method: 'POST',
      })

      if (response.ok) {
        const data = await response.json()
        setCallHistory((prev) => [
          {
            ...activeCall,
            state: 'completed',
            uptime_seconds: data.duration_seconds || activeCall.uptime_seconds,
          },
          ...prev.slice(0, 9),
        ])
        setActiveCall(null)
        setCallQuality(null)
        if (qualityIntervalRef.current) {
          clearInterval(qualityIntervalRef.current)
        }
      }
    } catch (err) {
      setError(isZh ? '停止通话失败' : 'Failed to stop call')
    } finally {
      setLoading(false)
    }
  }, [activeCall, isZh])

  // Update network conditions
  const handleUpdateConditions = useCallback(async () => {
    if (!activeCall) return

    try {
      const response = await fetch(`/api/v1/voice/calls/${activeCall.call_id}/conditions`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latency_ms: latency,
          jitter_ms: jitter,
          packet_loss_percent: packetLoss,
          bandwidth_kbps: bandwidth,
        }),
      })

      if (response.ok) {
        // Refresh call status
        const statusResponse = await fetch(`/api/v1/voice/calls/${activeCall.call_id}/status`)
        if (statusResponse.ok) {
          const status = await statusResponse.json()
          setActiveCall(status)
        }
      }
    } catch (err) {
      console.error('Failed to update conditions:', err)
    }
  }, [activeCall, latency, jitter, packetLoss, bandwidth])

  // Setup and cleanup
  useEffect(() => {
    fetchCodecs()
    return () => {
      if (qualityIntervalRef.current) {
        clearInterval(qualityIntervalRef.current)
      }
    }
  }, [fetchCodecs])

  // Auto-update conditions when active call exists
  useEffect(() => {
    if (activeCall) {
      handleUpdateConditions()
    }
  }, [latency, jitter, packetLoss, bandwidth, activeCall, handleUpdateConditions])

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const selectedCodecConfig = codecs.find((c) => c.id === selectedCodec)

  return (
    <div className="flex flex-col h-full bg-dark-900">
      {/* Header */}
      <div className="px-4 py-3 border-b border-dark-700 bg-dark-800/50">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">
            {isZh ? '语音模拟 (VoIP)' : 'Voice Simulator (VoIP)'}
          </h2>
          {activeCall && (
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <span className="text-sm text-green-400">
                {isZh ? '通话中' : 'Call Active'} - {formatDuration(activeCall.uptime_seconds)}
              </span>
            </div>
          )}
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
        {/* Left Panel - Controls */}
        <div className="w-80 border-r border-dark-700 bg-dark-800/30 overflow-y-auto">
          {/* Codec Selection */}
          <div className="p-4 border-b border-dark-700">
            <h3 className="text-sm font-semibold text-white mb-3">
              {isZh ? '语音编码' : 'Voice Codec'}
            </h3>
            <div className="space-y-2">
              {codecs.map((codec) => (
                <button
                  key={codec.id}
                  onClick={() => setSelectedCodec(codec.id)}
                  disabled={!!activeCall}
                  className={`w-full p-3 rounded-lg border text-left ${
                    selectedCodec === codec.id
                      ? 'bg-neon-cyan/10 border-neon-cyan/50 text-neon-cyan'
                      : 'bg-dark-700/50 border-dark-600 text-dark-300 hover:border-dark-500'
                  } ${activeCall ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <div className="font-medium">{codec.name}</div>
                  <div className="text-xs text-dark-400 mt-1">{codec.description}</div>
                  <div className="flex items-center space-x-2 mt-2 text-xs">
                    <span className="text-dark-500">{codec.bitrate_kbps} kbps</span>
                    <span className="text-dark-600">|</span>
                    <span className="text-dark-500">{codec.sample_rate_hz / 1000} kHz</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Network Conditions */}
          <div className="p-4 border-b border-dark-700">
            <h3 className="text-sm font-semibold text-white mb-3">
              {isZh ? '网络条件' : 'Network Conditions'}
            </h3>
            <div className="space-y-4">
              {/* Latency */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs text-dark-400">{isZh ? '延迟' : 'Latency'}</label>
                  <span className="text-xs text-white font-mono">{latency} ms</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="500"
                  value={latency}
                  onChange={(e) => setLatency(Number(e.target.value))}
                  className="w-full h-2 bg-dark-700 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              {/* Jitter */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs text-dark-400">{isZh ? '抖动' : 'Jitter'}</label>
                  <span className="text-xs text-white font-mono">{jitter} ms</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={jitter}
                  onChange={(e) => setJitter(Number(e.target.value))}
                  className="w-full h-2 bg-dark-700 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              {/* Packet Loss */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs text-dark-400">{isZh ? '丢包率' : 'Packet Loss'}</label>
                  <span className="text-xs text-white font-mono">{packetLoss}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="50"
                  value={packetLoss}
                  onChange={(e) => setPacketLoss(Number(e.target.value))}
                  className="w-full h-2 bg-dark-700 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              {/* Bandwidth */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs text-dark-400">{isZh ? '带宽' : 'Bandwidth'}</label>
                  <span className="text-xs text-white font-mono">{bandwidth} kbps</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="10000"
                  step="10"
                  value={bandwidth}
                  onChange={(e) => setBandwidth(Number(e.target.value))}
                  className="w-full h-2 bg-dark-700 rounded-lg appearance-none cursor-pointer"
                />
              </div>
            </div>
          </div>

          {/* Call Control */}
          <div className="p-4">
            <h3 className="text-sm font-semibold text-white mb-3">
              {isZh ? '通话控制' : 'Call Control'}
            </h3>
            <div className="space-y-3">
              {/* IP Addresses */}
              <div>
                <label className="text-xs text-dark-400 block mb-1">{isZh ? '呼叫方 IP' : 'Caller IP'}</label>
                <input
                  type="text"
                  value={callerIp}
                  onChange={(e) => setCallerIp(e.target.value)}
                  disabled={!!activeCall}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded text-sm text-white font-mono disabled:opacity-50"
                />
              </div>
              <div>
                <label className="text-xs text-dark-400 block mb-1">{isZh ? '被叫方 IP' : 'Callee IP'}</label>
                <input
                  type="text"
                  value={calleeIp}
                  onChange={(e) => setCalleeIp(e.target.value)}
                  disabled={!!activeCall}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded text-sm text-white font-mono disabled:opacity-50"
                />
              </div>

              {/* Start/Stop Button */}
              {activeCall ? (
                <button
                  onClick={handleStopCall}
                  disabled={loading}
                  className="w-full py-3 rounded-lg font-medium bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 disabled:opacity-50"
                >
                  {loading
                    ? (isZh ? '停止中...' : 'Stopping...')
                    : (isZh ? '结束通话' : 'End Call')}
                </button>
              ) : (
                <button
                  onClick={handleStartCall}
                  disabled={loading}
                  className="w-full py-3 rounded-lg font-medium bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30 disabled:opacity-50"
                >
                  {loading
                    ? (isZh ? '连接中...' : 'Connecting...')
                    : (isZh ? '发起通话' : 'Start Call')}
                </button>
              )}
            </div>
          </div>

          {/* Call History */}
          {callHistory.length > 0 && (
            <div className="p-4 border-t border-dark-700">
              <h3 className="text-sm font-semibold text-white mb-3">
                {isZh ? '通话记录' : 'Call History'}
              </h3>
              <div className="space-y-2">
                {callHistory.map((call) => (
                  <div key={call.call_id} className="p-2 bg-dark-700/30 rounded text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-dark-300">{call.codec}</span>
                      <span className="text-dark-500">{formatDuration(call.uptime_seconds)}</span>
                    </div>
                    <div className="text-dark-500 font-mono mt-1">
                      {call.caller_ip} <ArrowRightIcon className="w-4 h-4 inline" /> {call.callee_ip}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Panel - Quality Dashboard */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {activeCall ? (
            <>
              {/* MOS Score Display */}
              <div className="p-6 border-b border-dark-700 bg-dark-800/30">
                <div className="flex items-center justify-center space-x-8">
                  {/* MOS */}
                  <div className="text-center">
                    <div className="text-sm text-dark-400 mb-2">{isZh ? 'MOS 评分' : 'MOS Score'}</div>
                    <div className={`text-5xl font-bold ${MOS_COLORS[getMosCategory(callQuality?.quality_metrics.mos || 4.5)]}`}>
                      {(callQuality?.quality_metrics.mos || activeCall.quality_metrics.mos).toFixed(1)}
                    </div>
                    <div className={`text-sm mt-1 ${MOS_COLORS[getMosCategory(callQuality?.quality_metrics.mos || 4.5)]}`}>
                      {getMosLabel(callQuality?.quality_metrics.mos || activeCall.quality_metrics.mos, isZh)}
                    </div>
                    <div className="text-xs text-dark-500 mt-1">1.0 - 5.0</div>
                  </div>

                  {/* R-Factor */}
                  <div className="text-center">
                    <div className="text-sm text-dark-400 mb-2">{isZh ? 'R 因子' : 'R-Factor'}</div>
                    <div className="text-4xl font-bold text-neon-cyan">
                      {(callQuality?.quality_metrics.r_factor || activeCall.quality_metrics.r_factor).toFixed(0)}
                    </div>
                    <div className="text-xs text-dark-500 mt-1">0 - 100</div>
                  </div>

                  {/* Quality Gauge */}
                  <div className="text-center">
                    <div className="text-sm text-dark-400 mb-2">{isZh ? '质量等级' : 'Quality'}</div>
                    <div className={`px-4 py-2 rounded-lg ${
                      MOS_BG_COLORS[getMosCategory(callQuality?.quality_metrics.mos || 4.5)]
                    }`}>
                      <span className={`text-lg font-bold ${
                        MOS_COLORS[getMosCategory(callQuality?.quality_metrics.mos || 4.5)]
                      }`}>
                        {getMosLabel(callQuality?.quality_metrics.mos || activeCall.quality_metrics.mos, isZh).toUpperCase()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="p-4 border-b border-dark-700">
                <div className="grid grid-cols-4 gap-4">
                  <div className="bg-dark-700/50 rounded-lg p-3">
                    <div className="text-xs text-dark-400">{isZh ? '延迟' : 'Latency'}</div>
                    <div className="text-xl font-bold text-white mt-1">
                      {(callQuality?.quality_metrics.latency_ms || activeCall.quality_metrics.latency_ms).toFixed(1)}
                      <span className="text-sm text-dark-400"> ms</span>
                    </div>
                  </div>
                  <div className="bg-dark-700/50 rounded-lg p-3">
                    <div className="text-xs text-dark-400">{isZh ? '抖动' : 'Jitter'}</div>
                    <div className="text-xl font-bold text-yellow-400 mt-1">
                      {(callQuality?.quality_metrics.jitter_ms || activeCall.quality_metrics.jitter_ms).toFixed(1)}
                      <span className="text-sm text-dark-400"> ms</span>
                    </div>
                  </div>
                  <div className="bg-dark-700/50 rounded-lg p-3">
                    <div className="text-xs text-dark-400">{isZh ? '丢包率' : 'Packet Loss'}</div>
                    <div className="text-xl font-bold text-red-400 mt-1">
                      {(callQuality?.quality_metrics.packet_loss_percent || activeCall.quality_metrics.packet_loss_percent).toFixed(2)}
                      <span className="text-sm text-dark-400">%</span>
                    </div>
                  </div>
                  <div className="bg-dark-700/50 rounded-lg p-3">
                    <div className="text-xs text-dark-400">{isZh ? '已发送包' : 'Packets Sent'}</div>
                    <div className="text-xl font-bold text-green-400 mt-1">
                      {(callQuality?.quality_metrics.packets_sent || activeCall.quality_metrics.packets_sent).toLocaleString()}
                    </div>
                  </div>
                </div>
              </div>

              {/* Quality History Chart (Simple ASCII) */}
              <div className="flex-1 p-4 overflow-y-auto">
                <h3 className="text-sm font-semibold text-white mb-3">
                  {isZh ? '质量历史' : 'Quality History'}
                </h3>
                <div className="bg-dark-800 rounded-lg p-4 font-mono text-xs">
                  {callQuality?.quality_history && callQuality.quality_history.length > 0 ? (
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-dark-400 mb-2">
                        <span>{isZh ? '时间' : 'Time'}</span>
                        <span>MOS</span>
                        <span>{isZh ? '延迟' : 'Lat'}</span>
                        <span>{isZh ? '抖动' : 'Jit'}</span>
                        <span>{isZh ? '丢包' : 'Loss'}</span>
                      </div>
                      {callQuality.quality_history.slice(-20).reverse().map((point, idx) => (
                        <div key={idx} className="flex items-center justify-between">
                          <span className="text-dark-500">
                            {new Date(point.timestamp * 1000).toLocaleTimeString()}
                          </span>
                          <span className={MOS_COLORS[getMosCategory(point.mos)]}>
                            {point.mos.toFixed(2)}
                          </span>
                          <span className="text-dark-300">{point.latency_ms.toFixed(0)}ms</span>
                          <span className="text-yellow-400">{point.jitter_ms.toFixed(0)}ms</span>
                          <span className="text-red-400">{point.packet_loss_percent.toFixed(1)}%</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center text-dark-500 py-8">
                      {isZh ? '等待数据...' : 'Waiting for data...'}
                    </div>
                  )}
                </div>

                {/* Codec Info */}
                <div className="mt-4 bg-dark-800 rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-white mb-2">
                    {isZh ? '编码信息' : 'Codec Information'}
                  </h4>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-dark-400">{isZh ? '编码' : 'Codec'}:</span>
                      <span className="text-white">{activeCall.codec}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-dark-400">{isZh ? '呼叫方' : 'Caller'}:</span>
                      <span className="text-white font-mono">{activeCall.caller_ip}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-dark-400">{isZh ? '被叫方' : 'Callee'}:</span>
                      <span className="text-white font-mono">{activeCall.callee_ip}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-dark-400">{isZh ? '通话时长' : 'Duration'}:</span>
                      <span className="text-white">{formatDuration(activeCall.uptime_seconds)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            /* No Active Call */
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <VoiceIcon className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                <h3 className="text-xl font-semibold text-white mb-2">
                  {isZh ? '开始语音模拟' : 'Start Voice Simulation'}
                </h3>
                <p className="text-dark-400 max-w-md">
                  {isZh
                    ? '选择语音编码，配置网络条件，然后发起模拟通话来测试 VoIP 质量。'
                    : 'Select a voice codec, configure network conditions, and start a simulated call to test VoIP quality.'}
                </p>
                {selectedCodecConfig && (
                  <div className="mt-6 p-4 bg-dark-800 rounded-lg inline-block">
                    <div className="text-sm text-dark-400 mb-2">{isZh ? '当前编码' : 'Current Codec'}</div>
                    <div className="text-lg font-bold text-neon-cyan">{selectedCodecConfig.name}</div>
                    <div className="text-xs text-dark-400 mt-1">{selectedCodecConfig.description}</div>
                    <div className="text-xs text-dark-500 mt-2">
                      {selectedCodecConfig.bitrate_kbps} kbps | {selectedCodecConfig.sample_rate_hz / 1000} kHz
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
