import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line } from 'react-chartjs-2'
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
  Select,
  Progress,
} from './ui'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

interface Preset {
  name: string
  fault_type: string
  param: string
  change_type: string
  start_value: number
  end_value: number
  duration_seconds: number
  period_seconds?: number
  step_at_seconds?: number | null
  target?: string
}

interface ImpairmentRecord {
  id: string
  name: string
  fault_type: string
  param: string
  change_type: string
  start_value: number
  end_value: number
  duration_seconds: number
  period_seconds: number
  step_at_seconds: number | null
  target: string
  active: boolean
  created_at: string
  started_at: string | null
  stopped_at: string | null
}

interface ImpairmentStatus extends ImpairmentRecord {
  elapsed_seconds: number | null
  progress: number
  current_value: number | null
}

interface TimelinePoint {
  t: number
  value: number
}

const FAULT_TYPES = [
  { value: 'latency', label: 'Latency (延迟)' },
  { value: 'packet_loss', label: 'Packet Loss (丢包)' },
  { value: 'bandwidth', label: 'Bandwidth (带宽)' },
  { value: 'reorder', label: 'Reorder (乱序)' },
  { value: 'duplicate', label: 'Duplicate (重复)' },
  { value: 'corrupt', label: 'Corrupt (损坏)' },
]

const CHANGE_TYPES = [
  { value: 'linear', label: 'Linear (线性)' },
  { value: 'exponential', label: 'Exponential (指数)' },
  { value: 'step', label: 'Step (阶跃)' },
  { value: 'sine', label: 'Sine (正弦)' },
  { value: 'random', label: 'Random (随机)' },
]

const COMMON_PARAMS = ['delay_ms', 'jitter_ms', 'loss_rate', 'bandwidth_kbps']

const TimelineChart = ({ points, unit }: { points: TimelinePoint[]; unit: string }) => {
  const chartData = {
    labels: points.map((p) => p.t.toFixed(1)),
    datasets: [
      {
        label: `${unit}`,
        data: points.map((p) => p.value),
        borderColor: 'rgb(168, 85, 247)',
        backgroundColor: 'rgba(168, 85, 247, 0.1)',
        borderWidth: 2,
        fill: false,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 4,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        titleColor: '#e2e8f0',
        bodyColor: '#cbd5e1',
      },
    },
    scales: {
      x: {
        title: { display: true, text: 't (s)' },
        grid: { color: 'rgba(148, 163, 184, 0.1)' },
        ticks: { color: '#64748b', font: { size: 11 } },
      },
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(148, 163, 184, 0.1)' },
        ticks: { color: '#64748b', font: { size: 11 } },
      },
    },
  }

  return (
    <div className="h-[240px]">
      <Line data={chartData} options={options} />
    </div>
  )
}

