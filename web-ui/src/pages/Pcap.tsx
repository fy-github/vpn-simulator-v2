import { useTranslation } from 'react-i18next'
import PcapSimulator from '../components/PcapSimulator'

const Pcap = () => {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('nav.pcap', 'PCAP 回放')}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          上传 PCAP/PCAPNG 文件，按原始时序变速回放（0.5x–10x），支持按协议过滤
        </p>
      </div>

      <PcapSimulator />
    </div>
  )
}

export default Pcap
