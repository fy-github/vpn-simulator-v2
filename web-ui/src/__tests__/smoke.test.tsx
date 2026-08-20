import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import '../i18n'

import Attacks from '../pages/Attacks'
import C2 from '../pages/C2'
import Comparison from '../pages/Comparison'
import Connections from '../pages/Connections'
import Dashboard from '../pages/Dashboard'
import DHCP from '../pages/DHCP'
import DPI from '../pages/DPI'
import Faults from '../pages/Faults'
import Grafana from '../pages/Grafana'
import Impairment from '../pages/Impairment'
import IoT from '../pages/IoT'
import Learning from '../pages/Learning'
import Metrics from '../pages/Metrics'
import Obfuscation from '../pages/Obfuscation'
import Packets from '../pages/Packets'
import Pcap from '../pages/Pcap'
import Protocols from '../pages/Protocols'
import Retention from '../pages/Retention'
import Routing from '../pages/Routing'
import Scale from '../pages/Scale'
import Scenarios from '../pages/Scenarios'
import Snmp from '../pages/Snmp'
import Traffic from '../pages/Traffic'
import Tutorial from '../pages/Tutorial'
import Validation from '../pages/Validation'
import VendorCLI from '../pages/VendorCLI'
import Voice from '../pages/Voice'

// Returns an "empty" value that tolerates arbitrary property access, function
// calls, array iteration and numeric coercion: a callable proxy whose unknown
// properties resolve to further such values, so `data.packets`, `stats.by_type`,
// `data.codecs`, `stats.avg_cpu_percent.toFixed(1)`, `data.something()` etc.
// never throw. Array-ish methods return real empty arrays / falsey values so
// React can render the result.
function emptyData(): unknown {
  const value = (): unknown => emptyData()
  return new Proxy(value, {
    get(target, prop) {
      if (prop === 'then' || prop === 'toJSON' || prop === '$$typeof' || prop === Symbol.toPrimitive) {
        return undefined
      }
      if (prop === Symbol.iterator) return function* () {}
      if (prop === 'valueOf') return () => 0
      if (prop === 'toString') return () => ''
      if (prop === 'toFixed' || prop === 'toPrecision' || prop === 'toLocaleString') return () => '0'
      if (prop === 'length') return 0
      if (prop === 'map' || prop === 'filter' || prop === 'slice' || prop === 'reverse' || prop === 'concat') {
        return () => []
      }
      if (prop === 'find' || prop === 'findIndex') return () => undefined
      if (prop === 'forEach' || prop === 'reduce' || prop === 'some' || prop === 'every' || prop === 'sort') {
        return () => undefined
      }
      if (prop === 'includes') return () => false
      if (prop === 'indexOf') return () => -1
      if (prop === 'join') return () => ''
      if (prop in target) return Reflect.get(target, prop)
      return emptyData()
    },
    apply() {
      return emptyData()
    },
  })
}

// Mock the API client: every method resolves to an empty list so pages render
// their shell without hitting a real backend.
vi.mock('../api/client', () => ({
  api: new Proxy(
    {},
    {
      get: (_target, prop) => {
        if (prop === 'getRetentionStatus') {
          return vi.fn(() => Promise.resolve({ data: { packets: 0, state_transitions: 0 } }))
        }
        return vi.fn(() => Promise.resolve({ data: emptyData() }))
      },
    },
  ),
}))

// Chart.js needs a real <canvas> 2D context which jsdom does not provide;
// stub the chart components so pages render their shell without charting.
vi.mock('react-chartjs-2', () => ({
  Line: () => <div data-testid="chart-stub" />,
  Bar: () => <div data-testid="chart-stub" />,
  Doughnut: () => <div data-testid="chart-stub" />,
  Radar: () => <div data-testid="chart-stub" />,
}))

beforeAll(() => {
  // Pages such as Learning / Tutorial / Voice use native fetch; resolve them
  // to an empty list so they render their shell without a backend.
  vi.stubGlobal(
    'fetch',
    vi.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve(emptyData()) }),
    ),
  )
})

afterEach(cleanup)

const pages: Array<[string, () => React.JSX.Element, string]> = [
  ['Attacks', () => <Attacks />, '攻击管理'],
  ['C2', () => <C2 />, 'C2 场景'],
  ['Comparison', () => <Comparison />, '协议对比'],
  ['Connections', () => <Connections />, '连接管理'],
  ['Dashboard', () => <Dashboard />, '总连接数'],
  ['DHCP', () => <DHCP />, 'DHCP 模拟'],
  ['DPI', () => <DPI />, '深度包检测 (DPI)'],
  ['Faults', () => <Faults />, '故障注入'],
  ['Grafana', () => <Grafana />, 'Grafana'],
  ['Impairment', () => <Impairment />, '网络损伤'],
  ['IoT', () => <IoT />, 'IoT 设备模拟器'],
  ['Learning', () => <MemoryRouter><Learning /></MemoryRouter>, '学习资源'],
  ['Metrics', () => <Metrics />, 'Performance Metrics'],
  ['Obfuscation', () => <Obfuscation />, '流量混淆测试'],
  ['Packets', () => <Packets />, '报文查看器'],
  ['Pcap', () => <Pcap />, 'PCAP 回放'],
  ['Protocols', () => <Protocols />, '协议管理'],
  ['Retention', () => <Retention />, '数据保留'],
  ['Routing', () => <Routing />, '路由协议'],
  ['Scale', () => <Scale />, '大规模设备'],
  ['Scenarios', () => <Scenarios />, '网络场景'],
  ['Snmp', () => <Snmp />, 'SNMP 仿真'],
  ['Traffic', () => <Traffic />, 'Traffic Visualization'],
  ['Tutorial', () => <Tutorial />, 'VPN 协议教程'],
  ['Validation', () => <Validation />, '配置验证'],
  ['VendorCLI', () => <VendorCLI />, '多厂商 CLI 终端'],
  ['Voice', () => <Voice />, 'Voice Simulator'],
]

describe('feature pages smoke', () => {
  it.each(pages)('renders the %s page shell', async (_name, renderPage, expectedText) => {
    render(renderPage())
    const matches = await screen.findAllByText(expectedText)
    expect(matches.length).toBeGreaterThan(0)
  })
})
