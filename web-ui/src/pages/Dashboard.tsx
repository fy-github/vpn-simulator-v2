import { useTranslation } from 'react-i18next'
import { useEffect, useState, useCallback, useRef } from 'react'

import { ConnectionIcon, ProtocolIcon, ClockIcon, VendorCLIIcon, PlayIcon, StopIcon, RefreshCwIcon, SettingsIcon, ChevronUpIcon, ChevronDownIcon, EyeIcon, EyeOffIcon } from '../components/Icons'
import { api } from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/Dialog'

interface ProtocolStatus {
  name: string
  status: 'running' | 'stopped' | 'error'
  port: number
  connections: number
}

interface SystemStats {
  totalConnections: number
  activeProtocols: number
  uptime: string
  memoryUsage: number
  memoryPercent: number
  cpuUsage: number
}

interface ProtocolPreference {
  name: string
  visible: boolean
  order: number
}

const STORAGE_KEY = 'dashboard_protocol_prefs'

const loadPreferences = (protocolNames: string[]): ProtocolPreference[] => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored) as ProtocolPreference[]
      const storedNames = new Set(parsed.map(p => p.name))
      const newProtocols = protocolNames.filter(n => !storedNames.has(n))
      return [
        ...parsed.filter(p => protocolNames.includes(p.name)),
        ...newProtocols.map((name, i) => ({ name, visible: true, order: parsed.length + i })),
      ]
    }
  } catch {}
  return protocolNames.map((name, i) => ({ name, visible: true, order: i }))
}

const savePreferences = (prefs: ProtocolPreference[]) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
}

