import { useTranslation } from 'react-i18next'
import GrafanaPanel from '../components/GrafanaPanel'

const Grafana = () => {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('nav.grafana', 'Grafana')}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          内置仪表板 JSON 与 Prometheus 告警规则，供一键导入 Grafana
        </p>
      </div>

      <GrafanaPanel />
    </div>
  )
}

export default Grafana
