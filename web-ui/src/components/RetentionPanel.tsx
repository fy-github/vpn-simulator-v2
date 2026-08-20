import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Input,
} from './ui'

interface RetentionStatus {
  packets: number
  state_transitions: number
}

interface CleanupResult {
  deleted_packets: number
  deleted_state_transitions: number
  remaining_packets: number
  remaining_state_transitions: number
}

const RetentionPanel = () => {
  const [status, setStatus] = useState<RetentionStatus | null>(null)
  const [result, setResult] = useState<CleanupResult | null>(null)
  const [maxPackets, setMaxPackets] = useState('')
  const [packetTtl, setPacketTtl] = useState('')
  const [maxTransitions, setMaxTransitions] = useState('')
  const [transitionTtl, setTransitionTtl] = useState('')
  const [loading, setLoading] = useState(false)

  const loadStatus = useCallback(async () => {
    const res = await api.getRetentionStatus()
    setStatus(res.data as RetentionStatus)
  }, [])

  useEffect(() => {
    loadStatus().catch(() => undefined)
  }, [loadStatus])

  const runCleanup = async () => {
    setLoading(true)
    try {
      const overrides: Record<string, unknown> = {}
      if (maxPackets) overrides.max_packets = Number(maxPackets)
      if (packetTtl) overrides.packet_ttl_seconds = Number(packetTtl)
      if (maxTransitions) overrides.max_transitions = Number(maxTransitions)
      if (transitionTtl) overrides.transition_ttl_seconds = Number(transitionTtl)
      const res = await api.runRetentionCleanup(Object.keys(overrides).length ? overrides : undefined)
      setResult(res.data as CleanupResult)
      await loadStatus()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Status */}
      <Card>
        <CardHeader>
          <CardTitle>当前行数</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-md border px-3 py-2 text-center">
              <p className="text-xs text-muted-foreground">packets</p>
              <p className="text-2xl font-bold">
                {status ? status.packets.toLocaleString() : '—'}
              </p>
            </div>
            <div className="rounded-md border px-3 py-2 text-center">
              <p className="text-xs text-muted-foreground">state_transitions</p>
              <p className="text-2xl font-bold">
                {status ? status.state_transitions.toLocaleString() : '—'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Cleanup */}
      <Card>
        <CardHeader>
          <CardTitle>清理</CardTitle>
          <CardDescription>
            留空使用默认：packets 10 万行/7 天，state_transitions 5 万行/30 天
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Input
              label="packets 最大行数"
              value={maxPackets}
              placeholder="100000"
              onChange={(e) => setMaxPackets(e.target.value)}
            />
            <Input
              label="packets TTL(秒)"
              value={packetTtl}
              placeholder="604800"
              onChange={(e) => setPacketTtl(e.target.value)}
            />
            <Input
              label="state_transitions 最大行数"
              value={maxTransitions}
              placeholder="50000"
              onChange={(e) => setMaxTransitions(e.target.value)}
            />
            <Input
              label="state_transitions TTL(秒)"
              value={transitionTtl}
              placeholder="2592000"
              onChange={(e) => setTransitionTtl(e.target.value)}
            />
          </div>
          <Button loading={loading} onClick={runCleanup}>
            执行清理
          </Button>

          {result && (
            <div className="rounded-md border px-4 py-3 space-y-1 text-sm">
              <p>
                删除 packets：<span className="font-medium">{result.deleted_packets}</span>
                （剩余 {result.remaining_packets}）
              </p>
              <p>
                删除 state_transitions：
                <span className="font-medium">{result.deleted_state_transitions}</span>
                （剩余 {result.remaining_state_transitions}）
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default RetentionPanel
