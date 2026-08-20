import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Badge,
} from './ui'

interface RouterInfo {
  id: string
  name: string
  router_id: string
  asn: number
  area: string
}

interface Neighbor {
  id: string
  router_id: string
  neighbor_id: string
  protocol: string
  state: string
  last_transition: string
}

interface RouteEntry {
  prefix: string
  next_hop: string
  metric: number
  protocol: string
  route_type: string
}

const FINAL_STATES: Record<string, string> = {
  ospf: 'full',
  bgp: 'established',
}

const RoutingSimulator = () => {
  const [routers, setRouters] = useState<RouterInfo[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [neighbors, setNeighbors] = useState<Neighbor[]>([])
  const [routes, setRoutes] = useState<RouteEntry[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.getRouters().then((res) => {
      const list = res.data as RouterInfo[]
      setRouters(list)
      if (list.length > 0) setSelectedId(list[0].id)
    })
  }, [])

  const loadNeighbors = useCallback(async (routerId: string) => {
    const res = await api.getRoutingNeighbors(routerId)
    setNeighbors(res.data as Neighbor[])
  }, [])

  const loadRoutes = useCallback(async (routerId: string) => {
    const res = await api.getRoutingTable(routerId)
    setRoutes(res.data as RouteEntry[])
  }, [])

  useEffect(() => {
    if (selectedId) {
      loadNeighbors(selectedId)
      loadRoutes(selectedId)
    }
  }, [selectedId, loadNeighbors, loadRoutes])

  const establish = async (neighborId: string, protocol: string) => {
    if (!selectedId) return
    setLoading(true)
    try {
      await api.establishNeighbor(selectedId, neighborId, protocol)
      await Promise.all([loadNeighbors(selectedId), loadRoutes(selectedId)])
    } finally {
      setLoading(false)
    }
  }

  const selectedRouter = routers.find((r) => r.id === selectedId)

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>路由器拓扑</CardTitle>
          <CardDescription>点击选择一台路由器查看邻居与路由表</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {routers.map((r) => (
            <button
              key={r.id}
              onClick={() => setSelectedId(r.id)}
              className={`rounded-md border px-4 py-3 text-left transition-all ${
                selectedId === r.id
                  ? 'border-primary bg-primary/5'
                  : 'hover:border-primary/50'
              }`}
            >
              <p className="text-sm font-medium">{r.name}</p>
              <p className="text-xs text-muted-foreground">{r.router_id}</p>
              <p className="text-xs text-muted-foreground">ASN {r.asn} · {r.area}</p>
            </button>
          ))}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Neighbors */}
        <Card>
          <CardHeader>
            <CardTitle>邻居 ({selectedRouter?.name ?? '—'})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {neighbors.length === 0 && (
              <p className="text-sm text-muted-foreground">无邻居</p>
            )}
            {neighbors.map((n) => {
              const isEstablished = n.state === FINAL_STATES[n.protocol]
              return (
                <div
                  key={n.id}
                  className="flex items-center justify-between rounded-md border px-3 py-2"
                >
                  <div>
                    <p className="text-sm font-medium">
                      → {n.neighbor_id}{' '}
                      <Badge variant="outline">{n.protocol.toUpperCase()}</Badge>
                    </p>
                    <p className="text-xs text-muted-foreground">{n.state}</p>
                  </div>
                  <Button
                    size="sm"
                    variant={isEstablished ? 'secondary' : 'outline'}
                    loading={loading}
                    onClick={() => establish(n.neighbor_id, n.protocol)}
                  >
                    {isEstablished ? '已建立' : '建立邻接'}
                  </Button>
                </div>
              )
            })}
          </CardContent>
        </Card>

        {/* Routing table */}
        <Card>
          <CardHeader>
            <CardTitle>路由表</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-2 pr-3">前缀</th>
                    <th className="py-2 pr-3">下一跳</th>
                    <th className="py-2 pr-3">度量</th>
                    <th className="py-2">类型</th>
                  </tr>
                </thead>
                <tbody>
                  {routes.map((r) => (
                    <tr key={`${r.prefix}-${r.next_hop}-${r.protocol}`} className="border-b">
                      <td className="py-2 pr-3 font-medium">{r.prefix}</td>
                      <td className="py-2 pr-3">{r.next_hop}</td>
                      <td className="py-2 pr-3">{r.metric}</td>
                      <td className="py-2">
                        <Badge variant="outline">
                          {r.route_type} ({r.protocol})
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default RoutingSimulator
