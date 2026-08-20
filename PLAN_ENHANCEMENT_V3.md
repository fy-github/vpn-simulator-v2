# VPN Simulator v2 — 功能前端化 + 收尾计划 v3

> 本计划承接 `PLAN_ENHANCEMENT_V2.md`（Phase 0/1 与 F1–F8 已完成后端实现），
> 目标：把 F1–F8 的 9 组后端能力**暴露到 Web UI**，补齐契约测试、文档、损伤
> 引擎剩余类型、前端测试基建与 OpenVPN 真实报文试点，形成完整可演示产品。

## 一、背景与现状

后端已具备 9 组 API（`/impairments` `/validation` `/pcap` `/snmp` `/routing`
`/grafana` `/scale` `/c2` `/retention`），但 Web UI（18 页面）完全没有对应页面，
`api/client.ts` 也未接这些端点。本计划以「前端化」为主，其余为收尾。

## 二、范围总览（P0–P3）

| 阶段 | 主题 | 交付 |
|------|------|------|
| P0-A | 前端第一批 | Impairment / Validation / PCAP / Routing 四页 |
| P0-B | 前端第二批 | SNMP / Grafana / Scale / C2 / Retention 五页 |
| P1 | 契约测试 + 文档 | 9 组路由的 HTTP 集成测试 + README 同步 |
| P2 | 损伤补全 + 前端测试 | corrupt/reorder/duplicate/bandwidth 接入真实报文；vitest + CI |
| P3 | OpenVPN 试点 + 覆盖率门禁 | OpenVPN 控制信道 framing + `--tls-auth` HMAC；`--cov-fail-under` |

## 三、前端架构约定（P0 统一遵守）

每个新功能按固定模式落地，共 6 处改动：

1. `web-ui/src/api/client.ts` — 追加该功能的 `api.*` 方法。
2. `web-ui/src/components/Icons.tsx` — 追加一个 SVG 图标。
3. `web-ui/src/components/Layout.tsx` — `navItems` 追加 `{path,label,icon,group}`。
4. `web-ui/src/App.tsx` — `<Route path=... element=...>`。
5. `web-ui/src/locales/en.json` + `zh-CN.json` — 追加 `nav.*` 与页面文案 key。
6. `web-ui/src/pages/X.tsx` — 页面壳（标题 + 功能组件）；功能逻辑放
   `web-ui/src/components/XSimulator.tsx`（复用 `Card/Button/Badge/Tabs/Select/Input/
   Progress/Skeleton`，图表用 `react-chartjs-2`）。

验收：`cd web-ui && npx tsc --noEmit` 与 `npx eslint .` 全绿；页面在
http://localhost:3000 可操作。

## 四、分阶段任务清单

### P0-A 前端第一批（教学/可视化价值最高）

| # | 页面 | API 端点 | 功能要点 |
|---|------|----------|----------|
| A1 | Impairment | `GET/POST /impairments`, `POST /impairments/{id}/start\|stop`, `GET /impairments/presets`, `GET /impairments/{id}/timeline`, `GET /impairments/status` | 预设选择、创建时间变化损伤、启动/停止、时间线折线图（5 种变化类型） |
| A2 | Validation | `POST /validation/validate`, `GET /validation/results`, `/history`, `/batch` | 6 协议配置验证表单、7 步结果展示（pass/fail/skip）、延迟+吞吐指标、历史列表 |
| A3 | PCAP | `POST /pcap/upload`, `GET /pcap/files`, `POST /pcap/replay`, `GET /pcap/status/{id}`, `/stats/{id}` | 文件上传、回放（速度 0.5–10x + 协议过滤）、状态轮询、统计 |
| A4 | Routing | `GET /routing/routers`, `GET /routing/{id}/neighbors`, `POST /routing/{id}/neighbors/{n}/establish`, `GET /routing/{id}/routes` | 拓扑列表、邻居状态推进（OSPF full / BGP established）、路由表 |

### P0-B 前端第二批