const Dashboard = () => {
  const { t } = useTranslation()
  const [protocols, setProtocols] = useState<ProtocolStatus[]>([])
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [showSettings, setShowSettings] = useState(false)
  const [preferences, setPreferences] = useState<ProtocolPreference[]>([])
  const statsRef = useRef<HTMLDivElement>(null)
  const protocolsRef = useRef<HTMLDivElement>(null)
  const actionsRef = useRef<HTMLDivElement>(null)

  const fetchData = useCallback(async () => {
    try {
      const [protocolsRes, connectionsRes, statsRes] = await Promise.all([
        api.getProtocols().catch(() => ({ data: [] })),
        api.getConnections().catch(() => ({ data: [] })),
        api.getStats().catch(() => ({ data: null })),
      ])

      const protocolData = protocolsRes.data as Array<Record<string, unknown>>
      const connectionData = connectionsRes.data as Array<Record<string, unknown>>
      const statsData = statsRes.data as Record<string, unknown> | null

      if (Array.isArray(protocolData) && protocolData.length > 0) {
        const names = protocolData.map(p => (p.name as string || '').toLowerCase())
        setPreferences(prev => {
          if (prev.length === 0) {
            const prefs = loadPreferences(names)
            savePreferences(prefs)
            return prefs
          }
          return prev
        })

        setProtocols(protocolData.map(p => ({
          name: p.name as string || '',
          status: (p.state as 'running' | 'stopped') || 'stopped',
          port: p.port as number || 0,
          connections: p.connections as number || 0,
        })))
      } else {
        setProtocols([])
      }

      const uptimeSeconds = (statsData?.uptime_seconds as number) || 0
      const hours = Math.floor(uptimeSeconds / 3600)
      const minutes = Math.floor((uptimeSeconds % 3600) / 60)
      const seconds = Math.floor(uptimeSeconds % 60)
      const uptimeStr = uptimeSeconds > 0 ? `${hours}h ${minutes}m ${seconds}s` : 'N/A'

      setStats({
        totalConnections: (statsData?.total_connections as number) || (Array.isArray(connectionData) ? connectionData.length : 0),
        activeProtocols: Array.isArray(protocolData) ? protocolData.filter(p => p.state === 'running').length : 0,
        uptime: uptimeStr,
        memoryUsage: (statsData?.memory_used_mb as number) || 0,
        memoryPercent: (statsData?.memory_percent as number) || 0,
        cpuUsage: (statsData?.cpu_percent as number) || 0,
      })
    } catch {
      setProtocols([])
      setStats({ totalConnections: 0, activeProtocols: 0, uptime: 'N/A', memoryUsage: 0, memoryPercent: 0, cpuUsage: 0 })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 3000)
    return () => clearInterval(interval)
  }, [fetchData])

  useEffect(() => {
    if (!loading) {
      if (statsRef.current) {
      }
      if (protocolsRef.current) {
      }
      if (actionsRef.current) {
      }
    }
  }, [loading])

  const handleStartAll = useCallback(async () => {
    try {
      await Promise.all(protocols.map(p =>
        api.startProtocol(p.name.toLowerCase()).catch(() => null)
      ))
      fetchData()
    } catch {
      fetchData()
    }
  }, [protocols, fetchData])

  const handleStopAll = useCallback(async () => {
    try {
      await Promise.all(protocols.map(p =>
        api.stopProtocol(p.name.toLowerCase()).catch(() => null)
      ))
      fetchData()
    } catch {
      fetchData()
    }
  }, [protocols, fetchData])

  const toggleVisibility = (name: string) => {
    setPreferences(prev => {
      const updated = prev.map(p =>
        p.name === name ? { ...p, visible: !p.visible } : p
      )
      savePreferences(updated)
      return updated
    })
  }

  const moveUp = (name: string) => {
    setPreferences(prev => {
      const idx = prev.findIndex(p => p.name === name)
      if (idx <= 0) return prev
      const updated = [...prev]
      const temp = updated[idx - 1]
      updated[idx - 1] = { ...updated[idx], order: idx - 1 }
      updated[idx] = { ...temp, order: idx }
      savePreferences(updated)
      return updated
    })
  }

  const moveDown = (name: string) => {
    setPreferences(prev => {
      const idx = prev.findIndex(p => p.name === name)
      if (idx >= prev.length - 1) return prev
      const updated = [...prev]
      const temp = updated[idx + 1]
      updated[idx + 1] = { ...updated[idx], order: idx + 1 }
      updated[idx] = { ...temp, order: idx }
      savePreferences(updated)
      return updated
    })
  }

  const getOrderedProtocols = (): ProtocolStatus[] => {
    const sorted = [...preferences].sort((a, b) => a.order - b.order)
    const protocolMap = new Map(protocols.map(p => [p.name.toLowerCase(), p]))
    return sorted
      .filter(p => p.visible)
      .map(p => protocolMap.get(p.name))
      .filter((p): p is ProtocolStatus => p !== undefined)
  }

  const showAll = () => {
    setPreferences(prev => {
      const updated = prev.map(p => ({ ...p, visible: true }))
      savePreferences(updated)
      return updated
    })
  }

  const hideAll = () => {
    setPreferences(prev => {
      const updated = prev.map(p => ({ ...p, visible: false }))
      savePreferences(updated)
      return updated
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  const statusVariant = (status: string) => {
    switch (status) {
      case 'running':
        return 'success'
      case 'error':
        return 'destructive'
      default:
        return 'secondary'
    }
  }

  const orderedProtocols = getOrderedProtocols()

  return (
    <div className="space-y-6">
      {/* Stats Overview */}
      <div ref={statsRef} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card variant="hover">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('dashboard.totalConnections')}</p>
                <p className="text-2xl font-bold">{stats?.totalConnections || 0}</p>
              </div>
              <div className="p-3 bg-muted rounded-lg">
                <ConnectionIcon className="w-6 h-6 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card variant="hover">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('dashboard.activeProtocols')}</p>
                <p className="text-2xl font-bold">{stats?.activeProtocols || 0}</p>
              </div>
              <div className="p-3 bg-muted rounded-lg">
                <ProtocolIcon className="w-6 h-6 text-success" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card variant="hover">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('dashboard.uptime')}</p>
                <p className="text-2xl font-bold font-mono">{stats?.uptime || '00:00:00'}</p>
              </div>
              <div className="p-3 bg-muted rounded-lg">
                <ClockIcon className="w-6 h-6 text-warning" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card variant="hover">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('dashboard.systemLoad')}</p>
                <p className="text-2xl font-bold">{stats?.cpuUsage || 0}%</p>
                <p className="text-xs text-muted-foreground mt-1">
                  MEM {stats?.memoryPercent || 0}% ({stats?.memoryUsage ? Math.round(stats.memoryUsage) : 0} MB)
                </p>
              </div>
              <div className="p-3 bg-muted rounded-lg">
                <VendorCLIIcon className="w-6 h-6 text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Protocol Status Grid */}
      <Card ref={protocolsRef}>
        <CardHeader className="border-b">
          <div className="flex items-center justify-between">
            <CardTitle>{t('dashboard.protocolStatus')}</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => setShowSettings(true)}>
              <SettingsIcon className="w-4 h-4 mr-2" />
              {t('dashboard.customize', '自定义')}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          {orderedProtocols.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {t('dashboard.noProtocolsVisible', '没有可见的协议。点击"自定义"按钮添加。')}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {orderedProtocols.map((protocol) => (
                <Card key={protocol.name} variant="hover" className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-semibold">{protocol.name}</h4>
                    <Badge variant={statusVariant(protocol.status)}>
                      {protocol.status}
                    </Badge>
                  </div>
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <div className="flex justify-between">
                      <span>{t('dashboard.port')}</span>
                      <span className="font-mono text-foreground">{protocol.port}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>{t('dashboard.connections')}</span>
                      <span className="font-mono text-foreground">{protocol.connections}</span>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card ref={actionsRef}>
        <CardHeader className="border-b">
          <CardTitle>{t('dashboard.quickActions')}</CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Button onClick={handleStartAll} className="w-full">
              <PlayIcon className="w-5 h-5 mr-2" />
              {t('dashboard.startAll')}
            </Button>
            <Button variant="destructive" onClick={handleStopAll} className="w-full">
              <StopIcon className="w-5 h-5 mr-2" />
              {t('dashboard.stopAll')}
            </Button>
            <Button variant="outline" onClick={() => fetchData()} className="w-full">
              <RefreshCwIcon className="w-5 h-5 mr-2" />
              {t('dashboard.refresh')}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Settings Dialog */}
      <Dialog open={showSettings} onClose={() => setShowSettings(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('dashboard.customizeProtocols', '自定义协议显示')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <p className="text-sm text-muted-foreground">
                {t('dashboard.dragToReorder', '拖拽排序，点击眼睛图标控制显示')}
              </p>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={showAll}>显示全部</Button>
                <Button variant="ghost" size="sm" onClick={hideAll}>隐藏全部</Button>
              </div>
            </div>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {preferences.map((pref, index) => (
                <div
                  key={pref.name}
                  className="flex items-center gap-3 p-3 rounded-lg border bg-muted"
                >
                  <div className="flex flex-col gap-1">
                    <button
                      onClick={() => moveUp(pref.name)}
                      disabled={index === 0}
                      className="p-1 hover:bg-background rounded disabled:opacity-30"
                    >
                      <ChevronUpIcon className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => moveDown(pref.name)}
                      disabled={index === preferences.length - 1}
                      className="p-1 hover:bg-background rounded disabled:opacity-30"
                    >
                      <ChevronDownIcon className="w-3 h-3" />
                    </button>
                  </div>
                  <div className="flex-1">
                    <span className="font-medium">{pref.name.toUpperCase()}</span>
                  </div>
                  <button
                    onClick={() => toggleVisibility(pref.name)}
                    className="p-2 hover:bg-background rounded transition-colors"
                    title={pref.visible ? '点击隐藏' : '点击显示'}
                  >
                    {pref.visible ? (
                      <EyeIcon className="w-4 h-4 text-primary" />
                    ) : (
                      <EyeOffIcon className="w-4 h-4 text-muted-foreground" />
                    )}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default Dashboard
