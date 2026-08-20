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

interface DashboardMeta {
  name: string
  uid: string
  title: string
}

interface AlertRule {
  alert: string
  expr: string
  for?: string
  labels?: Record<string, string>
  annotations?: Record<string, string>
}

interface AlertGroup {
  name: string
  rules: AlertRule[]
}

const GrafanaPanel = () => {
  const [dashboards, setDashboards] = useState<DashboardMeta[]>([])
  const [rules, setRules] = useState<AlertGroup[]>([])
  const [selected, setSelected] = useState<string>('')
  const [dashboardJson, setDashboardJson] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    api.getGrafanaDashboards().then((res) => {
      const list = res.data as DashboardMeta[]
      setDashboards(list)
      if (list.length > 0) setSelected(list[0].name)
    })
    api.getGrafanaAlertRules().then((res) => setRules(res.data as AlertGroup[]))
  }, [])

  const viewDashboard = async (name: string) => {
    setSelected(name)
    const res = await api.getGrafanaDashboard(name)
    setDashboardJson(res.data as Record<string, unknown>)
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Dashboards */}
        <Card>
          <CardHeader>
            <CardTitle>内置仪表板</CardTitle>
            <CardDescription>点击查看 JSON 定义</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {dashboards.length === 0 && (
              <p className="text-sm text-muted-foreground">暂无仪表板</p>
            )}
            {dashboards.map((d) => (
              <div
                key={d.name}
                className="flex items-center justify-between rounded-md border px-3 py-2"
              >
                <div>
                  <p className="text-sm font-medium">{d.title}</p>
                  <p className="text-xs text-muted-foreground">uid: {d.uid}</p>
                </div>
                <Button
                  size="sm"
                  variant={selected === d.name ? 'secondary' : 'outline'}
                  onClick={() => viewDashboard(d.name)}
                >
                  JSON
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Alert rules */}
        <Card>
          <CardHeader>
            <CardTitle>告警规则</CardTitle>
            <CardDescription>Prometheus 告警规则</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {rules.map((group) => (
              <div key={group.name}>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  {group.name}
                </p>
                <div className="space-y-2">
                  {group.rules.map((rule) => {
                    const severity = rule.labels?.severity ?? 'warning'
                    return (
                      <div key={rule.alert} className="rounded-md border px-3 py-2">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium">{rule.alert}</p>
                          <Badge variant={severity === 'critical' ? 'destructive' : 'warning'}>
                            {severity}
                          </Badge>
                        </div>
                        <p className="text-xs font-mono text-muted-foreground mt-1">{rule.expr}</p>
                        <p className="text-xs text-muted-foreground">
                          {rule.annotations?.summary ?? ''}
                        </p>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
            {rules.length === 0 && (
              <p className="text-sm text-muted-foreground">暂无告警规则</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Dashboard JSON */}
      {dashboardJson && (
        <Card>
          <CardHeader>
            <CardTitle>仪表板 JSON</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="overflow-x-auto rounded-md bg-muted p-4 text-xs font-mono whitespace-pre-wrap">
              {JSON.stringify(dashboardJson, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default GrafanaPanel
