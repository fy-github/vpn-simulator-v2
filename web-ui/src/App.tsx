import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Protocols from './pages/Protocols'
import Connections from './pages/Connections'
import Faults from './pages/Faults'
import Attacks from './pages/Attacks'
import Comparison from './pages/Comparison'
import Tutorial from './pages/Tutorial'
import Learning from './pages/Learning'
import Packets from './pages/Packets'
import Metrics from './pages/Metrics'
import Scenarios from './pages/Scenarios'
import Traffic from './pages/Traffic'
import IoT from './pages/IoT'
import DPI from './pages/DPI'
import Voice from './pages/Voice'
import Obfuscation from './pages/Obfuscation'
import VendorCLI from './pages/VendorCLI'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="protocols" element={<Protocols />} />
        <Route path="connections" element={<Connections />} />
        <Route path="faults" element={<Faults />} />
        <Route path="comparison" element={<Comparison />} />
        <Route path="attacks" element={<Attacks />} />
        <Route path="tutorials" element={<Tutorial />} />
        <Route path="learning" element={<Learning />} />
        <Route path="packets" element={<Packets />} />
        <Route path="metrics" element={<Metrics />} />
        <Route path="scenarios" element={<Scenarios />} />
        <Route path="traffic" element={<Traffic />} />
        <Route path="iot" element={<IoT />} />
        <Route path="dpi" element={<DPI />} />
        <Route path="voice" element={<Voice />} />
        <Route path="obfuscation" element={<Obfuscation />} />
        <Route path="vendor-cli" element={<VendorCLI />} />
      </Route>
    </Routes>
  )
}

export default App