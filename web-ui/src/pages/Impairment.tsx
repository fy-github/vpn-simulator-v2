import { useTranslation } from 'react-i18next'
import ImpairmentSimulator from '../components/ImpairmentSimulator'

const Impairment = () => {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('nav.impairment', '网络损伤')}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          按 5 种变化曲线（linear / exponential / step / sine / random）随时间演变网络损伤参数，叠加到真实报文流
        </p>
      </div>

      <ImpairmentSimulator />
    </div>
  )
}

export default Impairment
