import { useTranslation } from 'react-i18next'
import ValidationSimulator from '../components/ValidationSimulator'

const Validation = () => {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('nav.validation', '配置验证')}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          对 6 种 VPN 协议配置执行 7 步验证（语法 / 端口 / 握手 / 认证 / 隧道 / 延迟 / 吞吐）
        </p>
      </div>

      <ValidationSimulator />
    </div>
  )
}

export default Validation
