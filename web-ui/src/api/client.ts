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
  // Health check
  healthCheck: () => apiClient.get('/health'),

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
}

export default apiClient