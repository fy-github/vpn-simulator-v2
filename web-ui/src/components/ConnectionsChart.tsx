import { useRef, useCallback } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  TooltipItem,
} from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

interface ConnectionsChartProps {
  data: {
    timestamps: string[]
    total: number[]
    protocols: Record<string, number[]>
    unit: string
    time_range: string
  }
  timeRange: string
}

const PROTOCOL_COLORS: Record<string, { border: string; bg: string }> = {
  pptp: { border: 'rgb(239, 68, 68)', bg: 'rgba(239, 68, 68, 0.1)' },
  l2tp: { border: 'rgb(249, 115, 22)', bg: 'rgba(249, 115, 22, 0.1)' },
  openvpn: { border: 'rgb(34, 211, 238)', bg: 'rgba(34, 211, 238, 0.1)' },
  ipsec: { border: 'rgb(168, 85, 247)', bg: 'rgba(168, 85, 247, 0.1)' },
  ikev2: { border: 'rgb(236, 72, 153)', bg: 'rgba(236, 72, 153, 0.1)' },
  wireguard: { border: 'rgb(34, 197, 94)', bg: 'rgba(34, 197, 94, 0.1)' },
}

const ConnectionsChart = ({ data, timeRange }: ConnectionsChartProps) => {
  const chartRef = useRef<ChartJS<'line'>>(null)

  const formatTimestamp = useCallback(
    (ts: string) => {
      const date = new Date(ts)
      if (timeRange === '1h') {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    },
    [timeRange]
  )

  const datasets = [
    {
      label: 'Total',
      data: data.total,
      borderColor: 'rgb(255, 255, 255)',
      backgroundColor: 'rgba(255, 255, 255, 0.05)',
      borderWidth: 2.5,
      fill: false,
      tension: 0.4,
      pointRadius: 0,
      pointHoverRadius: 4,
      order: 0,
    },
    ...Object.entries(data.protocols).map(([name, values]) => ({
      label: name.toUpperCase(),
      data: values,
      borderColor: PROTOCOL_COLORS[name]?.border || 'rgb(148, 163, 184)',
      backgroundColor: PROTOCOL_COLORS[name]?.bg || 'rgba(148, 163, 184, 0.1)',
      borderWidth: 1.5,
      fill: true,
      tension: 0.4,
      pointRadius: 0,
      pointHoverRadius: 3,
      order: 1,
    })),
  ]

  const chartData = {
    labels: data.timestamps.map(formatTimestamp),
    datasets,
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
        labels: {
          color: '#94a3b8',
          font: { size: 11 },
          boxWidth: 12,
          padding: 10,
        },
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        titleColor: '#e2e8f0',
        bodyColor: '#cbd5e1',
        borderColor: 'rgba(148, 163, 184, 0.3)',
        borderWidth: 1,
        callbacks: {
          label: (context: TooltipItem<'line'>) => `${context.dataset.label}: ${context.parsed.y}`,
        },
      },
    },
    scales: {
      x: {
        stacked: false,
        grid: {
          color: 'rgba(148, 163, 184, 0.1)',
          drawBorder: false,
        },
        ticks: {
          color: '#64748b',
          maxRotation: 0,
          maxTicksLimit: 10,
          font: { size: 11 },
        },
      },
      y: {
        beginAtZero: true,
        stacked: false,
        grid: {
          color: 'rgba(148, 163, 184, 0.1)',
          drawBorder: false,
        },
        ticks: {
          color: '#64748b',
          font: { size: 11 },
        },
      },
    },
  }

  return (
    <div className="h-[300px]">
      <Line ref={chartRef} data={chartData} options={options} />
    </div>
  )
}

export default ConnectionsChart
