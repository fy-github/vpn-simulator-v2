# VPN Simulator v2 — 前端测试覆盖计划 v22

> 现状：前端 25 页 + 30+ 组件 + 90+ 方法 API client + 双语言 i18n，仅 1 个 smoke 测试（4 用例）。
> 目标：在不引入新依赖的前提下，用现有 vitest + @testing-library 补齐有意义的前端测试。

## 一、现状与工具

- 工具已就绪：vitest 4 + jsdom + @testing-library/react + jest-dom + i18next + axios。
- `vitest.config.ts`：jsdom 环境，setupFiles=`./src/test/setup.ts`（当前只 import i18n）。
- 现有 `src/__tests__/smoke.test.tsx`：`vi.mock('../api/client')` 用 Proxy 让所有方法返回
  `{ data: [] }`，覆盖 Retention/Snmp/C2/Routing 4 页的标题渲染。
- 页面标题：多数页用 `<h1 className="text-2xl font-bold">` + `t('key', '默认值')`；部分页
  无 h1（Dashboard/IoT/Packets 包组件）；Learning 用 `useParams`（需 MemoryRouter）。

## 二、分阶段任务

### P1 — setup + UI 组件库测试
- `src/test/setup.ts` 追加 `@testing-library/jest-dom/vitest`（启用 toBeInTheDocument 等）。
- 新增 `src/__tests__/ui.test.tsx`：Button（variant/size/loading/onClick）、Badge（variant）、
  Input/Textarea（label/error/helperText）、Select（options/onChange/placeholder/error）、
  Card（header/footer/title/description）、Dialog、Tabs、Progress、Skeleton。

### P2 — API client 测试
- `src/__tests__/client.test.ts`：`vi.mock('axios')`，断言各方法映射到正确的
  URL / HTTP method / params / body（协议、连接、故障、攻击、校验、PCAP、DPI、DHCP 等代表方法）。

### P3 — i18n 测试
- `src/__tests__/i18n.test.ts`：en 与 zh-CN 键集合一致；`t()` 返回中文/英文值；fallback。

### P4 — 页面 smoke 测试（覆盖全部 25 页）
- 扩展 `smoke.test.tsx`：用统一 mock 渲染所有页面并断言标题/稳定文案渲染；Learning 用
  MemoryRouter 包裹；Dashboard 断言「总连接数」、IoT 断言「IoT 设备模拟器」等稳定文案。

## 三、验收

- `cd web-ui && npx tsc --noEmit`、`npx eslint .`、`npm test`（vitest run）全绿。
- 前端测试用例数从 4 提升到 60+。
- 每阶段独立提交并推送到 `origin/main`。

## 四、完成状态

全部阶段（P1–P4）已实现、测试并推送到 `origin/main`。前端测试从 4 个 smoke 用例
提升到 **61 个**（4 个测试文件）：UI 组件库 15、API client 14、i18n 5、页面 smoke 27。

| 阶段 | 说明 |
|------|------|
| P1 | `setup.ts` 追加 `@testing-library/jest-dom/vitest`；`ui.test.tsx` 覆盖 Button/Badge/Input/Textarea/Select/Card/Dialog/Tabs/Progress/Skeleton |
| P2 | `client.test.ts`：`vi.mock('axios')`，断言 14 组方法 → URL/method/params/body 映射 |
| P3 | `i18n.test.ts`：en/zh-CN 键集合一致 + 中/英解析 + 插值 + fallback |
| P4 | `smoke.test.tsx`：27 个页面 shell 渲染（统一 mock api/fetch/react-chartjs-2） |

技术要点：
- jsdom 无 canvas → `vi.mock('react-chartjs-2')` 桩掉 Line/Bar/Doughnut/Radar。
- 页面数据形状各异（`data.packets`、`stats.by_type`、`data.codecs`、数值 `.toFixed`、
  函数调用）→ 用「可调用 Proxy 空值」（未知属性递归返回自身，含 valueOf/toString/
  toFixed/数组方法/Symbol.toPrimitive 兜底）统一 mock，避免 undefined 崩溃。
- Learning 用 `useNavigate` → 包 `MemoryRouter`；Validation 标题重复出现 → `findAllByText`。

