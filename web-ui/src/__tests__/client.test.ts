import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
  axiosGet: vi.fn(),
}))

vi.mock('axios', () => {
  const instance = {
    get: mocks.get,
    post: mocks.post,
    delete: mocks.delete,
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  }
  return {
    default: {
      create: vi.fn(() => instance),
      get: mocks.axiosGet,
    },
  }
})

import { api } from '../api/client'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('api client method → URL/method mapping', () => {
  it('healthCheck hits the root /health via axios.get', () => {
    api.healthCheck()
    expect(mocks.axiosGet).toHaveBeenCalledWith('/health')
  })

  it('protocols', () => {
    api.getProtocols()
    api.getProtocolStatus('udp')
    api.startProtocol('udp', { port: 1194 })
    api.stopProtocol('udp')
    expect(mocks.get).toHaveBeenCalledWith('/protocols')
    expect(mocks.get).toHaveBeenCalledWith('/protocols/udp/status')
    expect(mocks.post).toHaveBeenCalledWith('/protocols/udp/start', { port: 1194 })
    expect(mocks.post).toHaveBeenCalledWith('/protocols/udp/stop')
  })

  it('connections', () => {
    api.getConnections()
    api.getConnection('42')
    api.disconnectConnection('42')
    expect(mocks.get).toHaveBeenCalledWith('/connections')
    expect(mocks.get).toHaveBeenCalledWith('/connections/42')
    expect(mocks.delete).toHaveBeenCalledWith('/connections/42')
  })

  it('faults and attacks', () => {
    api.injectFault({ name: 'x' })
    api.clearFault('1')
    api.startAttack({ type: 'dos' })
    api.stopAttack('2')
    expect(mocks.post).toHaveBeenCalledWith('/faults', { name: 'x' })
    expect(mocks.delete).toHaveBeenCalledWith('/faults/1')
    expect(mocks.post).toHaveBeenCalledWith('/attacks', { type: 'dos' })
    expect(mocks.delete).toHaveBeenCalledWith('/attacks/2')
  })

  it('stats and logs forward params', () => {
    api.getStats()
    api.getLogs({ level: 'info' })
    expect(mocks.get).toHaveBeenCalledWith('/stats')
    expect(mocks.get).toHaveBeenCalledWith('/logs', { params: { level: 'info' } })
  })

  it('comparison passes query params', () => {
    api.compareProtocols('udp', 'tcp')
    expect(mocks.get).toHaveBeenCalledWith('/compare', {
      params: { protocol1: 'udp', protocol2: 'tcp' },
    })
  })

  it('packets: search, statistics, export blob', () => {
    api.searchPackets('GET', { protocol: 'tcp' })
    expect(mocks.get).toHaveBeenCalledWith('/packets/search', {
      params: { query: 'GET', protocol: 'tcp' },
    })
    api.getPacketStatistics()
    expect(mocks.get).toHaveBeenCalledWith('/packets/statistics')
    api.exportPcap({ limit: 10 })
    expect(mocks.get).toHaveBeenCalledWith('/packets/export/pcap', {
      params: { limit: 10 },
      responseType: 'blob',
    })
  })

  it('validation: single and batch', () => {
    api.validateConfig('udp', { port: 0 })
    expect(mocks.post).toHaveBeenCalledWith('/validation/validate', {
      protocol: 'udp',
      config: { port: 0 },
    })
    api.batchValidate(['udp', 'tcp'])
    expect(mocks.post).toHaveBeenCalledWith('/validation/batch', {
      protocols: ['udp', 'tcp'],
      configs: undefined,
    })
  })

  it('dhcp status forwards the after param', () => {
    api.getDhcpStatus(100)
    expect(mocks.get).toHaveBeenCalledWith('/dhcp/status', { params: { after: 100 } })
  })

  it('snmp get/walk forward oid and version', () => {
    api.snmpGet('dev1', '1.3.6.1', 'v2c')
    expect(mocks.get).toHaveBeenCalledWith('/snmp/devices/dev1/get', {
      params: { oid: '1.3.6.1', version: 'v2c' },
    })
    api.snmpWalk('dev1', '1.3.6.1', 'v2c')
    expect(mocks.get).toHaveBeenCalledWith('/snmp/devices/dev1/walk', {
      params: { oid: '1.3.6.1', version: 'v2c' },
    })
  })

  it('scale poll posts body', () => {
    api.runScalePoll(50, 4)
    expect(mocks.post).toHaveBeenCalledWith('/scale/poll', { count: 50, concurrency: 4 })
  })

  it('c2 simulate posts to the scenario id', () => {
    api.simulateC2('sc1')
    expect(mocks.post).toHaveBeenCalledWith('/c2/scenarios/sc1/simulate')
  })

  it('retention cleanup posts overrides', () => {
    api.runRetentionCleanup({ packets: true })
    expect(mocks.post).toHaveBeenCalledWith('/retention/cleanup', { packets: true })
  })

  it('impairment preset apply URL-encodes the name', () => {
    api.applyImpairmentPreset('loss 5%')
    expect(mocks.post).toHaveBeenCalledWith('/impairments/presets/loss%205%25/apply')
  })
})
