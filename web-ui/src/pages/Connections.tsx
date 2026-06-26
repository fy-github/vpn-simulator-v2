import { useTranslation } from 'react-i18next'
import { useEffect, useState, useCallback, useRef } from 'react'

import { ConnectionIcon, MetricsIcon, ProtocolIcon } from '../components/Icons'
import { api } from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Select } from '../components/ui/Select'

interface Connection {
  id: string
  protocol: string
  clientIp: string
  clientPort: number
  serverIp: string
  serverPort: number
  status: 'connected' | 'disconnecting' | 'disconnected'
  connectedAt: string
  duration: string
  bytesIn: number
  bytesOut: number
}

const Connections = () => {
  const { t } = useTranslation()
  const [connections, setConnections] = useState<Connection[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const statsRef = useRef<HTMLDivElement>(null)
  const tableRef = useRef<HTMLDivElement>(null)

  const fetchConnections = useCallback(async () => {
    try {
      const response = await api.getConnections()
      const data = response.data
      if (Array.isArray(data)) {
        setConnections(data.map((c: Record<string, unknown>) => ({
          id: c.id as string || '',
          protocol: c.protocol as string || '',
          clientIp: c.local_address as string || '',
          clientPort: c.local_port as number || 0,
          serverIp: c.remote_address as string || '',
          serverPort: c.remote_port as number || 0,
          status: (c.state as 'connected' | 'disconnected') || 'disconnected',
          connectedAt: c.connected_at as string || '',
          duration: '',
          bytesIn: c.bytes_received as number || 0,
          bytesOut: c.bytes_sent as number || 0,
        })))
      }
    } catch {
      setConnections([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchConnections()
  }, [fetchConnections])

  // GSAP animations
  useEffect(() => {
    if (!loading) {
      if (statsRef.current) {
      }
      if (tableRef.current) {
      }
    }
  }, [loading])

  const handleDisconnect = async (id: string) => {
    try {
      await api.disconnectConnection(id)
      setConnections(prev => prev.filter(conn => conn.id !== id))
    } catch (e) {
      console.error('Failed to disconnect:', e)
    }
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const filteredConnections = connections.filter(conn => {
    if (filter === 'all') return true
    return conn.protocol.toLowerCase() === filter.toLowerCase()
  })

  const filterOptions = [
    { value: 'all', label: t('connections.allProtocols') },
    { value: 'pptp', label: 'PPTP' },
    { value: 'l2tp', label: 'L2TP' },
    { value: 'openvpn', label: 'OpenVPN' },
    { value: 'ipsec', label: 'IPSec' },
    { value: 'ikev2', label: 'IKEv2' },
    { value: 'wireguard', label: 'WireGuard' },
  ]

  const statusVariant = (status: string) => {
    switch (status) {
      case 'connected':
        return 'success'
      case 'disconnecting':
        return 'warning'
      default:
        return 'secondary'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t('connections.title')}</h1>
          <p className="text-muted-foreground mt-1">{t('connections.subtitle')}</p>
        </div>
        <div className="flex items-center gap-4">
          <Select
            options={filterOptions}
            value={filter}
            onChange={setFilter}
            className="w-40"
          />
          <Button variant="outline" onClick={fetchConnections}>
            {t('connections.refresh')}
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div ref={statsRef} className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card variant="hover">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('connections.totalConnections')}</p>
                <p className="text-2xl font-bold">{connections.length}</p>
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
                <p className="text-sm text-muted-foreground">{t('connections.totalTraffic')}</p>
                <p className="text-2xl font-bold">
                  {formatBytes(connections.reduce((acc, conn) => acc + conn.bytesIn + conn.bytesOut, 0))}
                </p>
              </div>
              <div className="p-3 bg-muted rounded-lg">
                <MetricsIcon className="w-6 h-6 text-success" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card variant="hover">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('connections.protocolsInUse')}</p>
                <p className="text-2xl font-bold">
                  {new Set(connections.map(conn => conn.protocol)).size}
                </p>
              </div>
              <div className="p-3 bg-muted rounded-lg">
                <ProtocolIcon className="w-6 h-6 text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Connections Table */}
      <Card ref={tableRef}>
        <CardHeader className="border-b">
          <CardTitle>{t('connections.activeConnections')}</CardTitle>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  {t('connections.protocol')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  {t('connections.client')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  {t('connections.server')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  {t('connections.duration')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  {t('connections.traffic')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  {t('connections.status')}
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  {t('connections.actions')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filteredConnections.map((connection) => (
                <tr key={connection.id} className="hover:bg-muted transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Badge variant="outline">
                      {connection.protocol}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-mono">
                      {connection.clientIp}:{connection.clientPort}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-mono">
                      {connection.serverIp}:{connection.serverPort}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-mono">
                      {connection.duration}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm">
                      <div>{formatBytes(connection.bytesIn)}</div>
                      <div>{formatBytes(connection.bytesOut)}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Badge variant={statusVariant(connection.status)}>
                      {connection.status}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDisconnect(connection.id)}
                      disabled={connection.status !== 'connected'}
                    >
                      {t('connections.disconnect')}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredConnections.length === 0 && (
          <div className="px-6 py-12 text-center">
            <p className="text-muted-foreground">{t('connections.noConnections')}</p>
          </div>
        )}
      </Card>
    </div>
  )
}

export default Connections
