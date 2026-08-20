import { afterEach, describe, expect, it } from 'vitest'

import i18n from '../i18n'
import en from '../locales/en.json'
import zhCN from '../locales/zh-CN.json'

function flattenKeys(obj: Record<string, unknown>, prefix = ''): string[] {
  const keys: string[] = []
  for (const [k, v] of Object.entries(obj)) {
    const full = prefix ? `${prefix}.${k}` : k
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      keys.push(...flattenKeys(v as Record<string, unknown>, full))
    } else {
      keys.push(full)
    }
  }
  return keys
}

afterEach(async () => {
  await i18n.changeLanguage('zh-CN')
})

describe('i18n locales', () => {
  it('en and zh-CN expose the same key set', () => {
    const enKeys = flattenKeys(en).sort()
    const zhKeys = flattenKeys(zhCN).sort()
    expect(enKeys).toEqual(zhKeys)
  })

  it('resolves Chinese translations by default (lng=zh-CN)', () => {
    expect(i18n.t('nav.dashboard')).toBe('仪表盘')
    expect(i18n.t('attacks.title')).toBe('攻击管理')
  })

  it('resolves English translations after switching language', async () => {
    await i18n.changeLanguage('en')
    expect(i18n.t('nav.dashboard')).toBe('Dashboard')
    expect(i18n.t('attacks.title')).toBe('Attack Management')
  })

  it('falls back to the provided default when a key is missing', () => {
    const missing = i18n.t('nav.nonexistent', 'Fallback Label')
    expect(missing).toBe('Fallback Label')
  })

  it('interpolates values', () => {
    const result = i18n.t('__interpolation_test__', '运行时间 {{value}}', { value: '00:01' })
    expect(result).toBe('运行时间 00:01')
  })
})
