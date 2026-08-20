import { useCallback, useEffect, useRef, useState } from 'react'
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
  Progress,
} from './ui'

interface PcapFile {
  id: string
  filename: string
  packet_count: number
  protocols: string[]
  duration_seconds: number
  size_bytes: number
  uploaded_at: string
}

interface ReplaySession {
  id: string
  pcap_file_id: string
  speed: number
  protocol_filter: string | null
  status: string
  packets_replayed: number
  total_packets: number
  started_at: string | null
  finished_at: string | null
}

interface PcapStats extends PcapFile {
  by_protocol: Record<string, number>
}

const PcapSimulator = () => {
  const [files, setFiles] = useState<PcapFile[]>([])
  const [stats, setStats] = useState<PcapStats | null>(null)
  const [session, setSession] = useState<ReplaySession | null>(null)
  const [selectedFileId, setSelectedFileId] = useState('')
  const [speed, setSpeed] = useState('1')
  const [protocolFilter, setProtocolFilter] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadFiles = useCallback(async () => {
    const res = await api.getPcapFiles()
    setFiles(res.data as PcapFile[])
  }, [])

  useEffect(() => {
    loadFiles().catch(() => undefined)
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [loadFiles])

  const upload = async (file: File) => {
    setLoading(true)
    setError('')
    try {
      await api.uploadPcap(file)
      await loadFiles()
    } catch (e) {
      setError(typeof e === 'object' && e !== null && 'message' in e ? String(e.message) : String(e))
    } finally {
      setLoading(false)
    }
  }

  const viewStats = async (fileId: string) => {
    const res = await api.getPcapStats(fileId)
    setStats(res.data as PcapStats)
  }

  const startReplay = async () => {
    if (!selectedFileId) {
      setError('请先选择一个文件')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await api.startPcapReplay(selectedFileId, Number(speed), protocolFilter || undefined)
      const newSession = res.data as ReplaySession
      setSession(newSession)
      startPolling(newSession.id)
    } catch (e) {
      setError(typeof e === 'object' && e !== null && 'message' in e ? String(e.message) : String(e))
    } finally {
      setLoading(false)
    }
  }

  const startPolling = (sessionId: string) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const res = await api.getPcapStatus(sessionId)
        const s = res.data as ReplaySession
        setSession(s)
        if (s.status === 'completed' || s.status === 'stopped') {
          if (pollRef.current) clearInterval(pollRef.current)
        }
      } catch {
        if (pollRef.current) clearInterval(pollRef.current)
      }
    }, 800)
  }

  const stopReplay = async () => {
    if (!session) return
    await api.stopPcapReplay(session.id)
    if (pollRef.current) clearInterval(pollRef.current)
    const res = await api.getPcapStatus(session.id)
    setSession(res.data as ReplaySession)
  }

  const progress = session && session.total_packets > 0
    ? Math.round((session.packets_replayed / session.total_packets) * 100)
    : 0

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-md border border-destructive bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload */}
        <Card>
          <CardHeader>
            <CardTitle>上传 PCAP</CardTitle>
            <CardDescription>支持 .pcap / .pcapng / .cap</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pcap,.pcapng,.cap"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) upload(f)
                e.target.value = ''
              }}
            />
            <Button loading={loading} onClick={() => fileInputRef.current?.click()}>
              选择文件
            </Button>
          </CardContent>
        </Card>

        {/* Replay controls */}
        <Card>
          <CardHeader>
            <CardTitle>回放控制</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <label className="block text-sm font-medium">
              文件
              <select
                className="mt-2 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={selectedFileId}
                onChange={(e) => setSelectedFileId(e.target.value)}
              >
                <option value="">选择文件…</option>
                {files.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.filename} ({f.packet_count} pkts)
                  </option>
                ))}
              </select>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="速度倍率 (0.5–10)"
                value={speed}
                onChange={(e) => setSpeed(e.target.value)}
              />
              <Input
                label="协议过滤(可选)"
                value={protocolFilter}
                placeholder="tcp"
                onChange={(e) => setProtocolFilter(e.target.value)}
              />
            </div>
            <div className="flex gap-3">
              <Button loading={loading} onClick={startReplay}>
                开始回放
              </Button>
              {session && (session.status === 'running' || session.status === 'idle') && (
                <Button variant="destructive" onClick={stopReplay}>
                  停止
                </Button>
              )}
            </div>
            {session && (
              <div className="space-y-2 rounded-md border px-3 py-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{session.status}</Badge>
                  <span className="text-sm">
                    {session.packets_replayed} / {session.total_packets} 报文
                  </span>
                </div>
                <Progress value={progress} max={100} />
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Files list */}
      <Card>
        <CardHeader>
          <CardTitle>已上传文件</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {files.length === 0 && (
            <p className="text-sm text-muted-foreground">暂无文件</p>
          )}
          {files.map((f) => (
            <div key={f.id} className="flex items-center justify-between rounded-md border px-3 py-2">
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{f.filename}</p>
                <p className="text-xs text-muted-foreground">
                  {f.packet_count} 报文 · {f.protocols.join(', ') || '—'} ·{' '}
                  {f.duration_seconds}s · {(f.size_bytes / 1024).toFixed(1)} KB
                </p>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => viewStats(f.id)}>
                  统计
                </Button>
                <Button size="sm" variant="outline" onClick={() => setSelectedFileId(f.id)}>
                  选择
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Stats */}
      {stats && (
        <Card>
          <CardHeader>
            <CardTitle>{stats.filename} · 统计</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(stats.by_protocol).map(([proto, count]) => (
                <div key={proto} className="rounded-md border px-3 py-2 text-center">
                  <p className="text-xs text-muted-foreground">{proto}</p>
                  <p className="text-lg font-bold">{count}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default PcapSimulator