const ImpairmentSimulator = () => {
  const { t } = useTranslation()
  const [presets, setPresets] = useState<Preset[]>([])
  const [impairments, setImpairments] = useState<ImpairmentRecord[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedStatus, setSelectedStatus] = useState<ImpairmentStatus | null>(null)
  const [timeline, setTimeline] = useState<TimelinePoint[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [form, setForm] = useState({
    fault_type: 'latency',
    change_type: 'linear',
    param: 'delay_ms',
    start_value: '0',
    end_value: '300',
    duration_seconds: '60',
    period_seconds: '0',
    step_at_seconds: '',
    target: '',
    name: '',
  })

  const refreshImpairments = useCallback(async () => {
    const res = await api.getImpairments()
    setImpairments(res.data as ImpairmentRecord[])
  }, [])

  const refreshPresets = useCallback(async () => {
    const res = await api.getImpairmentPresets()
    setPresets(res.data as Preset[])
  }, [])

  useEffect(() => {
    refreshPresets().catch(() => setError(t('impairment.loadError', '加载预设失败')))
    refreshImpairments().catch(() => setError(t('impairment.loadError', '加载损伤失败')))
  }, [refreshPresets, refreshImpairments, t])

  const loadDetail = useCallback(async (id: string) => {
    setSelectedId(id)
    const [statusRes, timelineRes] = await Promise.all([
      api.getImpairmentStatus(id),
      api.getImpairmentTimeline(id, 120),
    ])
    setSelectedStatus(statusRes.data as ImpairmentStatus)
    setTimeline(timelineRes.data as TimelinePoint[])
  }, [])

  const applyPreset = async (name: string) => {
    setLoading(true)
    setError('')
    try {
      await api.applyImpairmentPreset(name)
      await refreshImpairments()
    } catch (e) {
      setError(typeof e === 'object' && e !== null && 'message' in e ? String(e.message) : String(e))
    } finally {
      setLoading(false)
    }
  }

  const createImpairment = async () => {
    setLoading(true)
    setError('')
    try {
      await api.createImpairment({
        fault_type: form.fault_type,
        change_type: form.change_type,
        param: form.param,
        start_value: Number(form.start_value),
        end_value: Number(form.end_value),
        duration_seconds: Number(form.duration_seconds),
        period_seconds: Number(form.period_seconds || '0'),
        step_at_seconds: form.step_at_seconds ? Number(form.step_at_seconds) : null,
        target: form.target,
        name: form.name,
      })
      await refreshImpairments()
    } catch (e) {
      setError(typeof e === 'object' && e !== null && 'message' in e ? String(e.message) : String(e))
    } finally {
      setLoading(false)
    }
  }

  const startImpairment = async (id: string) => {
    await api.startImpairment(id)
    await refreshImpairments()
    await loadDetail(id)
  }

  const stopImpairment = async (id: string) => {
    await api.stopImpairment(id)
    await refreshImpairments()
    await loadDetail(id)
  }

  const removeImpairment = async (id: string) => {
    await api.removeImpairment(id)
    if (selectedId === id) {
      setSelectedId(null)
      setSelectedStatus(null)
      setTimeline([])
    }
    await refreshImpairments()
  }

  const setField = (key: keyof typeof form, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-md border border-destructive bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Presets */}
        <Card>
          <CardHeader>
            <CardTitle>{t('impairment.presets', '内置预设')}</CardTitle>
            <CardDescription>
              {t('impairment.presetsHint', '点击预设立即应用一条时间变化损伤')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {presets.length === 0 && (
              <p className="text-sm text-muted-foreground">
                {t('impairment.noPresets', '暂无预设')}
              </p>
            )}
            {presets.map((p) => (
              <div
                key={p.name}
                className="flex items-center justify-between rounded-md border px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{p.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {p.fault_type} · {p.change_type} · {p.start_value} → {p.end_value} ({p.param})
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  loading={loading}
                  onClick={() => applyPreset(p.name)}
                >
                  {t('impairment.apply', '应用')}
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Create form */}
        <Card>
          <CardHeader>
            <CardTitle>{t('impairment.create', '创建损伤')}</CardTitle>
            <CardDescription>
              {t('impairment.createHint', '自定义故障类型、变化曲线与参数范围')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Select
                label={t('impairment.faultType', '故障类型')}
                options={FAULT_TYPES}
                value={form.fault_type}
                onChange={(v) => setField('fault_type', v)}
              />
              <Select
                label={t('impairment.changeType', '变化类型')}
                options={CHANGE_TYPES}
                value={form.change_type}
                onChange={(v) => setField('change_type', v)}
              />
            </div>
            <Input
              label={t('impairment.param', '参数名')}
              list="impairment-params"
              value={form.param}
              onChange={(e) => setField('param', e.target.value)}
            />
            <datalist id="impairment-params">
              {COMMON_PARAMS.map((p) => (
                <option key={p} value={p} />
              ))}
            </datalist>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label={t('impairment.startValue', '起始值')}
                value={form.start_value}
                onChange={(e) => setField('start_value', e.target.value)}
              />
              <Input
                label={t('impairment.endValue', '结束值')}
                value={form.end_value}
                onChange={(e) => setField('end_value', e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label={t('impairment.duration', '时长(秒)')}
                value={form.duration_seconds}
                onChange={(e) => setField('duration_seconds', e.target.value)}
              />
              <Input
                label={t('impairment.period', '周期(秒,正弦)')}
                value={form.period_seconds}
                onChange={(e) => setField('period_seconds', e.target.value)}
              />
            </div>
            <Input
              label={t('impairment.stepAt', '阶跃时刻(秒,可选)')}
              value={form.step_at_seconds}
              onChange={(e) => setField('step_at_seconds', e.target.value)}
            />
            <Input
              label={t('impairment.target', '目标(协议/连接)')}
              value={form.target}
              placeholder="wireguard"
              onChange={(e) => setField('target', e.target.value)}
            />
            <Input
              label={t('impairment.name', '名称(可选)')}
              value={form.name}
              onChange={(e) => setField('name', e.target.value)}
            />
            <Button loading={loading} onClick={createImpairment}>
              {t('impairment.createBtn', '创建')}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Active impairments */}
      <Card>
        <CardHeader>
          <CardTitle>{t('impairment.active', '活动损伤')}</CardTitle>
          <CardDescription>
            {t('impairment.activeHint', '启动/停止/删除，点击条目查看变化曲线')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {impairments.length === 0 && (
            <p className="text-sm text-muted-foreground">
              {t('impairment.none', '暂无损伤实例')}
            </p>
          )}
          {impairments.map((imp) => (
            <div key={imp.id} className="rounded-md border px-3 py-2">
              <div className="flex items-center justify-between gap-3">
                <button
                  className="flex-1 text-left min-w-0"
                  onClick={() => loadDetail(imp.id)}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium truncate">
                      {imp.name || imp.id.slice(0, 8)}
                    </span>
                    <Badge variant={imp.active ? 'success' : 'secondary'}>
                      {imp.active ? 'running' : 'stopped'}
                    </Badge>
                    <Badge variant="outline">{imp.fault_type}</Badge>
                    <Badge variant="outline">{imp.change_type}</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {imp.param}: {imp.start_value} → {imp.end_value} · {imp.duration_seconds}s
                  </p>
                </button>
                <div className="flex items-center gap-1">
                  {imp.active ? (
                    <Button size="sm" variant="outline" onClick={() => stopImpairment(imp.id)}>
                      stop
                    </Button>
                  ) : (
                    <Button size="sm" variant="outline" onClick={() => startImpairment(imp.id)}>
                      start
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => removeImpairment(imp.id)}
                  >
                    ×
                  </Button>
                </div>
              </div>
            </div>
          ))}

          {selectedStatus && (
            <div className="mt-4 rounded-md border bg-muted/30 px-4 py-3 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">
                  {selectedStatus.name || selectedStatus.id.slice(0, 8)}
                </p>
                <p className="text-sm text-muted-foreground">
                  {t('impairment.current', '当前值')}:{' '}
                  {selectedStatus.current_value ?? '—'} {selectedStatus.param}
                </p>
              </div>
              <Progress value={Math.round(selectedStatus.progress * 100)} max={100} />
              <TimelineChart points={timeline} unit={selectedStatus.param} />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default ImpairmentSimulator
