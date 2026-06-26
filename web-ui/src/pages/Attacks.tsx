import { useTranslation } from 'react-i18next'
import { useState, useEffect, useCallback, useRef } from 'react'

import { ZapIcon, UsersIcon, RefreshCwIcon, ToolIcon, ShieldIcon } from '../components/Icons'
import { api } from '../api/client'
import { Card, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Input, Textarea } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/Dialog'

interface Attack {
  id: string
  name: string
  description: string
  type: 'dos' | 'mitm' | 'replay' | 'bruteforce' | 'injection'
  target: string
  status: 'running' | 'stopped' | 'completed' | 'failed'
  startedAt?: string
  duration?: string
  packetsSent: number
  successRate: number
}

const Attacks = () => {
  const { t } = useTranslation()
  const [attacks, setAttacks] = useState<Attack[]>([])
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newAttack, setNewAttack] = useState({
    name: '',
    description: '',
    type: 'dos' as 'dos' | 'mitm' | 'replay' | 'bruteforce' | 'injection',
    target: '',
  })
  const typesRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const attackTypes = [
    { value: 'dos', label: t('attacks.types.dos'), description: t('attacks.types.dosDesc') },
    { value: 'mitm', label: t('attacks.types.mitm'), description: t('attacks.types.mitmDesc') },
    { value: 'replay', label: t('attacks.types.replay'), description: t('attacks.types.replayDesc') },
    { value: 'bruteforce', label: t('attacks.types.bruteforce'), description: t('attacks.types.bruteforceDesc') },
    { value: 'injection', label: t('attacks.types.injection'), description: t('attacks.types.injectionDesc') },
  ]

  const attackTypeOptions = attackTypes.map(type => ({
    value: type.value,
    label: type.label,
  }))

  const fetchAttacks = useCallback(async () => {
    try {
      const response = await api.getAttacks()
      const data = response.data
      if (Array.isArray(data)) {
        setAttacks(data.map((a: Record<string, unknown>) => ({
          id: a.id as string || '',
          name: a.type as string || '',
          description: '',
          type: (a.type as 'dos' | 'mitm' | 'replay' | 'bruteforce' | 'injection') || 'dos',
          target: a.target as string || '',
          status: (a.status as 'running' | 'stopped') || 'stopped',
          packetsSent: 0,
          successRate: 0,
        })))
      }
    } catch {
      setAttacks([])
    }
  }, [])

  useEffect(() => {
    fetchAttacks()
  }, [fetchAttacks])

  // GSAP animations
  useEffect(() => {
    if (typesRef.current) {
    }
    if (listRef.current) {
    }
  }, [])

  const handleCreateAttack = async () => {
    try {
      await api.startAttack({
        type: newAttack.type,
        target: newAttack.target,
        params: {},
      })
      fetchAttacks()
    } catch {
    }
    setShowCreateModal(false)
    setNewAttack({ name: '', description: '', type: 'dos', target: '' })
  }

  const handleStartAttack = async (id: string) => {
    try {
      await api.startAttack({ id })
      setAttacks(prev => prev.map(a => a.id === id ? { ...a, status: 'running' } : a))
    } catch (e) {
      console.error('Failed to start attack:', e)
    }
  }

  const handleStopAttack = async (id: string) => {
    try {
      await api.stopAttack(id)
      setAttacks(prev => prev.map(a => a.id === id ? { ...a, status: 'stopped' } : a))
    } catch (e) {
      console.error('Failed to stop attack:', e)
    }
  }

  const getAttackIcon = (type: string) => {
    switch (type) {
      case 'dos':
        return <ZapIcon className="w-8 h-8 mx-auto text-red-400" />
      case 'mitm':
        return <UsersIcon className="w-8 h-8 mx-auto text-blue-400" />
      case 'replay':
        return <RefreshCwIcon className="w-8 h-8 mx-auto text-yellow-400" />
      case 'bruteforce':
        return <ToolIcon className="w-8 h-8 mx-auto text-purple-400" />
      default:
        return <ShieldIcon className="w-8 h-8 mx-auto text-green-400" />
    }
  }

  const statusVariant = (status: string) => {
    switch (status) {
      case 'running':
        return 'success'
      case 'completed':
        return 'default'
      case 'failed':
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
          <h1 className="text-2xl font-bold">{t('attacks.title')}</h1>
          <p className="text-muted-foreground mt-1">{t('attacks.subtitle')}</p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          {t('attacks.createAttack')}
        </Button>
      </div>

      {/* Attack Types Overview */}
      <div ref={typesRef} className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {attackTypes.map((type) => (
          <Card key={type.value} variant="hover" className="p-4">
            <div className="text-center">
              <div className="mb-2">
                {getAttackIcon(type.value)}
              </div>
              <h4 className="text-sm font-medium">{type.label}</h4>
              <p className="text-xs text-muted-foreground mt-1">{type.description}</p>
            </div>
          </Card>
        ))}
      </div>

      {/* Active Attacks */}
      <Card ref={listRef}>
        <CardHeader className="border-b">
          <CardTitle>{t('attacks.attackSimulations')}</CardTitle>
        </CardHeader>
        <div className="divide-y">
          {attacks.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <p className="text-muted-foreground">{t('attacks.noAttacks')}</p>
              <p className="text-sm text-muted-foreground mt-2">{t('attacks.createFirst')}</p>
            </div>
          ) : (
            attacks.map((attack) => (
              <div key={attack.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <h4 className="font-medium">{attack.name}</h4>
                      <Badge variant={statusVariant(attack.status)}>
                        {attack.status}
                      </Badge>
                      <Badge variant="outline">
                        {attack.type}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">{attack.description}</p>
                    <div className="flex items-center space-x-6 mt-3">
                      <div className="text-sm">
                        <span className="text-muted-foreground">{t('attacks.target')}: </span>
                        <span className="font-mono">{attack.target}</span>
                      </div>
                      {attack.status === 'running' && (
                        <>
                          <div className="text-sm">
                            <span className="text-muted-foreground">{t('attacks.packets')}: </span>
                            <span className="font-mono">{attack.packetsSent.toLocaleString()}</span>
                          </div>
                          <div className="text-sm">
                            <span className="text-muted-foreground">{t('attacks.successRate')}: </span>
                            <span className="font-mono">{attack.successRate.toFixed(1)}%</span>
                          </div>
                          <div className="text-sm">
                            <span className="text-muted-foreground">{t('attacks.duration')}: </span>
                            <span className="font-mono">{attack.duration}</span>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    {attack.status === 'running' ? (
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleStopAttack(attack.id)}
                      >
                        {t('attacks.stop')}
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => handleStartAttack(attack.id)}
                        disabled={attack.status === 'completed'}
                      >
                        {t('attacks.start')}
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>

      {/* Create Attack Modal */}
      <Dialog open={showCreateModal} onClose={() => setShowCreateModal(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('attacks.createAttack')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <Input
              label={t('attacks.name')}
              value={newAttack.name}
              onChange={(e) => setNewAttack(prev => ({ ...prev, name: e.target.value }))}
              placeholder={t('attacks.namePlaceholder')}
            />
            <Textarea
              label={t('attacks.description')}
              value={newAttack.description}
              onChange={(e) => setNewAttack(prev => ({ ...prev, description: e.target.value }))}
              placeholder={t('attacks.descriptionPlaceholder')}
              rows={3}
            />
            <Select
              label={t('attacks.type')}
              options={attackTypeOptions}
              value={newAttack.type}
              onChange={(value) => setNewAttack(prev => ({ ...prev, type: value as 'dos' | 'mitm' | 'replay' | 'bruteforce' | 'injection' }))}
            />
            <Input
              label={t('attacks.target')}
              value={newAttack.target}
              onChange={(e) => setNewAttack(prev => ({ ...prev, target: e.target.value }))}
              placeholder={t('attacks.targetPlaceholder')}
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
              onClick={handleCreateAttack}
              disabled={!newAttack.name || !newAttack.target}
            >
              {t('common.create')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default Attacks
