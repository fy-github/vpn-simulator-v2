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
import DHCP from './pages/DHCP'
import Impairment from './pages/Impairment'
import Validation from './pages/Validation'
import Pcap from './pages/Pcap'
import Routing from './pages/Routing'
import Snmp from './pages/Snmp'
import Grafana from './pages/Grafana'
import Scale from './pages/Scale'
import C2 from './pages/C2'
import Retention from './pages/Retention'

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
        <Route path="dhcp" element={<DHCP />} />
        <Route path="impairment" element={<Impairment />} />
        <Route path="validation" element={<Validation />} />
        <Route path="pcap" element={<Pcap />} />
        <Route path="routing" element={<Routing />} />
        <Route path="snmp" element={<Snmp />} />
        <Route path="grafana" element={<Grafana />} />
        <Route path="scale" element={<Scale />} />
        <Route path="c2" element={<C2 />} />
        <Route path="retention" element={<Retention />} />
      </Route>
    </Routes>
  )
}

export default App
