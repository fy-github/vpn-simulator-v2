import { useTranslation } from 'react-i18next'
import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

import RFCReference from '../components/RFCReference'
import { FileIcon, HelpCircleIcon, NavigationIcon, SearchIcon } from '../components/Icons'
import { Card, CardContent } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Input } from '../components/ui/Input'
import { Tabs } from '../components/ui/Tabs'

interface RFCReferenceItem {
  protocol: string
  protocol_name: string
  number: string
  title: string
  url: string
  description: string
  published: string
  status: string
  type: string
}

interface ProtocolRFCData {
  protocol: string
  name: string
  full_name: string
  rfcs: Array<{
    number: string
    title: string
    url: string
    description: string
    published: string
    status: string
  }>
  references: Array<{
    title: string
    url: string
    description: string
  }>
}

interface FAQCategory {
  id: string
  name: string
  icon: string
  question_count: number
}

interface FAQItem {
  category_id: string
  category_name: string
  category_icon: string
  id: string
  question: string
  answer: string
  tags: string[]
}

interface LearningPath {
  id: string
  name: string
  description: string
  icon: string
  difficulty: string
  estimated_hours: number
  target_audience: string
  protocol_count: number
}

const Learning = () => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('rfc')
  const [_rfcReferences, setRfcReferences] = useState<RFCReferenceItem[]>([])
  const [protocolRFCData, setProtocolRFCData] = useState<Record<string, ProtocolRFCData>>({})
  const [faqCategories, setFaqCategories] = useState<FAQCategory[]>([])
  const [faqItems, setFaqItems] = useState<FAQItem[]>([])
  const [learningPaths, setLearningPaths] = useState<LearningPath[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchData()
  }, [])

  // GSAP animations
  useEffect(() => {
    if (!loading && contentRef.current) {
    }
  }, [loading, activeTab])

  const fetchData = async () => {
    try {
      await Promise.all([
        fetchRFCReferences(),
        fetchFAQCategories(),
        fetchFAQItems(),
        fetchLearningPaths(),
      ])
    } catch (error) {
      console.error('Failed to fetch learning resources:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchRFCReferences = async () => {
    try {
      const response = await fetch('/api/v1/learning/rfc')
      if (response.ok) {
        const data = await response.json()
        setRfcReferences(data)

        const grouped: Record<string, ProtocolRFCData> = {}
        for (const item of data) {
          if (!grouped[item.protocol]) {
            grouped[item.protocol] = {
              protocol: item.protocol,
              name: item.protocol_name,
              full_name: '',
              rfcs: [],
              references: [],
            }
          }
          if (item.type === 'rfc') {
            grouped[item.protocol].rfcs.push({
              number: item.number,
              title: item.title,
              url: item.url,
              description: item.description,
              published: item.published,
              status: item.status,
            })
          } else {
            grouped[item.protocol].references.push({
              title: item.title,
              url: item.url,
              description: item.description,
            })
          }
        }
        setProtocolRFCData(grouped)
      }
    } catch (error) {
      console.error('Failed to fetch RFC references:', error)
    }
  }

  const fetchFAQCategories = async () => {
    try {
      const response = await fetch('/api/v1/learning/faq/categories')
      if (response.ok) {
        const data = await response.json()
        setFaqCategories(data)
      }
    } catch (error) {
      console.error('Failed to fetch FAQ categories:', error)
    }
  }

  const fetchFAQItems = async () => {
    try {
      const url = selectedCategory
        ? `/api/v1/learning/faq?category=${selectedCategory}`
        : '/api/v1/learning/faq'
      const response = await fetch(url)
      if (response.ok) {
        const data = await response.json()
        setFaqItems(data)
      }
    } catch (error) {
      console.error('Failed to fetch FAQ items:', error)
    }
  }

  const fetchLearningPaths = async () => {
    try {
      const response = await fetch('/api/v1/learning/paths')
      if (response.ok) {
        const data = await response.json()
        setLearningPaths(data)
      }
    } catch (error) {
      console.error('Failed to fetch learning paths:', error)
    }
  }

  useEffect(() => {
    fetchFAQItems()
  }, [selectedCategory])

  const filteredFAQ = faqItems.filter((item) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      item.question.toLowerCase().includes(query) ||
      item.answer.toLowerCase().includes(query) ||
      item.tags.some((tag) => tag.toLowerCase().includes(query))
    )
  })

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

  const getDifficultyLabel = (difficulty: string) => {
    switch (difficulty) {
      case 'beginner':
        return t('learning.difficulty.beginner', '初学者')
      case 'intermediate':
        return t('learning.difficulty.intermediate', '进阶')
      case 'advanced':
        return t('learning.difficulty.advanced', '高级')
      default:
        return difficulty
    }
  }

  const tabs = [
    {
      id: 'rfc',
      label: t('learning.tabs.rfc', 'RFC 文档'),
      icon: <FileIcon className="w-4 h-4" />,
      content: (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {Object.entries(protocolRFCData).map(([protocol, data]) => (
            <RFCReference
              key={protocol}
              protocol={protocol}
              protocolName={data.name}
              fullName={data.full_name}
              rfcs={data.rfcs}
              references={data.references}
            />
          ))}
        </div>
      ),
    },
    {
      id: 'faq',
      label: t('learning.tabs.faq', '常见问题'),
      icon: <HelpCircleIcon className="w-4 h-4" />,
      content: (
        <div className="space-y-6">
          {/* Search */}
          <div className="relative">
            <SearchIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('learning.faq.searchPlaceholder', '搜索问题...')}
              className="pl-10"
            />
          </div>

          {/* Categories */}
          <div className="flex flex-wrap gap-2">
            <Button
              variant={selectedCategory === null ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(null)}
            >
              {t('learning.faq.allCategories', '全部')}
            </Button>
            {faqCategories.map((category) => (
              <Button
                key={category.id}
                variant={selectedCategory === category.id ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedCategory(category.id)}
              >
                {category.icon} {category.name}
                <span className="ml-1 text-xs opacity-75">({category.question_count})</span>
              </Button>
            ))}
          </div>

          {/* FAQ Items */}
          <div className="space-y-4">
            {filteredFAQ.map((item) => (
              <Card key={item.id}>
                <CardContent className="p-6">
                  <div className="flex items-start space-x-3">
                    <span className="text-xl">{item.category_icon}</span>
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold mb-2">
                        {item.question}
                      </h3>
                      <div className="prose prose-invert max-w-none">
                        <p className="text-muted-foreground whitespace-pre-wrap">{item.answer}</p>
                      </div>
                      <div className="flex flex-wrap gap-2 mt-4">
                        {item.tags.map((tag, index) => (
                          <Badge key={index} variant="outline">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ),
    },
    {
      id: 'paths',
      label: t('learning.tabs.paths', '学习路径'),
      icon: <NavigationIcon className="w-4 h-4" />,
      content: (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {learningPaths.map((path) => (
            <Card key={path.id} variant="hover">
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <span className="text-3xl">{path.icon}</span>
                    <div>
                      <h3 className="text-lg font-semibold">{path.name}</h3>
                      <p className="text-sm text-muted-foreground">{path.description}</p>
                    </div>
                  </div>
                  <Badge variant={getDifficultyVariant(path.difficulty)}>
                    {getDifficultyLabel(path.difficulty)}
                  </Badge>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      {t('learning.paths.targetAudience', '适合人群')}
                    </span>
                    <span>{path.target_audience}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      {t('learning.paths.protocols', '包含协议')}
                    </span>
                    <span>{path.protocol_count} 个</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      {t('learning.paths.estimatedTime', '预计时长')}
                    </span>
                    <span>{path.estimated_hours} 小时</span>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t">
                  <Button className="w-full" onClick={() => navigate('/tutorials')}>
                    {t('learning.paths.startLearning', '开始学习')}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ),
    },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">
          {t('learning.title', '学习资源')}
        </h1>
        <p className="text-muted-foreground mt-1">
          {t('learning.subtitle', 'RFC 文档、常见问题和学习路径')}
        </p>
      </div>

      {/* Tabs */}
      <Tabs
        tabs={tabs}
        defaultTab="rfc"
        onChange={setActiveTab}
      />
    </div>
  )
}

export default Learning
