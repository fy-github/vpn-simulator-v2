import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { ArrowRightIcon, ArrowLeftIcon } from './Icons'

interface PacketField {
  name: string
  offset: number
  length: number
  value: string
  description: string
  field_type: string
}

interface Packet {
  id: string
  timestamp: string
  direction: string
  packet_type: string
  protocol: string
  src_ip: string
  dst_ip: string
  src_port: number
  dst_port: number
  raw_data_hex: string
  fields: PacketField[]
  parsed: boolean
  parse_error: string | null
  connection_id: string | null
  session_id: string | null
}

interface PacketStatistics {
  total: number
  by_protocol: Record<string, number>
  by_direction: Record<string, number>
  by_type: Record<string, number>
}

const directionColors: Record<string, string> = {
  incoming: 'text-blue-400',
  outgoing: 'text-green-400',
}

const typeColors: Record<string, string> = {
  control: 'text-purple-400',
  data: 'text-cyan-400',
  error: 'text-red-400',
}

const protocolColors: Record<string, string> = {
  pptp: 'text-orange-400',
  l2tp: 'text-yellow-400',
  openvpn: 'text-green-400',
  ipsec: 'text-blue-400',
  ikev2: 'text-indigo-400',
  wireguard: 'text-teal-400',
}

export default function PacketViewer() {
  const { i18n } = useTranslation()
  const isZh = i18n.language === 'zh-CN'

  const [packets, setPackets] = useState<Packet[]>([])
  const [selectedPacket, setSelectedPacket] = useState<Packet | null>(null)
  const [statistics, setStatistics] = useState<PacketStatistics | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [searchQuery, setSearchQuery] = useState('')
  const [filterProtocol, setFilterProtocol] = useState<string>('')
  const [filterDirection, setFilterDirection] = useState<string>('')
  const [filterType, setFilterType] = useState<string>('')

  const [protocols, setProtocols] = useState<string[]>([])

  const fetchPackets = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string> = {}
      if (filterProtocol) params.protocol = filterProtocol
      if (filterDirection) params.direction = filterDirection
      if (filterType) params.packet_type = filterType

      const response = await api.getPackets(params)
      setPackets(response.data.packets)
    } catch (err) {
      setError(isZh ? '获取报文失败' : 'Failed to fetch packets')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [filterProtocol, filterDirection, filterType, isZh])

  const fetchStatistics = useCallback(async () => {
    try {
      const response = await api.getPacketStatistics()
      setStatistics(response.data)
    } catch (err) {
      console.error('Failed to fetch statistics:', err)
    }
  }, [])

  const fetchProtocols = useCallback(async () => {
    try {
      const response = await api.getPacketProtocols()
      setProtocols(response.data.protocols)
    } catch (err) {
      console.error('Failed to fetch protocols:', err)
    }
  }, [])

  useEffect(() => {
    fetchPackets()
    fetchStatistics()
    fetchProtocols()
  }, [fetchPackets, fetchStatistics, fetchProtocols])

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      fetchPackets()
      return
    }

    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string> = {}
      if (filterProtocol) params.protocol = filterProtocol
      const response = await api.searchPackets(searchQuery, params)
      setPackets(response.data)
    } catch (err) {
      setError(isZh ? '搜索失败' : 'Search failed')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateSamples = async () => {
    setLoading(true)
    try {
      await api.generateSamplePackets()
      fetchPackets()
      fetchStatistics()
    } catch (err) {
      setError(isZh ? '生成示例失败' : 'Failed to generate samples')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleClearPackets = async () => {
    try {
      await api.clearPackets()
      setPackets([])
      setSelectedPacket(null)
      setStatistics(null)
    } catch (err) {
      setError(isZh ? '清空失败' : 'Failed to clear packets')
      console.error(err)
    }
  }

  const handleExportPcap = async () => {
    try {
      const params: Record<string, string> = {}
      if (filterProtocol) params.protocol = filterProtocol
      if (filterDirection) params.direction = filterDirection
      if (filterType) params.packet_type = filterType

      const response = await api.exportPcap(params)
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'packets.pcap')
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      setError(isZh ? '导出失败' : 'Export failed')
      console.error(err)
    }
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString()
  }

  const formatHex = (hex: string) => {
    if (!hex) return ''
    return hex.match(/.{1,2}/g)?.join(' ') || hex
  }

  return (
    <div className="flex flex-col h-full bg-dark-900">
      {/* Header */}
      <div className="px-4 py-3 border-b border-dark-700 bg-dark-800/50">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">
            {isZh ? '报文查看器' : 'Packet Viewer'}
          </h2>
          <div className="flex space-x-2">
            <button
              onClick={handleGenerateSamples}
              disabled={loading}
              className="px-3 py-1.5 text-xs font-medium rounded bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/30 hover:bg-neon-cyan/30 disabled:opacity-50"
            >
              {isZh ? '生成示例' : 'Generate Samples'}
            </button>
            <button
              onClick={handleExportPcap}
              className="px-3 py-1.5 text-xs font-medium rounded bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30"
            >
              {isZh ? '导出 PCAP' : 'Export PCAP'}
            </button>
            <button
              onClick={handleClearPackets}
              className="px-3 py-1.5 text-xs font-medium rounded bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30"
            >
              {isZh ? '清空' : 'Clear'}
            </button>
          </div>
        </div>

        {/* Statistics */}
        {statistics && (
          <div className="mt-2 flex space-x-4 text-xs text-dark-400">
            <span>{isZh ? '总数' : 'Total'}: {statistics.total}</span>
            {Object.entries(statistics.by_protocol).map(([protocol, count]) => (
              <span key={protocol} className={protocolColors[protocol] || 'text-dark-400'}>
                {protocol.toUpperCase()}: {count}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Filters and Search */}
      <div className="px-4 py-2 border-b border-dark-700 bg-dark-800/30">
        <div className="flex space-x-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder={isZh ? '搜索报文...' : 'Search packets...'}
            className="flex-1 px-3 py-1.5 text-sm bg-dark-800 border border-dark-600 rounded text-white placeholder-dark-400 focus:outline-none focus:border-neon-cyan"
          />
          <select
            value={filterProtocol}
            onChange={(e) => setFilterProtocol(e.target.value)}
            className="px-3 py-1.5 text-sm bg-dark-800 border border-dark-600 rounded text-white focus:outline-none focus:border-neon-cyan"
          >
            <option value="">{isZh ? '所有协议' : 'All Protocols'}</option>
            {protocols.map((p) => (
              <option key={p} value={p}>{p.toUpperCase()}</option>
            ))}
          </select>
          <select
            value={filterDirection}
            onChange={(e) => setFilterDirection(e.target.value)}
            className="px-3 py-1.5 text-sm bg-dark-800 border border-dark-600 rounded text-white focus:outline-none focus:border-neon-cyan"
          >
            <option value="">{isZh ? '所有方向' : 'All Directions'}</option>
            <option value="incoming">{isZh ? '入站' : 'Incoming'}</option>
            <option value="outgoing">{isZh ? '出站' : 'Outgoing'}</option>
          </select>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-1.5 text-sm bg-dark-800 border border-dark-600 rounded text-white focus:outline-none focus:border-neon-cyan"
          >
            <option value="">{isZh ? '所有类型' : 'All Types'}</option>
            <option value="control">{isZh ? '控制' : 'Control'}</option>
            <option value="data">{isZh ? '数据' : 'Data'}</option>
            <option value="error">{isZh ? '错误' : 'Error'}</option>
          </select>
          <button
            onClick={handleSearch}
            className="px-4 py-1.5 text-sm font-medium rounded bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/30 hover:bg-neon-cyan/30"
          >
            {isZh ? '搜索' : 'Search'}
          </button>
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
        {/* Packet List */}
        <div className="w-1/2 border-r border-dark-700 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-full text-dark-400">
              {isZh ? '加载中...' : 'Loading...'}
            </div>
          ) : packets.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-dark-400">
              <p>{isZh ? '没有报文数据' : 'No packet data'}</p>
              <button
                onClick={handleGenerateSamples}
                className="mt-2 text-neon-cyan hover:underline"
              >
                {isZh ? '生成示例数据' : 'Generate sample data'}
              </button>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-dark-800/50 sticky top-0">
                <tr className="text-dark-400 text-left">
                  <th className="px-3 py-2 font-medium">{isZh ? '时间' : 'Time'}</th>
                  <th className="px-3 py-2 font-medium">{isZh ? '协议' : 'Protocol'}</th>
                  <th className="px-3 py-2 font-medium">{isZh ? '方向' : 'Dir'}</th>
                  <th className="px-3 py-2 font-medium">{isZh ? '类型' : 'Type'}</th>
                  <th className="px-3 py-2 font-medium">{isZh ? '源' : 'Source'}</th>
                  <th className="px-3 py-2 font-medium">{isZh ? '目的' : 'Dest'}</th>
                </tr>
              </thead>
              <tbody>
                {packets.map((packet) => (
                  <tr
                    key={packet.id}
                    onClick={() => setSelectedPacket(packet)}
                    className={`cursor-pointer hover:bg-dark-800/50 ${
                      selectedPacket?.id === packet.id ? 'bg-neon-cyan/10' : ''
                    }`}
                  >
                    <td className="px-3 py-2 font-mono text-dark-300">
                      {formatTimestamp(packet.timestamp)}
                    </td>
                    <td className={`px-3 py-2 font-medium ${protocolColors[packet.protocol] || 'text-dark-300'}`}>
                      {packet.protocol.toUpperCase()}
                    </td>
                    <td className={`px-3 py-2 ${directionColors[packet.direction] || 'text-dark-300'}`}>
                      {packet.direction === 'incoming' ? <ArrowRightIcon className="w-4 h-4 inline" /> : <ArrowLeftIcon className="w-4 h-4 inline" />}
                    </td>
                    <td className={`px-3 py-2 ${typeColors[packet.packet_type] || 'text-dark-300'}`}>
                      {packet.packet_type}
                    </td>
                    <td className="px-3 py-2 font-mono text-dark-300">
                      {packet.src_ip}:{packet.src_port}
                    </td>
                    <td className="px-3 py-2 font-mono text-dark-300">
                      {packet.dst_ip}:{packet.dst_port}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Packet Detail */}
        <div className="w-1/2 overflow-y-auto">
          {selectedPacket ? (
            <div className="p-4">
              {/* Packet Header */}
              <div className="mb-4 p-3 bg-dark-800/50 rounded-lg border border-dark-700">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-white">
                    {isZh ? '报文详情' : 'Packet Details'}
                  </h3>
                  <span className={`text-xs px-2 py-0.5 rounded ${protocolColors[selectedPacket.protocol] || 'text-dark-300'} bg-dark-700`}>
                    {selectedPacket.protocol.toUpperCase()}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs text-dark-400">
                  <div>
                    <span className="text-dark-500">{isZh ? 'ID:' : 'ID:'}</span>{' '}
                    <span className="font-mono">{selectedPacket.id.slice(0, 8)}...</span>
                  </div>
                  <div>
                    <span className="text-dark-500">{isZh ? '时间:' : 'Time:'}</span>{' '}
                    <span className="font-mono">{new Date(selectedPacket.timestamp).toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-dark-500">{isZh ? '方向:' : 'Direction:'}</span>{' '}
                    <span className={directionColors[selectedPacket.direction]}>
                      {selectedPacket.direction === 'incoming' ? (isZh ? '入站' : 'Incoming') : (isZh ? '出站' : 'Outgoing')}
                    </span>
                  </div>
                  <div>
                    <span className="text-dark-500">{isZh ? '类型:' : 'Type:'}</span>{' '}
                    <span className={typeColors[selectedPacket.packet_type]}>
                      {selectedPacket.packet_type}
                    </span>
                  </div>
                  <div>
                    <span className="text-dark-500">{isZh ? '源:' : 'Source:'}</span>{' '}
                    <span className="font-mono">{selectedPacket.src_ip}:{selectedPacket.src_port}</span>
                  </div>
                  <div>
                    <span className="text-dark-500">{isZh ? '目的:' : 'Destination:'}</span>{' '}
                    <span className="font-mono">{selectedPacket.dst_ip}:{selectedPacket.dst_port}</span>
                  </div>
                </div>
              </div>

              {/* Fields Tree */}
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-white mb-2">
                  {isZh ? '字段解析' : 'Field Parsing'}
                </h4>
                {selectedPacket.parsed ? (
                  <div className="bg-dark-800 rounded-lg border border-dark-700 overflow-hidden">
                    <table className="w-full text-xs">
                      <thead className="bg-dark-700/50">
                        <tr className="text-dark-400 text-left">
                          <th className="px-3 py-2 font-medium">{isZh ? '字段' : 'Field'}</th>
                          <th className="px-3 py-2 font-medium">{isZh ? '偏移' : 'Offset'}</th>
                          <th className="px-3 py-2 font-medium">{isZh ? '长度' : 'Len'}</th>
                          <th className="px-3 py-2 font-medium">{isZh ? '值' : 'Value'}</th>
                          <th className="px-3 py-2 font-medium">{isZh ? '描述' : 'Description'}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedPacket.fields.map((field, index) => (
                          <tr
                            key={index}
                            className="border-t border-dark-700 hover:bg-dark-700/30 group"
                          >
                            <td className="px-3 py-2 font-mono text-neon-cyan">
                              {field.name}
                            </td>
                            <td className="px-3 py-2 font-mono text-dark-400">
                              {field.offset}
                            </td>
                            <td className="px-3 py-2 font-mono text-dark-400">
                              {field.length}
                            </td>
                            <td className="px-3 py-2 font-mono text-yellow-400 max-w-[200px] truncate">
                              {field.value}
                            </td>
                            <td className="px-3 py-2 text-dark-400 group-hover:text-dark-300">
                              {field.description}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="p-3 bg-dark-800 rounded-lg border border-dark-700 text-dark-400 text-sm">
                    {selectedPacket.parse_error || (isZh ? '未解析' : 'Not parsed')}
                  </div>
                )}
              </div>

              {/* Raw Data */}
              <div>
                <h4 className="text-sm font-semibold text-white mb-2">
                  {isZh ? '原始数据' : 'Raw Data'}
                </h4>
                <div className="p-3 bg-dark-800 rounded-lg border border-dark-700">
                  <pre className="text-xs font-mono text-dark-300 overflow-x-auto whitespace-pre-wrap break-all">
                    {formatHex(selectedPacket.raw_data_hex)}
                  </pre>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-dark-400">
              {isZh ? '选择一个报文查看详情' : 'Select a packet to view details'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
