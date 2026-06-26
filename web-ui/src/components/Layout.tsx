import { useState, useEffect } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  DashboardIcon,
  ProtocolIcon,
  ConnectionIcon,
  MetricsIcon,
  ComparisonIcon,
  FaultIcon,
  ScenarioIcon,
  AttackIcon,
  TutorialIcon,
  LearningIcon,
  PacketIcon,
  TrafficIcon,
  IoTIcon,
  DPIIcon,
  ObfuscationIcon,
  VoiceIcon,
  VendorCLIIcon,
  GlobeIcon,
  MenuIcon,
  ChevronLeftIcon,
} from './Icons'

const Layout = () => {
  const { t, i18n } = useTranslation()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [mobileOpen, setMobileOpen] = useState(false)

  const toggleLanguage = () => {
    const newLang = i18n.language === 'zh-CN' ? 'en' : 'zh-CN'
    i18n.changeLanguage(newLang)
  }

  const navItems = [
    { path: '/', label: t('nav.dashboard'), icon: DashboardIcon, group: 'main' },
    { path: '/protocols', label: t('nav.protocols'), icon: ProtocolIcon, group: 'main' },
    { path: '/connections', label: t('nav.connections'), icon: ConnectionIcon, group: 'main' },
    { path: '/metrics', label: t('nav.metrics', 'Metrics'), icon: MetricsIcon, group: 'analytics' },
    { path: '/comparison', label: t('nav.comparison'), icon: ComparisonIcon, group: 'analytics' },
    { path: '/packets', label: t('nav.packets'), icon: PacketIcon, group: 'analytics' },
    { path: '/traffic', label: t('nav.traffic', 'Traffic'), icon: TrafficIcon, group: 'analytics' },
    { path: '/scenarios', label: t('nav.scenarios', 'Scenarios'), icon: ScenarioIcon, group: 'testing' },
    { path: '/faults', label: t('nav.faults'), icon: FaultIcon, group: 'testing' },
    { path: '/attacks', label: t('nav.attacks'), icon: AttackIcon, group: 'testing' },
    { path: '/tutorials', label: t('nav.tutorials'), icon: TutorialIcon, group: 'learning' },
    { path: '/learning', label: t('nav.learning'), icon: LearningIcon, group: 'learning' },
    { path: '/iot', label: t('nav.iot', 'IoT'), icon: IoTIcon, group: 'advanced' },
    { path: '/dpi', label: t('nav.dpi', 'DPI'), icon: DPIIcon, group: 'advanced' },
    { path: '/obfuscation', label: t('nav.obfuscation', 'Obfuscation'), icon: ObfuscationIcon, group: 'advanced' },
    { path: '/voice', label: t('nav.voice', 'Voice'), icon: VoiceIcon, group: 'advanced' },
    { path: '/vendor-cli', label: t('nav.vendor-cli', 'Vendor CLI'), icon: VendorCLIIcon, group: 'advanced' },
  ]

  const groups = [
    { id: 'main', label: t('nav.groups.main', 'Main') },
    { id: 'analytics', label: t('nav.groups.analytics', 'Analytics') },
    { id: 'testing', label: t('nav.groups.testing', 'Testing') },
    { id: 'learning', label: t('nav.groups.learning', 'Learning') },
    { id: 'advanced', label: t('nav.groups.advanced', 'Advanced') },
  ]

  // Close mobile sidebar on route change
  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  const renderNavItem = (item: typeof navItems[0]) => {
    const IconComponent = item.icon
    return (
      <NavLink
        key={item.path}
        to={item.path}
        end={item.path === '/'}
        className={({ isActive }) =>
          `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 ${
            isActive
              ? 'text-primary border border-primary'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground'
          }`
        }
      >
        <IconComponent className="h-4 w-4 shrink-0" />
        <span className="truncate">{item.label}</span>
      </NavLink>
    )
  }

  const renderNavGroup = (group: typeof groups[0]) => {
    const groupItems = navItems.filter((item) => item.group === group.id)
    if (groupItems.length === 0) return null

    return (
      <div key={group.id} className="mb-4">
        {sidebarOpen && (
          <h3 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {group.label}
          </h3>
        )}
        <div className="space-y-1">
          {groupItems.map(renderNavItem)}
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Mobile Overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 lg:hidden"
          style={{ backgroundColor: 'rgba(0,0,0,0.8)' }}
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex flex-col border-r bg-card transition-all duration-300 lg:static lg:z-auto ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        } ${sidebarOpen ? 'w-64' : 'w-16'}`}
      >
        {/* Logo */}
        <div className="flex h-16 items-center justify-between border-b px-4">
          {sidebarOpen ? (
            <h1 className="text-lg font-display font-bold text-primary">
              VPN SIMULATOR
            </h1>
          ) : (
            <div className="h-8 w-8 rounded-lg bg-muted flex items-center justify-center">
              <span className="text-primary font-bold text-sm">V</span>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="hidden lg:flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <ChevronLeftIcon
              className={`h-4 w-4 transition-transform duration-300 ${
                !sidebarOpen ? 'rotate-180' : ''
              }`}
            />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-3">
          {groups.map(renderNavGroup)}
        </nav>

        {/* Footer */}
        <div className="border-t p-3">
          <button
            onClick={toggleLanguage}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <GlobeIcon className="h-4 w-4 shrink-0" />
            {sidebarOpen && (
              <span>{i18n.language === 'zh-CN' ? 'English' : '中文'}</span>
            )}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="flex h-16 items-center gap-4 border-b bg-card px-6">
          <button
            onClick={() => setMobileOpen(true)}
            className="lg:hidden h-10 w-10 flex items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <MenuIcon className="h-5 w-5" />
          </button>

          <div className="flex-1">
            <h2 className="text-lg font-semibold text-foreground">
              {navItems.find((item) => item.path === location.pathname)?.label || t('nav.dashboard')}
            </h2>
          </div>

          <div className="flex items-center gap-4">
            {/* Status Indicator */}
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-success animate-pulse" />
              <span className="text-sm text-muted-foreground">{t('status.connected')}</span>
            </div>

            {/* User Menu */}
            <div className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2">
              <span className="text-sm font-medium">Admin</span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-6 bg-background">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default Layout
