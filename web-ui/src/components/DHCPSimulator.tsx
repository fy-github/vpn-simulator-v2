import { Fragment, useCallback, useEffect, useRef, useState } from 'react'
import type { ComponentType, ReactNode } from 'react'
import { api } from '../api/client'
import {
  ActivityIcon,
  AlertTriangleIcon,
  ArrowRightIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ListIcon,
  NetworkIcon,
  PlayIcon,
  RotateCcwIcon,
  ServerIcon,
  SettingsIcon,
  SlidersIcon,
  StopIcon,
  TerminalIcon,
  XIcon,
} from './Icons'
import { Badge, type BadgeVariant } from './ui/Badge'
import { Button } from './ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/Card'
import { Input } from './ui/Input'
import { Select } from './ui/Select'

interface DhcpLogLine {
  seq: number
  line: string
  ts: string
}

interface DhcpLease {
  mac: string
  ip: string
  server: string
  lease: number
}

interface DhcpStatus {
  state: string
  seq: number
  logs: DhcpLogLine[]
  leases: DhcpLease[]
  returncode: number | null
}

interface FormState {
  count: number
  interval: number
  timeout: number
  attempts: number
  iface: string
  vlan: string
  sourceMac: string
  hold: boolean
  duration: number
  server: string
  pool: string
  blind: boolean
  raw: boolean
  verbose: boolean
}

const STATUS_MAP: Record<string, { label: string; variant: BadgeVariant }> = {
  idle: { label: '空闲', variant: 'outline' },
  running: { label: '运行中', variant: 'success' },
  stopping: { label: '停止中', variant: 'warning' },
  completed: { label: '已完成', variant: 'default' },
  error: { label: '出错', variant: 'destructive' },
}

const STATUS_DOT: Record<string, string> = {
  idle: 'bg-muted-foreground',
  running: 'bg-success animate-pulse',
  stopping: 'bg-warning animate-pulse',
  completed: 'bg-primary',
  error: 'bg-destructive',
}

// DHCP 握手四步（DORA）
const DORA_STAGES = ['DISCOVER', 'OFFER', 'REQUEST', 'ACK']

interface StatCardProps {
  label: string
  icon: ComponentType<{ className?: string }>
  children: ReactNode
}

const StatCard = ({ label, icon: Icon, children }: StatCardProps) => (
  <Card className="p-4">
    <div className="flex items-center justify-between gap-3">
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
        <div className="mt-1.5 flex items-center gap-2">{children}</div>
      </div>
      <Icon className="h-5 w-5 shrink-0 text-muted-foreground/60" />
    </div>
  </Card>
)

interface ToggleProps {
  checked: boolean
  onChange: (value: boolean) => void
  label: string
  description?: string
  disabled?: boolean
}

const Toggle = ({ checked, onChange, label, description, disabled }: ToggleProps) => (
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    disabled={disabled}
    onClick={() => onChange(!checked)}
    className="flex w-full items-center gap-3 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
  >
    <span
      className={`relative inline-flex h-5 w-9 shrink-0 rounded-full transition-colors duration-200 ${
        checked ? 'bg-primary' : 'bg-secondary'
      }`}
    >
      <span
        className={`absolute left-0.5 top-0.5 inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200 ${
          checked ? 'translate-x-4' : 'translate-x-0'
        }`}
      />
    </span>
    <span className="min-w-0">
      <span className="block text-sm font-medium">{label}</span>
      {description && <span className="block text-xs text-muted-foreground">{description}</span>}
    </span>
  </button>
)

interface SectionLabelProps {
  icon: ComponentType<{ className?: string }>
  children: ReactNode
}

const SectionLabel = ({ icon: Icon, children }: SectionLabelProps) => (
  <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
    <Icon className="h-3.5 w-3.5 text-primary" />
    <span>{children}</span>
  </div>
)

