import { useTranslation } from 'react-i18next'
import { CheckIcon, XIcon } from './Icons'

export interface StateData {
  name: string
  description: string
  phase: string
  is_initial: boolean
  is_final: boolean
}

export interface TransitionData {
  from_state: string
  to_state: string
  event: string
  description: string
  phase: string
}

export interface ProtocolStateData {
  name: string
  description: string
  states: StateData[]
  transitions: TransitionData[]
}

interface StateMachineViewerProps {
  protocol: ProtocolStateData
  highlightPhases: string[]
  differentPhases: string[]
}

const phaseColors: Record<string, { bg: string; border: string; text: string; label: string; labelEn: string }> = {
  connection_init: { bg: 'bg-slate-800', border: 'border-slate-500', text: 'text-slate-300', label: '连接初始化', labelEn: 'Connection Init' },
  control_channel: { bg: 'bg-blue-900/50', border: 'border-blue-500', text: 'text-blue-300', label: '控制通道', labelEn: 'Control Channel' },
  key_exchange: { bg: 'bg-purple-900/50', border: 'border-purple-500', text: 'text-purple-300', label: '密钥交换', labelEn: 'Key Exchange' },
  authentication: { bg: 'bg-amber-900/50', border: 'border-amber-500', text: 'text-amber-300', label: '认证', labelEn: 'Authentication' },
  tunnel_setup: { bg: 'bg-teal-900/50', border: 'border-teal-500', text: 'text-teal-300', label: '隧道建立', labelEn: 'Tunnel Setup' },
  connected: { bg: 'bg-green-900/50', border: 'border-green-500', text: 'text-green-300', label: '已连接', labelEn: 'Connected' },
  error: { bg: 'bg-red-900/50', border: 'border-red-500', text: 'text-red-300', label: '错误', labelEn: 'Error' },
}

function getPhaseColor(phase: string) {
  return phaseColors[phase] || phaseColors.tunnel_setup
}

function isCommonPhase(phase: string, highlightPhases: string[]) {
  return highlightPhases.includes(phase)
}

function isDifferentPhase(phase: string, differentPhases: string[]) {
  return differentPhases.includes(phase)
}

