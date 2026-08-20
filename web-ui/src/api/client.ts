import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // You can add auth tokens here if needed
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // Handle common errors
    if (error.response) {
      switch (error.response.status) {
        case 401:
          // Handle unauthorized
          console.error('Unauthorized access')
          break
        case 403:
          // Handle forbidden
          console.error('Forbidden access')
          break
        case 404:
          // Handle not found
          console.error('Resource not found')
          break
        case 500:
          // Handle server error
          console.error('Internal server error')
          break
      }
    } else if (error.request) {
      // Network error
      console.error('Network error:', error.message)
    }
    return Promise.reject(error)
  }
)

// API methods
export const api = {
  // Health check (backend exposes it at the root, outside /api/v1)
  healthCheck: () => axios.get('/health'),

  // Protocols
  getProtocols: () => apiClient.get('/protocols'),
  getProtocolStatus: (protocol: string) => apiClient.get(`/protocols/${protocol}/status`),
  startProtocol: (protocol: string, data?: Record<string, unknown>) => apiClient.post(`/protocols/${protocol}/start`, data || {}),
  stopProtocol: (protocol: string) => apiClient.post(`/protocols/${protocol}/stop`),

  // Connections
  getConnections: () => apiClient.get('/connections'),
  getConnection: (id: string) => apiClient.get(`/connections/${id}`),
  disconnectConnection: (id: string) => apiClient.delete(`/connections/${id}`),

  // Faults
  getFaults: () => apiClient.get('/faults'),
  injectFault: (fault: Record<string, unknown>) => apiClient.post('/faults', fault),
  clearFault: (id: string) => apiClient.delete(`/faults/${id}`),

  // Attacks
  getAttacks: () => apiClient.get('/attacks'),
  startAttack: (attack: Record<string, unknown>) => apiClient.post('/attacks', attack),
  stopAttack: (id: string) => apiClient.delete(`/attacks/${id}`),

  // Stats
  getStats: () => apiClient.get('/stats'),

  // Logs
  getLogs: (params?: Record<string, unknown>) => apiClient.get('/logs', { params }),

  // Comparison
  getComparisonProtocols: () => apiClient.get('/compare/protocols'),
  compareProtocols: (protocol1: string, protocol2: string) =>
    apiClient.get('/compare', { params: { protocol1, protocol2 } }),

  // Packets
  getPackets: (params?: Record<string, unknown>) => apiClient.get('/packets', { params }),
  getPacket: (id: string) => apiClient.get(`/packets/${id}`),
  searchPackets: (query: string, params?: Record<string, unknown>) =>
    apiClient.get('/packets/search', { params: { query, ...params } }),
  getPacketStatistics: () => apiClient.get('/packets/statistics'),
  getPacketProtocols: () => apiClient.get('/packets/protocols'),
  generateSamplePackets: () => apiClient.post('/packets/samples'),
  clearPackets: () => apiClient.delete('/packets'),
  exportPcap: (params?: Record<string, unknown>) =>
    apiClient.get('/packets/export/pcap', { params, responseType: 'blob' }),

  // Scenarios
  getScenarios: (params?: Record<string, unknown>) => apiClient.get('/scenarios', { params }),
  getScenario: (id: string) => apiClient.get(`/scenarios/${id}`),
  applyScenario: (id: string) => apiClient.post(`/scenarios/${id}/apply`),
  removeScenario: (id: string) => apiClient.delete(`/scenarios/${id}/remove`),

  // Traffic
  startTrafficCapture: (protocols?: string[]) =>
    apiClient.post('/traffic/capture', { protocols }),
  stopTrafficCapture: () => apiClient.post('/traffic/stop'),
  getTrafficStatistics: () => apiClient.get('/traffic/statistics'),
  getTrafficPackets: (limit?: number) =>
    apiClient.get('/traffic/packets', { params: { limit } }),
  getTrafficStatus: () => apiClient.get('/traffic/status'),

  // DPI (Deep Packet Inspection)
  getDpiProtocols: () => apiClient.get('/dpi/protocols'),
  getDpiStatistics: () => apiClient.get('/dpi/statistics'),
  analyzePacket: (data: Record<string, unknown>) => apiClient.post('/dpi/analyze', data),
  getDpiClassification: () => apiClient.get('/dpi/classification'),
  getDpiDistribution: () => apiClient.get('/dpi/distribution'),
  getDpiAnomalies: (limit?: number) => apiClient.get('/dpi/anomalies', { params: { limit } }),
  getDpiResults: (limit?: number) => apiClient.get('/dpi/results', { params: { limit } }),
  generateDpiSamples: (count?: number) => apiClient.post(`/dpi/samples?count=${count || 50}`),
  clearDpiData: () => apiClient.delete('/dpi'),

  getObfuscationTechniques: () => apiClient.get('/obfuscation/techniques'),
  runObfuscationTest: (data: Record<string, unknown>) => apiClient.post('/obfuscation/test', data),
  getObfuscationResults: (limit?: number) => apiClient.get('/obfuscation/results', { params: { limit } }),
  getObfuscationComparison: () => apiClient.get('/obfuscation/comparison'),
  clearObfuscationData: () => apiClient.delete('/obfuscation'),

  // DHCP
  startDhcp: (data: Record<string, unknown>) => apiClient.post('/dhcp/start', data),
  stopDhcp: () => apiClient.post('/dhcp/stop'),
  releaseDhcp: (data?: Record<string, unknown>) => apiClient.post('/dhcp/release', data || {}),
  getDhcpStatus: (after?: number) => apiClient.get('/dhcp/status', { params: { after } }),
  getDhcpLeases: () => apiClient.get('/dhcp/leases'),

  // Impairments (F1)
  getImpairmentPresets: () => apiClient.get('/impairments/presets'),
  applyImpairmentPreset: (name: string) =>
    apiClient.post(`/impairments/presets/${encodeURIComponent(name)}/apply`),
  getImpairments: () => apiClient.get('/impairments'),
  createImpairment: (data: Record<string, unknown>) => apiClient.post('/impairments', data),
  startImpairment: (id: string) => apiClient.post(`/impairments/${id}/start`),
  stopImpairment: (id: string) => apiClient.post(`/impairments/${id}/stop`),
  getImpairmentStatus: (id: string) => apiClient.get(`/impairments/${id}/status`),
  getImpairmentTimeline: (id: string, samples = 60) =>
    apiClient.get(`/impairments/${id}/timeline`, { params: { samples } }),
  removeImpairment: (id: string) => apiClient.delete(`/impairments/${id}`),

  // Validation (F2)
  validateConfig: (protocol: string, config: Record<string, unknown>) =>
    apiClient.post('/validation/validate', { protocol, config }),
  getValidationResult: (id: string) => apiClient.get(`/validation/results/${id}`),
  getValidationHistory: (protocol?: string, limit = 50) =>
    apiClient.get('/validation/history', { params: { protocol, limit } }),
  batchValidate: (
    protocols?: string[],
    configs?: Record<string, Record<string, unknown>>,
  ) => apiClient.post('/validation/batch', { protocols, configs }),

  // PCAP (F3)
  uploadPcap: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/pcap/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  getPcapFiles: () => apiClient.get('/pcap/files'),
  startPcapReplay: (fileId: string, speed: number, protocolFilter?: string) =>
    apiClient.post('/pcap/replay', {
      file_id: fileId,
      speed,
      protocol_filter: protocolFilter || null,
    }),
  getPcapStatus: (sessionId: string) => apiClient.get(`/pcap/status/${sessionId}`),
  stopPcapReplay: (sessionId: string) => apiClient.post(`/pcap/stop/${sessionId}`),
  getPcapStats: (fileId: string) => apiClient.get(`/pcap/stats/${fileId}`),

  // Routing (F5)
  getRouters: () => apiClient.get('/routing/routers'),
  getRoutingNeighbors: (routerId: string, protocol?: string) =>
    apiClient.get(`/routing/${routerId}/neighbors`, { params: { protocol } }),
  establishNeighbor: (routerId: string, neighborId: string, protocol: string) =>
    apiClient.post(`/routing/${routerId}/neighbors/${neighborId}/establish`, null, {
      params: { protocol },
    }),
  getRoutingTable: (routerId: string) => apiClient.get(`/routing/${routerId}/routes`),
}

export default apiClient