const DHCPSimulator = () => {
  const [form, setForm] = useState<FormState>({
    count: 5,
    interval: 0.5,
    timeout: 6.0,
    attempts: 3,
    iface: '',
    vlan: '',
    sourceMac: 'random',
    hold: false,
    duration: 0,
    server: '',
    pool: '',
    blind: false,
    raw: false,
    verbose: false,
  })

  const [jobState, setJobState] = useState('idle')
  const [logs, setLogs] = useState<DhcpLogLine[]>([])
  const [leases, setLeases] = useState<DhcpLease[]>([])
  const [returncode, setReturncode] = useState<number | null>(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [releaseMsg, setReleaseMsg] = useState('')
  const [startLoading, setStartLoading] = useState(false)
  const [releaseLoading, setReleaseLoading] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)

  const lastSeqRef = useRef(0)
  const consoleRef = useRef<HTMLDivElement>(null)

  const updateField = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const refreshStatus = useCallback(async () => {
    try {
      const response = await api.getDhcpStatus(lastSeqRef.current)
      const data: DhcpStatus = response.data
      setJobState(data.state)
      setLeases(data.leases || [])
      setReturncode(data.returncode)
      lastSeqRef.current = data.seq
      if (data.logs?.length) {
        setLogs((prev) => {
          const seen = new Set(prev.map((log) => log.seq))
          return [...prev, ...data.logs.filter((log) => !seen.has(log.seq))]
        })
      }
    } catch (err) {
      console.error('Failed to fetch DHCP status:', err)
    }
  }, [])

  // 首次挂载拉取状态
  useEffect(() => {
    refreshStatus()
  }, [refreshStatus])

  // 运行/停止中时每秒轮询
  const isActive = jobState === 'running' || jobState === 'stopping'
  useEffect(() => {
    if (!isActive) return
    const id = setInterval(() => {
      refreshStatus()
    }, 1000)
    return () => clearInterval(id)
  }, [isActive, refreshStatus])

  // 日志自动滚动到底部
  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight
    }
  }, [logs])

  const handleStart = async () => {
    setStartLoading(true)
    setErrorMsg('')
    setReleaseMsg('')
    try {
      const payload: Record<string, unknown> = {
        count: form.count,
        interval: form.interval,
        timeout: form.timeout,
        attempts: form.attempts,
        source_mac: form.sourceMac,
        hold: form.hold,
        duration: form.duration,
        blind: form.blind,
        raw: form.raw,
        verbose: form.verbose,
      }
      if (form.iface.trim()) payload.iface = form.iface.trim()
      if (form.vlan.trim() !== '') payload.vlan = Number(form.vlan)
      if (form.server.trim()) payload.server = form.server.trim()
      if (form.pool.trim()) payload.pool = form.pool.trim()

      await api.startDhcp(payload)
      setLogs([])
      lastSeqRef.current = 0
      setJobState('running')
      await refreshStatus()
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErrorMsg(detail || '启动失败，请查看后端日志')
    } finally {
      setStartLoading(false)
    }
  }

  const handleStop = async () => {
    try {
      await api.stopDhcp()
      setJobState('stopping')
    } catch (err) {
      console.error('Failed to stop DHCP job:', err)
    }
  }

  const handleRelease = async () => {
    setReleaseLoading(true)
    setReleaseMsg('')
    setErrorMsg('')
    try {
      const payload: Record<string, unknown> = {}
      if (form.iface.trim()) payload.iface = form.iface.trim()
      if (form.vlan.trim() !== '') payload.vlan = Number(form.vlan)
      if (form.server.trim()) payload.server = form.server.trim()

      const response = await api.releaseDhcp(payload)
      setLeases(response.data.leases || [])
      setReleaseMsg(response.data.message || '释放完成')
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErrorMsg(detail || '释放失败')
    } finally {
      setReleaseLoading(false)
    }
  }

  const clearConsole = () => setLogs([])

  const status = STATUS_MAP[jobState] || STATUS_MAP.idle

  return (
    <div className="space-y-6">
      {errorMsg && (
        <Card className="border-l-4 border-destructive">
          <CardContent className="flex items-start gap-3 p-4">
            <AlertTriangleIcon className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
            <p className="text-sm text-foreground">{errorMsg}</p>
          </CardContent>
        </Card>
      )}

      {/* 状态统计 */}
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatCard label="任务状态" icon={ActivityIcon}>
          <span className={`h-2.5 w-2.5 rounded-full ${STATUS_DOT[jobState] || STATUS_DOT.idle}`} />
          <span className="text-lg font-semibold">{status.label}</span>
        </StatCard>
        <StatCard label="已获取地址" icon={ServerIcon}>
          <span className="text-lg font-semibold text-primary">{leases.length}</span>
          <span className="text-sm text-muted-foreground">个</span>
        </StatCard>
        <StatCard label="日志行数" icon={ListIcon}>
          <span className="text-lg font-semibold">{logs.length}</span>
        </StatCard>
        <StatCard label="返回码" icon={TerminalIcon}>
          {returncode === null ? (
            <span className="text-lg font-semibold text-muted-foreground">—</span>
          ) : (
            <span
              className={`text-lg font-semibold ${
                returncode === 0 ? 'text-success' : 'text-destructive'
              }`}
            >
              {returncode}
            </span>
          )}
        </StatCard>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* 模拟配置 */}
        <Card className="self-start xl:col-span-1">
          <CardHeader className="border-b">
            <CardTitle className="text-lg">模拟参数</CardTitle>
            <CardDescription>伪造随机 MAC 并发获取 DHCP 地址</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* 基础参数 */}
            <section>
              <SectionLabel icon={SlidersIcon}>基础参数</SectionLabel>
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="地址数量"
                  type="number"
                  min={1}
                  max={200}
                  value={form.count}
                  onChange={(e) => updateField('count', Number(e.target.value))}
                />
                <Input
                  label="启动间隔 (秒)"
                  type="number"
                  min={0}
                  step={0.1}
                  value={form.interval}
                  onChange={(e) => updateField('interval', Number(e.target.value))}
                />
                <Input
                  label="超时 (秒)"
                  type="number"
                  min={0.1}
                  step={0.1}
                  value={form.timeout}
                  onChange={(e) => updateField('timeout', Number(e.target.value))}
                />
                <Input
                  label="重试次数"
                  type="number"
                  min={1}
                  value={form.attempts}
                  onChange={(e) => updateField('attempts', Number(e.target.value))}
                />
              </div>
            </section>

            {/* 网络接口 */}
            <section>
              <SectionLabel icon={NetworkIcon}>网络接口</SectionLabel>
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="网卡名 (iface)"
                  placeholder="en0"
                  value={form.iface}
                  onChange={(e) => updateField('iface', e.target.value)}
                />
                <Input
                  label="VLAN ID"
                  type="number"
                  min={1}
                  max={4094}
                  placeholder="可选"
                  value={form.vlan}
                  onChange={(e) => updateField('vlan', e.target.value)}
                />
              </div>
              <div className="mt-4">
                <Select
                  label="源 MAC"
                  options={[
                    { value: 'random', label: '随机 MAC' },
                    { value: 'real', label: '真实 MAC' },
                  ]}
                  value={form.sourceMac}
                  onChange={(value) => updateField('sourceMac', value)}
                />
              </div>
            </section>

            {/* 高级选项 */}
            <section>
              <button
                type="button"
                onClick={() => setShowAdvanced((v) => !v)}
                className="flex w-full items-center justify-between text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                <span className="flex items-center gap-2">
                  <SettingsIcon className="h-4 w-4" />
                  高级选项
                </span>
                {showAdvanced ? (
                  <ChevronUpIcon className="h-4 w-4" />
                ) : (
                  <ChevronDownIcon className="h-4 w-4" />
                )}
              </button>
              {showAdvanced && (
                <div className="mt-4 space-y-4">
                  <Input
                    label="DHCP 服务器 IP"
                    placeholder="192.168.46.1"
                    value={form.server}
                    onChange={(e) => updateField('server', e.target.value)}
                  />
                  <Input
                    label="地址池区间"
                    placeholder="192.168.99.50-150"
                    value={form.pool}
                    onChange={(e) => updateField('pool', e.target.value)}
                  />
                  <div className="space-y-1">
                    <Toggle
                      checked={form.blind}
                      onChange={(v) => updateField('blind', v)}
                      label="盲写模式"
                      description="配合地址池 / 服务器指定"
                    />
                    <Toggle
                      checked={form.raw}
                      onChange={(v) => updateField('raw', v)}
                      label="BPF 抓包接收"
                      description="需要后端进程具备抓包权限"
                    />
                    <Toggle
                      checked={form.verbose}
                      onChange={(v) => updateField('verbose', v)}
                      label="详细日志"
                      description="打印每个收发报文"
                    />
                  </div>
                </div>
              )}
            </section>

            {/* 持续模拟 */}
            <section>
              <Toggle
                checked={form.hold}
                onChange={(v) => updateField('hold', v)}
                label="持续模拟（续期保持）"
                description="周期续租以长期占用地址"
              />
              {form.hold && (
                <div className="mt-3">
                  <Input
                    label="持续时长 (秒，0 为手动停止)"
                    type="number"
                    min={0}
                    value={form.duration}
                    onChange={(e) => updateField('duration', Number(e.target.value))}
                  />
                </div>
              )}
            </section>

            {/* 操作按钮 */}
            <div className="flex gap-3 border-t pt-4">
              <Button
                onClick={handleStart}
                loading={startLoading}
                disabled={isActive}
                className="flex-1"
              >
                <PlayIcon className="mr-2 h-4 w-4" />
                开始模拟
              </Button>
              <Button variant="outline" onClick={handleStop} disabled={!isActive}>
                <StopIcon className="mr-2 h-4 w-4" />
                停止
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* 右侧：日志 + 租约 */}
        <div className="space-y-6 xl:col-span-2">
          {/* 运行日志 */}
          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0 border-b">
              <div className="flex items-center gap-2">
                <TerminalIcon className="h-5 w-5 text-primary" />
                <CardTitle className="text-lg">运行日志</CardTitle>
                <Badge variant={status.variant}>{status.label}</Badge>
              </div>
              <Button variant="ghost" size="sm" onClick={clearConsole}>
                <XIcon className="mr-1 h-4 w-4" />
                清空
              </Button>
            </CardHeader>
            <CardContent className="p-4">
              <div
                ref={consoleRef}
                className="h-72 overflow-y-auto rounded-md bg-black/40 p-4 font-mono text-xs leading-relaxed text-foreground"
              >
                {logs.length === 0 ? (
                  <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
                    <p className="text-muted-foreground">启动模拟后，此处将实时显示脚本输出。</p>
                    <div className="flex items-center gap-2">
                      {DORA_STAGES.map((stage, index) => (
                        <Fragment key={stage}>
                          <span className="rounded bg-secondary px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
                            {stage}
                          </span>
                          {index < DORA_STAGES.length - 1 && (
                            <ArrowRightIcon className="h-3 w-3 text-muted-foreground" />
                          )}
                        </Fragment>
                      ))}
                    </div>
                  </div>
                ) : (
                  logs.map((log) => (
                    <div key={log.seq} className="whitespace-pre-wrap break-all">
                      <span className="text-muted-foreground">[{log.ts}]</span> {log.line}
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {/* 租约结果 */}
          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0 border-b">
              <div>
                <CardTitle className="text-lg">租约结果</CardTitle>
                <CardDescription>当前模拟获取的 DHCP 地址</CardDescription>
              </div>
              <Button
                variant="outline"
                onClick={handleRelease}
                loading={releaseLoading}
                disabled={isActive}
              >
                <RotateCcwIcon className="mr-2 h-4 w-4" />
                释放地址
              </Button>
            </CardHeader>
            {releaseMsg && (
              <CardContent className="border-b py-3">
                <div className="rounded-md border border-info bg-muted px-4 py-3">
                  <pre className="whitespace-pre-wrap font-mono text-xs text-foreground">
                    {releaseMsg}
                  </pre>
                </div>
              </CardContent>
            )}
            <CardContent className="p-0">
              {leases.length === 0 ? (
                <div className="flex items-center justify-center gap-3 py-10 text-muted-foreground">
                  <ServerIcon className="h-6 w-6 shrink-0" />
                  <p className="text-sm">暂无租约，开始模拟后此处将列出成功获取的地址。</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/40 text-left">
                        <th className="px-4 py-2.5 font-medium text-muted-foreground">序号</th>
                        <th className="px-4 py-2.5 font-medium text-muted-foreground">MAC</th>
                        <th className="px-4 py-2.5 font-medium text-muted-foreground">IP</th>
                        <th className="px-4 py-2.5 font-medium text-muted-foreground">服务器</th>
                        <th className="px-4 py-2.5 font-medium text-muted-foreground">租约</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leases.map((lease, index) => (
                        <tr
                          key={`${lease.mac}-${lease.ip}`}
                          className="border-b transition-colors last:border-0 hover:bg-muted"
                        >
                          <td className="px-4 py-2.5 text-muted-foreground">{index + 1}</td>
                          <td className="px-4 py-2.5 font-mono">{lease.mac}</td>
                          <td className="px-4 py-2.5 font-mono text-primary">{lease.ip}</td>
                          <td className="px-4 py-2.5 font-mono text-muted-foreground">
                            {lease.server}
                          </td>
                          <td className="px-4 py-2.5 text-muted-foreground">{lease.lease}s</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* 权限提示 */}
          <Card className="border-l-4 border-warning">
            <CardContent className="flex items-start gap-3 p-4">
              <AlertTriangleIcon className="mt-0.5 h-5 w-5 shrink-0 text-warning" />
              <div className="space-y-1 text-sm text-muted-foreground">
                <p>
                  普通 UDP 模式无需特权；使用 VLAN 打标走 trunk 口、或 BPF 抓包接收时，需要后端进程具备对应权限。
                </p>
                <p>
                  一个地址都拿不到时，可改用「真实 MAC」复测：若 real 能拿到而随机 MAC 不行，说明网关开启了 IP-MAC 绑定 / 防 DHCP 欺骗。
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default DHCPSimulator
