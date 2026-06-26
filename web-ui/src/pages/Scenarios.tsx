import { useTranslation } from 'react-i18next'
import { useState, useEffect, useRef } from 'react'

import { api } from '../api/client'
import ScenarioSelector from '../components/ScenarioSelector'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'

interface Scenario {
  id: string
  name: string
  description: string
  icon: string
  category: string
  faults: Record<string, Record<string, number>>
  active: boolean
}

const Scenarios = () => {
  const { t } = useTranslation()
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [loading, setLoading] = useState(true)
  const [applying, setApplying] = useState<string | null>(null)
  const [filter, setFilter] = useState<string>('all')
  const gridRef = useRef<HTMLDivElement>(null)
  const tableRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchScenarios()
  }, [])

  // GSAP animations
  useEffect(() => {
    if (!loading) {
      if (gridRef.current) {
      }
      if (tableRef.current) {
      }
    }
  }, [loading])

  const fetchScenarios = async () => {
    try {
      setLoading(true)
      const response = await api.getScenarios()
      setScenarios(response.data)
    } catch (err) {
      console.error('Failed to fetch scenarios:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleApply = async (id: string) => {
    try {
      setApplying(id)
      await api.applyScenario(id)
      await fetchScenarios()
    } catch (err) {
      console.error('Failed to apply scenario:', err)
    } finally {
      setApplying(null)
    }
  }

  const handleRemove = async (id: string) => {
    try {
      setApplying(id)
      await api.removeScenario(id)
      await fetchScenarios()
    } catch (err) {
      console.error('Failed to remove scenario:', err)
    } finally {
      setApplying(null)
    }
  }

  const categories = [
    { value: 'all', label: t('scenarios.categories.all') },
    { value: 'mobile', label: t('scenarios.categories.mobile') },
    { value: 'satellite', label: t('scenarios.categories.satellite') },
    { value: 'wifi', label: t('scenarios.categories.wifi') },
    { value: 'wired', label: t('scenarios.categories.wired') },
  ]

  const filteredScenarios = filter === 'all'
    ? scenarios
    : scenarios.filter(s => s.category === filter)

  const activeScenario = scenarios.find(s => s.active)

  const formatBandwidth = (kbps: number) => {
    if (kbps >= 1000000) return `${kbps / 1000000}Gbps`
    if (kbps >= 1000) return `${kbps / 1000}Mbps`
    return `${kbps}Kbps`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">{t('scenarios.title')}</h1>
        <p className="text-muted-foreground mt-1">{t('scenarios.subtitle')}</p>
      </div>

      {/* Active Scenario Banner */}
      {activeScenario && (
        <Card className="border-l-4 border-success bg-muted">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-success">{t('scenarios.activeScenario')}</p>
                <p className="text-lg font-semibold">{activeScenario.name}</p>
                <p className="text-sm text-muted-foreground">{activeScenario.description}</p>
              </div>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => handleRemove(activeScenario.id)}
                disabled={applying !== null}
                loading={applying === activeScenario.id}
              >
                {t('scenarios.removeScenario')}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Category Filter */}
      <div className="flex flex-wrap gap-2">
        {categories.map((cat) => (
          <Button
            key={cat.value}
            variant={filter === cat.value ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter(cat.value)}
          >
            {cat.label}
          </Button>
        ))}
      </div>

      {/* Scenarios Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : (
        <div ref={gridRef} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredScenarios.map((scenario) => (
            <ScenarioSelector
              key={scenario.id}
              scenario={scenario}
              onApply={handleApply}
              onRemove={handleRemove}
              applying={applying === scenario.id}
            />
          ))}
        </div>
      )}

      {!loading && filteredScenarios.length === 0 && (
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-muted-foreground">{t('scenarios.noScenarios')}</p>
          </CardContent>
        </Card>
      )}

      {/* Quick Reference */}
      <Card ref={tableRef}>
        <CardHeader>
          <CardTitle>{t('scenarios.quickReference')}</CardTitle>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-4 text-muted-foreground font-medium">{t('scenarios.table.scenario')}</th>
                <th className="text-left py-2 px-4 text-muted-foreground font-medium">{t('scenarios.table.latency')}</th>
                <th className="text-left py-2 px-4 text-muted-foreground font-medium">{t('scenarios.table.jitter')}</th>
                <th className="text-left py-2 px-4 text-muted-foreground font-medium">{t('scenarios.table.loss')}</th>
                <th className="text-left py-2 px-4 text-muted-foreground font-medium">{t('scenarios.table.bandwidth')}</th>
              </tr>
            </thead>
            <tbody>
              {scenarios.map((s) => (
                <tr key={s.id} className="border-b hover:bg-muted transition-colors">
                  <td className="py-2 px-4">{s.name}</td>
                  <td className="py-2 px-4 text-muted-foreground">{s.faults.latency?.delay_ms ?? '-'}ms</td>
                  <td className="py-2 px-4 text-muted-foreground">{s.faults.latency?.jitter_ms ?? '-'}ms</td>
                  <td className="py-2 px-4 text-muted-foreground">
                    {s.faults.packet_loss?.loss_rate != null
                      ? `${(s.faults.packet_loss.loss_rate * 100).toFixed(1)}%`
                      : '-'}
                  </td>
                  <td className="py-2 px-4 text-muted-foreground">
                    {s.faults.bandwidth?.bandwidth_kbps != null
                      ? formatBandwidth(s.faults.bandwidth.bandwidth_kbps)
                      : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}

export default Scenarios
