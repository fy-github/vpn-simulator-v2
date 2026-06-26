import { useRef } from 'react'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  ChartData,
  TooltipItem,
} from 'chart.js'
import { Doughnut } from 'react-chartjs-2'

ChartJS.register(ArcElement, Tooltip, Legend)

interface ProtocolDistributionChartProps {
  data: {
    protocols: string[]
    counts: number[]
    percentages: number[]
    total: number
  }
}

const PROTOCOL_COLORS = [
  'rgb(239, 68, 68)',   // pptp - red
  'rgb(249, 115, 22)',  // l2tp - orange
  'rgb(34, 211, 238)',  // openvpn - cyan
  'rgb(168, 85, 247)',  // ipsec - purple
  'rgb(236, 72, 153)',  // ikev2 - pink
  'rgb(34, 197, 94)',   // wireguard - green
]

const PROTOCOL_BORDER_COLORS = [
  'rgba(239, 68, 68, 0.8)',
  'rgba(249, 115, 22, 0.8)',
  'rgba(34, 211, 238, 0.8)',
  'rgba(168, 85, 247, 0.8)',
  'rgba(236, 72, 153, 0.8)',
  'rgba(34, 197, 94, 0.8)',
]

const ProtocolDistributionChart = ({ data }: ProtocolDistributionChartProps) => {
  const chartRef = useRef<ChartJS<'doughnut'>>(null)

  const chartData = {
    labels: data.protocols.map((p) => p.toUpperCase()),
    datasets: [
      {
        data: data.counts,
        backgroundColor: PROTOCOL_COLORS,
        borderColor: PROTOCOL_BORDER_COLORS,
        borderWidth: 2,
        hoverOffset: 8,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '55%',
    plugins: {
      legend: {
        display: true,
        position: 'right' as const,
        labels: {
          color: '#94a3b8',
          font: { size: 12 },
          padding: 16,
          usePointStyle: true,
          pointStyleWidth: 12,
          generateLabels: (chart: ChartJS<'doughnut'>) => {
            const d = chart.data as ChartData<'doughnut', number[], string>
            const dataset = d.datasets[0]
            return (d.labels ?? []).map((label, i) => ({
              text: `${label} (${data.percentages[i]}%)`,
              fillStyle: (dataset.backgroundColor as string[])[i],
              strokeStyle: (dataset.borderColor as string[])[i],
              lineWidth: 2,
              hidden: false,
              index: i,
              pointStyle: 'circle' as const,
            }))
          },
        },
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        titleColor: '#e2e8f0',
        bodyColor: '#cbd5e1',
        borderColor: 'rgba(148, 163, 184, 0.3)',
        borderWidth: 1,
        callbacks: {
          label: (context: TooltipItem<'doughnut'>) => {
            const idx = context.dataIndex
            return ` ${context.label}: ${data.counts[idx]} connections (${data.percentages[idx]}%)`
          },
        },
      },
    },
  }

  return (
    <div className="relative h-[300px]">
      <Doughnut ref={chartRef} data={chartData} options={options} />
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="text-center">
          <div className="text-3xl font-bold text-white">{data.total}</div>
          <div className="text-xs text-dark-400">Total</div>
        </div>
      </div>
    </div>
  )
}

export default ProtocolDistributionChart
