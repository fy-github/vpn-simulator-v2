import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Progress,
  Select,
  Skeleton,
  SkeletonText,
  Tabs,
  Textarea,
} from '../components/ui'

afterEach(cleanup)

describe('Button', () => {
  it('renders its children and fires onClick', () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>点击</Button>)
    const btn = screen.getByRole('button', { name: '点击' })
    expect(btn).toBeInTheDocument()
    fireEvent.click(btn)
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('is disabled while loading and shows a spinner', () => {
    render(<Button loading>提交</Button>)
    const btn = screen.getByRole('button', { name: '提交' })
    expect(btn).toBeDisabled()
    expect(btn.querySelector('svg')).toBeInTheDocument()
  })

  it('applies variant and size classes', () => {
    render(
      <Button variant="destructive" size="lg">
        Danger
      </Button>,
    )
    expect(screen.getByRole('button', { name: 'Danger' }).className).toContain('bg-destructive')
    expect(screen.getByRole('button', { name: 'Danger' }).className).toContain('h-11')
  })
})

describe('Badge', () => {
  it('renders children and applies variant class', () => {
    render(<Badge variant="success">在线</Badge>)
    const badge = screen.getByText('在线')
    expect(badge).toBeInTheDocument()
    expect(badge.className).toContain('bg-success')
  })
})

describe('Input / Textarea', () => {
  it('renders a label bound to the input', () => {
    render(<Input label="用户名" />)
    expect(screen.getByLabelText('用户名')).toBeInTheDocument()
  })

  it('renders error and helperText', () => {
    render(<Input label="主机" error="必填" />)
    expect(screen.getByText('必填')).toBeInTheDocument()
    render(<Input label="端口" helperText="1-65535" />)
    expect(screen.getByText('1-65535')).toBeInTheDocument()
  })

  it('renders a textarea', () => {
    render(<Textarea label="描述" />)
    expect(screen.getByLabelText('描述').tagName).toBe('TEXTAREA')
  })
})

describe('Select', () => {
  it('renders options and fires onChange with the value', () => {
    const onChange = vi.fn()
    render(
      <Select
        label="协议"
        options={[
          { value: 'udp', label: 'UDP' },
          { value: 'tcp', label: 'TCP' },
        ]}
        onChange={onChange}
      />,
    )
    const select = screen.getByLabelText('协议')
    expect(screen.getByRole('option', { name: 'UDP' })).toBeInTheDocument()
    fireEvent.change(select, { target: { value: 'tcp' } })
    expect(onChange).toHaveBeenCalledWith('tcp')
  })

  it('renders a placeholder option', () => {
    render(<Select placeholder="请选择" options={[{ value: 'a', label: 'A' }]} />)
    expect(screen.getByRole('option', { name: '请选择' })).toBeDisabled()
  })
})

describe('Card', () => {
  it('renders header/title/description/content/footer', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>标题</CardTitle>
          <CardDescription>描述</CardDescription>
        </CardHeader>
        <CardContent>内容</CardContent>
        <CardFooter>底部</CardFooter>
      </Card>,
    )
    expect(screen.getByText('标题')).toBeInTheDocument()
    expect(screen.getByText('描述')).toBeInTheDocument()
    expect(screen.getByText('内容')).toBeInTheDocument()
    expect(screen.getByText('底部')).toBeInTheDocument()
  })
})

describe('Dialog', () => {
  it('renders nothing when closed and content when open', () => {
    const { rerender } = render(
      <Dialog open={false} onClose={vi.fn()}>
        <DialogContent>body</DialogContent>
      </Dialog>,
    )
    expect(screen.queryByText('body')).not.toBeInTheDocument()
    rerender(
      <Dialog open onClose={vi.fn()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>标题</DialogTitle>
            <DialogDescription>说明</DialogDescription>
          </DialogHeader>
          <DialogFooter>底部</DialogFooter>
        </DialogContent>
      </Dialog>,
    )
    expect(screen.getByText('标题')).toBeInTheDocument()
    expect(screen.getByText('说明')).toBeInTheDocument()
  })

  it('closes on Escape keydown', () => {
    const onClose = vi.fn()
    render(
      <Dialog open onClose={onClose}>
        <DialogContent>body</DialogContent>
      </Dialog>,
    )
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})

describe('Tabs', () => {
  it('renders tabs and switches active content', () => {
    const onChange = vi.fn()
    render(
      <Tabs
        defaultTab="a"
        onChange={onChange}
        tabs={[
          { id: 'a', label: 'A 标签', content: <span>A 内容</span> },
          { id: 'b', label: 'B 标签', content: <span>B 内容</span> },
        ]}
      />,
    )
    expect(screen.getByText('A 内容')).toBeInTheDocument()
    expect(screen.queryByText('B 内容')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'B 标签' }))
    expect(screen.getByText('B 内容')).toBeInTheDocument()
    expect(screen.queryByText('A 内容')).not.toBeInTheDocument()
    expect(onChange).toHaveBeenCalledWith('b')
  })
})

describe('Progress', () => {
  it('exposes progressbar semantics and clamps percentage', () => {
    render(<Progress value={50} max={100} />)
    const bar = screen.getByRole('progressbar')
    expect(bar).toHaveAttribute('aria-valuenow', '50')
    render(<Progress value={200} max={100} showLabel />)
    expect(screen.getByText('100%')).toBeInTheDocument()
  })
})

describe('Skeleton', () => {
  it('renders Skeleton and SkeletonText with line count', () => {
    const { container } = render(
      <>
        <Skeleton data-testid="sk" width={120} height={24} variant="circular" />
        <SkeletonText lines={2} />
      </>,
    )
    expect(screen.getByTestId('sk')).toBeInTheDocument()
    expect(container.querySelectorAll('.space-y-2 > div')).toHaveLength(2)
  })
})
