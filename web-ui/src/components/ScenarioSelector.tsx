import { useTranslation } from 'react-i18next'
import { SmartphoneIcon, SatelliteIcon, WifiIcon, PlugIcon, GlobeIcon } from './Icons'

interface Scenario {
  id: string
  name: string
  description: string
  icon: string
  category: string
  faults: Record<string, Record<string, number>>
  active: boolean
}

interface ScenarioSelectorProps {
  scenario: Scenario
  onApply: (id: string) => void
  onRemove: (id: string) => void
  applying: boolean
}

const categoryColors: Record<string, string> = {
  mobile: 'bg-blue-500/20 text-blue-400',
  satellite: 'bg-purple-500/20 text-purple-400',
  wifi: 'bg-yellow-500/20 text-yellow-400',
  wired: 'bg-green-500/20 text-green-400',
}

const categoryIconComponents: Record<string, React.FC<{ className?: string; size?: number }>> = {
  mobile: SmartphoneIcon,
  satellite: SatelliteIcon,
  wifi: WifiIcon,
  wired: PlugIcon,
}

const getCategoryIcon = (category: string, className: string = 'w-6 h-6') => {
  const IconComponent = categoryIconComponents[category] || GlobeIcon
  return <IconComponent className={className} />
}

const ScenarioSelector = ({ scenario, onApply, onRemove, applying }: ScenarioSelectorProps) => {
  const { t } = useTranslation()

  const formatBandwidth = (kbps: number) => {
    if (kbps >= 1000000) return `${kbps / 1000000}Gbps`
    if (kbps >= 1000) return `${kbps / 1000}Mbps`
    return `${kbps}Kbps`
  }

  const latency = scenario.faults.latency?.delay_ms
  const jitter = scenario.faults.latency?.jitter_ms
  const lossRate = scenario.faults.packet_loss?.loss_rate
  const bandwidth = scenario.faults.bandwidth?.bandwidth_kbps

  return (
    <div
      className={`card p-6 transition-all ${
        scenario.active
          ? 'border-2 border-green-500 bg-green-500/5'
          : 'hover:border-dark-600'
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
          {getCategoryIcon(scenario.category, 'w-8 h-8 text-gray-400')}
          <div>
            <h3 className="text-lg font-semibold text-white">{scenario.name}</h3>
            <span
              className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                categoryColors[scenario.category] || 'bg-dark-700 text-dark-300'
              }`}
            >
              {scenario.category}
            </span>
          </div>
        </div>
        {scenario.active && (
          <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
            {t('scenarios.active')}
          </span>
        )}
      </div>

      {/* Description */}
      <p className="text-sm text-dark-400 mb-4">{scenario.description}</p>

      {/* Parameters */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        {latency != null && (
          <div className="bg-dark-800 rounded-lg p-3">
            <p className="text-xs text-dark-500">{t('scenarios.params.latency')}</p>
            <p className="text-lg font-semibold text-white">
              {latency}ms
              {jitter != null && (
                <span className="text-xs text-dark-400 ml-1">+/-{jitter}ms</span>
              )}
            </p>
          </div>
        )}
        {lossRate != null && (
          <div className="bg-dark-800 rounded-lg p-3">
            <p className="text-xs text-dark-500">{t('scenarios.params.packetLoss')}</p>
            <p className="text-lg font-semibold text-white">
              {(lossRate * 100).toFixed(1)}%
            </p>
          </div>
        )}
        {bandwidth != null && (
          <div className="bg-dark-800 rounded-lg p-3 col-span-2">
            <p className="text-xs text-dark-500">{t('scenarios.params.bandwidth')}</p>
            <p className="text-lg font-semibold text-white">
              {formatBandwidth(bandwidth)}
            </p>
          </div>
        )}
      </div>

      {/* Action Button */}
      <div className="flex justify-end">
        {scenario.active ? (
          <button
            onClick={() => onRemove(scenario.id)}
            disabled={applying}
            className="btn-danger text-sm"
          >
            {applying ? t('common.removing') : t('scenarios.removeScenario')}
          </button>
        ) : (
          <button
            onClick={() => onApply(scenario.id)}
            disabled={applying}
            className="btn-primary text-sm"
          >
            {applying ? t('common.applying') : t('scenarios.applyScenario')}
          </button>
        )}
      </div>
    </div>
  )
}

export default ScenarioSelector
