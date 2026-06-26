import { useState, useEffect, useCallback } from 'react'

import axios from 'axios'
import {
  SecurityIcon,
  SensorIcon,
  ConsumerIcon,
  LightingIcon,
  ApplianceIcon,
  EntertainmentIcon,
  IndustrialIcon,
  AutomotiveIcon,
  ClimateIcon,
  BoxIcon,
} from './Icons'

const apiClient = axios.create({
  baseURL: '/api/v1/iot',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

interface NetworkProfile {
  upload_kbps: number
  download_kbps: number
  packet_size_bytes: number
  interval_ms: number
}

interface Device {
  id: string
  name: string
  name_en: string
  description: string
  icon: string
  category: string
  protocols: string[]
  traffic_pattern: string
  default_params: Record<string, unknown>
  network_profile: NetworkProfile
  instance_id: string | null
  state: string
}

interface TrafficStats {
  total_devices: number
  online_devices: number
  total_packets_sent: number
  total_packets_received: number
  total_bytes_sent: number
  total_bytes_received: number
  total_errors: number
  by_pattern: Record<string, { count: number; bytes_sent: number; bytes_received: number }>
  by_category: Record<string, { count: number; bytes_sent: number; bytes_received: number }>
  devices: Array<{
    instance_id: string
    device_id: string
    device_name: string
    state: string
    traffic_pattern: string
    category: string
    stats: Record<string, number>
  }>
}

const categoryColors: Record<string, string> = {
  security: 'bg-red-500/20 text-red-400',
  sensor: 'bg-blue-500/20 text-blue-400',
  consumer: 'bg-purple-500/20 text-purple-400',
  lighting: 'bg-yellow-500/20 text-yellow-400',
  appliance: 'bg-green-500/20 text-green-400',
  entertainment: 'bg-pink-500/20 text-pink-400',
  industrial: 'bg-indigo-500/20 text-indigo-400',
  automotive: 'bg-teal-500/20 text-teal-400',
  climate: 'bg-orange-500/20 text-orange-400',
}

const categoryIconComponents: Record<string, React.FC<{ className?: string; size?: number }>> = {
  security: SecurityIcon,
  sensor: SensorIcon,
  consumer: ConsumerIcon,
  lighting: LightingIcon,
  appliance: ApplianceIcon,
  entertainment: EntertainmentIcon,
  industrial: IndustrialIcon,
  automotive: AutomotiveIcon,
  climate: ClimateIcon,
}

const getCategoryIcon = (category: string, className: string = 'w-6 h-6') => {
  const IconComponent = categoryIconComponents[category] || BoxIcon
  return <IconComponent className={className} />
}

const patternColors: Record<string, string> = {
  continuous: 'text-red-400',
  periodic: 'text-blue-400',
  burst: 'text-yellow-400',
  idle: 'text-gray-400',
}

const stateColors: Record<string, string> = {
  offline: 'bg-gray-500/20 text-gray-400',
  starting: 'bg-yellow-500/20 text-yellow-400',
  online: 'bg-green-500/20 text-green-400',
  error: 'bg-red-500/20 text-red-400',
}

const formatBytes = (bytes: number): string => {
  if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(2)} GB`
  if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(2)} MB`
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(2)} KB`
  return `${bytes} B`
}

const formatNumber = (num: number): string => {
  if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
  return num.toString()
}

const IoTSimulator = () => {
  const [devices, setDevices] = useState<Device[]>([])
  const [trafficStats, setTrafficStats] = useState<TrafficStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [startingDevice, setStartingDevice] = useState<string | null>(null)
  const [stoppingDevice, setStoppingDevice] = useState<string | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchDevices = useCallback(async () => {
    try {
      const params = selectedCategory ? { category: selectedCategory } : {}
      const response = await apiClient.get('/devices', { params })
      setDevices(response.data)
    } catch (err) {
      console.error('Failed to fetch devices:', err)
      setError('Failed to load devices')
    }
  }, [selectedCategory])

  const fetchTrafficStats = useCallback(async () => {
    try {
      const response = await apiClient.get('/traffic')
      setTrafficStats(response.data)
    } catch (err) {
      console.error('Failed to fetch traffic stats:', err)
    }
  }, [])

  useEffect(() => {
    fetchDevices()
    fetchTrafficStats()

    const interval = setInterval(() => {
      fetchDevices()
      fetchTrafficStats()
    }, 3000)

    return () => clearInterval(interval)
  }, [fetchDevices, fetchTrafficStats])

  const handleStartDevice = async (deviceId: string) => {
    setStartingDevice(deviceId)
    setError(null)
    try {
      await apiClient.post('/devices/start', { device_id: deviceId })
      await fetchDevices()
      await fetchTrafficStats()
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to start device'
      setError(message)
    } finally {
      setStartingDevice(null)
    }
  }

  const handleStopDevice = async (instanceId: string) => {
    setStoppingDevice(instanceId)
    setError(null)
    try {
      await apiClient.post(`/devices/${instanceId}/stop`)
      await fetchDevices()
      await fetchTrafficStats()
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to stop device'
      setError(message)
    } finally {
      setStoppingDevice(null)
    }
  }

  const handleStopAll = async () => {
    setLoading(true)
    setError(null)
    try {
      await apiClient.post('/devices/stop-all')
      await fetchDevices()
      await fetchTrafficStats()
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to stop all devices'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const categories = Array.from(new Set(devices.map((d) => d.category)))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">IoT 设备模拟器</h2>
          <p className="text-dark-400 mt-1">模拟常见 IoT 设备的网络行为</p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={handleStopAll}
            disabled={loading || trafficStats?.online_devices === 0}
            className="btn-danger text-sm"
          >
            {loading ? '停止中...' : '全部停止'}
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400">
          {error}
        </div>
      )}

      {/* Traffic Stats Summary */}
      {trafficStats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card p-4">
            <p className="text-xs text-dark-500">在线设备</p>
            <p className="text-2xl font-bold text-green-400">
              {trafficStats.online_devices}/{trafficStats.total_devices}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-dark-500">发送数据</p>
            <p className="text-2xl font-bold text-blue-400">
              {formatBytes(trafficStats.total_bytes_sent)}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-dark-500">接收数据</p>
            <p className="text-2xl font-bold text-purple-400">
              {formatBytes(trafficStats.total_bytes_received)}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-dark-500">数据包</p>
            <p className="text-2xl font-bold text-yellow-400">
              {formatNumber(trafficStats.total_packets_sent + trafficStats.total_packets_received)}
            </p>
          </div>
        </div>
      )}

      {/* Category Filter */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setSelectedCategory(null)}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            selectedCategory === null
              ? 'bg-blue-500 text-white'
              : 'bg-dark-700 text-dark-300 hover:bg-dark-600'
          }`}
        >
          全部
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(selectedCategory === cat ? null : cat)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              selectedCategory === cat
                ? 'bg-blue-500 text-white'
                : 'bg-dark-700 text-dark-300 hover:bg-dark-600'
            }`}
          >
            {getCategoryIcon(cat, 'w-4 h-4 mr-1')} {cat}
          </button>
        ))}
      </div>

      {/* Device Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {devices.map((device) => (
          <div
            key={device.id}
            className={`card p-5 transition-all ${
              device.state === 'online'
                ? 'border-2 border-green-500/50 bg-green-500/5'
                : device.state === 'error'
                ? 'border-2 border-red-500/50 bg-red-500/5'
                : 'hover:border-dark-600'
            }`}
          >
            {/* Device Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center space-x-3">
                {getCategoryIcon(device.category, 'w-8 h-8 text-gray-400')}
                <div>
                  <h3 className="text-lg font-semibold text-white">{device.name}</h3>
                  <span
                    className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                      categoryColors[device.category] || 'bg-dark-700 text-dark-300'
                    }`}
                  >
                    {device.category}
                  </span>
                </div>
              </div>
              <span
                className={`px-2 py-1 rounded-full text-xs font-medium ${
                  stateColors[device.state] || stateColors.offline
                }`}
              >
                {device.state}
              </span>
            </div>

            {/* Description */}
            <p className="text-sm text-dark-400 mb-3">{device.description}</p>

            {/* Protocols */}
            <div className="flex flex-wrap gap-1.5 mb-3">
              {device.protocols.map((protocol) => (
                <span
                  key={protocol}
                  className="px-2 py-0.5 bg-dark-700 text-dark-300 rounded text-xs"
                >
                  {protocol}
                </span>
              ))}
            </div>

            {/* Traffic Pattern */}
            <div className="flex items-center space-x-2 mb-3">
              <span className="text-xs text-dark-500">流量模式:</span>
              <span className={`text-sm font-medium ${patternColors[device.traffic_pattern] || 'text-gray-400'}`}>
                {device.traffic_pattern}
              </span>
            </div>

            {/* Network Profile */}
            <div className="grid grid-cols-2 gap-2 mb-4">
              <div className="bg-dark-800 rounded p-2">
                <p className="text-xs text-dark-500">上行</p>
                <p className="text-sm font-semibold text-blue-400">
                  {device.network_profile.upload_kbps >= 1000
                    ? `${(device.network_profile.upload_kbps / 1000).toFixed(1)} Mbps`
                    : `${device.network_profile.upload_kbps} Kbps`}
                </p>
              </div>
              <div className="bg-dark-800 rounded p-2">
                <p className="text-xs text-dark-500">下行</p>
                <p className="text-sm font-semibold text-purple-400">
                  {device.network_profile.download_kbps >= 1000
                    ? `${(device.network_profile.download_kbps / 1000).toFixed(1)} Mbps`
                    : `${device.network_profile.download_kbps} Kbps`}
                </p>
              </div>
            </div>

            {/* Instance Stats (if running) */}
            {device.state === 'online' && trafficStats && (
              <div className="bg-dark-800/50 rounded-lg p-3 mb-4">
                <p className="text-xs text-dark-500 mb-2">实时统计</p>
                {(() => {
                  const deviceStats = trafficStats.devices.find(
                    (d) => d.device_id === device.id
                  )
                  if (!deviceStats) return null
                  return (
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-dark-500">发送: </span>
                        <span className="text-green-400">
                          {formatBytes(deviceStats.stats.bytes_sent || 0)}
                        </span>
                      </div>
                      <div>
                        <span className="text-dark-500">接收: </span>
                        <span className="text-blue-400">
                          {formatBytes(deviceStats.stats.bytes_received || 0)}
                        </span>
                      </div>
                    </div>
                  )
                })()}
              </div>
            )}

            {/* Action Button */}
            <div className="flex justify-end">
              {device.state === 'online' ? (
                <button
                  onClick={() => device.instance_id && handleStopDevice(device.instance_id)}
                  disabled={stoppingDevice === device.instance_id}
                  className="btn-danger text-sm"
                >
                  {stoppingDevice === device.instance_id ? '停止中...' : '停止'}
                </button>
              ) : (
                <button
                  onClick={() => handleStartDevice(device.id)}
                  disabled={startingDevice === device.id}
                  className="btn-primary text-sm"
                >
                  {startingDevice === device.id ? '启动中...' : '启动'}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Traffic Pattern Distribution */}
      {trafficStats && Object.keys(trafficStats.by_pattern).length > 0 && (
        <div className="card p-5">
          <h3 className="text-lg font-semibold text-white mb-4">流量模式分布</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(trafficStats.by_pattern).map(([pattern, stats]) => (
              <div key={pattern} className="bg-dark-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className={`font-medium ${patternColors[pattern] || 'text-gray-400'}`}>
                    {pattern}
                  </span>
                  <span className="text-xs text-dark-500">{stats.count} 设备</span>
                </div>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-dark-500">发送</span>
                    <span className="text-blue-400">{formatBytes(stats.bytes_sent)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-dark-500">接收</span>
                    <span className="text-purple-400">{formatBytes(stats.bytes_received)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Category Distribution */}
      {trafficStats && Object.keys(trafficStats.by_category).length > 0 && (
        <div className="card p-5">
          <h3 className="text-lg font-semibold text-white mb-4">设备分类统计</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {Object.entries(trafficStats.by_category).map(([category, stats]) => (
              <div key={category} className="bg-dark-800 rounded-lg p-3 text-center">
                <div className="flex justify-center mb-1">{getCategoryIcon(category, 'w-6 h-6')}</div>
                <p className="text-sm font-medium text-white">{category}</p>
                <p className="text-xs text-dark-400">{stats.count} 设备</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default IoTSimulator
