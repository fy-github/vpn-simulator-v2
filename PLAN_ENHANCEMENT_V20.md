# VPN Simulator v2 — OpenVPN 真实 TLS 控制信道计划 v20

> 承接 V19（PPP LCP/IPCP 收尾）。本计划把 OpenVPN 控制信道从「Hard Reset +
> HKDF 数据密钥」升级为**真实 TLS 握手 + TLS 加密信道内交换数据密钥 + PUSH 下发**，
> 替换 `data_channel.py` 里「用 HKDF 模拟 TLS keying-material export」的简化。

## 一、背景与现状

- `openvpn_handshake.py` 当前只做 Hard Reset（P_CONTROL_HARD_RESET_CLIENT_V2/SERVER_V2，
  真实 `--tls-auth` HMAC），随后直接 `START_TLS` 结束，未做真实 TLS 握手。
- `data_channel.py::derive_data_key()` 用 HKDF-SHA256 从 `--tls-auth` 预共享密钥 +
  双方 session_id 派生数据密钥，明示「不实现完整 TLS 握手」。
- 状态机已定义完整流程（TLS_HANDSHAKE → TLS_ESTABLISHED → PUSH_REQUEST_SENT →
  CONNECTED），事件 `TLS_COMPLETE` / `SEND_PUSH_REQUEST` / `RECEIVE_PUSH_REPLY` 已就位但未被驱动。

## 二、技术要点

- **TLS over UDP**：OpenVPN 控制信道在 Hard Reset 后承载 TLS 记录（P_CONTROL_V1 载荷）。
  用 Python `ssl` 的 `MemoryBIO` + `SSLObject`（`wrap_bio`）在无 socket 字节流上驱动
  真实 TLS 1.3 握手，复用 `sstp/tls.py::create_tls_contexts()` 的自签名证书。
- **数据密钥**：真实 OpenVPN 用 TLS keying-material exporter（标签
  `EXPORTER-network-tunnel`）；本环境 Python ssl 未暴露 `export_keying_material`
  （OpenSSL 4.x 移除），故改为在**真实 TLS 加密信道内**交换随机 32 字节数据密钥，
  数据密钥由 TLS 会话保护、不再是可由 `--tls-auth` 预共享密钥直接推导。
- **PUSH 阶段**：TLS 建立后客户端发 PUSH_REQUEST（P_CONTROL_V1 载荷），服务端回
  PUSH_REPLY（含 ifconfig 配置），驱动状态机到 CONNECTED。

## 三、分阶段任务

### P1 — TLS-over-控制信道助手

新增 `plugins/protocols/openvpn/tls.py`：`TLSBIO`（MemoryBIO + SSLObject，非阻塞
`do_handshake`/`feed_incoming`/`take_outgoing`/`write`/`read`）+ `create_tls_contexts`。
单元测试验证 TLS 1.3 握手往返。

### P2 — 接入握手服务

`openvpn_handshake.py`：Hard Reset 后跑真实 TLS 握手（`initiate()` 客户端 /
`respond()` 服务端），TLS 加密信道内交换数据密钥，随后 PUSH_REQUEST/PUSH_REPLY，
返回 `(client_session_id, server_session_id, data_key)`；服务端返回
`(client_session_id, data_key)`。驱动状态机到 CONNECTED。移除 `derive_data_key`。

### P3 — 接线 + 测试 + 文档

- `validation.py`：用握手返回的真实数据密钥（不再调用 `derive_data_key`）。
- `tests/integration/test_openvpn_handshake.py` / `test_openvpn_transport_flow.py` 同步。
- `README.md`：测试数/特性说明同步。

## 四、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- OpenVPN 控制信道走真实 TLS 1.3 握手 + 状态机到 CONNECTED + 数据密钥 TLS 信道内交换。
- 每功能独立提交并推送到 `origin/main`。
