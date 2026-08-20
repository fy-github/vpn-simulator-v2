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
} from './ui'

interface C2Scenario {
  id: string
  name: string
  description: string
  channel: string
  technique: string
  mitre_attck_id: string
  beacon_interval_seconds: number
  indicators: string[]
  severity: string
}

interface C2Step {
  stage: string
  channel: string
  detail: string
}

interface C2Simulation {
  scenario_id: string
  steps: C2Step[]
  detected_indicators: string[]
  started_at: string
}

interface C2Detection {
  scenario_id: string
  channel: string
  mitre_attck_id: string
  indicators: string[]
}

interface C2Ethics {
  title?: string
  purpose?: string
  restrictions?: string[]
  authorization?: string
}

const severityVariant = (severity: string): 'destructive' | 'warning' | 'success' => {
  if (severity === 'critical' || severity === 'high') return 'destructive'
  if (severity === 'low') return 'success'
  return 'warning'
}

const C2Simulator = () => {
  const [scenarios, setScenarios] = useState<C2Scenario[]>([])
  const [ethics, setEthics] = useState<C2Ethics | null>(null)
  const [selectedId, setSelectedId] = useState('')
  const [detection, setDetection] = useState<C2Detection | null>(null)
  const [simulation, setSimulation] = useState<C2Simulation | null>(null)

  useEffect(() => {
    api.getC2Scenarios().then((res) => {
      const list = res.data as C2Scenario[]
      setScenarios(list)
      if (list.length > 0) setSelectedId(list[0].id)
    })
    api.getC2Ethics().then((res) => setEthics(res.data as C2Ethics))
  }, [])

  useEffect(() => {
    if (selectedId) {
      api.getC2Detection(selectedId).then((res) => setDetection(res.data as C2Detection))
      setSimulation(null)
    }
  }, [selectedId])

  const selected = scenarios.find((s) => s.id === selectedId)

  const simulate = async () => {
    if (!selectedId) return
    const res = await api.simulateC2(selectedId)
    setSimulation(res.data as C2Simulation)
  }

  return (
    <div className="space-y-6">
      {/* Ethics */}
      {ethics && (
        <div className="rounded-md border border-warning bg-warning/10 px-4 py-3 text-sm">
          <p className="font-semibold">{ethics.title ?? '伦理声明'}</p>
          <p className="text-muted-foreground mt-1">{ethics.purpose}</p>
          {ethics.restrictions && (
            <ul className="list-disc list-inside mt-1 text-muted-foreground">
              {ethics.restrictions.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
          {ethics.authorization && (
            <p className="text-muted-foreground mt-1">{ethics.authorization}</p>
          )}
        </div>
      )}

      {/* Scenario cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {scenarios.map((s) => (
          <button
            key={s.id}
            onClick={() => setSelectedId(s.id)}
            className={`rounded-lg border p-4 text-left transition-all ${
              selectedId === s.id ? 'border-primary bg-primary/5' : 'hover:border-primary/50'
            }`}
          >
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold">{s.name}</p>
              <Badge variant={severityVariant(s.severity)}>{s.severity}</Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-2">{s.description}</p>
            <p className="text-xs text-muted-foreground mt-2">
              {s.technique} · {s.mitre_attck_id}
            </p>
          </button>
        ))}
      </div>

      {/* Detail */}
      {selected && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <CardTitle>{selected.name}</CardTitle>
              <Badge variant="outline">{selected.channel}</Badge>
              <Badge variant={severityVariant(selected.severity)}>{selected.severity}</Badge>
            </div>
            <CardDescription>{selected.technique} · {selected.mitre_attck_id}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-3">
              <Button onClick={simulate}>模拟</Button>
            </div>

            {detection && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  检测特征（IOC）
                </p>
                <ul className="list-disc list-inside space-y-1">
                  {detection.indicators.map((i) => (
                    <li key={i} className="text-sm">{i}</li>
                  ))}
                </ul>
              </div>
            )}

            {simulation && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  模拟步骤
                </p>
                <div className="space-y-2">
                  {simulation.steps.map((step, idx) => (
                    <div key={idx} className="flex items-center gap-3 rounded-md border px-3 py-2">
                      <Badge variant="outline">{step.stage}</Badge>
                      <span className="text-sm">{step.detail}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default C2Simulator
