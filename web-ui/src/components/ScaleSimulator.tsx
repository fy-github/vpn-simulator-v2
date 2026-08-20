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
  Input,
} from './ui'

interface ScaleDevice {
  index: number
  name: string
  device_type: string
  ip: string
  state: string
  cpu_percent: number
  memory_percent: number
}

interface ScaleDevicePage {
  total: number
  offset: number
  limit: number
  count: number
  devices: ScaleDevice[]
}

interface ScaleStats {
  total: number
  by_type: Record<string, number>
  by_state: Record<string, number>
  avg_cpu_percent: number
  avg_memory_percent: number
  pool_size: number
}

interface PollResult {
  polled: number
  duration_ms: number
  throughput_devices_per_sec: number
  concurrency: number
  by_state: Record<string, number>
}

interface Snapshot {
  id: number
  total_devices: number
  by_type: Record<string, number>
  by_state: Record<string, number>
  avg_cpu_percent: number
  avg_memory_percent: number
  pool_size: number
  created_at: string | null
}

const ScaleSimulator = () => {
  const [stats, setStats] = useState<ScaleStats | null>(null)
  const [page, setPage] = useState<ScaleDevicePage | null>(null)
  const [offset, setOffset] = useState(0)
  const [limit, setLimit] = useState(50)
  const [poll, setPoll] = useState<PollResult | null>(null)
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [pollCount, setPollCount] = useState('1000')
  const [concurrency, setConcurrency] = useState('1000')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.getScaleStats().then((res) => setStats(res.data as ScaleStats))
    api.getScaleSnapshot().then((res) => setSnapshot(res.data as Snapshot)).catch(() => undefined)
  }, [])

  useEffect(() => {
    api.getScaleDevices(offset, limit).then((res) => setPage(res.data as ScaleDevicePage))
  }, [offset, limit])

  const runPoll = async () => {
    setLoading(true)
    try {
      const res = await api.runScalePoll(
        pollCount ? Number(pollCount) : undefined,
        concurrency ? Number(concurrency) : undefined,
      )
      setPoll(res.data as PollResult)
    } finally {
      setLoading(false)
    }
  }

  const persist = async () => {
    setLoading(true)
    try {
      const res = await api.persistScaleSnapshot()
      setStats(res.data as ScaleStats)
      const snap = await api.getScaleSnapshot()
      setSnapshot(snap.data as Snapshot)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Stats */}
      {stats && (
        <Card>
          <CardHeader>
            <CardTitle>聚合统计</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <div className="rounded-md border px-3 py-2 text-center">
                <p className="text-xs text-muted-foreground">设备总数</p>
                <p className="text-lg font-bold">{stats.total.toLocaleString()}</p>
              </div>
              <div className="rounded-md border px-3 py-2 text-center">
                <p className="text-xs text-muted-foreground">平均 CPU</p>
                <p className="text-lg font-bold">{stats.avg_cpu_percent.toFixed(1)}%</p>
              </div>
              <div className="rounded-md border px-3 py-2 text-center">
                <p className="text-xs text-muted-foreground">平均内存</p>
                <p className="text-lg font-bold">{stats.avg_memory_percent.toFixed(1)}%</p>
              </div>
              <div className="rounded-md border px-3 py-2 text-center">
                <p className="text-xs text-muted-foreground">连接池</p>
                <p className="text-lg font-bold">{stats.pool_size}</p>
              </div>
              <div className="rounded-md border px-3 py-2 text-center">
                <p className="text-xs text-muted-foreground">设备类型</p>
                <p className="text-lg font-bold">{Object.keys(stats.by_type).length}</p>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  按类型
                </p>
                {Object.entries(stats.by_type).map(([t, c]) => (
                  <div key={t} className="flex items-center justify-between py-1">
                    <span className="text-sm">{t}</span>
                    <span className="text-sm font-medium">{c.toLocaleString()}</span>
                  </div>
                ))}
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  按状态
                </p>
                {Object.entries(stats.by_state).map(([s, c]) => (
                  <div key={s} className="flex items-center justify-between py-1">
                    <span className="text-sm">{s}</span>
                    <span className="text-sm font-medium">{c.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Poll */}
        <Card>
          <CardHeader>
            <CardTitle>并发巡检</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="巡检设备数(空=全部)"
                value={pollCount}
                onChange={(e) => setPollCount(e.target.value)}
              />
              <Input
                label="并发上限"
                value={concurrency}
                onChange={(e) => setConcurrency(e.target.value)}
              />
            </div>
            <div className="flex gap-3">
              <Button loading={loading} onClick={runPoll}>
                运行巡检
              </Button>
              <Button variant="outline" loading={loading} onClick={persist}>
                持久化快照
              </Button>
            </div>
            {poll && (
              <div className="rounded-md border px-3 py-2 space-y-1">
                <p className="text-sm font-medium">巡检 {poll.polled.toLocaleString()} 台</p>
                <p className="text-xs text-muted-foreground">
                  {poll.duration_ms}ms · {poll.throughput_devices_per_sec} 台/秒 · 并发 {poll.concurrency}
                </p>
                <p className="text-xs">
                  {Object.entries(poll.by_state)
                    .map(([s, c]) => `${s}:${c}`)
                    .join('  ')}
                </p>
              </div>
            )}
            {snapshot && (
              <div className="rounded-md border px-3 py-2">
                <p className="text-xs font-medium">最近快照 #{snapshot.id}</p>
                <p className="text-xs text-muted-foreground">
                  {snapshot.total_devices.toLocaleString()} 台 · CPU {snapshot.avg_cpu_percent.toFixed(1)}% ·{' '}
                  {snapshot.created_at ?? '—'}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Devices */}
        <Card>
          <CardHeader>
            <CardTitle>设备列表</CardTitle>
            <CardDescription>
              {page ? `第 ${page.offset}-${page.offset + page.count} / ${page.total.toLocaleString()} 台` : '加载中…'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-3">
              <Input
                label="每页数量"
                value={String(limit)}
                onChange={(e) => setLimit(Number(e.target.value) || 50)}
              />
              <div className="flex items-end gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setOffset((o) => Math.max(0, o - limit))}
                >
                  上一页
                </Button>
                <Button size="sm" variant="outline" onClick={() => setOffset((o) => o + limit)}>
                  下一页
                </Button>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-2 pr-3">#</th>
                    <th className="py-2 pr-3">名称</th>
                    <th className="py-2 pr-3">IP</th>
                    <th className="py-2 pr-3">状态</th>
                    <th className="py-2">CPU</th>
                  </tr>
                </thead>
                <tbody>
                  {page?.devices.map((d) => (
                    <tr key={d.index} className="border-b">
                      <td className="py-2 pr-3 text-muted-foreground">{d.index}</td>
                      <td className="py-2 pr-3 font-medium">{d.name}</td>
                      <td className="py-2 pr-3 font-mono text-xs">{d.ip}</td>
                      <td className="py-2 pr-3">
                        <Badge variant="outline">{d.state}</Badge>
                      </td>
                      <td className="py-2">{d.cpu_percent}%</td>
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

export default ScaleSimulator