| # | 页面 | API 端点 | 功能要点 |
|---|------|----------|----------|
| B1 | SNMP | `GET /snmp/devices`, `/oids`, `/devices/{id}`, `/devices/{id}/get`, `/devices/{id}/walk` | 设备列表（12 类型）、OID 查询/遍历（v2c/v3 选择） |
| B2 | Grafana | `GET /grafana/dashboards`, `/dashboards/{name}`, `/alert-rules` | 内置仪表板列表、JSON 预览、告警规则展示 |
| B3 | Scale | `GET /scale/devices`, `/stats`, `POST /scale/poll`, `/persist`, `GET /scale/snapshots` | 3 万设备分页浏览、聚合统计、并发巡检（连接池）、快照持久化 |
| B4 | C2 | `GET /c2/scenarios`, `/scenarios/{id}`, `/scenarios/{id}/detection`, `POST /scenarios/{id}/simulate`, `GET /c2/ethics` | 6 场景卡片、模拟步骤、检测特征（IOC）、伦理声明 |
| B5 | Retention | `GET /retention/status`, `POST /retention/cleanup` | 行数展示、保留策略清理（带参数覆盖） |

### P1 契约测试 + 文档

- 新增 `tests/integration/test_api_enhancements.py`（或按功能拆分），用
  `httpx.AsyncClient` + ASGITransport 直连 `app`，覆盖 9 组新路由的关键路径
  （正常 + 404/400 错误路径），不依赖真实网络。
- `README.md`：测试数改 1140→最新；API 端点表补 9 组；特性表补 F1–F8。

### P2 损伤补全 + 前端测试

- `core/impairment_engine.py` 扩展出站决策模型（drop / delay / corrupt /
  duplicate / reorder / bandwidth），`core/packetio.py` 的 `sendto` 落地：
  - corrupt：翻转报文字节；duplicate：重复发送；reorder：单报文 hold-back 缓冲
    交换相邻顺序；bandwidth：令牌桶限速。
  - 保持 `delay_ms/jitter_ms/loss_rate` 现有语义与测试不回归。
- `web-ui` 引入 `vitest`，加 3–5 个组件冒烟测试；`package.json` 增 `test` 脚本；
  `.github/workflows/ci.yml` frontend job 增 `npm test`。

### P3 OpenVPN 试点 + 覆盖率门禁

- OpenVPN 控制信道：`P_CONTROL_HARD_RESET_CLIENT_V2/SERVER_V2` 报文 framing +
  `--tls-auth` 静态密钥 HMAC-SHA256 生成/校验（标准库 `hmac`/`hashlib`），驱动
  OpenVPN 插件状态机推进一次握手状态跳转；TLS 会话载荷为 stub（同 WireGuard
  「控制面/握手层」边界，不做数据面）。
- CI backend job 增 `--cov-fail-under=78`（实测当前覆盖率 80%，取略低的安全阈值）。

## 五、执行顺序与提交粒度

P0-A（A1→A2→A3→A4）→ P0-B（B1→B2→B3→B4→B5）→ P1 → P2 → P3。
每项独立提交并推送到 `origin/main`；每步保持 `tsc/eslint/pytest/mypy/ruff/black` 全绿。

## 六、验收总则

- 前端：9 个新页面可在 http://localhost:3000 操作；`tsc --noEmit`、`eslint` 全绿。
- 后端：全部 pytest 通过（含新增契约测试与损伤/OpenVPN 测试）；mypy/ruff/black 全绿。
- CI：backend（ruff/black/mypy/pytest+cov）、frontend（lint+build+test）全绿。
- 文档：README 与计划文档与实际一致。

## 七、完成状态

全部阶段（P0-A → P0-B → P1 → P2 → P3）已实现、测试并推送到 `origin/main`。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P0-A | `1b430a4` `f2a1e99` `630d2fc` `0bc5251` | Impairment / Validation / PCAP / Routing 四页 |
| P0-B | `3c6835f` `9ba318d` `d0b2960` `0364c64` `86830d1` | SNMP / Grafana / Scale / C2 / Retention 五页 |
| P1 | `bbf6694` | 9 组路由 HTTP 集成测试（40 条）+ README 同步 |
| P2 | `ef16558` `e853a90` | 损伤引擎 corrupt/reorder/duplicate/bandwidth + vitest 冒烟测试 + CI |
| P3 | `05556f5` | OpenVPN 控制信道 framing + `--tls-auth` HMAC + 覆盖率门禁 |

最终指标：后端 1197 tests 通过、80% 覆盖率（`--cov-fail-under=78`）；
前端 4 个组件冒烟测试；`tsc --noEmit`、`eslint`、`mypy`、`ruff`、`black` 全绿。
