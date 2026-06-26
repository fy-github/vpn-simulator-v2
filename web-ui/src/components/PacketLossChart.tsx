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

interface PacketLossChartProps {
  data: {
    timestamps: string[]
    values: number[]
    unit: string
    time_range: string
    protocol: string
  }
  timeRange: string
}

const PacketLossChart = ({ data, timeRange }: PacketLossChartProps) => {
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

  const chartData = {
    labels: data.timestamps.map(formatTimestamp),
    datasets: [
      {
        label: `Packet Loss (${data.unit})`,
        data: data.values,
        borderColor: 'rgb(239, 68, 68)',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: 'rgb(239, 68, 68)',
        pointHoverBorderColor: '#fff',
      },
    ],
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
          font: { size: 12 },
        },
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        titleColor: '#e2e8f0',
        bodyColor: '#cbd5e1',
        borderColor: 'rgba(239, 68, 68, 0.3)',
        borderWidth: 1,
        callbacks: {
          label: (context: TooltipItem<'line'>) =>
            `${(context.parsed.y ?? 0).toFixed(3)} ${data.unit}`,
        },
      },
    },
    scales: {
      x: {
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
        suggestedMax: 2,
        grid: {
          color: 'rgba(148, 163, 184, 0.1)',
          drawBorder: false,
        },
        ticks: {
          color: '#64748b',
          callback: (value: string | number) => `${value}%`,
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

export default PacketLossChart
