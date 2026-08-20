import { useEffect, useState } from 'react'
import { api } from '../api/client'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Badge,
  Select,
} from './ui'

interface SnmpDevice {
  id: string
  name: string
  device_type: string
  ip: string
  community: string
  usm_user: string
  auth_protocol: string
  priv_protocol: string
  versions: string[]
  location: string
  contact: string
  uptime_seconds: number
  interfaces: string[]
}

interface SnmpOid {
  oid: string
  name: string
  description: string
}

interface SnmpValue {
  oid: string
  name: string
  type: string
  value: unknown
  version: string
}

const VERSION_OPTIONS = [
  { value: '2c', label: 'v2c' },
  { value: '3', label: 'v3' },
]

const SnmpSimulator = () => {
  const [devices, setDevices] = useState<SnmpDevice[]>([])
  const [oids, setOids] = useState<SnmpOid[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [version, setVersion] = useState('2c')
  const [oid, setOid] = useState('1.3.6.1.2.1.1.5.0')
  const [getResult, setGetResult] = useState<SnmpValue | null>(null)
  const [walkResult, setWalkResult] = useState<SnmpValue[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.getSnmpDevices().then((res) => {
      const list = res.data as SnmpDevice[]
      setDevices(list)
      if (list.length > 0) setSelectedId(list[0].id)
    })
    api.getSnmpOids().then((res) => setOids(res.data as SnmpOid[]))
  }, [])

  const selected = devices.find((d) => d.id === selectedId)

  const doGet = async () => {
    if (!selectedId) return
    setLoading(true)
    setError('')
    try {
      const res = await api.snmpGet(selectedId, oid, version)
      setGetResult(res.data as SnmpValue)
    } catch (e) {
      setError(typeof e === 'object' && e !== null && 'message' in e ? String(e.message) : String(e))
    } finally {
      setLoading(false)
    }
  }

  const doWalk = async () => {
    if (!selectedId) return
    setLoading(true)
    setError('')
    try {
      const res = await api.snmpWalk(selectedId, oid, version)
      setWalkResult(res.data as SnmpValue[])
    } catch (e) {
      setError(typeof e === 'object' && e !== null && 'message' in e ? String(e.message) : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-md border border-destructive bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Devices */}
      <Card>
        <CardHeader>
          <CardTitle>设备列表（{devices.length}）</CardTitle>
          <CardDescription>点击设备选择，版本支持标注在卡片上</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {devices.map((d) => (
            <button
              key={d.id}
              onClick={() => {
                setSelectedId(d.id)
                setGetResult(null)
                setWalkResult([])
              }}
              className={`rounded-md border px-3 py-2 text-left transition-all ${
                selectedId === d.id
                  ? 'border-primary bg-primary/5'
                  : 'hover:border-primary/50'
              }`}
            >
              <p className="text-xs font-medium truncate">{d.name}</p>
              <p className="text-[11px] text-muted-foreground">{d.device_type}</p>
              <p className="text-[11px] text-muted-foreground">{d.ip}</p>
              <div className="mt-1 flex gap-1">
                {d.versions.map((v) => (
                  <Badge key={v} variant="outline">v{v}</Badge>
                ))}
              </div>
            </button>
          ))}
        </CardContent>
      </Card>

      {/* Query */}
      <Card>
        <CardHeader>
          <CardTitle>OID 查询</CardTitle>
          <CardDescription>
            {selected ? `${selected.name}（${selected.device_type}）` : '选择设备'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <Select
              label="SNMP 版本"
              options={VERSION_OPTIONS}
              value={version}
              onChange={setVersion}
            />
            <label className="block text-sm font-medium">
              OID
              <select
                className="mt-2 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={oid}
                onChange={(e) => setOid(e.target.value)}
              >
                {oids.map((o) => (
                  <option key={o.oid} value={o.oid}>
                    {o.name} ({o.oid})
                  </option>
                ))}
              </select>
            </label>
            <div className="flex items-end gap-2">
              <Button loading={loading} onClick={doGet}>
                GET
              </Button>
              <Button variant="outline" loading={loading} onClick={doWalk}>
                WALK
              </Button>
            </div>
          </div>

          {getResult && (
            <div className="rounded-md border px-4 py-3">
              <p className="text-sm font-medium">{getResult.name}</p>
              <p className="text-xs text-muted-foreground">
                {getResult.oid} · {getResult.type} · v{getResult.version}
              </p>
              <p className="mt-1 text-lg font-bold">{String(getResult.value)}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Walk results */}
      {walkResult.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>WALK 结果（{walkResult.length}）</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-2 pr-3">OID</th>
                    <th className="py-2 pr-3">名称</th>
                    <th className="py-2 pr-3">类型</th>
                    <th className="py-2">值</th>
                  </tr>
                </thead>
                <tbody>
                  {walkResult.map((r) => (
                    <tr key={r.oid} className="border-b">
                      <td className="py-2 pr-3 font-mono text-xs">{r.oid}</td>
                      <td className="py-2 pr-3">{r.name}</td>
                      <td className="py-2 pr-3">{r.type}</td>
                      <td className="py-2">{String(r.value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default SnmpSimulator
