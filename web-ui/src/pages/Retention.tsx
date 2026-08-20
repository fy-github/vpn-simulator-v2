import { useTranslation } from 'react-i18next'
import RetentionPanel from '../components/RetentionPanel'

const Retention = () => {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('nav.retention', '数据保留')}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          packets / state_transitions 两表的保留策略清理（最大行数 + TTL），防止无限增长
        </p>
      </div>

      <RetentionPanel />
    </div>
  )
}

export default Retention
