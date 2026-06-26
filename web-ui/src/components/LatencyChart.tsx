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
  LegendItem,
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

interface LatencyChartProps {
  data: {
    timestamps: string[]
    values: number[]
    min_values: number[]
    max_values: number[]
    unit: string
    time_range: string
    protocol: string
  }
  timeRange: string
}

const LatencyChart = ({ data, timeRange }: LatencyChartProps) => {
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
        label: `Avg Latency (${data.unit})`,
        data: data.values,
        borderColor: 'rgb(168, 85, 247)',
        backgroundColor: 'rgba(168, 85, 247, 0.1)',
        borderWidth: 2,
        fill: false,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: 'rgb(168, 85, 247)',
        pointHoverBorderColor: '#fff',
        order: 1,
      },
      {
        label: 'Range',
        data: data.max_values,
        borderColor: 'rgba(168, 85, 247, 0.2)',
        backgroundColor: 'rgba(168, 85, 247, 0.05)',
        borderWidth: 1,
        fill: '+1',
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 0,
        order: 2,
      },
      {
        label: 'Min',
        data: data.min_values,
        borderColor: 'rgba(168, 85, 247, 0.2)',
        backgroundColor: 'transparent',
        borderWidth: 1,
        fill: false,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 0,
        order: 3,
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
          filter: (item: LegendItem) => item.text === `Avg Latency (${data.unit})`,
        },
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        titleColor: '#e2e8f0',
        bodyColor: '#cbd5e1',
        borderColor: 'rgba(168, 85, 247, 0.3)',
        borderWidth: 1,
        callbacks: {
          label: (context: TooltipItem<'line'>) => {
            if (context.dataset.label === `Avg Latency (${data.unit})`) {
              return `Avg: ${(context.parsed.y ?? 0).toFixed(2)} ${data.unit}`
            }
            return undefined
          },
          afterBody: (contexts: Array<{ dataIndex: number }>) => {
            const idx = contexts[0]?.dataIndex
            if (idx !== undefined) {
              return [
                `Min: ${data.min_values[idx].toFixed(2)} ${data.unit}`,
                `Max: ${data.max_values[idx].toFixed(2)} ${data.unit}`,
              ]
            }
            return []
          },
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
        grid: {
          color: 'rgba(148, 163, 184, 0.1)',
          drawBorder: false,
        },
        ticks: {
          color: '#64748b',
          callback: (value: string | number) => `${value} ${data.unit}`,
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

export default LatencyChart
