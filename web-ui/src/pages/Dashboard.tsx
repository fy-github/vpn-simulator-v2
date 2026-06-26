import { useTranslation } from 'react-i18next'
import { useEffect, useState, useCallback, useRef } from 'react'

import { ConnectionIcon, ProtocolIcon, ClockIcon, VendorCLIIcon, PlayIcon, StopIcon, RefreshCwIcon } from '../components/Icons'
import { api } from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'

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

const Dashboard = () => {
  const { t } = useTranslation()
  const [protocols, setProtocols] = useState<ProtocolStatus[]>([])
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [loading, setLoading] = useState(true)
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
  }, [fetchData])

  // GSAP animations
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
          <CardTitle>{t('dashboard.protocolStatus')}</CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {protocols.map((protocol) => (
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
    </div>
  )
}

export default Dashboard
