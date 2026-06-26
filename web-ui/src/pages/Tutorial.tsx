import { useTranslation } from 'react-i18next'
import { useEffect, useState, useRef } from 'react'

import TutorialStep from '../components/TutorialStep'
import { TutorialIcon, RefreshCwIcon, StarIcon, EditIcon, ClockIcon, ArrowLeftIcon, ArrowRightIcon } from '../components/Icons'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Progress } from '../components/ui/Progress'

interface TutorialSummary {
  id: string
  name: string
  protocol: string
  description: string
  difficulty: string
  estimated_time: number
  total_steps: number
}

interface TutorialStepInfo {
  title: string
  description: string
  packet_info: string
  rfc_reference: string
  expected_state: string
  hint: string
}

interface TutorialDetail {
  id: string
  name: string
  protocol: string
  description: string
  difficulty: string
  estimated_time: number
  total_steps: number
  steps: TutorialStepInfo[]
}

interface TutorialSession {
  tutorial_id: string
  current_step: number
  total_steps: number
  is_completed: boolean
  started_at: string
  completed_at: string | null
  current_step_info: TutorialStepInfo | null
  message: string
}

const Tutorial = () => {
  const { t } = useTranslation()
  const [tutorials, setTutorials] = useState<TutorialSummary[]>([])
  const [selectedTutorial, setSelectedTutorial] = useState<TutorialDetail | null>(null)
  const [session, setSession] = useState<TutorialSession | null>(null)
  const [loading, setLoading] = useState(true)
  const gridRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchTutorials()
  }, [])

  // GSAP animations
  useEffect(() => {
    if (!loading && gridRef.current) {
    }
  }, [loading])

  const fetchTutorials = async () => {
    try {
      const response = await fetch('/api/v1/tutorials')
      if (response.ok) {
        const data = await response.json()
        setTutorials(data)
      }
    } catch (error) {
      console.error('Failed to fetch tutorials:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchTutorialDetail = async (tutorialId: string) => {
    try {
      const response = await fetch(`/api/v1/tutorials/${tutorialId}`)
      if (response.ok) {
        const data = await response.json()
        setSelectedTutorial(data)
      }
    } catch (error) {
      console.error('Failed to fetch tutorial detail:', error)
    }
  }

  const startTutorial = async (tutorialId: string) => {
    try {
      const response = await fetch(`/api/v1/tutorials/${tutorialId}/start`, {
        method: 'POST',
      })
      if (response.ok) {
        const data = await response.json()
        setSession(data)
        await fetchTutorialDetail(tutorialId)
      }
    } catch (error) {
      console.error('Failed to start tutorial:', error)
    }
  }

  const nextStep = async () => {
    if (!session) return
    try {
      const response = await fetch(`/api/v1/tutorials/${session.tutorial_id}/next`, {
        method: 'POST',
      })
      if (response.ok) {
        const data = await response.json()
        setSession(data)
      }
    } catch (error) {
      console.error('Failed to advance step:', error)
    }
  }

  const prevStep = async () => {
    if (!session) return
    try {
      const response = await fetch(`/api/v1/tutorials/${session.tutorial_id}/prev`, {
        method: 'POST',
      })
      if (response.ok) {
        const data = await response.json()
        setSession(data)
      }
    } catch (error) {
      console.error('Failed to go back:', error)
    }
  }

  const resetTutorial = async () => {
    if (!session) return
    try {
      const response = await fetch(`/api/v1/tutorials/${session.tutorial_id}/reset`, {
        method: 'POST',
      })
      if (response.ok) {
        const data = await response.json()
        setSession(data)
      }
    } catch (error) {
      console.error('Failed to reset tutorial:', error)
    }
  }

  const backToList = () => {
    setSelectedTutorial(null)
    setSession(null)
  }

  const getDifficultyVariant = (difficulty: string) => {
    switch (difficulty) {
      case 'beginner':
        return 'success'
      case 'intermediate':
        return 'warning'
      case 'advanced':
        return 'destructive'
      default:
        return 'secondary'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (selectedTutorial && session) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <Button
              variant="ghost"
              onClick={backToList}
              className="mb-2"
            >
              <ArrowLeftIcon className="w-4 h-4 mr-2" />
              {t('tutorial.backToList', '返回教程列表')}
            </Button>
            <h1 className="text-2xl font-bold">{selectedTutorial.name}</h1>
            <p className="text-muted-foreground mt-1">{selectedTutorial.description}</p>
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant={getDifficultyVariant(selectedTutorial.difficulty)}>
              {selectedTutorial.difficulty}
            </Badge>
            <Badge variant="outline">
              <ClockIcon className="w-3 h-3 mr-1" />
              {selectedTutorial.estimated_time} {t('tutorial.minutes', '分钟')}
            </Badge>
          </div>
        </div>

        {/* Progress Bar */}
        <Card>
          <CardContent className="p-4">
            <Progress
              value={session.current_step + 1}
              max={session.total_steps}
              showLabel
            />
          </CardContent>
        </Card>

        {/* Current Step */}
        {session.current_step_info && (
          <TutorialStep
            step={session.current_step_info}
            stepNumber={session.current_step}
            totalSteps={session.total_steps}
            isActive={true}
          />
        )}

        {/* Navigation Buttons */}
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={prevStep}
            disabled={session.current_step === 0}
          >
            <ArrowLeftIcon className="w-4 h-4 mr-2" />
            {t('tutorial.prev', '上一步')}
          </Button>

          <Button
            variant="outline"
            onClick={resetTutorial}
          >
            <RefreshCwIcon className="w-4 h-4 mr-2" />
            {t('tutorial.reset', '重置')}
          </Button>

          <Button
            onClick={nextStep}
            disabled={session.is_completed}
            variant={session.is_completed ? 'outline' : 'default'}
          >
            {session.is_completed ? t('tutorial.completed', '已完成') : t('tutorial.next', '下一步')}
            {!session.is_completed && <ArrowRightIcon className="w-4 h-4 ml-2" />}
          </Button>
        </div>

        {/* Completion Message */}
        {session.is_completed && (
          <Card className="border-success bg-muted">
            <CardContent className="p-6 text-center">
              <StarIcon className="w-12 h-12 mx-auto text-success" />
              <h3 className="text-xl font-bold text-success mt-3">
                {t('tutorial.congratulations', '恭喜完成教程！')}
              </h3>
              <p className="text-muted-foreground mt-2">
                {t('tutorial.completedMessage', '您已成功完成本教程的所有步骤。')}
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">
          {t('tutorial.title', 'VPN 协议教程')}
        </h1>
        <p className="text-muted-foreground mt-1">
          {t('tutorial.subtitle', '通过分步引导学习 VPN 协议的握手流程')}
        </p>
      </div>

      {/* Tutorial List */}
      {tutorials.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <TutorialIcon className="w-12 h-12 mx-auto text-muted-foreground" />
            <h3 className="text-lg font-semibold mt-4">
              {t('tutorial.noTutorials', '暂无教程')}
            </h3>
            <p className="text-muted-foreground mt-2">
              {t('tutorial.noTutorialsDesc', '教程配置文件尚未添加。')}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div ref={gridRef} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {tutorials.map((tutorial) => (
            <Card
              key={tutorial.id}
              variant="hover"
              className="cursor-pointer"
              onClick={() => startTutorial(tutorial.id)}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <CardTitle className="text-lg">{tutorial.name}</CardTitle>
                  <Badge variant={getDifficultyVariant(tutorial.difficulty)}>
                    {tutorial.difficulty}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                  {tutorial.description}
                </p>
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <Badge variant="outline">
                    {tutorial.protocol.toUpperCase()}
                  </Badge>
                  <div className="flex items-center space-x-3">
                    <span className="flex items-center">
                      <EditIcon className="w-4 h-4 mr-1" /> {tutorial.total_steps} {t('tutorial.steps', '步')}
                    </span>
                    <span className="flex items-center">
                      <ClockIcon className="w-4 h-4 mr-1" /> {tutorial.estimated_time} {t('tutorial.minutes', '分钟')}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

export default Tutorial
