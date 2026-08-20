import { useTranslation } from 'react-i18next'
import SnmpSimulator from '../components/SnmpSimulator'

const Snmp = () => {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('nav.snmp', 'SNMP 仿真')}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          模拟 12 种设备类型（v2c / v3），支持 MIB-II OID 查询（GET）与子树遍历（WALK）
        </p>
      </div>

      <SnmpSimulator />
    </div>
  )
}

export default Snmp
