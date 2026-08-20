import { useTranslation } from 'react-i18next'
import C2Simulator from '../components/C2Simulator'

const C2 = () => {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('nav.c2', 'C2 场景')}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          6 种 C2 攻击场景的行为模拟与检测特征（仅用于教学 / 防御研究）
        </p>
      </div>

      <C2Simulator />
    </div>
  )
}

export default C2
