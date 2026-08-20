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
  Select,
  Textarea,
} from './ui'

interface ValidationStep {
  name: string
  status: 'pass' | 'fail' | 'skip'
  message: string
  metrics: Record<string, unknown>
}

interface ValidationResult {
  id: string
  protocol: string
  config: Record<string, unknown>
  status: string
  steps: ValidationStep[]
  metrics: Record<string, unknown>
  created_at: string
}

const PROTOCOLS = [
  { value: 'wireguard', label: 'WireGuard' },
  { value: 'openvpn', label: 'OpenVPN' },
  { value: 'ipsec', label: 'IPSec' },
  { value: 'ikev2', label: 'IKEv2' },
  { value: 'pptp', label: 'PPTP' },
  { value: 'l2tp', label: 'L2TP' },
]

const statusVariant = (status: string): 'success' | 'destructive' | 'warning' => {
  if (status === 'pass') return 'success'
  if (status === 'fail') return 'destructive'
  return 'warning'
}

const ValidationSimulator = () => {
  const [protocol, setProtocol] = useState('wireguard')
  const [configText, setConfigText] = useState('{}')
  const [result, setResult] = useState<ValidationResult | null>(null)
  const [batch, setBatch] = useState<ValidationResult[]>([])
  const [history, setHistory] = useState<ValidationResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadHistory = useCallback(async () => {
    const res = await api.getValidationHistory()
    setHistory(res.data as ValidationResult[])
  }, [])

  useEffect(() => {
    loadHistory().catch(() => undefined)
  }, [loadHistory])

  const runValidate = async () => {
    setLoading(true)
    setError('')
    try {
      const config = JSON.parse(configText || '{}') as Record<string, unknown>
      const res = await api.validateConfig(protocol, config)
      setResult(res.data as ValidationResult)
      await loadHistory()
    } catch (e) {
      setError(
        e instanceof SyntaxError
          ? '配置 JSON 解析失败：' + e.message
          : typeof e === 'object' && e !== null && 'message' in e
            ? String(e.message)
            : String(e),
      )
    } finally {
      setLoading(false)
    }
  }

  const runBatch = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.batchValidate()
      setBatch(res.data as ValidationResult[])
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

      <Card>
        <CardHeader>
          <CardTitle>配置验证</CardTitle>
          <CardDescription>选择协议并填入配置 JSON，执行 7 步验证</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Select
              label="协议"
              options={PROTOCOLS}
              value={protocol}
              onChange={setProtocol}
            />
            <div>
              <Textarea
                label="配置 JSON"
                value={configText}
                onChange={(e) => setConfigText(e.target.value)}
                rows={5}
              />
            </div>
          </div>
          <div className="flex gap-3">
            <Button loading={loading} onClick={runValidate}>
              验证
            </Button>
            <Button variant="outline" loading={loading} onClick={runBatch}>
              批量验证（全部 6 种）
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Single result */}
      {result && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <CardTitle>{result.protocol}</CardTitle>
              <Badge variant={result.status === 'pass' ? 'success' : 'destructive'}>
                {result.status}
              </Badge>
            </div>
            <CardDescription>{result.created_at}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {result.steps.map((step) => (
              <div
                key={step.name}
                className="flex items-start justify-between gap-3 rounded-md border px-3 py-2"
              >
                <div>
                  <p className="text-sm font-medium">{step.name}</p>
                  <p className="text-xs text-muted-foreground">{step.message}</p>
                  {Object.keys(step.metrics).length > 0 && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {Object.entries(step.metrics)
                        .map(([k, v]) => `${k}=${String(v)}`)
                        .join(' · ')}
                    </p>
                  )}
                </div>
                <Badge variant={statusVariant(step.status)}>{step.status}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Batch results */}
      {batch.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>批量结果</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-2 pr-3">协议</th>
                    <th className="py-2 pr-3">状态</th>
                    <th className="py-2">步骤</th>
                  </tr>
                </thead>
                <tbody>
                  {batch.map((r) => (
                    <tr key={r.id} className="border-b">
                      <td className="py-2 pr-3 font-medium">{r.protocol}</td>
                      <td className="py-2 pr-3">
                        <Badge variant={r.status === 'pass' ? 'success' : 'destructive'}>
                          {r.status}
                        </Badge>
                      </td>
                      <td className="py-2">
                        {r.steps
                          .map((s) => `${s.name}:${s.status}`)
                          .join('  ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* History */}
      <Card>
        <CardHeader>
          <CardTitle>验证历史</CardTitle>
        </CardHeader>
        <CardContent>
          {history.length === 0 && (
            <p className="text-sm text-muted-foreground">暂无历史</p>
          )}
          <div className="space-y-2">
            {history.map((r) => (
              <div
                key={r.id}
                className="flex items-center justify-between rounded-md border px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{r.protocol}</span>
                  <Badge variant={r.status === 'pass' ? 'success' : 'destructive'}>
                    {r.status}
                  </Badge>
                </div>
                <span className="text-xs text-muted-foreground">{r.created_at}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default ValidationSimulator
