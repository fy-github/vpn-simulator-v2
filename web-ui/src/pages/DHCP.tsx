import { useTranslation } from 'react-i18next'
import DHCPSimulator from '../components/DHCPSimulator'

const DHCP = () => {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('nav.dhcp', 'DHCP 模拟')}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          伪造随机 MAC 并发获取 DHCP 地址，支持 802.1Q VLAN 打标走 trunk 口，含租约汇总与显式释放
        </p>
      </div>

      <DHCPSimulator />
    </div>
  )
}

export default DHCP
