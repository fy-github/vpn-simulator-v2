import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import '../i18n'

import C2 from '../pages/C2'
import Retention from '../pages/Retention'
import Routing from '../pages/Routing'
import Snmp from '../pages/Snmp'

// Mock the API client: every method resolves to an empty list so pages render
// their shell without hitting a real backend. getRetentionStatus returns a
// shape-compatible object.
vi.mock('../api/client', () => ({
  api: new Proxy(
    {},
    {
      get: (_target, prop) => {
        if (prop === 'getRetentionStatus') {
          return vi.fn(() => Promise.resolve({ data: { packets: 0, state_transitions: 0 } }))
        }
        return vi.fn(() => Promise.resolve({ data: [] }))
      },
    },
  ),
}))

afterEach(cleanup)

describe('feature pages smoke', () => {
  it('renders the Retention page heading', async () => {
    render(<Retention />)
    expect(await screen.findByText('数据保留')).toBeDefined()
  })

  it('renders the SNMP page heading', async () => {
    render(<Snmp />)
    expect(await screen.findByText('SNMP 仿真')).toBeDefined()
  })

  it('renders the C2 page heading', async () => {
    render(<C2 />)
    expect(await screen.findByText('C2 场景')).toBeDefined()
  })

  it('renders the Routing page heading', async () => {
    render(<Routing />)
    expect(await screen.findByText('路由协议')).toBeDefined()
  })
})
