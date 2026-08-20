import { useTranslation } from 'react-i18next'
import ScaleSimulator from '../components/ScaleSimulator'

const Scale = () => {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('nav.scale', '大规模设备')}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          惰性模拟 3 万设备（O(1) 推导），聚合统计 + 并发巡检 + 聚合快照持久化
        </p>
      </div>

      <ScaleSimulator />
    </div>
  )
}

export default Scale
