import { useTranslation } from 'react-i18next'
import { useState, useEffect } from 'react'
import StateMachineViewer, { type ProtocolStateData } from './StateMachineViewer'
import { api } from '../api/client'
import { CheckIcon, XIcon, RefreshCwIcon } from './Icons'

interface ProtocolOption {
  name: string
  description: string
}

interface ComparisonData {
  protocol1: ProtocolStateData
  protocol2: ProtocolStateData
  common_phases: string[]
  different_phases: string[]
}

export default function ProtocolComparator() {
  const { i18n } = useTranslation()
  const isZh = i18n.language === 'zh-CN'

  const [protocols, setProtocols] = useState<ProtocolOption[]>([])
  const [selectedP1, setSelectedP1] = useState<string>('')
  const [selectedP2, setSelectedP2] = useState<string>('')
  const [comparison, setComparison] = useState<ComparisonData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchProtocols = async () => {
      try {
        const res = await api.getComparisonProtocols()
        setProtocols(res.data)
        if (res.data.length >= 2) {
          setSelectedP1(res.data[0].name)
          setSelectedP2(res.data[1].name)
        }
      } catch {
        setProtocols([
          { name: 'pptp', description: 'PPTP' },
          { name: 'l2tp', description: 'L2TP' },
          { name: 'openvpn', description: 'OpenVPN' },
          { name: 'ipsec', description: 'IPSec' },
          { name: 'ikev2', description: 'IKEv2' },
          { name: 'wireguard', description: 'WireGuard' },
        ])
        setSelectedP1('pptp')
        setSelectedP2('l2tp')
      }
    }
    fetchProtocols()
  }, [])

  const handleCompare = async () => {
    if (!selectedP1 || !selectedP2 || selectedP1 === selectedP2) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.compareProtocols(selectedP1, selectedP2)
      setComparison(res.data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to compare'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (selectedP1 && selectedP2 && selectedP1 !== selectedP2) {
      handleCompare()
    }
  }, [selectedP1, selectedP2])

  const swapProtocols = () => {
    setSelectedP1(selectedP2)
    setSelectedP2(selectedP1)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Selector Bar */}
      <div className="flex items-center gap-4 p-4 bg-dark-900 border-b border-dark-700">
        <div className="flex-1">
          <label className="block text-xs text-dark-400 mb-1">{isZh ? '协议 A' : 'Protocol A'}</label>
          <select
            value={selectedP1}
            onChange={e => setSelectedP1(e.target.value)}
            className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white text-sm focus:border-neon-cyan focus:outline-none"
          >
            {protocols.map(p => (
              <option key={p.name} value={p.name} disabled={p.name === selectedP2}>
                {p.name.toUpperCase()}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={swapProtocols}
          className="mt-5 p-2 rounded-lg bg-dark-800 border border-dark-600 text-dark-300 hover:text-neon-cyan hover:border-neon-cyan/30 transition-colors"
          title={isZh ? '交换' : 'Swap'}
        >
          <RefreshCwIcon className="w-4 h-4" />
        </button>

        <div className="flex-1">
          <label className="block text-xs text-dark-400 mb-1">{isZh ? '协议 B' : 'Protocol B'}</label>
          <select
            value={selectedP2}
            onChange={e => setSelectedP2(e.target.value)}
            className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white text-sm focus:border-neon-cyan focus:outline-none"
          >
            {protocols.map(p => (
              <option key={p.name} value={p.name} disabled={p.name === selectedP1}>
                {p.name.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-neon-cyan"></div>
        </div>
      ) : error ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-red-400 text-sm">{error}</div>
        </div>
      ) : comparison ? (
        <div className="flex-1 flex overflow-hidden">
          {/* Phase Summary */}
          <div className="w-full flex flex-col">
            {/* Common/Different phases banner */}
            <div className="px-4 py-2 bg-dark-800/80 border-b border-dark-700 flex flex-wrap gap-3 text-xs">
              {comparison.common_phases.length > 0 && (
                <div className="flex items-center gap-1">
                  <span className="text-dark-400">{isZh ? '相同阶段:' : 'Common:'}</span>
                  {comparison.common_phases.map(p => (
                    <span key={p} className="px-1.5 py-0.5 rounded bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 flex items-center">
                      <CheckIcon className="w-3 h-3 mr-1" /> {p}
                    </span>
                  ))}
                </div>
              )}
              {comparison.different_phases.length > 0 && (
                <div className="flex items-center gap-1">
                  <span className="text-dark-400">{isZh ? '差异阶段:' : 'Different:'}</span>
                  {comparison.different_phases.map(p => (
                    <span key={p} className="px-1.5 py-0.5 rounded bg-yellow-500/10 text-yellow-400 border border-yellow-500/30 flex items-center">
                      <XIcon className="w-3 h-3 mr-1" /> {p}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Side by side comparison */}
            <div className="flex-1 flex overflow-hidden">
              <div className="flex-1 border-r border-dark-700 overflow-y-auto">
                <StateMachineViewer
                  protocol={comparison.protocol1}
                  highlightPhases={comparison.common_phases}
                  differentPhases={comparison.different_phases}
                />
              </div>
              <div className="flex-1 overflow-y-auto">
                <StateMachineViewer
                  protocol={comparison.protocol2}
                  highlightPhases={comparison.common_phases}
                  differentPhases={comparison.different_phases}
                />
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-dark-500 text-sm">
          {isZh ? '选择两个协议开始对比' : 'Select two protocols to compare'}
        </div>
      )}
    </div>
  )
}