export default function StateMachineViewer({ protocol, highlightPhases, differentPhases }: StateMachineViewerProps) {
  const { i18n } = useTranslation()
  const isZh = i18n.language === 'zh-CN'

  const normalStates = protocol.states.filter(s => !s.is_final)
  const finalStates = protocol.states.filter(s => s.is_final)

  return (
    <div className="flex flex-col h-full">
      {/* Protocol Header */}
      <div className="px-4 py-3 border-b border-dark-700 bg-dark-800/50">
        <h3 className="text-lg font-bold text-white">{protocol.name}</h3>
        <p className="text-xs text-dark-400 mt-1">{protocol.description}</p>
      </div>

      {/* State Flow */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {/* Legend */}
        <div className="flex flex-wrap gap-2 mb-4">
          {Object.entries(phaseColors).filter(([k]) => k !== 'error').map(([key, val]) => {
            const common = isCommonPhase(key, highlightPhases)
            const diff = isDifferentPhase(key, differentPhases)
            return (
              <span
                key={key}
                className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${
                  common ? 'border-neon-cyan bg-neon-cyan/10 text-neon-cyan' :
                  diff ? 'border-yellow-500 bg-yellow-500/10 text-yellow-400' :
                  `${val.border} ${val.bg} ${val.text}`
                }`}
              >
                {common && <CheckIcon className="w-3 h-3 mr-1" />}
                {diff && <XIcon className="w-3 h-3 mr-1" />}
                {isZh ? val.label : val.labelEn}
              </span>
            )
          })}
        </div>

        {/* States as flow */}
        <div className="space-y-2">
          {normalStates.map((state) => {
            const pc = getPhaseColor(state.phase)
            const common = isCommonPhase(state.phase, highlightPhases)
            const diff = isDifferentPhase(state.phase, differentPhases)
            const outgoingTransitions = protocol.transitions.filter(t => t.from_state === state.name)

            return (
              <div key={state.name}>
                {/* State Node */}
                <div
                  className={`relative p-3 rounded-lg border ${pc.bg} ${pc.border} ${
                    common ? 'ring-1 ring-neon-cyan/50' : ''
                  } ${diff ? 'ring-1 ring-yellow-500/50' : ''}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {state.is_initial && (
                        <span className="text-xs bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded">
                          {isZh ? '起始' : 'INIT'}
                        </span>
                      )}
                      <span className={`font-mono text-sm font-semibold ${pc.text}`}>
                        {state.name}
                      </span>
                    </div>
                    <div className="flex items-center space-x-2">
                      {common && (
                        <span className="text-xs bg-neon-cyan/20 text-neon-cyan px-1.5 py-0.5 rounded border border-neon-cyan/30 flex items-center">
                          <CheckIcon className="w-3 h-3 mr-1" /> {isZh ? '相同阶段' : 'Same Phase'}
                        </span>
                      )}
                      {diff && (
                        <span className="text-xs bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded border border-yellow-500/30 flex items-center">
                          <XIcon className="w-3 h-3 mr-1" /> {isZh ? '差异阶段' : 'Different'}
                        </span>
                      )}
                      <span className={`text-xs px-1.5 py-0.5 rounded ${pc.bg} ${pc.text} border ${pc.border}`}>
                        {isZh ? pc.label : pc.labelEn}
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-dark-400 mt-1">{state.description}</p>
                </div>

                {/* Arrow + Transitions */}
                {outgoingTransitions.length > 0 && (
                  <div className="flex flex-col items-center my-1">
                    {outgoingTransitions.map((t, ti) => {
                      const targetState = protocol.states.find(s => s.name === t.to_state)
                      const targetPhase = targetState?.phase || ''
                      const isError = targetPhase === 'error'

                      return (
                        <div key={ti} className="flex flex-col items-center w-full">
                          <div className={`flex flex-col items-center ${isError ? 'opacity-50' : ''}`}>
                            <svg width="2" height="16" className="text-dark-500">
                              <line x1="1" y1="0" x2="1" y2="16" stroke="currentColor" strokeWidth="2" strokeDasharray={isError ? "4,4" : "none"} />
                            </svg>
                            <div className={`text-xs px-2 py-0.5 rounded ${
                              isError ? 'bg-red-900/30 text-red-400 border border-red-800' : 'bg-dark-700 text-dark-300 border border-dark-600'
                            }`}>
                              <span className="font-mono">{t.event}</span>
                              {t.description && (
                                <span className="ml-1 text-dark-500">- {t.description}</span>
                              )}
                            </div>
                            <svg width="2" height="8" className="text-dark-500">
                              <line x1="1" y1="0" x2="1" y2="8" stroke="currentColor" strokeWidth="2" strokeDasharray={isError ? "4,4" : "none"} />
                            </svg>
                            {!isError && (
                              <svg width="12" height="8" className="text-dark-500 -mt-1">
                                <polygon points="6,0 0,8 12,8" fill="currentColor" />
                              </svg>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}

          {/* Final States */}
          {finalStates.length > 0 && (
            <div className="mt-4 pt-4 border-t border-dark-700">
              <p className="text-xs text-dark-500 mb-2">{isZh ? '终态' : 'Final States'}</p>
              <div className="flex flex-wrap gap-2">
                {finalStates.map(state => {
                  const pc = getPhaseColor(state.phase)
                  return (
                    <div
                      key={state.name}
                      className={`px-3 py-2 rounded-lg border ${pc.bg} ${pc.border}`}
                    >
                      <span className={`font-mono text-sm ${pc.text}`}>{state.name}</span>
                      <p className="text-xs text-dark-400">{state.description}</p>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Stats Footer */}
      <div className="px-4 py-2 border-t border-dark-700 bg-dark-800/50 flex items-center justify-between text-xs text-dark-400">
        <span>{isZh ? '状态数' : 'States'}: {protocol.states.length}</span>
        <span>{isZh ? '转换数' : 'Transitions'}: {protocol.transitions.length}</span>
      </div>
    </div>
  )
}
