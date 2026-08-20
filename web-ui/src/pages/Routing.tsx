import { useTranslation } from 'react-i18next'
import RoutingSimulator from '../components/RoutingSimulator'

const Routing = () => {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('nav.routing', '路由协议')}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          模拟 4 台路由器（2 核心 + 2 边缘）的 OSPF / BGP 邻居建立状态机与路由表
        </p>
      </div>

      <RoutingSimulator />
    </div>
  )
}

export default Routing
