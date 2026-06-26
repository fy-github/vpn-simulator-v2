import { useTranslation } from 'react-i18next'
import { useState, useEffect, useCallback, useRef } from 'react'

import { GlobeIcon, ClipboardIcon, KeyIcon, LockIcon } from '../components/Icons'
import { api } from '../api/client'
import { Card, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Input, Textarea } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/Dialog'

interface Fault {
  id: string
  name: string
  description: string
  type: 'network' | 'protocol' | 'authentication' | 'encryption'
  severity: 'low' | 'medium' | 'high' | 'critical'
  status: 'active' | 'inactive'
  target: string
  parameters: Record<string, unknown>
}

const Faults = () => {
  const { t } = useTranslation()
  const [faults, setFaults] = useState<Fault[]>([])
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newFault, setNewFault] = useState({
    name: '',
    description: '',
    type: 'network' as 'network' | 'protocol' | 'authentication' | 'encryption',
    severity: 'medium' as 'low' | 'medium' | 'high' | 'critical',
    target: '',
    parameters: {},
  })
  const typesRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const faultTypes = [
    { value: 'network', label: t('faults.types.network') },
    { value: 'protocol', label: t('faults.types.protocol') },
    { value: 'authentication', label: t('faults.types.authentication') },
    { value: 'encryption', label: t('faults.types.encryption') },
  ]

  const severityLevels = [
    { value: 'low', label: t('faults.severity.low'), variant: 'default' as const },
    { value: 'medium', label: t('faults.severity.medium'), variant: 'warning' as const },
    { value: 'high', label: t('faults.severity.high'), variant: 'warning' as const },
    { value: 'critical', label: t('faults.severity.critical'), variant: 'destructive' as const },
  ]

  const faultTypeOptions = faultTypes.map(type => ({
    value: type.value,
    label: type.label,
  }))

  const severityOptions = severityLevels.map(level => ({
    value: level.value,
    label: level.label,
  }))

  const fetchFaults = useCallback(async () => {
    try {
      const response = await api.getFaults()
      const data = response.data
      if (Array.isArray(data)) {
        setFaults(data.map((f: Record<string, unknown>) => ({
          id: f.id as string || '',
          name: f.type as string || '',
          description: '',
          type: (f.type as 'network' | 'protocol' | 'authentication' | 'encryption') || 'network',
          severity: 'medium',
          status: (f.active as boolean) ? 'active' : 'inactive',
          target: f.target as string || '',
          parameters: f.params as Record<string, unknown> || {},
        })))
      }
    } catch {
      setFaults([])
    }
  }, [])

  useEffect(() => {
    fetchFaults()
  }, [fetchFaults])

  // GSAP animations
  useEffect(() => {
    if (typesRef.current) {
    }
    if (listRef.current) {
    }
  }, [])

  const handleCreateFault = async () => {
    try {
      await api.injectFault({
        type: newFault.type,
        params: newFault.parameters,
        target: newFault.target,
      })
      fetchFaults()
    } catch {
    }
    setShowCreateModal(false)
    setNewFault({
      name: '',
      description: '',
      type: 'network',
      severity: 'medium',
      target: '',
      parameters: {},
    })
  }

  const handleInjectFault = async (id: string) => {
    try {
      await api.injectFault({ id })
      setFaults(prev => prev.map(fault => fault.id === id ? { ...fault, status: 'active' } : fault))
    } catch (e) {
      console.error('Failed to inject fault:', e)
    }
  }

  const handleClearFault = async (id: string) => {
    try {
      await api.clearFault(id)
      setFaults(prev => prev.filter(fault => fault.id !== id))
    } catch (e) {
      console.error('Failed to clear fault:', e)
    }
  }

  const getFaultIcon = (type: string) => {
    switch (type) {
      case 'network':
        return <GlobeIcon className="w-6 h-6 text-blue-400" />
      case 'protocol':
        return <ClipboardIcon className="w-6 h-6 text-green-400" />
      case 'authentication':
        return <KeyIcon className="w-6 h-6 text-yellow-400" />
      default:
        return <LockIcon className="w-6 h-6 text-red-400" />
    }
  }

  const getSeverityVariant = (severity: string) => {
    switch (severity) {
      case 'low':
        return 'default'
      case 'medium':
        return 'warning'
      case 'high':
        return 'warning'
      case 'critical':
        return 'destructive'
      default:
        return 'secondary'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t('faults.title')}</h1>
          <p className="text-muted-foreground mt-1">{t('faults.subtitle')}</p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          {t('faults.createFault')}
        </Button>
      </div>

      {/* Fault Types Overview */}
      <div ref={typesRef} className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {faultTypes.map((type) => (
          <Card key={type.value} variant="hover" className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{type.label}</p>
                <p className="text-2xl font-bold">
                  {faults.filter(f => f.type === type.value).length}
                </p>
              </div>
              <div className="p-3 bg-muted rounded-lg">
                {getFaultIcon(type.value)}
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Faults List */}
      <Card ref={listRef}>
        <CardHeader className="border-b">
          <CardTitle>{t('faults.faultDefinitions')}</CardTitle>
        </CardHeader>
        <div className="divide-y">
          {faults.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <p className="text-muted-foreground">{t('faults.noFaults')}</p>
              <p className="text-sm text-muted-foreground mt-2">{t('faults.createFirst')}</p>
            </div>
          ) : (
            faults.map((fault) => (
              <div key={fault.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <h4 className="font-medium">{fault.name}</h4>
                      <Badge variant={getSeverityVariant(fault.severity)}>
                        {fault.severity}
                      </Badge>
                      <Badge variant="outline">
                        {fault.type}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">{fault.description}</p>
                    <div className="flex items-center space-x-4 mt-2 text-sm text-muted-foreground">
                      <span>{t('faults.target')}: {fault.target}</span>
                      <span className="text-muted-foreground">|</span>
                      <span>
                        {t('faults.status')}: 
                        <span className={fault.status === 'active' ? 'text-success ml-1' : 'text-muted-foreground ml-1'}>
                          {fault.status}
                        </span>
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    {fault.status === 'active' ? (
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleClearFault(fault.id)}
                      >
                        {t('faults.clear')}
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => handleInjectFault(fault.id)}
                      >
                        {t('faults.inject')}
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>

      {/* Create Fault Modal */}
      <Dialog open={showCreateModal} onClose={() => setShowCreateModal(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('faults.createFault')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <Input
              label={t('faults.name')}
              value={newFault.name}
              onChange={(e) => setNewFault(prev => ({ ...prev, name: e.target.value }))}
              placeholder={t('faults.namePlaceholder')}
            />
            <Textarea
              label={t('faults.description')}
              value={newFault.description}
              onChange={(e) => setNewFault(prev => ({ ...prev, description: e.target.value }))}
              placeholder={t('faults.descriptionPlaceholder')}
              rows={3}
            />
            <div className="grid grid-cols-2 gap-4">
              <Select
                label={t('faults.type')}
                options={faultTypeOptions}
                value={newFault.type}
                onChange={(value) => setNewFault(prev => ({ ...prev, type: value as 'network' | 'protocol' | 'authentication' | 'encryption' }))}
              />
              <Select
                label={t('faults.severityLabel')}
                options={severityOptions}
                value={newFault.severity}
                onChange={(value) => setNewFault(prev => ({ ...prev, severity: value as 'low' | 'medium' | 'high' | 'critical' }))}
              />
            </div>
            <Input
              label={t('faults.target')}
              value={newFault.target}
              onChange={(e) => setNewFault(prev => ({ ...prev, target: e.target.value }))}
              placeholder={t('faults.targetPlaceholder')}
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowCreateModal(false)}
            >
              {t('common.cancel')}
            </Button>
            <Button
              onClick={handleCreateFault}
              disabled={!newFault.name || !newFault.target}
            >
              {t('common.create')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default Faults
