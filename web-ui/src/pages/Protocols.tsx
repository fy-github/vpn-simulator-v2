import { useTranslation } from 'react-i18next'
import { useEffect, useState, useCallback } from 'react'

import { api } from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/Dialog'
import ProtocolConfig from '../components/ProtocolConfig'

interface Protocol {
  id: string
  name: string
  description: string
  port: number
  transport: string
  status: 'running' | 'stopped' | 'error'
  connections: number
  config: Record<string, unknown>
}

interface ProtocolConfig {
  [key: string]: unknown
  port: number
  transport: string
  maxConnections: number
  timeout: number
  enableLogging: boolean
}

const defaultConfigs: Record<string, ProtocolConfig> = {
  pptp: { port: 1723, transport: 'TCP', maxConnections: 100, timeout: 30, enableLogging: true },
  l2tp: { port: 1701, transport: 'UDP', maxConnections: 100, timeout: 30, enableLogging: true },
  openvpn: { port: 1194, transport: 'UDP', maxConnections: 200, timeout: 60, enableLogging: true },
  ipsec: { port: 500, transport: 'UDP', maxConnections: 100, timeout: 30, enableLogging: true },
  ikev2: { port: 500, transport: 'UDP', maxConnections: 100, timeout: 30, enableLogging: true },
  wireguard: { port: 51820, transport: 'UDP', maxConnections: 500, timeout: 30, enableLogging: true },
  sstp: { port: 443, transport: 'TCP', maxConnections: 100, timeout: 30, enableLogging: true },
  openconnect: { port: 443, transport: 'TCP', maxConnections: 100, timeout: 30, enableLogging: true },
}

const Protocols = () => {
  const { t } = useTranslation()
  const [protocols, setProtocols] = useState<Protocol[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedProtocol, setSelectedProtocol] = useState<Protocol | null>(null)
  const [config, setConfig] = useState<Record<string, unknown>>({
    port: 0,
    transport: 'UDP',
    maxConnections: 100,
    timeout: 30,
    enableLogging: true,
  })

  const fetchProtocols = useCallback(async () => {
    try {
      const response = await api.getProtocols()
      const data = response.data
      if (Array.isArray(data) && data.length > 0) {
        setProtocols(data.map((p: Record<string, unknown>) => ({
          id: (p.name as string || '').toLowerCase(),
          name: p.name as string || '',
          description: getProtocolDescription(p.name as string || ''),
          port: p.port as number || 0,
          transport: p.transport as string || 'UDP',
          status: (p.state as 'running' | 'stopped') || 'stopped',
          connections: p.connections as number || 0,
          config: p.config as Record<string, unknown> || {},
        })))
      } else {
        setProtocols([])
      }
    } catch {
      setProtocols([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchProtocols()
  }, [fetchProtocols])

  const getProtocolDescription = (name: string): string => {
    const descriptions: Record<string, string> = {
      pptp: 'Point-to-Point Tunneling Protocol',
      l2tp: 'Layer 2 Tunneling Protocol',
      openvpn: 'Open-source VPN protocol',
      ipsec: 'Internet Protocol Security',
      ikev2: 'Internet Key Exchange v2',
      wireguard: 'Modern, fast VPN protocol',
      sstp: 'Secure Socket Tunneling Protocol',
      openconnect: 'Cisco AnyConnect compatible',
    }
    return descriptions[name] || 'VPN Protocol'
  }

  const handleStart = async (protocol: Protocol) => {
    try {
      await api.startProtocol(protocol.id)
      setProtocols(prev => prev.map(p => p.id === protocol.id ? { ...p, status: 'running' } : p))
    } catch (e) {
      console.error('Failed to start protocol:', e)
    }
  }

  const handleStop = async (protocol: Protocol) => {
    try {
      await api.stopProtocol(protocol.id)
      setProtocols(prev => prev.map(p => p.id === protocol.id ? { ...p, status: 'stopped' } : p))
    } catch (e) {
      console.error('Failed to stop protocol:', e)
    }
  }

  const handleStartAll = async () => {
    try {
      await Promise.all(protocols.map(p =>
        api.startProtocol(p.id).catch(() => null)
      ))
      fetchProtocols()
    } catch {
      fetchProtocols()
    }
  }

  const handleStopAll = async () => {
    try {
      await Promise.all(protocols.map(p =>
        api.stopProtocol(p.id).catch(() => null)
      ))
      fetchProtocols()
    } catch {
      fetchProtocols()
    }
  }

  const openConfig = (protocol: Protocol) => {
    setSelectedProtocol(protocol)
    const defaultConfig = defaultConfigs[protocol.id] || {
      port: protocol.port || 0,
      transport: protocol.transport || 'UDP',
      maxConnections: 100,
      timeout: 30,
      enableLogging: true,
    }
    setConfig(defaultConfig)
  }

  const handleSaveConfig = async () => {
    if (!selectedProtocol) return
    try {
      await api.startProtocol(selectedProtocol.id, { port: config.port, config: { ...config } })
      setSelectedProtocol(null)
      fetchProtocols()
    } catch (e) {
      console.error('Failed to save config:', e)
    }
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t('protocols.title')}</h1>
          <p className="text-muted-foreground mt-1">{t('protocols.subtitle')}</p>
        </div>
        <div className="flex space-x-3">
          <Button onClick={handleStartAll}>
            {t('protocols.startAll')}
          </Button>
          <Button variant="destructive" onClick={handleStopAll}>
            {t('protocols.stopAll', '全部停止')}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {protocols.map((protocol) => (
          <Card key={protocol.id} variant="hover">
            <CardHeader className="border-b">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>{protocol.name}</CardTitle>
                  <p className="text-sm text-muted-foreground">{protocol.description}</p>
                </div>
                <Badge variant={statusVariant(protocol.status)}>
                  {protocol.status}
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="p-6">
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <p className="text-sm text-muted-foreground">{t('protocols.port')}</p>
                  <p className="font-mono">{protocol.port || defaultConfigs[protocol.id]?.port || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t('protocols.transport')}</p>
                  <p className="font-mono">{protocol.transport || defaultConfigs[protocol.id]?.transport || 'UDP'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t('protocols.connections')}</p>
                  <p className="font-mono">{protocol.connections}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t('protocols.status')}</p>
                  <p className="font-mono">{protocol.status}</p>
                </div>
              </div>

              <div className="flex space-x-3">
                {protocol.status === 'running' ? (
                  <Button
                    variant="destructive"
                    onClick={() => handleStop(protocol)}
                    className="flex-1"
                  >
                    {t('protocols.stop')}
                  </Button>
                ) : (
                  <Button
                    onClick={() => handleStart(protocol)}
                    className="flex-1"
                  >
                    {t('protocols.start')}
                  </Button>
                )}
                <Button
                  variant="outline"
                  onClick={() => openConfig(protocol)}
                >
                  {t('protocols.configure')}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={!!selectedProtocol} onClose={() => setSelectedProtocol(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {selectedProtocol?.name} {t('protocols.configure', '参数设置')}
            </DialogTitle>
          </DialogHeader>
          {selectedProtocol && (
            <ProtocolConfig
              protocol={selectedProtocol.id}
              config={config}
              onSave={handleSaveConfig}
              onCancel={() => setSelectedProtocol(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default Protocols
